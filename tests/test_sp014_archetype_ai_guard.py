"""Tests for US-SP-014: AI waits for human archetype selection before moving.

Covers:
- is_ai_turn returns False when any player has archetype=None
- AI turn triggers from archetype endpoint (not draft) when AI goes first
- AI does not move after archetype if human goes first
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.models.game import (
    AIDifficulty,
    Archetype,
    GameStatus,
    PlayerState,
)
from app.services.game_service import (
    AI_PLAYER_ID,
    create_game_vs_ai,
    execute_ai_turn,
    is_ai_turn,
    select_archetype,
    submit_draft,
)
from app.store.memory import MemoryCardStore, MemoryGameStore
from tests.conftest import _TEST_CARDS, pick_valid_hand


@pytest.fixture()
def card_store() -> MemoryCardStore:
    return MemoryCardStore(cards=_TEST_CARDS)


def _run(coro):  # noqa: ANN001, ANN202
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestIsAiTurnArchetypeGuard:
    """is_ai_turn must return False when any player has archetype=None."""

    def test_false_when_human_has_no_archetype(self) -> None:
        """AI's turn, but human hasn't picked archetype yet → False."""
        from app.models.game import GameState

        state = GameState(
            game_id="g1",
            status=GameStatus.ACTIVE,
            current_player_index=1,
            players=[
                PlayerState(player_id="human", player_type="human", archetype=None),
                PlayerState(
                    player_id=AI_PLAYER_ID,
                    player_type="ai",
                    ai_difficulty=AIDifficulty.EASY,
                    archetype=Archetype.MARTIAL,
                ),
            ],
        )
        assert is_ai_turn(state) is False

    def test_true_when_all_archetypes_set(self) -> None:
        """AI's turn and all archetypes selected → True."""
        from app.models.game import GameState

        state = GameState(
            game_id="g1",
            status=GameStatus.ACTIVE,
            current_player_index=1,
            players=[
                PlayerState(
                    player_id="human",
                    player_type="human",
                    archetype=Archetype.SKULKER,
                ),
                PlayerState(
                    player_id=AI_PLAYER_ID,
                    player_type="ai",
                    ai_difficulty=AIDifficulty.EASY,
                    archetype=Archetype.MARTIAL,
                ),
            ],
        )
        assert is_ai_turn(state) is True


class TestAiTurnAfterArchetype:
    """AI turn should trigger from archetype endpoint, not from draft."""

    def test_ai_does_not_move_before_archetype(self, card_store: MemoryCardStore) -> None:
        """After draft in AI game where AI goes first, is_ai_turn is False (no archetype)."""
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
        hand = pick_valid_hand(human.deal, card_store)
        state = submit_draft(gs, card_store, state.game_id, human.player_id, hand)
        assert state.status == GameStatus.ACTIVE

        # AI should NOT move yet — human hasn't picked archetype
        assert is_ai_turn(state) is False

    def test_ai_moves_after_archetype_when_ai_goes_first(
        self, card_store: MemoryCardStore
    ) -> None:
        """After human selects archetype in AI-goes-first game, AI turn triggers."""
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
        hand = pick_valid_hand(human.deal, card_store)
        state = submit_draft(gs, card_store, state.game_id, human.player_id, hand)
        assert state.status == GameStatus.ACTIVE

        state = select_archetype(gs, state.game_id, human.player_id, Archetype.MARTIAL)

        # Now AI should be ready to move
        assert is_ai_turn(state) is True

        version_before = state.state_version
        with patch("asyncio.sleep", new_callable=AsyncMock):
            _run(execute_ai_turn(state.game_id, gs, card_store))

        after = gs.get_game(state.game_id)
        assert after is not None
        assert after.state_version > version_before
        placed = [c for c in after.board if c is not None]
        assert len(placed) == 1

    def test_ai_does_not_move_after_archetype_when_human_goes_first(
        self, card_store: MemoryCardStore
    ) -> None:
        """After human selects archetype in human-goes-first game, AI should not move."""
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
        hand = pick_valid_hand(human.deal, card_store)
        state = submit_draft(gs, card_store, state.game_id, human.player_id, hand)
        assert state.status == GameStatus.ACTIVE

        state = select_archetype(gs, state.game_id, human.player_id, Archetype.MARTIAL)

        # Human goes first, so AI should NOT move
        assert is_ai_turn(state) is False
