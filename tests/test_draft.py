"""Tests for US-DR-003: draft phase (deal 8, keep 5)."""

import pytest

from app.models.game import GameState, GameStatus, PlayerState
from app.rules.deck import DEAL_SIZE, HAND_SIZE
from app.services.game_service import submit_draft
from app.store.memory import MemoryGameStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_drafting_state(
    game_id: str = "test-draft",
    deal_a: list[str] | None = None,
    deal_b: list[str] | None = None,
) -> GameState:
    """Build a DRAFTING state with two players and 8-card deals."""
    if deal_a is None:
        deal_a = [f"a{i}" for i in range(DEAL_SIZE)]
    if deal_b is None:
        deal_b = [f"b{i}" for i in range(DEAL_SIZE)]
    return GameState(
        game_id=game_id,
        status=GameStatus.DRAFTING,
        state_version=2,
        players=[
            PlayerState(player_id="alice", deal=deal_a),
            PlayerState(player_id="bob", deal=deal_b),
        ],
        starting_player_index=0,
        current_player_index=0,
        seed=42,
    )


def _store_with_state(state: GameState) -> MemoryGameStore:
    store = MemoryGameStore()
    store.create_game(state.game_id, state)
    return store


# ---------------------------------------------------------------------------
# Valid submission
# ---------------------------------------------------------------------------


def test_submit_draft_sets_hand_and_clears_deal() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)
    selected = state.players[0].deal[:HAND_SIZE]

    result = submit_draft(store, "test-draft", "alice", selected)

    assert result.players[0].hand == selected
    assert result.players[0].deal == []


def test_submit_draft_stays_drafting_until_both_submit() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    result = submit_draft(store, "test-draft", "alice", state.players[0].deal[:HAND_SIZE])
    assert result.status == GameStatus.DRAFTING


def test_both_drafts_transitions_to_active() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    submit_draft(store, "test-draft", "alice", state.players[0].deal[:HAND_SIZE])
    result = submit_draft(store, "test-draft", "bob", state.players[1].deal[:HAND_SIZE])

    assert result.status == GameStatus.ACTIVE
    assert len(result.players[0].hand) == HAND_SIZE
    assert len(result.players[1].hand) == HAND_SIZE
    assert result.players[0].deal == []
    assert result.players[1].deal == []


def test_draft_bumps_state_version() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    result = submit_draft(store, "test-draft", "alice", state.players[0].deal[:HAND_SIZE])
    assert result.state_version == state.state_version + 1


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_wrong_card_count_raises() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    with pytest.raises(ValueError, match=f"{HAND_SIZE}"):
        submit_draft(store, "test-draft", "alice", state.players[0].deal[:3])


def test_card_not_in_deal_raises() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    bad_selection = state.players[0].deal[:4] + ["not_in_deal"]
    with pytest.raises(ValueError, match="not in your deal"):
        submit_draft(store, "test-draft", "alice", bad_selection)


def test_duplicate_cards_in_selection_raises() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    duped = [state.players[0].deal[0]] * HAND_SIZE
    with pytest.raises(ValueError, match="Duplicate"):
        submit_draft(store, "test-draft", "alice", duped)


def test_double_submit_raises() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    submit_draft(store, "test-draft", "alice", state.players[0].deal[:HAND_SIZE])
    with pytest.raises(ValueError, match="already submitted"):
        submit_draft(store, "test-draft", "alice", state.players[0].deal[:HAND_SIZE])


def test_not_in_game_raises() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    with pytest.raises(PermissionError, match="not in this game"):
        submit_draft(store, "test-draft", "charlie", ["c0", "c1", "c2", "c3", "c4"])


def test_wrong_status_raises() -> None:
    state = _make_drafting_state()
    state = state.model_copy(update={"status": GameStatus.ACTIVE})
    store = _store_with_state(state)

    with pytest.raises(ValueError, match="DRAFTING"):
        submit_draft(store, "test-draft", "alice", state.players[0].deal[:HAND_SIZE])


def test_game_not_found_raises() -> None:
    store = MemoryGameStore()
    with pytest.raises(KeyError):
        submit_draft(store, "nonexistent", "alice", ["c0", "c1", "c2", "c3", "c4"])
