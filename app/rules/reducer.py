"""Pure rules engine reducer.

apply_intent(state, intent, card_lookup, rng) -> GameState

All game logic flows through here. Randomness flows through the explicit rng
argument (seeded Random instance) — never global random.*
"""

from dataclasses import dataclass, field
from random import Random
from typing import NamedTuple

from app.models.cards import CardDefinition
from app.models.game import Archetype, BoardCell, GameResult, GameState, GameStatus, LastMoveInfo, PlayerState
from app.rules.archetypes import apply_skulker_boost, rotate_card_ccw, rotate_card_once
from app.rules.board import get_adjacent_indices
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
    intimidate_target_cell: int | None = field(default=None)
    martial_rotation_direction: str | None = field(default=None)


def mists_modifier_from_roll(roll: int) -> int:
    """Map a 1d6 Mists roll to a comparison modifier.

    1 (Fog)  → -2 (all comparisons this placement reduced by 2)
    6 (Omen) → +2 (all comparisons this placement increased by 2)
    2-5      →  0 (no effect)
    """
    if roll == 1:
        return -2
    if roll == 6:
        return 2
    return 0


def _mists_effect_label(roll: int, modifier: int) -> str:
    """Human-readable effect label for LastMoveInfo."""
    if roll == 1 and modifier == 0:
        return "fog_negated"  # Devout negated a Fog
    if modifier == -2:
        return "fog"
    if modifier == 2:
        return "omen"
    return "none"


def compute_round_result(
    board: list[BoardCell | None],
    players: list[PlayerState] | None = None,
) -> GameResult:
    """Return the result of a completed round.

    Score = cells owned on board + cards remaining in hand (hand-in-score).
    When players is None (legacy/tests), only board cells are counted.
    Equal scores resolve as a draw (triggers Sudden Death).
    """
    p0_cells = sum(1 for cell in board if cell is not None and cell.owner == 0)
    p1_cells = sum(1 for cell in board if cell is not None and cell.owner == 1)
    p0_hand = len(players[0].hand) if players else 0
    p1_hand = len(players[1].hand) if players else 0
    p0 = p0_cells + p0_hand
    p1 = p1_cells + p1_hand
    if p0 > p1:
        return GameResult(winner=0, is_draw=False, completion_reason="normal")
    if p1 > p0:
        return GameResult(winner=1, is_draw=False, completion_reason="normal")
    return GameResult(winner=None, is_draw=True, completion_reason="normal")


def begin_sudden_death_round(state: GameState) -> GameState:
    """Transition a tied board-full state into a new Sudden Death round.

    If the cap (3 SD rounds already used) is reached, returns a COMPLETE state
    with a draw result instead of starting a new round.

    Rebuilds each player's hand from the cards they own on the current board.
    Resets the board; starting player alternates each SD round based on
    starting_player_index. Preserves archetype_used (once-per-game).

    Does NOT bump state_version — the caller is responsible for that.
    """
    if state.sudden_death_rounds_used >= 3:
        return state.model_copy(
            update={
                "result": GameResult(winner=None, is_draw=True, completion_reason="normal"),
                "status": GameStatus.COMPLETE,
            }
        )

    # Rebuild hands: cards owned on board + cards remaining in hand.
    # On a standard tie (P1 owns 5 cells + 0 hand, P2 owns 4 cells + 1 hand),
    # both players get exactly 5 cards back.
    sd_hands: list[list[str]] = [list(p.hand) for p in state.players]
    for bcel in state.board:
        if bcel is not None:
            sd_hands[bcel.owner].append(bcel.card_key)

    new_players = [p.model_copy(update={"hand": sd_hands[i]}) for i, p in enumerate(state.players)]
    empty_board: list[BoardCell | None] = [None] * 9
    new_round_number = state.round_number + 1
    # Alternate starting player each SD round: round 1 → starting_player_index,
    # round 2 → the other player, round 3 → back, etc.
    new_starting_player = (state.starting_player_index + (new_round_number - 1)) % 2
    return state.model_copy(
        update={
            "round_number": new_round_number,
            "sudden_death_rounds_used": state.sudden_death_rounds_used + 1,
            "board": empty_board,
            "players": new_players,
            "current_player_index": new_starting_player,
            "result": None,
            "status": GameStatus.ACTIVE,
            "last_move": None,
        }
    )


class _ArchetypeResult(NamedTuple):
    card: CardDefinition
    activated: bool
    caster_reroll: bool
    devout_negate_fog: bool
    intimidate_target: int | None


_NO_ARCHETYPE = _ArchetypeResult(
    card=None,  # type: ignore[arg-type]  # placeholder, replaced by caller
    activated=False,
    caster_reroll=False,
    devout_negate_fog=False,
    intimidate_target=None,
)


def _apply_archetype(
    state: GameState,
    intent: PlacementIntent,
    card: CardDefinition,
) -> _ArchetypeResult:
    """Validate and apply the archetype power for this placement.

    Returns the (possibly modified) card and side-effect flags.
    Raises domain errors for invalid archetype usage.
    """
    if not intent.use_archetype or not state.players:
        return _NO_ARCHETYPE._replace(card=card)

    player = state.players[intent.player_index]
    if player.archetype_used:
        raise ArchetypeAlreadyUsedError(
            f"Player {intent.player_index} has already used their archetype power"
        )

    if player.archetype == Archetype.MARTIAL:
        direction = intent.martial_rotation_direction or "cw"
        if direction not in {"cw", "ccw"}:
            raise ArchetypePowerArgumentError(
                f"Martial rotation direction must be 'cw' or 'ccw', "
                f"got {direction!r}"
            )
        rotated = rotate_card_ccw(card) if direction == "ccw" else rotate_card_once(card)
        return _ArchetypeResult(
            card=rotated,
            activated=True,
            caster_reroll=False,
            devout_negate_fog=False,
            intimidate_target=None,
        )

    if player.archetype == Archetype.SKULKER:
        if intent.skulker_boost_side not in {"n", "e", "s", "w"}:
            raise ArchetypePowerArgumentError(
                f"Skulker boost requires skulker_boost_side in {{n,e,s,w}}, "
                f"got {intent.skulker_boost_side!r}"
            )
        return _ArchetypeResult(
            card=apply_skulker_boost(card, intent.skulker_boost_side),
            activated=True,
            caster_reroll=False,
            devout_negate_fog=False,
            intimidate_target=None,
        )

    if player.archetype == Archetype.CASTER:
        return _ArchetypeResult(
            card=card,
            activated=True,
            caster_reroll=True,
            devout_negate_fog=False,
            intimidate_target=None,
        )

    if player.archetype == Archetype.DEVOUT:
        return _ArchetypeResult(
            card=card,
            activated=False,  # consumed only when Fog actually rolls
            caster_reroll=False,
            devout_negate_fog=True,
            intimidate_target=None,
        )

    if player.archetype == Archetype.INTIMIDATE:
        if intent.intimidate_target_cell is None or not (
            0 <= intent.intimidate_target_cell <= 8
        ):
            raise ArchetypePowerArgumentError(
                f"Intimidate requires intimidate_target_cell in 0-8, "
                f"got {intent.intimidate_target_cell!r}"
            )
        target_cell = intent.intimidate_target_cell
        adjacent_indices = get_adjacent_indices(intent.cell_index)
        if target_cell not in adjacent_indices:
            raise ArchetypePowerArgumentError(
                f"Intimidate target cell {target_cell} is not adjacent "
                f"to placement cell {intent.cell_index}"
            )
        target_board_cell = state.board[target_cell]
        if target_board_cell is None:
            raise ArchetypePowerArgumentError(
                f"Intimidate target cell {target_cell} is empty"
            )
        if target_board_cell.owner == intent.player_index:
            raise ArchetypePowerArgumentError(
                f"Intimidate target cell {target_cell} contains your own card"
            )
        return _ArchetypeResult(
            card=card,
            activated=True,
            caster_reroll=False,
            devout_negate_fog=False,
            intimidate_target=target_cell,
        )

    raise ArchetypeNotAvailableError(
        f"Player {intent.player_index} has archetype {player.archetype!r}, "
        "which has no active placement power implemented"
    )


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
    arch = _apply_archetype(state, intent, card_lookup[intent.card_key])
    placed_card = arch.card
    placed_owner = intent.player_index
    archetype_activated = arch.activated
    caster_reroll = arch.caster_reroll
    devout_negate_fog = arch.devout_negate_fog
    intimidate_target = arch.intimidate_target

    # --- Mists roll ---
    mists_roll: int | None = None
    mists_modifier = 0
    if rng is not None:
        roll = rng.randint(1, 6)
        if caster_reroll:
            roll = max(roll, rng.randint(1, 6))  # best of two rolls
        mists_modifier = mists_modifier_from_roll(roll)
        if devout_negate_fog and mists_modifier == -2:
            mists_modifier = 0  # Devout treats Fog as no effect
            archetype_activated = True  # power consumed only on actual Fog
        mists_roll = roll

    # --- Elemental bonus ---
    # +1 to all initial comparisons when placed card's element matches the cell's element.
    # Treated as missing (0) if board_elements is absent (old snapshot backward compat).
    # Does not apply to BFS combo chain or Plus sum calculations.
    elemental_bonus = 0
    if state.board_elements is not None:
        if state.board_elements[intent.cell_index] == placed_card.element:
            elemental_bonus = 1

    # --- Board update ---
    new_board: list[BoardCell | None] = list(state.board)
    new_board[intent.cell_index] = BoardCell(card_key=intent.card_key, owner=placed_owner)

    new_board, plus_triggered = resolve_captures(
        new_board,
        intent.cell_index,
        placed_card,
        placed_owner,
        card_lookup,
        mists_modifier=mists_modifier + elemental_bonus,
        intimidate_target_cell=intimidate_target,
    )

    # --- Build state delta ---
    updates: dict[str, object] = {
        "board": new_board,
        "state_version": state.state_version + 1,
    }

    if mists_roll is not None:
        updates["last_move"] = LastMoveInfo(
            player_index=intent.player_index,
            card_key=intent.card_key,
            cell_index=intent.cell_index,
            mists_roll=mists_roll,
            mists_effect=_mists_effect_label(mists_roll, mists_modifier),
            plus_triggered=plus_triggered,
            elemental_triggered=elemental_bonus > 0,
        )

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

    # --- Early finish check (mathematically decided) ---
    # With hand-in-score, total points = 9 cells + hand cards.  A player wins
    # early when their minimum possible final score >= 6 (strictly more than
    # half of the 10 total points).  The first player ends with 0 in hand, the
    # second player ends with 1 in hand (they place only 4 of 5 cards).
    # Conservative bound: opponent fills all empty cells + captures `empty_cells`
    # existing cells → player's min cells = current_cells - empty_cells.
    # Skip if the losing player still has an unspent archetype (could swing the game).
    empty_cells = sum(1 for cell in new_board if cell is None)
    if empty_cells > 0 and state.players:
        p0_cells = sum(1 for cell in new_board if cell is not None and cell.owner == 0)
        p1_cells = sum(1 for cell in new_board if cell is not None and cell.owner == 1)
        first_player = state.starting_player_index
        for pi, count in ((0, p0_cells), (1, p1_cells)):
            opponent = 1 - pi
            if not state.players[opponent].archetype_used:
                continue
            hand_end = 0 if pi == first_player else 1
            min_score = (count - empty_cells) + hand_end
            if min_score >= 6:
                updates["result"] = GameResult(
                    winner=pi, is_draw=False, completion_reason="normal", early_finish=True
                )
                updates["status"] = GameStatus.COMPLETE
                return state.model_copy(update=updates)

    # --- End-of-round check ---
    if all(cell is not None for cell in new_board):
        updated_players = updates.get("players")
        round_result = compute_round_result(
            new_board,
            updated_players,  # type: ignore[arg-type]
        )
        if round_result.is_draw and state.players:
            # Sudden Death: apply all placement updates first, then reset for the new round.
            # begin_sudden_death_round rebuilds hands from the board and handles the SD cap.
            post_placement = state.model_copy(update=updates)
            return begin_sudden_death_round(post_placement)
        updates["result"] = round_result
        updates["status"] = GameStatus.COMPLETE

    return state.model_copy(update=updates)
