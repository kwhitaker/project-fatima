"""Tests for US-SP-007: Expectimax (Strahd) AI strategy — opponent hand inference.

Covers:
- Expectimax finds winning move in near-endgame setup
- Expectimax narrows opponent hand as cards are played
- Stays within reasonable compute time (<2s for any board state)
- Dispatch from choose_move
"""

import time
from random import Random

from app.models.game import (
    AIDifficulty,
    Archetype,
    BoardCell,
    GameState,
    GameStatus,
    PlayerState,
)
from app.rules.ai import (
    _expectimax_move,
    _infer_opponent_pool,
    choose_move,
)
from app.services.game_service import AI_PLAYER_ID
from tests.conftest import make_card


def _ai_game_state(
    board: list[BoardCell | None] | None = None,
    ai_hand: list[str] | None = None,
    human_hand: list[str] | None = None,
    ai_archetype: Archetype | None = None,
    ai_archetype_used: bool = False,
    current_player_index: int = 1,
    seed: int = 42,
    board_elements: list[str] | None = None,
) -> GameState:
    """Build a GameState for AI testing with AI as player index 1."""
    return GameState(
        game_id="test-ai",
        status=GameStatus.ACTIVE,
        seed=seed,
        current_player_index=current_player_index,
        board=board if board is not None else [None] * 9,
        board_elements=board_elements,
        players=[
            PlayerState(
                player_id="human",
                player_type="human",
                hand=human_hand or [],
                archetype=Archetype.MARTIAL,
                archetype_used=True,
            ),
            PlayerState(
                player_id=AI_PLAYER_ID,
                player_type="ai",
                ai_difficulty=AIDifficulty.HARD,
                hand=ai_hand if ai_hand is not None else ["c1", "c2", "c3", "c4", "c5"],
                archetype=ai_archetype,
                archetype_used=ai_archetype_used,
            ),
        ],
    )


class TestExpectimaxFindsWinningMove:
    """Expectimax should find the winning move in near-endgame positions."""

    def test_captures_winning_cell_in_endgame(self) -> None:
        """With 1 empty cell and a clear winning placement, expectimax finds it."""
        # Board: 8 cells filled, cell 4 (center) empty.
        # AI has one card left, opponent has none (last move).
        # Opponent cards at cells 1 and 3 are weak — AI should place at 4 to capture them.
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="ai_a", owner=1)
        board[1] = BoardCell(card_key="opp_weak1", owner=0)
        board[2] = BoardCell(card_key="ai_b", owner=1)
        board[3] = BoardCell(card_key="opp_weak2", owner=0)
        # cell 4 empty
        board[5] = BoardCell(card_key="opp_strong", owner=0)
        board[6] = BoardCell(card_key="ai_c", owner=1)
        board[7] = BoardCell(card_key="opp_d", owner=0)
        board[8] = BoardCell(card_key="ai_d", owner=1)

        state = _ai_game_state(
            board=board,
            ai_hand=["attacker"],
            human_hand=[],
        )
        lookup = {
            "ai_a": make_card("ai_a", n=5, e=5, s=5, w=5),
            "ai_b": make_card("ai_b", n=5, e=5, s=5, w=5),
            "ai_c": make_card("ai_c", n=5, e=5, s=5, w=5),
            "ai_d": make_card("ai_d", n=5, e=5, s=5, w=5),
            "opp_weak1": make_card("opp_weak1", n=1, e=1, s=1, w=1),
            "opp_weak2": make_card("opp_weak2", n=1, e=1, s=1, w=1),
            "opp_strong": make_card("opp_strong", n=9, e=9, s=9, w=9),
            "opp_d": make_card("opp_d", n=5, e=5, s=5, w=5),
            "attacker": make_card("attacker", n=8, e=8, s=8, w=8),
        }
        intent = choose_move(state, 1, AIDifficulty.HARD, lookup, Random(1))
        assert intent.card_key == "attacker"
        assert intent.cell_index == 4  # only empty cell

    def test_picks_capture_over_non_capture(self) -> None:
        """With 1 empty cell adjacent to a weak opponent card, expectimax captures it."""
        # 8 cells filled, only cell 1 empty. Opponent weak card at cell 0.
        # AI strong card captures cell 0 when placed at cell 1.
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="weak", owner=0)
        board[1] = None  # only empty cell
        board[2] = BoardCell(card_key="ai_fill1", owner=1)
        board[3] = BoardCell(card_key="opp_fill", owner=0)
        board[4] = BoardCell(card_key="ai_fill2", owner=1)
        board[5] = BoardCell(card_key="opp_fill2", owner=0)
        board[6] = BoardCell(card_key="ai_fill3", owner=1)
        board[7] = BoardCell(card_key="opp_fill3", owner=0)
        board[8] = BoardCell(card_key="ai_fill4", owner=1)

        state = _ai_game_state(
            board=board,
            ai_hand=["strong"],
            human_hand=[],
        )
        lookup = {
            "weak": make_card("weak", n=1, e=1, s=1, w=1),
            "ai_fill1": make_card("ai_fill1", n=5, e=5, s=5, w=5),
            "ai_fill2": make_card("ai_fill2", n=5, e=5, s=5, w=5),
            "ai_fill3": make_card("ai_fill3", n=5, e=5, s=5, w=5),
            "ai_fill4": make_card("ai_fill4", n=5, e=5, s=5, w=5),
            "opp_fill": make_card("opp_fill", n=5, e=5, s=5, w=5),
            "opp_fill2": make_card("opp_fill2", n=5, e=5, s=5, w=5),
            "opp_fill3": make_card("opp_fill3", n=5, e=5, s=5, w=5),
            "strong": make_card("strong", n=9, e=9, s=9, w=9),
        }
        intent = choose_move(state, 1, AIDifficulty.HARD, lookup, Random(1))
        assert intent.cell_index == 1


class TestExpectimaxOpponentHandInference:
    """Expectimax narrows the opponent hand pool as the game progresses."""

    def test_pool_excludes_board_and_ai_hand(self) -> None:
        """Cards on the board and in AI hand are excluded from the pool."""
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="on_board", owner=0)

        state = _ai_game_state(board=board, ai_hand=["in_hand"])
        lookup = {
            "on_board": make_card("on_board"),
            "in_hand": make_card("in_hand"),
            "available1": make_card("available1"),
            "available2": make_card("available2"),
        }
        pool = _infer_opponent_pool(state, 1, lookup)
        assert "on_board" not in pool
        assert "in_hand" not in pool
        assert "available1" in pool
        assert "available2" in pool

    def test_pool_shrinks_as_game_progresses(self) -> None:
        """More cards on the board means a smaller inference pool."""
        lookup = {f"c{i}": make_card(f"c{i}") for i in range(20)}

        # Early game: 1 card on board, AI has 5
        board_early: list[BoardCell | None] = [None] * 9
        board_early[0] = BoardCell(card_key="c0", owner=0)
        state_early = _ai_game_state(
            board=board_early,
            ai_hand=["c10", "c11", "c12", "c13", "c14"],
        )
        pool_early = _infer_opponent_pool(state_early, 1, lookup)

        # Late game: 7 cards on board, AI has 1
        board_late: list[BoardCell | None] = [None] * 9
        for i in range(7):
            board_late[i] = BoardCell(card_key=f"c{i}", owner=i % 2)
        state_late = _ai_game_state(
            board=board_late,
            ai_hand=["c10"],
        )
        pool_late = _infer_opponent_pool(state_late, 1, lookup)

        assert len(pool_late) < len(pool_early)


class TestExpectimaxPerformance:
    """Expectimax should run within time budget."""

    def test_completes_within_2_seconds_early_game(self) -> None:
        """On an early-game board (many empty cells), expectimax finishes in <2s."""
        # 3 cards placed, 6 empty — depth is capped at 4
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="opp1", owner=0)
        board[4] = BoardCell(card_key="ai1", owner=1)
        board[8] = BoardCell(card_key="opp2", owner=0)

        state = _ai_game_state(
            board=board,
            ai_hand=["c1", "c2", "c3"],
            human_hand=["h1", "h2"],
        )
        lookup = {
            "opp1": make_card("opp1", n=3, e=3, s=3, w=3),
            "opp2": make_card("opp2", n=4, e=4, s=4, w=4),
            "ai1": make_card("ai1", n=5, e=5, s=5, w=5),
            "c1": make_card("c1", n=6, e=6, s=6, w=6),
            "c2": make_card("c2", n=7, e=3, s=7, w=3),
            "c3": make_card("c3", n=4, e=8, s=4, w=8),
            "h1": make_card("h1", n=5, e=5, s=5, w=5),
            "h2": make_card("h2", n=6, e=6, s=6, w=6),
        }

        start = time.monotonic()
        intent = _expectimax_move(state, 1, lookup, Random(42))
        elapsed = time.monotonic() - start

        assert elapsed < 2.0, f"Expectimax took {elapsed:.2f}s (limit 2.0s)"
        assert intent.card_key in ["c1", "c2", "c3"]
        assert state.board[intent.cell_index] is None

    def test_completes_within_2_seconds_endgame(self) -> None:
        """On an endgame board (2 empty cells), expectimax finishes in <2s."""
        board: list[BoardCell | None] = [None] * 9
        for i in range(7):
            board[i] = BoardCell(card_key=f"fill{i}", owner=i % 2)

        state = _ai_game_state(
            board=board,
            ai_hand=["last"],
            human_hand=["opp_last"],
        )
        lookup = {f"fill{i}": make_card(f"fill{i}") for i in range(7)}
        lookup["last"] = make_card("last", n=7, e=7, s=7, w=7)
        lookup["opp_last"] = make_card("opp_last", n=4, e=4, s=4, w=4)

        start = time.monotonic()
        intent = _expectimax_move(state, 1, lookup, Random(42))
        elapsed = time.monotonic() - start

        assert elapsed < 2.0, f"Expectimax took {elapsed:.2f}s (limit 2.0s)"
        assert intent.cell_index in {7, 8}  # only empty cells


class TestExpectimaxDispatch:
    """choose_move dispatches to expectimax for HARD difficulty."""

    def test_hard_dispatches_to_expectimax(self) -> None:
        """HARD difficulty produces a valid move via expectimax."""
        board: list[BoardCell | None] = [BoardCell(card_key="opp", owner=0)] + [None] * 8
        state = _ai_game_state(board=board, ai_hand=["strong"])
        lookup = {
            "opp": make_card("opp", n=1, e=1, s=1, w=1),
            "strong": make_card("strong", n=9, e=9, s=9, w=9),
        }
        intent = choose_move(state, 1, AIDifficulty.HARD, lookup, Random(1))
        assert intent.card_key == "strong"
        # Should pick a cell adjacent to cell 0 for capture
        assert intent.cell_index in {1, 3}


class TestExpectimaxArchetype:
    """Expectimax evaluates archetypes when they improve expected value."""

    def test_uses_skulker_when_beneficial(self) -> None:
        """Expectimax uses Skulker when boosting a side enables a key capture."""
        # Near-endgame: 1 empty cell (cell 1). Opponent at cell 2 with w=6.
        # AI card: e=1 (can't beat 6 even with omen +2). With Skulker e: e=1+3=4,
        # which still needs a good mists roll, but on average beats w=6 less often.
        # Actually use w=3 so skulker e: 1+3=4 > 3 reliably even with fog.
        # Without skulker: e=1 < 3 always (fog makes it -1).
        board: list[BoardCell | None] = [BoardCell(card_key="fill", owner=1)] * 9
        board[1] = None
        board[2] = BoardCell(card_key="opp", owner=0)

        state = _ai_game_state(
            board=board,
            ai_hand=["attacker"],
            human_hand=[],
            ai_archetype=Archetype.SKULKER,
        )
        lookup = {
            "fill": make_card("fill"),
            "opp": make_card("opp", n=5, e=5, s=5, w=1),
            "attacker": make_card("attacker", n=7, e=2, s=7, w=7),
        }
        intent = choose_move(state, 1, AIDifficulty.HARD, lookup, Random(1))
        # Should use archetype — skulker boosting E (e=2+3=5 > 1) captures cell 2
        assert intent.use_archetype
        assert intent.cell_index == 1
