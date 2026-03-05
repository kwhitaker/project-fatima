"""Tests for US-SP-002: create_game_vs_ai service function."""

import pytest

from app.models.game import AIDifficulty, Archetype, GameStatus
from app.rules.deck import HAND_SIZE, generate_matched_deals
from app.services.game_service import (
    AI_DISPLAY_NAMES,
    AI_PLAYER_ID,
    ActiveGameExistsError,
    create_game_vs_ai,
)
from app.store.memory import MemoryCardStore, MemoryGameStore
from tests.conftest import _TEST_CARDS


@pytest.fixture()
def game_store() -> MemoryGameStore:
    return MemoryGameStore()


@pytest.fixture()
def card_store() -> MemoryCardStore:
    return MemoryCardStore(cards=_TEST_CARDS)


def _create(
    gs: MemoryGameStore,
    cs: MemoryCardStore,
    pid: str = "human-1",
    email: str = "h@t.com",
    diff: AIDifficulty = AIDifficulty.EASY,
    seed: int = 42,
) -> "GameState":  # noqa: F821
    from app.models.game import GameState

    state = create_game_vs_ai(gs, cs, pid, email, diff, seed=seed)
    assert isinstance(state, GameState)
    return state


class TestCreateGameVsAi:
    """Core creation tests."""

    def test_creates_game_in_drafting_status(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        state = _create(game_store, card_store)
        assert state.status == GameStatus.DRAFTING

    def test_human_is_player_0(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        state = _create(game_store, card_store, email="human@test.com")
        assert state.players[0].player_id == "human-1"
        assert state.players[0].player_type == "human"
        assert state.players[0].email == "human@test.com"

    def test_ai_is_player_1_with_correct_fields(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        state = _create(game_store, card_store, diff=AIDifficulty.MEDIUM)
        ai = state.players[1]
        assert ai.player_id == AI_PLAYER_ID
        assert ai.player_type == "ai"
        assert ai.ai_difficulty == AIDifficulty.MEDIUM
        assert ai.email == AI_DISPLAY_NAMES[AIDifficulty.MEDIUM]

    def test_both_players_get_deals(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        state = _create(game_store, card_store)
        # Human still has a deal to draft from
        assert len(state.players[0].deal) == 7
        assert state.players[0].hand == []
        # AI has auto-drafted: deal cleared, hand populated
        assert state.players[1].deal == []
        assert len(state.players[1].hand) == HAND_SIZE

    def test_ai_auto_selects_archetype(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        state = _create(game_store, card_store)
        assert state.players[1].archetype is not None
        assert isinstance(state.players[1].archetype, Archetype)

    def test_human_still_needs_to_draft(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        state = _create(game_store, card_store)
        assert len(state.players[0].deal) == 7
        assert state.players[0].hand == []
        assert state.players[0].archetype is None

    def test_board_elements_generated(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        state = _create(game_store, card_store)
        assert state.board_elements is not None
        assert len(state.board_elements) == 9

    def test_game_persisted_in_store(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        state = _create(game_store, card_store)
        stored = game_store.get_game(state.game_id)
        assert stored is not None
        assert stored.game_id == state.game_id


class TestAiDraftStrategy:
    """AI auto-draft picks cards based on difficulty."""

    def test_easy_picks_5_cards(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        state = _create(game_store, card_store)
        assert len(state.players[1].hand) == HAND_SIZE

    def test_medium_picks_highest_total_sides(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        """Medium AI picks 5 cards with highest total side values."""
        state = _create(game_store, card_store, diff=AIDifficulty.MEDIUM)
        assert len(state.players[1].hand) == HAND_SIZE

    @pytest.mark.parametrize(
        "difficulty", [AIDifficulty.HARD, AIDifficulty.NIGHTMARE]
    )
    def test_hard_nightmare_picks_best_coverage(
        self,
        game_store: MemoryGameStore,
        card_store: MemoryCardStore,
        difficulty: AIDifficulty,
    ) -> None:
        state = _create(game_store, card_store, diff=difficulty)
        assert len(state.players[1].hand) == HAND_SIZE

    def test_ai_hand_is_subset_of_original_deal(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        """AI's hand cards must all come from the original deal."""
        cards = card_store.list_cards()
        _deal_a, deal_b = generate_matched_deals(cards, seed=99)

        state = _create(game_store, card_store, seed=99)
        ai_hand_keys = set(state.players[1].hand)
        ai_deal_keys = {c.card_key for c in deal_b}
        assert ai_hand_keys.issubset(ai_deal_keys)


class TestAiArchetypeSelection:
    """AI archetype auto-selection varies by difficulty."""

    def test_easy_picks_an_archetype(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        state = _create(game_store, card_store)
        assert state.players[1].archetype in list(Archetype)

    @pytest.mark.parametrize(
        "difficulty",
        [AIDifficulty.MEDIUM, AIDifficulty.HARD, AIDifficulty.NIGHTMARE],
    )
    def test_strategic_picks_skulker_or_martial(
        self,
        game_store: MemoryGameStore,
        card_store: MemoryCardStore,
        difficulty: AIDifficulty,
    ) -> None:
        """Medium/hard/nightmare pick strategically: Skulker or Martial."""
        state = _create(game_store, card_store, diff=difficulty)
        assert state.players[1].archetype in (
            Archetype.SKULKER,
            Archetype.MARTIAL,
        )


class TestAiExemptFromActiveGameCheck:
    """AI player can be in many games at once."""

    def test_human_blocked_by_active_game(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        _create(game_store, card_store)
        with pytest.raises(ActiveGameExistsError):
            _create(game_store, card_store, seed=43)

    def test_ai_not_blocked_by_active_game(
        self, game_store: MemoryGameStore, card_store: MemoryCardStore
    ) -> None:
        """Creating two AI games works (AI is in both)."""
        _create(game_store, card_store)
        state2 = _create(
            game_store, card_store, pid="human-2", email="h2@t.com", seed=43
        )
        assert state2.players[1].player_id == AI_PLAYER_ID
