"""Tests for US-SP-004: AI turn trigger after human moves.

Covers:
- is_ai_turn correctly identifies AI turns
- execute_ai_turn computes and submits a valid AI move
- AI turn fires after human move
- No AI turn when game is complete
- choose_move returns valid (card, cell) pairs
"""

import asyncio
from random import Random
from unittest.mock import AsyncMock, patch

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
from app.rules.reducer import PlacementIntent
from app.services.game_service import (
    AI_PLAYER_ID,
    create_game_vs_ai,
    execute_ai_turn,
    is_ai_turn,
    select_archetype,
    submit_draft,
    submit_move,
)
from app.store.memory import MemoryCardStore, MemoryGameStore
from tests.conftest import _TEST_CARDS, make_card


@pytest.fixture()
def card_store() -> MemoryCardStore:
    return MemoryCardStore(cards=_TEST_CARDS)


def _make_ai_state(status: GameStatus, current: int) -> GameState:
    """Minimal AI game state for is_ai_turn tests."""
    return GameState(
        game_id="g1",
        status=status,
        current_player_index=current,
        players=[
            PlayerState(player_id="human", player_type="human"),
            PlayerState(
                player_id=AI_PLAYER_ID,
                player_type="ai",
                ai_difficulty=AIDifficulty.EASY,
            ),
        ],
    )


def _run(coro):  # noqa: ANN001, ANN202
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestIsAiTurn:
    """is_ai_turn correctly identifies when it's an AI player's turn."""

    def test_true_when_ai_turn(self) -> None:
        assert is_ai_turn(_make_ai_state(GameStatus.ACTIVE, 1)) is True

    def test_false_when_human_turn(self) -> None:
        assert is_ai_turn(_make_ai_state(GameStatus.ACTIVE, 0)) is False

    def test_false_when_not_active(self) -> None:
        assert is_ai_turn(_make_ai_state(GameStatus.DRAFTING, 1)) is False

    def test_false_for_human_vs_human(self) -> None:
        state = GameState(
            game_id="g1",
            status=GameStatus.ACTIVE,
            current_player_index=0,
            players=[
                PlayerState(player_id="p1"),
                PlayerState(player_id="p2"),
            ],
        )
        assert is_ai_turn(state) is False


class TestChooseMove:
    """choose_move returns valid (card, cell) pairs."""

    def test_returns_valid_placement(self) -> None:
        state = _make_ai_state(GameStatus.ACTIVE, 1)
        state = state.model_copy(
            update={
                "players": [
                    state.players[0].model_copy(update={"hand": ["c1", "c2"]}),
                    state.players[1].model_copy(update={"hand": ["c3", "c4"]}),
                ],
            }
        )
        card_lookup = {f"c{i}": make_card(f"c{i}") for i in range(1, 5)}
        intent = choose_move(state, 1, AIDifficulty.EASY, card_lookup, Random(42))

        assert isinstance(intent, PlacementIntent)
        assert intent.player_index == 1
        assert intent.card_key in ["c3", "c4"]
        assert 0 <= intent.cell_index <= 8

    def test_picks_from_empty_cells_only(self) -> None:
        board: list[BoardCell | None] = [
            BoardCell(card_key="c1", owner=0),
            BoardCell(card_key="c2", owner=1),
        ] + [None] * 7
        state = _make_ai_state(GameStatus.ACTIVE, 1)
        state = state.model_copy(
            update={
                "board": board,
                "players": [
                    state.players[0].model_copy(update={"hand": ["c5"]}),
                    state.players[1].model_copy(update={"hand": ["c6"]}),
                ],
            }
        )
        card_lookup = {f"c{i}": make_card(f"c{i}") for i in range(1, 7)}
        intent = choose_move(state, 1, AIDifficulty.EASY, card_lookup, Random(42))
        assert intent.cell_index >= 2

    def test_raises_on_no_legal_moves(self) -> None:
        state = _make_ai_state(GameStatus.ACTIVE, 1)
        with pytest.raises(ValueError, match="no legal moves"):
            choose_move(state, 1, AIDifficulty.EASY, {}, Random(1))


class TestExecuteAiTurn:
    """execute_ai_turn computes and submits a valid AI move."""

    def test_noop_when_game_missing(self, card_store: MemoryCardStore) -> None:
        gs = MemoryGameStore()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            _run(execute_ai_turn("nonexistent", gs, card_store))

    def test_noop_when_game_complete(self, card_store: MemoryCardStore) -> None:
        gs = MemoryGameStore()
        state = create_game_vs_ai(gs, card_store, "h1", "h@t", AIDifficulty.EASY, seed=100)
        completed = state.model_copy(update={"status": GameStatus.COMPLETE})
        gs._states[state.game_id] = completed

        with patch("asyncio.sleep", new_callable=AsyncMock):
            _run(execute_ai_turn(state.game_id, gs, card_store))

        after = gs.get_game(state.game_id)
        assert after is not None
        assert after.status == GameStatus.COMPLETE
        assert after.state_version == completed.state_version

    def test_noop_when_human_turn(self, card_store: MemoryCardStore) -> None:
        gs = MemoryGameStore()
        state = create_game_vs_ai(gs, card_store, "h1", "h@t", AIDifficulty.EASY, seed=100)
        human = state.players[0]
        state = submit_draft(gs, state.game_id, human.player_id, human.deal[:5])
        if state.status != GameStatus.ACTIVE:
            pytest.skip("Game not ACTIVE after draft")

        forced = state.model_copy(update={"current_player_index": 0})
        gs._states[state.game_id] = forced
        version_before = forced.state_version

        with patch("asyncio.sleep", new_callable=AsyncMock):
            _run(execute_ai_turn(state.game_id, gs, card_store))

        after = gs.get_game(state.game_id)
        assert after is not None
        assert after.state_version == version_before

    def test_ai_move_submitted_when_ai_turn(self, card_store: MemoryCardStore) -> None:
        # Find a seed where AI goes first (so after draft, it's AI's turn)
        for seed in range(200):
            gs = MemoryGameStore()
            st = create_game_vs_ai(gs, card_store, "h1", "h@t", AIDifficulty.EASY, seed=seed)
            if st.starting_player_index == 1:
                break
        else:
            pytest.skip("Could not find seed where AI starts")

        gs = MemoryGameStore()
        state = create_game_vs_ai(gs, card_store, "h1", "h@t", AIDifficulty.EASY, seed=seed)
        human = state.players[0]
        state = submit_draft(gs, state.game_id, human.player_id, human.deal[:5])
        assert state.status == GameStatus.ACTIVE
        assert is_ai_turn(state)

        version_before = state.state_version
        with patch("asyncio.sleep", new_callable=AsyncMock):
            _run(execute_ai_turn(state.game_id, gs, card_store))

        updated = gs.get_game(state.game_id)
        assert updated is not None
        assert updated.state_version > version_before
        placed = [c for c in updated.board if c is not None]
        assert len(placed) == 1  # AI placed one card


class TestAiTurnAfterHumanMove:
    """Integration: AI move after human submits a move in an AI game."""

    def test_game_progresses_after_human_move(self, card_store: MemoryCardStore) -> None:
        # Find a seed where human goes first
        for seed in range(200):
            gs = MemoryGameStore()
            st = create_game_vs_ai(gs, card_store, "h1", "h@t", AIDifficulty.EASY, seed=seed)
            if st.starting_player_index == 0:
                break
        else:
            pytest.skip("Could not find seed where human starts")

        gs = MemoryGameStore()
        state = create_game_vs_ai(gs, card_store, "h1", "h@t", AIDifficulty.EASY, seed=seed)
        human = state.players[0]
        state = submit_draft(gs, state.game_id, human.player_id, human.deal[:5])
        assert state.status == GameStatus.ACTIVE
        assert state.current_player_index == 0

        state = select_archetype(gs, state.game_id, human.player_id, Archetype.MARTIAL)

        card_key = state.players[0].hand[0]
        state = submit_move(
            gs, card_store, state.game_id, human.player_id,
            card_key, 0, state.state_version,
        )
        assert state.current_player_index == 1
        assert is_ai_turn(state)

        version_before = state.state_version
        with patch("asyncio.sleep", new_callable=AsyncMock):
            _run(execute_ai_turn(state.game_id, gs, card_store))

        after = gs.get_game(state.game_id)
        assert after is not None
        assert after.state_version > version_before
        placed_count = sum(1 for c in after.board if c is not None)
        assert placed_count == 2  # human + AI
