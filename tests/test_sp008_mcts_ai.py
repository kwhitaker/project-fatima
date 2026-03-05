"""Tests for US-SP-008: MCTS (The Dark Powers) AI strategy.

Covers:
- MCTS returns valid move within time budget
- SimBoard produces same captures as full apply_intent
- Semaphore limits concurrency (503 on timeout)
- MCTS dispatches via choose_move for NIGHTMARE difficulty
"""

import asyncio
import time
from random import Random

import pytest

from app.models.game import (
    AIDifficulty,
    Archetype,
    BoardCell,
    GameState,
    GameStatus,
    PlayerState,
)
from app.rules.ai import choose_move
from app.rules.mcts import (
    SimBoard,
    _nightmare_semaphore,
    mcts_move,
)
from app.rules.reducer import PlacementIntent, apply_intent
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
                ai_difficulty=AIDifficulty.NIGHTMARE,
                hand=ai_hand if ai_hand is not None else ["c1", "c2", "c3", "c4", "c5"],
                archetype=ai_archetype,
                archetype_used=ai_archetype_used,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# SimBoard tests: must match full apply_intent capture results
# ---------------------------------------------------------------------------


class TestSimBoardCaptures:
    """SimBoard must produce the same captures as the full apply_intent."""

    @pytest.mark.parametrize(
        "desc, placed_cell, placed_sides, opp_cell, opp_sides",
        [
            ("strong_beats_weak", 1, (8, 8, 8, 8), 0, (2, 2, 2, 2)),
            ("weak_loses_to_strong", 1, (2, 2, 2, 2), 0, (8, 8, 8, 8)),
            ("equal_no_capture", 1, (5, 5, 5, 5), 0, (5, 5, 5, 5)),
            ("south_beats_north", 4, (1, 1, 8, 1), 7, (2, 2, 2, 2)),
        ],
        ids=lambda x: x if isinstance(x, str) else "",
    )
    def test_single_capture_matches_apply_intent(
        self, desc: str, placed_cell: int, placed_sides: tuple, opp_cell: int, opp_sides: tuple
    ) -> None:
        """SimBoard and apply_intent agree on single-card capture scenarios."""
        pn, pe, ps, pw = placed_sides
        on, oe, os_, ow = opp_sides
        placed = make_card("placed", n=pn, e=pe, s=ps, w=pw)
        opp = make_card("opp", n=on, e=oe, s=os_, w=ow)
        lookup = {"placed": placed, "opp": opp}

        board: list[BoardCell | None] = [None] * 9
        board[opp_cell] = BoardCell(card_key="opp", owner=0)

        state = _ai_game_state(
            board=board,
            ai_hand=["placed"],
            human_hand=["dummy"],
            current_player_index=1,
        )
        lookup["dummy"] = make_card("dummy")

        # Full apply_intent
        intent = PlacementIntent(player_index=1, card_key="placed", cell_index=placed_cell)
        rng = Random(100)
        full_result = apply_intent(state, intent, lookup, rng)
        full_owners = [
            (c.card_key, c.owner) if c else None for c in full_result.board
        ]

        # SimBoard
        sim = SimBoard.from_game_state(state, lookup)
        sim_rng = Random(100)
        sim.place(placed_cell, "placed", 1, sim_rng)
        sim_owners = [
            (sim.cells[i][0], sim.cells[i][1]) if sim.cells[i] else None
            for i in range(9)
        ]

        # Compare ownership of occupied cells
        for i in range(9):
            if full_owners[i] is not None:
                assert sim_owners[i] is not None, f"Cell {i}: full has card, sim empty"
                assert full_owners[i][1] == sim_owners[i][1], (
                    f"Cell {i}: owners differ: full={full_owners[i][1]}, sim={sim_owners[i][1]}"
                )

    def test_combo_capture_matches(self) -> None:
        """SimBoard handles BFS combo chains the same as apply_intent."""
        # Place strong card at cell 4, captures weak at cell 1, which combos to cell 0
        strong = make_card("strong", n=9, e=9, s=9, w=9)
        weak = make_card("weak", n=1, e=1, s=1, w=1)
        medium = make_card("medium", n=3, e=3, s=3, w=3)
        lookup = {"strong": strong, "weak": weak, "medium": medium, "dummy": make_card("dummy")}

        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="medium", owner=0)  # adjacent to cell 1
        board[1] = BoardCell(card_key="weak", owner=0)     # adjacent to cell 4

        state = _ai_game_state(
            board=board,
            ai_hand=["strong"],
            human_hand=["dummy"],
            current_player_index=1,
        )

        intent = PlacementIntent(player_index=1, card_key="strong", cell_index=4)
        rng = Random(100)
        full_result = apply_intent(state, intent, lookup, rng)

        sim = SimBoard.from_game_state(state, lookup)
        sim.place(4, "strong", 1, Random(100))

        for i in range(9):
            full_cell = full_result.board[i]
            sim_cell = sim.cells[i]
            if full_cell is not None:
                assert sim_cell is not None
                assert full_cell.owner == sim_cell[1], f"Cell {i}: owner mismatch"


# ---------------------------------------------------------------------------
# MCTS strategy tests
# ---------------------------------------------------------------------------


class TestMCTSValidMove:
    """MCTS returns valid moves within the time budget."""

    def test_returns_valid_move_endgame(self) -> None:
        """MCTS picks a valid move with 1 empty cell remaining."""
        board: list[BoardCell | None] = [None] * 9
        for i in range(8):
            board[i] = BoardCell(card_key=f"fill{i}", owner=i % 2)
        # cell 8 is empty

        state = _ai_game_state(
            board=board,
            ai_hand=["last"],
            human_hand=[],
        )
        lookup = {f"fill{i}": make_card(f"fill{i}") for i in range(8)}
        lookup["last"] = make_card("last", n=7, e=7, s=7, w=7)

        intent = mcts_move(state, 1, lookup, Random(42))
        assert intent.card_key == "last"
        assert intent.cell_index == 8

    def test_completes_within_time_budget(self) -> None:
        """MCTS finishes in <3s for an early-game board."""
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="opp1", owner=0)
        board[4] = BoardCell(card_key="ai1", owner=1)

        state = _ai_game_state(
            board=board,
            ai_hand=["c1", "c2", "c3"],
            human_hand=["h1", "h2"],
        )
        lookup = {
            "opp1": make_card("opp1", n=3, e=3, s=3, w=3),
            "ai1": make_card("ai1", n=5, e=5, s=5, w=5),
            "c1": make_card("c1", n=6, e=6, s=6, w=6),
            "c2": make_card("c2", n=7, e=3, s=7, w=3),
            "c3": make_card("c3", n=4, e=8, s=4, w=8),
            "h1": make_card("h1", n=5, e=5, s=5, w=5),
            "h2": make_card("h2", n=6, e=6, s=6, w=6),
        }

        start = time.monotonic()
        intent = mcts_move(state, 1, lookup, Random(42))
        elapsed = time.monotonic() - start

        assert elapsed < 3.0, f"MCTS took {elapsed:.2f}s (limit 3.0s)"
        assert intent.card_key in ["c1", "c2", "c3"]
        assert state.board[intent.cell_index] is None

    def test_prefers_capture_move(self) -> None:
        """MCTS should prefer a move that captures over one that doesn't."""
        # 2 empty cells: cell 1 (adjacent to weak opp at 0), cell 8 (no adjacent opp)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="weak", owner=0)
        board[2] = BoardCell(card_key="ai_fill1", owner=1)
        board[3] = BoardCell(card_key="ai_fill2", owner=1)
        board[4] = BoardCell(card_key="opp_fill", owner=0)
        board[5] = BoardCell(card_key="ai_fill3", owner=1)
        board[6] = BoardCell(card_key="ai_fill4", owner=1)
        board[7] = BoardCell(card_key="opp_fill2", owner=0)
        # cells 1 and 8 empty

        state = _ai_game_state(
            board=board,
            ai_hand=["strong"],
            human_hand=["opp_last"],
        )
        lookup = {
            "weak": make_card("weak", n=1, e=1, s=1, w=1),
            "ai_fill1": make_card("ai_fill1", n=5, e=5, s=5, w=5),
            "ai_fill2": make_card("ai_fill2", n=5, e=5, s=5, w=5),
            "ai_fill3": make_card("ai_fill3", n=5, e=5, s=5, w=5),
            "ai_fill4": make_card("ai_fill4", n=5, e=5, s=5, w=5),
            "opp_fill": make_card("opp_fill", n=5, e=5, s=5, w=5),
            "opp_fill2": make_card("opp_fill2", n=5, e=5, s=5, w=5),
            "strong": make_card("strong", n=9, e=9, s=9, w=9),
            "opp_last": make_card("opp_last", n=4, e=4, s=4, w=4),
        }

        intent = mcts_move(state, 1, lookup, Random(42))
        # Cell 1 captures weak at cell 0 (w side of placed vs e side of neighbor)
        assert intent.cell_index == 1


# ---------------------------------------------------------------------------
# Concealment / sandbagging
# ---------------------------------------------------------------------------


class TestMCTSConcealment:
    """MCTS concealment prefers mid-strength cards when visit counts are close."""

    def test_sandbagging_prefers_mid_strength_early_game(self) -> None:
        """With similar visit counts, MCTS prefers mid-strength over strongest card."""
        # 7 empty cells — early game. AI has a strong and mid card, both can capture.
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="opp1", owner=0)
        board[4] = BoardCell(card_key="ai1", owner=1)

        state = _ai_game_state(
            board=board,
            ai_hand=["best", "mid"],
            human_hand=["h1", "h2", "h3"],
        )
        lookup = {
            "opp1": make_card("opp1", n=2, e=2, s=2, w=2),
            "ai1": make_card("ai1", n=5, e=5, s=5, w=5),
            "best": make_card("best", n=10, e=10, s=10, w=10),
            "mid": make_card("mid", n=5, e=5, s=5, w=5),
            "h1": make_card("h1", n=4, e=4, s=4, w=4),
            "h2": make_card("h2", n=4, e=4, s=4, w=4),
            "h3": make_card("h3", n=4, e=4, s=4, w=4),
        }

        # Run multiple times and check if mid is ever preferred
        mid_chosen = 0
        for seed in range(10):
            intent = mcts_move(state, 1, lookup, Random(seed))
            if intent.card_key == "mid":
                mid_chosen += 1

        # Concealment should prefer mid at least sometimes when visit counts are close
        assert mid_chosen >= 1, "Concealment never preferred mid-strength card"


# ---------------------------------------------------------------------------
# Concurrency limiter
# ---------------------------------------------------------------------------


class TestMCTSSemaphore:
    """asyncio.Semaphore(2) limits concurrent Nightmare computations."""

    def test_semaphore_has_value_2(self) -> None:
        """The semaphore allows 2 concurrent nightmare computations."""
        assert _nightmare_semaphore._value == 2  # type: ignore[attr-defined]

    def test_third_concurrent_request_gets_503(self) -> None:
        """Third concurrent MCTS request should timeout and raise."""
        from app.rules.mcts import acquire_nightmare_semaphore

        async def _run() -> None:
            # Acquire 2 slots
            await _nightmare_semaphore.acquire()
            await _nightmare_semaphore.acquire()
            try:
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(acquire_nightmare_semaphore(), timeout=0.1)
            finally:
                _nightmare_semaphore.release()
                _nightmare_semaphore.release()

        asyncio.new_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


class TestMCTSDispatch:
    """choose_move dispatches to MCTS for NIGHTMARE difficulty."""

    def test_nightmare_dispatches_to_mcts(self) -> None:
        """NIGHTMARE difficulty produces a valid move via MCTS."""
        board: list[BoardCell | None] = [BoardCell(card_key="opp", owner=0)] + [None] * 8
        state = _ai_game_state(board=board, ai_hand=["strong"])
        lookup = {
            "opp": make_card("opp", n=1, e=1, s=1, w=1),
            "strong": make_card("strong", n=9, e=9, s=9, w=9),
        }
        intent = choose_move(state, 1, AIDifficulty.NIGHTMARE, lookup, Random(1))
        assert intent.card_key == "strong"
        assert state.board[intent.cell_index] is None
