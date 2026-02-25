"""Pure rules engine reducer.

apply_intent(state, intent, card_lookup, rng) -> GameState

All game logic flows through here. Randomness flows through the explicit rng
argument (seeded Random instance) — never global random.*
"""

from dataclasses import dataclass, field
from random import Random

from app.models.cards import CardDefinition
from app.models.game import Archetype, BoardCell, GameState
from app.rules.archetypes import apply_skulker_boost, rotate_card_once
from app.rules.captures import resolve_captures
from app.rules.errors import (
    ArchetypeAlreadyUsedError,
    ArchetypeNotAvailableError,
    ArchetypePowerArgumentError,
    CardNotInHandError,
    OccupiedCellError,
    WrongPlayerTurnError,
)


@dataclass
class PlacementIntent:
    player_index: int
    card_key: str
    cell_index: int
    use_archetype: bool = field(default=False)
    skulker_boost_side: str | None = field(default=None)
    presence_boost_direction: str | None = field(default=None)


def mists_modifier_from_roll(roll: int) -> int:
    """Map a 1d6 Mists roll to a comparison modifier.

    1 (Fog)  → -1 (all comparisons this placement reduced by 1)
    6 (Omen) → +1 (all comparisons this placement increased by 1)
    2-5      →  0 (no effect)
    """
    if roll == 1:
        return -1
    if roll == 6:
        return 1
    return 0


def apply_intent(
    state: GameState,
    intent: PlacementIntent,
    card_lookup: dict[str, CardDefinition],
    rng: Random | None = None,
) -> GameState:
    """Apply a placement and return the next GameState.

    Validates turn order, hand contents, and cell availability when the game
    has players set up (len(state.players) > 0). Occupied-cell checks are
    always enforced.

    If rng is provided, rolls 1d6 for the Mists modifier before resolving
    captures. Otherwise the modifier defaults to 0 (no Mists effect).
    """
    # --- Validation ---
    if state.players:
        if state.current_player_index != intent.player_index:
            raise WrongPlayerTurnError(
                f"It is player {state.current_player_index}'s turn, "
                f"not player {intent.player_index}'s"
            )
        player = state.players[intent.player_index]
        if intent.card_key not in player.hand:
            raise CardNotInHandError(
                f"Card {intent.card_key!r} is not in player {intent.player_index}'s hand"
            )

    if state.board[intent.cell_index] is not None:
        raise OccupiedCellError(f"Cell {intent.cell_index} is already occupied")

    # --- Archetype power dispatch ---
    placed_card = card_lookup[intent.card_key]
    placed_owner = intent.player_index
    archetype_activated = False
    caster_reroll = False
    devout_negate_fog = False
    presence_direction_boost: str | None = None

    if intent.use_archetype and state.players:
        player = state.players[intent.player_index]
        if player.archetype_used:
            raise ArchetypeAlreadyUsedError(
                f"Player {intent.player_index} has already used their archetype power"
            )
        if player.archetype == Archetype.MARTIAL:
            placed_card = rotate_card_once(placed_card)
            archetype_activated = True
        elif player.archetype == Archetype.SKULKER:
            if intent.skulker_boost_side not in {"n", "e", "s", "w"}:
                raise ArchetypePowerArgumentError(
                    f"Skulker boost requires skulker_boost_side in {{n,e,s,w}}, "
                    f"got {intent.skulker_boost_side!r}"
                )
            placed_card = apply_skulker_boost(placed_card, intent.skulker_boost_side)
            archetype_activated = True
        elif player.archetype == Archetype.CASTER:
            caster_reroll = True
            archetype_activated = True
        elif player.archetype == Archetype.DEVOUT:
            devout_negate_fog = True
            archetype_activated = True
        elif player.archetype == Archetype.PRESENCE:
            if intent.presence_boost_direction not in {"n", "e", "s", "w"}:
                raise ArchetypePowerArgumentError(
                    f"Presence boost requires presence_boost_direction in {{n,e,s,w}}, "
                    f"got {intent.presence_boost_direction!r}"
                )
            presence_direction_boost = intent.presence_boost_direction
            archetype_activated = True
        else:
            raise ArchetypeNotAvailableError(
                f"Player {intent.player_index} has archetype {player.archetype!r}, "
                "which has no active placement power implemented"
            )

    # --- Mists roll ---
    mists_modifier = 0
    if rng is not None:
        roll = rng.randint(1, 6)
        if caster_reroll:
            roll = rng.randint(1, 6)  # second result is used
        mists_modifier = mists_modifier_from_roll(roll)
        if devout_negate_fog and mists_modifier == -1:
            mists_modifier = 0  # Devout treats Fog as no effect

    # --- Board update ---
    new_board: list[BoardCell | None] = list(state.board)
    new_board[intent.cell_index] = BoardCell(card_key=intent.card_key, owner=placed_owner)

    new_board = resolve_captures(
        new_board,
        intent.cell_index,
        placed_card,
        placed_owner,
        card_lookup,
        mists_modifier=mists_modifier,
        presence_direction=presence_direction_boost,
    )

    # --- Build state delta ---
    updates: dict[str, object] = {
        "board": new_board,
        "state_version": state.state_version + 1,
    }

    if state.players:
        player = state.players[intent.player_index]
        new_hand = list(player.hand)
        new_hand.remove(intent.card_key)
        player_updates: dict[str, object] = {"hand": new_hand}
        if archetype_activated:
            player_updates["archetype_used"] = True
        new_players = list(state.players)
        new_players[intent.player_index] = player.model_copy(update=player_updates)
        updates["players"] = new_players
        updates["current_player_index"] = (intent.player_index + 1) % 2

    return state.model_copy(update=updates)
