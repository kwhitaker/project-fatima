"""Tests for US-011: end-of-round scoring.

When the board fills (9 placements), the reducer sets a terminal
GameResult. Tests cover win (player 0 or 1) and tie detection.
"""

from app.models.cards import CardDefinition, CardSides
from app.models.game import BoardCell, GameResult, GameState, GameStatus, PlayerState
from app.rules.deck import HAND_SIZE
from app.rules.reducer import PlacementIntent, apply_intent, compute_round_result

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_card(key: str, n: int = 5, e: int = 5, s: int = 5, w: int = 5) -> CardDefinition:
    return CardDefinition(
        card_key=key,
        character_key=key,
        name=key,
        version="1.0",
        tier=1,
        rarity=50,
        is_named=False,
        sides=CardSides(n=n, e=e, s=s, w=w),
        set="test",
        element="shadow",
    )


def cell(key: str, owner: int) -> BoardCell:
    return BoardCell(card_key=key, owner=owner)


# ---------------------------------------------------------------------------
# Direct unit tests for compute_round_result
# ---------------------------------------------------------------------------


class TestComputeRoundResult:
    def test_player0_wins_board_only(self):
        """5 cells for p0 vs 4 for p1 (no players) → winner=0."""
        p0_cells: list[BoardCell | None] = [cell(f"c{i}", 0) for i in range(5)]
        board = p0_cells + [cell(f"c{i}", 1) for i in range(5, 9)]
        result = compute_round_result(board)
        assert result == GameResult(winner=0, is_draw=False, completion_reason="normal")

    def test_player1_wins_board_only(self):
        """4 cells for p0 vs 5 for p1 (no players) → winner=1."""
        p0_cells: list[BoardCell | None] = [cell(f"c{i}", 0) for i in range(4)]
        board = p0_cells + [cell(f"c{i}", 1) for i in range(4, 9)]
        result = compute_round_result(board)
        assert result == GameResult(winner=1, is_draw=False, completion_reason="normal")

    def test_sweep_player0(self):
        """All 9 cells owned by p0 → winner=0."""
        board: list[BoardCell | None] = [cell(f"c{i}", 0) for i in range(9)]
        result = compute_round_result(board)
        assert result == GameResult(winner=0, is_draw=False, completion_reason="normal")

    def test_sweep_player1(self):
        """All 9 cells owned by p1 → winner=1."""
        board: list[BoardCell | None] = [cell(f"c{i}", 1) for i in range(9)]
        result = compute_round_result(board)
        assert result == GameResult(winner=1, is_draw=False, completion_reason="normal")


class TestHandInScore:
    """Hand-in-score: final score = cells owned + cards in hand."""

    def test_p1_wins_at_6_cells(self):
        """P1 (first player) places all 5 cards, ends with 0 in hand.
        6 cells + 0 hand = 6 > 3 cells + 1 hand = 4 → P1 wins."""
        board: list[BoardCell | None] = (
            [cell(f"c{i}", 0) for i in range(6)]
            + [cell(f"c{i}", 1) for i in range(6, 9)]
        )
        players = [
            PlayerState(player_id="p0", hand=[]),
            PlayerState(player_id="p1", hand=["extra"]),
        ]
        result = compute_round_result(board, players)
        assert result.winner == 0
        assert result.is_draw is False

    def test_p2_wins_at_5_cells(self):
        """P2 (second player) places 4 cards, keeps 1 in hand.
        4 cells + 0 hand = 4 < 5 cells + 1 hand = 6 → P2 wins."""
        board: list[BoardCell | None] = (
            [cell(f"c{i}", 0) for i in range(4)]
            + [cell(f"c{i}", 1) for i in range(4, 9)]
        )
        players = [
            PlayerState(player_id="p0", hand=[]),
            PlayerState(player_id="p1", hand=["extra"]),
        ]
        result = compute_round_result(board, players)
        assert result.winner == 1
        assert result.is_draw is False

    def test_tie_at_5_5(self):
        """Standard tie: P1 owns 5 cells + 0 hand = 5, P2 owns 4 cells + 1 hand = 5."""
        board: list[BoardCell | None] = (
            [cell(f"c{i}", 0) for i in range(5)]
            + [cell(f"c{i}", 1) for i in range(5, 9)]
        )
        players = [
            PlayerState(player_id="p0", hand=[]),
            PlayerState(player_id="p1", hand=["extra"]),
        ]
        result = compute_round_result(board, players)
        assert result.is_draw is True
        assert result.winner is None


# ---------------------------------------------------------------------------
# End-of-round trigger via apply_intent
# ---------------------------------------------------------------------------


def _make_almost_full_state(
    last_placer: int,
    starting_player_index: int = 0,
) -> tuple[GameState, dict[str, CardDefinition]]:
    """Board with 8 cells filled (4 per player); cell 0 is empty.

    Layout (cell 0 empty, neighbors are cells 1 and 3 = both p0 → no captures/Plus):
      cell 0   → empty (the final placement cell)
      cells 1-4 → player 0
      cells 5-8 → player 1

    With hand-in-score, the second player keeps 1 card in hand at game end.
    """
    board: list[BoardCell | None] = (
        [None]
        + [cell(f"c{i}", 0) for i in range(1, 5)]
        + [cell(f"c{i}", 1) for i in range(5, 9)]
    )
    cards: dict[str, CardDefinition] = {f"c{i}": make_card(f"c{i}") for i in range(1, 9)}
    cards["last"] = make_card("last")
    cards["kept"] = make_card("kept")

    second_player = 1 - starting_player_index

    if last_placer == starting_player_index:
        # First player places their final card; second keeps 1 in hand
        p_hands: list[list[str]] = [[], []]
        p_hands[last_placer] = ["last"]
        p_hands[second_player] = ["kept"]
    else:
        # Second player places; they had 2 remaining, keep 1 after placement
        p_hands = [[], []]
        p_hands[last_placer] = ["last", "kept"]
        p_hands[1 - last_placer] = []

    state = GameState(
        game_id="test",
        status=GameStatus.ACTIVE,
        players=[
            PlayerState(player_id="p0", hand=p_hands[0]),
            PlayerState(player_id="p1", hand=p_hands[1]),
        ],
        board=board,
        current_player_index=last_placer,
        starting_player_index=starting_player_index,
    )
    return state, cards


class TestEndOfRoundViaReducer:
    def test_tie_triggers_sudden_death(self):
        """First player (p0) places 9th card: 5 cells + 0 hand = 5 vs 4 cells + 1 hand = 5 → tie → SD."""
        state, cards = _make_almost_full_state(last_placer=0, starting_player_index=0)
        intent = PlacementIntent(player_index=0, card_key="last", cell_index=0)
        result_state = apply_intent(state, intent, cards)

        # Tie triggers Sudden Death: board resets, status stays ACTIVE
        assert result_state.status == GameStatus.ACTIVE
        assert result_state.round_number == 2
        assert all(c is None for c in result_state.board)

    def test_second_player_last_placement_tie(self):
        """Second player (p1) places 9th card: p0=4+0=4, p1=5+1=6 → p1 wins."""
        state, cards = _make_almost_full_state(last_placer=1, starting_player_index=0)
        intent = PlacementIntent(player_index=1, card_key="last", cell_index=0)
        result_state = apply_intent(state, intent, cards)

        assert result_state.status == GameStatus.COMPLETE
        assert result_state.result is not None
        assert result_state.result.winner == 1
        assert result_state.result.is_draw is False

    def test_status_stays_active_before_board_full(self):
        """Status remains ACTIVE when empty cells remain after a placement."""
        card = make_card("card_a")
        state = GameState(
            game_id="test",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["card_a"]),
                PlayerState(player_id="p1", hand=[]),
            ],
            board=[None] * 9,
            current_player_index=0,
        )
        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=0)
        result_state = apply_intent(state, intent, {"card_a": card})

        assert result_state.status == GameStatus.ACTIVE
        assert result_state.result is None

    def test_result_not_set_mid_game(self):
        """result field is None until the board is full."""
        card = make_card("mid")
        state = GameState(
            game_id="test",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["mid"]),
                PlayerState(player_id="p1", hand=[]),
            ],
            board=[None] * 9,
            current_player_index=0,
        )
        intent = PlacementIntent(player_index=0, card_key="mid", cell_index=4)
        result_state = apply_intent(state, intent, {"mid": card})
        assert result_state.result is None

    def test_captures_affect_final_score(self):
        """A capture on the last placement is reflected in the final result.

        Layout: cell 2 is empty (top-right corner), neighbors: cell 1 (west, p1) and cell 5 (south, p0).
        p0 places at cell 2 with high west side to capture cell 1.
        p0: 5 cells + 1 captured = 6 + 0 hand = 6, p1: 3 cells + 1 hand = 4 → p0 wins.
        """
        # cells 0,3,4,5 = p0; cells 1,6,7,8 = p1; cell 2 = empty
        board: list[BoardCell | None] = [
            cell("c0", 0),    # cell 0: p0
            cell("c1", 1),    # cell 1: p1 (will be captured)
            None,             # cell 2: empty (placement target)
            cell("c3", 0),    # cell 3: p0
            cell("c4", 0),    # cell 4: p0
            cell("c5", 0),    # cell 5: p0
            cell("c6", 1),    # cell 6: p1
            cell("c7", 1),    # cell 7: p1
            cell("c8", 1),    # cell 8: p1
        ]
        cards: dict[str, CardDefinition] = {
            f"c{i}": make_card(f"c{i}", n=1, e=1, s=1, w=1) for i in range(9)
        }
        # "last" has a very high west side → captures cell 1 (west of cell 2)
        cards["last"] = make_card("last", n=1, e=1, s=1, w=10)
        cards["kept"] = make_card("kept")

        state = GameState(
            game_id="test",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["last"]),
                PlayerState(player_id="p1", hand=["kept"]),  # second player keeps 1
            ],
            board=board,
            current_player_index=0,
            starting_player_index=0,
        )
        intent = PlacementIntent(player_index=0, card_key="last", cell_index=2)
        result_state = apply_intent(state, intent, cards)

        assert result_state.board[1] is not None
        assert result_state.board[1].owner == 0  # captured!
        assert result_state.status == GameStatus.COMPLETE
        assert result_state.result is not None
        # p0: 6 cells + 0 hand = 6; p1: 3 cells + 1 hand = 4
        assert result_state.result.winner == 0
