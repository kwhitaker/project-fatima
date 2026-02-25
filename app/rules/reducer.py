"""Pure rules engine reducer.

apply_intent(state, intent, card_lookup, rng) -> GameState

All game logic flows through here. Randomness flows through the explicit rng
argument (seeded Random instance) — never global random.*
"""

from dataclasses import dataclass
from random import Random

from app.models.cards import CardDefinition
from app.models.game import BoardCell, GameState
from app.rules.captures import resolve_captures
from app.rules.errors import CardNotInHandError, OccupiedCellError, WrongPlayerTurnError


@dataclass
class PlacementIntent:
    player_index: int
    card_key: str
    cell_index: int


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

    # --- Mists roll ---
    placed_card = card_lookup[intent.card_key]
    placed_owner = intent.player_index

    mists_modifier = 0
    if rng is not None:
        roll = rng.randint(1, 6)
        mists_modifier = mists_modifier_from_roll(roll)

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
        new_players = list(state.players)
        new_players[intent.player_index] = player.model_copy(update={"hand": new_hand})
        updates["players"] = new_players
        updates["current_player_index"] = (intent.player_index + 1) % 2

    return state.model_copy(update=updates)
