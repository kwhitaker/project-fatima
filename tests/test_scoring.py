"""Tests for US-011: end-of-round scoring.

When the board fills (9 placements), the reducer sets a terminal
GameResult. Tests cover win (player 0 or 1) and tie detection.
"""

from app.models.cards import CardDefinition, CardSides
from app.models.game import BoardCell, GameResult, GameState, GameStatus, PlayerState
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
    )


def cell(key: str, owner: int) -> BoardCell:
    return BoardCell(card_key=key, owner=owner)


# ---------------------------------------------------------------------------
# Direct unit tests for compute_round_result
# ---------------------------------------------------------------------------


class TestComputeRoundResult:
    def test_player0_wins(self):
        """5 cells for p0 vs 4 for p1 → winner=0."""
        p0_cells: list[BoardCell | None] = [cell(f"c{i}", 0) for i in range(5)]
        board = p0_cells + [cell(f"c{i}", 1) for i in range(5, 9)]
        result = compute_round_result(board)
        assert result == GameResult(winner=0, is_draw=False)

    def test_player1_wins(self):
        """4 cells for p0 vs 5 for p1 → winner=1."""
        p0_cells: list[BoardCell | None] = [cell(f"c{i}", 0) for i in range(4)]
        board = p0_cells + [cell(f"c{i}", 1) for i in range(4, 9)]
        result = compute_round_result(board)
        assert result == GameResult(winner=1, is_draw=False)

    def test_tie_detection(self):
        """Equal ownership (4 vs 4) → is_draw=True, winner=None."""
        board: list[BoardCell | None] = (
            [cell(f"c{i}", 0) for i in range(4)] + [cell(f"c{i}", 1) for i in range(4, 8)] + [None]
        )
        result = compute_round_result(board)
        assert result == GameResult(winner=None, is_draw=True)

    def test_sweep_player0(self):
        """All 9 cells owned by p0 → winner=0."""
        board: list[BoardCell | None] = [cell(f"c{i}", 0) for i in range(9)]
        result = compute_round_result(board)
        assert result == GameResult(winner=0, is_draw=False)

    def test_sweep_player1(self):
        """All 9 cells owned by p1 → winner=1."""
        board: list[BoardCell | None] = [cell(f"c{i}", 1) for i in range(9)]
        result = compute_round_result(board)
        assert result == GameResult(winner=1, is_draw=False)


# ---------------------------------------------------------------------------
# End-of-round trigger via apply_intent
# ---------------------------------------------------------------------------


def _make_almost_full_state(last_placer: int) -> tuple[GameState, dict[str, CardDefinition]]:
    """Board with 8 cells filled (4 per player); cell 8 is empty.

    Layout:
      cells 0-3 → player 0
      cells 4-7 → player 1
      cell  8   → empty (the final placement cell)
    """
    board: list[BoardCell | None] = (
        [cell(f"c{i}", 0) for i in range(4)] + [cell(f"c{i}", 1) for i in range(4, 8)] + [None]
    )
    cards: dict[str, CardDefinition] = {f"c{i}": make_card(f"c{i}") for i in range(8)}
    cards["last"] = make_card("last")

    p0_hand = ["last"] if last_placer == 0 else []
    p1_hand = ["last"] if last_placer == 1 else []

    state = GameState(
        game_id="test",
        status=GameStatus.ACTIVE,
        players=[
            PlayerState(player_id="p0", hand=p0_hand),
            PlayerState(player_id="p1", hand=p1_hand),
        ],
        board=board,
        current_player_index=last_placer,
    )
    return state, cards


class TestEndOfRoundViaReducer:
    def test_player0_wins_on_last_placement(self):
        """p0 places the 9th card (no captures); 5 vs 4 → winner=0, status=COMPLETE."""
        state, cards = _make_almost_full_state(0)
        intent = PlacementIntent(player_index=0, card_key="last", cell_index=8)
        result_state = apply_intent(state, intent, cards)

        assert result_state.status == GameStatus.COMPLETE
        assert result_state.result is not None
        assert result_state.result.winner == 0
        assert result_state.result.is_draw is False

    def test_player1_wins_on_last_placement(self):
        """p1 places the 9th card (no captures); 4 vs 5 → winner=1, status=COMPLETE."""
        state, cards = _make_almost_full_state(1)
        intent = PlacementIntent(player_index=1, card_key="last", cell_index=8)
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
        """A capture on the last placement is reflected in the final result."""
        # Board: cells 0-7 set up so the last placement (cell 8, player 0) captures
        # cell 5 (player 1) due to high south side on the "last" card.
        # After capture: p0 = 4 (cells 0-3) + 1 (cell 5 captured) + 1 (cell 8 placed) = 6
        # p1 = 4 (cells 4-7) - 1 (cell 5 lost) = 3 → p0 wins
        board: list[BoardCell | None] = (
            [cell(f"c{i}", 0) for i in range(4)] + [cell(f"c{i}", 1) for i in range(4, 8)] + [None]
        )
        cards: dict[str, CardDefinition] = {
            f"c{i}": make_card(f"c{i}", n=5, e=5, s=5, w=5) for i in range(8)
        }
        # "last" has a very high north side → captures cell 5 (neighbor to the north of cell 8)
        cards["last"] = make_card("last", n=10, e=5, s=5, w=5)

        state = GameState(
            game_id="test",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["last"]),
                PlayerState(player_id="p1", hand=[]),
            ],
            board=board,
            current_player_index=0,
        )
        intent = PlacementIntent(player_index=0, card_key="last", cell_index=8)
        result_state = apply_intent(state, intent, cards)

        # Board cell 5 should now be owned by p0 (captured)
        assert result_state.board[5] is not None
        assert result_state.board[5].owner == 0
        assert result_state.status == GameStatus.COMPLETE
        assert result_state.result is not None
        # p0: 0,1,2,3,5,8 = 6; p1: 4,6,7 = 3
        assert result_state.result.winner == 0
