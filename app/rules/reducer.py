"""Pure rules engine reducer.

apply_intent(state, intent, card_lookup, rng) -> GameState

All game logic flows through here. Randomness flows through the explicit rng
argument (seeded Random instance) — never global random.*
"""

from dataclasses import dataclass, field
from random import Random

from app.models.cards import CardDefinition
from app.models.game import Archetype, BoardCell, GameResult, GameState, GameStatus, LastMoveInfo
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
    intimidate_target_cell: int | None = field(default=None)


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


def compute_round_result(board: list[BoardCell | None]) -> GameResult:
    """Return the result of a completed round from the current board state.

    Counts cells owned by each player. The player with more cells wins.
    Equal counts resolve as a draw (triggers Sudden Death in the next story).
    """
    p0 = sum(1 for cell in board if cell is not None and cell.owner == 0)
    p1 = sum(1 for cell in board if cell is not None and cell.owner == 1)
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

    sd_hands: list[list[str]] = [[], []]
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
    intimidate_target: int | None = None

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
        elif player.archetype == Archetype.INTIMIDATE:
            if intent.intimidate_target_cell is None or not (
                0 <= intent.intimidate_target_cell <= 8
            ):
                raise ArchetypePowerArgumentError(
                    f"Intimidate requires intimidate_target_cell in 0-8, "
                    f"got {intent.intimidate_target_cell!r}"
                )
            target_cell = intent.intimidate_target_cell
            # Validate target is adjacent to placement cell
            from app.rules.captures import _ADJACENCY

            adjacent_indices = {nb[0] for nb in _ADJACENCY[intent.cell_index]}
            if target_cell not in adjacent_indices:
                raise ArchetypePowerArgumentError(
                    f"Intimidate target cell {target_cell} is not adjacent "
                    f"to placement cell {intent.cell_index}"
                )
            # Validate target cell has an opponent card
            target_board_cell = state.board[target_cell]
            if target_board_cell is None:
                raise ArchetypePowerArgumentError(
                    f"Intimidate target cell {target_cell} is empty"
                )
            if target_board_cell.owner == intent.player_index:
                raise ArchetypePowerArgumentError(
                    f"Intimidate target cell {target_cell} contains your own card"
                )
            intimidate_target = target_cell
            archetype_activated = True
        else:
            raise ArchetypeNotAvailableError(
                f"Player {intent.player_index} has archetype {player.archetype!r}, "
                "which has no active placement power implemented"
            )

    # --- Mists roll ---
    mists_roll: int | None = None
    mists_modifier = 0
    if rng is not None:
        roll = rng.randint(1, 6)
        if caster_reroll:
            roll = rng.randint(1, 6)  # second result is used
        mists_modifier = mists_modifier_from_roll(roll)
        if devout_negate_fog and mists_modifier == -2:
            mists_modifier = 0  # Devout treats Fog as no effect
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
    # After capture resolution, check if one player owns enough cells that
    # the opponent cannot reach majority (5+) even by capturing all remaining.
    empty_cells = sum(1 for cell in new_board if cell is None)
    if empty_cells > 0:
        p0_cells = sum(1 for cell in new_board if cell is not None and cell.owner == 0)
        p1_cells = sum(1 for cell in new_board if cell is not None and cell.owner == 1)
        for pi, count in ((0, p0_cells), (1, p1_cells)):
            if count >= 5 + empty_cells:
                updates["result"] = GameResult(
                    winner=pi, is_draw=False, completion_reason="normal", early_finish=True
                )
                updates["status"] = GameStatus.COMPLETE
                return state.model_copy(update=updates)

    # --- End-of-round check ---
    if all(cell is not None for cell in new_board):
        round_result = compute_round_result(new_board)
        if round_result.is_draw and state.players:
            # Sudden Death: apply all placement updates first, then reset for the new round.
            # begin_sudden_death_round rebuilds hands from the board and handles the SD cap.
            post_placement = state.model_copy(update=updates)
            return begin_sudden_death_round(post_placement)
        updates["result"] = round_result
        updates["status"] = GameStatus.COMPLETE

    return state.model_copy(update=updates)
