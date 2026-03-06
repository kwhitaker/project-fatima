"""Tests for draft phase (deal 8, keep 5) and hand tier constraints (US-DR-002)."""

import pytest

from app.models.cards import CardDefinition, CardSides
from app.models.game import GameState, GameStatus, PlayerState
from app.rules.deck import HAND_SIZE
from app.services.game_service import submit_draft
from app.store.memory import MemoryCardStore, MemoryGameStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _card(key: str, tier: int = 1) -> CardDefinition:
    """Minimal card with controllable tier."""
    return CardDefinition(
        card_key=key,
        character_key=key,
        name=key,
        version="v1",
        tier=tier,
        rarity=15,
        is_named=False,
        sides=CardSides(n=4, e=4, s=4, w=4),
        set="test",
        element="shadow",
    )


# Deal layout: 2xT3, 3xT2, 3xT1  (matches DEAL_TIER_SLOTS)
_DEAL_A_CARDS = [
    _card("a_t3_0", tier=3), _card("a_t3_1", tier=3),
    _card("a_t2_0", tier=2), _card("a_t2_1", tier=2), _card("a_t2_2", tier=2),
    _card("a_t1_0", tier=1), _card("a_t1_1", tier=1), _card("a_t1_2", tier=1),
]
_DEAL_B_CARDS = [
    _card("b_t3_0", tier=3), _card("b_t3_1", tier=3),
    _card("b_t2_0", tier=2), _card("b_t2_1", tier=2), _card("b_t2_2", tier=2),
    _card("b_t1_0", tier=1), _card("b_t1_1", tier=1), _card("b_t1_2", tier=1),
]
_ALL_CARDS = _DEAL_A_CARDS + _DEAL_B_CARDS
_DEAL_A_KEYS = [c.card_key for c in _DEAL_A_CARDS]
_DEAL_B_KEYS = [c.card_key for c in _DEAL_B_CARDS]

# A valid hand: 1 T3 + 2 T2 + 2 T1
_VALID_HAND_A = [_DEAL_A_KEYS[0], _DEAL_A_KEYS[2], _DEAL_A_KEYS[3],
                 _DEAL_A_KEYS[5], _DEAL_A_KEYS[6]]
_VALID_HAND_B = [_DEAL_B_KEYS[0], _DEAL_B_KEYS[2], _DEAL_B_KEYS[3],
                 _DEAL_B_KEYS[5], _DEAL_B_KEYS[6]]


def _make_drafting_state(
    game_id: str = "test-draft",
    deal_a: list[str] | None = None,
    deal_b: list[str] | None = None,
) -> GameState:
    """Build a DRAFTING state with two players and 8-card deals."""
    if deal_a is None:
        deal_a = _DEAL_A_KEYS
    if deal_b is None:
        deal_b = _DEAL_B_KEYS
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


def _card_store() -> MemoryCardStore:
    return MemoryCardStore(cards=_ALL_CARDS)


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

    result = submit_draft(store, _card_store(), "test-draft", "alice", _VALID_HAND_A)

    assert result.players[0].hand == _VALID_HAND_A
    assert result.players[0].deal == []


def test_submit_draft_stays_drafting_until_both_submit() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    result = submit_draft(store, _card_store(), "test-draft", "alice", _VALID_HAND_A)
    assert result.status == GameStatus.DRAFTING


def test_both_drafts_transitions_to_active() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)
    cs = _card_store()

    submit_draft(store, cs, "test-draft", "alice", _VALID_HAND_A)
    result = submit_draft(store, cs, "test-draft", "bob", _VALID_HAND_B)

    assert result.status == GameStatus.ACTIVE
    assert len(result.players[0].hand) == HAND_SIZE
    assert len(result.players[1].hand) == HAND_SIZE
    assert result.players[0].deal == []
    assert result.players[1].deal == []


def test_draft_bumps_state_version() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    result = submit_draft(store, _card_store(), "test-draft", "alice", _VALID_HAND_A)
    assert result.state_version == state.state_version + 1


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_wrong_card_count_raises() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    with pytest.raises(ValueError, match=f"{HAND_SIZE}"):
        submit_draft(store, _card_store(), "test-draft", "alice", _DEAL_A_KEYS[:3])


def test_card_not_in_deal_raises() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    bad_selection = _DEAL_A_KEYS[:4] + ["not_in_deal"]
    with pytest.raises(ValueError, match="not in your deal"):
        submit_draft(store, _card_store(), "test-draft", "alice", bad_selection)


def test_duplicate_cards_in_selection_raises() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    duped = [_DEAL_A_KEYS[0]] * HAND_SIZE
    with pytest.raises(ValueError, match="Duplicate"):
        submit_draft(store, _card_store(), "test-draft", "alice", duped)


def test_double_submit_raises() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)
    cs = _card_store()

    submit_draft(store, cs, "test-draft", "alice", _VALID_HAND_A)
    with pytest.raises(ValueError, match="already submitted"):
        submit_draft(store, cs, "test-draft", "alice", _VALID_HAND_A)


def test_not_in_game_raises() -> None:
    state = _make_drafting_state()
    store = _store_with_state(state)

    with pytest.raises(PermissionError, match="not in this game"):
        submit_draft(store, _card_store(), "test-draft", "charlie", ["c0", "c1", "c2", "c3", "c4"])


def test_wrong_status_raises() -> None:
    state = _make_drafting_state()
    state = state.model_copy(update={"status": GameStatus.ACTIVE})
    store = _store_with_state(state)

    with pytest.raises(ValueError, match="DRAFTING"):
        submit_draft(store, _card_store(), "test-draft", "alice", _VALID_HAND_A)


def test_game_not_found_raises() -> None:
    store = MemoryGameStore()
    with pytest.raises(KeyError):
        submit_draft(store, _card_store(), "nonexistent", "alice", ["c0", "c1", "c2", "c3", "c4"])


# ---------------------------------------------------------------------------
# Hand tier constraints (US-DR-002)
# ---------------------------------------------------------------------------


def test_two_t3_cards_raises() -> None:
    """Selecting 2 T3 cards violates the max-1-T3 constraint."""
    state = _make_drafting_state()
    store = _store_with_state(state)

    # 2xT3 + 2xT2 + 1xT1
    hand = [_DEAL_A_KEYS[0], _DEAL_A_KEYS[1],  # T3, T3
            _DEAL_A_KEYS[2], _DEAL_A_KEYS[3],   # T2, T2
            _DEAL_A_KEYS[5]]                     # T1
    with pytest.raises(ValueError, match="Too many Tier 3"):
        submit_draft(store, _card_store(), "test-draft", "alice", hand)


def test_three_t2_cards_raises() -> None:
    """Selecting 3 T2 cards violates the max-2-T2 constraint."""
    state = _make_drafting_state()
    store = _store_with_state(state)

    # 0xT3 + 3xT2 + 2xT1
    hand = [_DEAL_A_KEYS[2], _DEAL_A_KEYS[3], _DEAL_A_KEYS[4],  # T2, T2, T2
            _DEAL_A_KEYS[5], _DEAL_A_KEYS[6]]                    # T1, T1
    with pytest.raises(ValueError, match="Too many Tier 2"):
        submit_draft(store, _card_store(), "test-draft", "alice", hand)


def test_valid_hand_1t3_2t2_2t1_passes() -> None:
    """1 T3 + 2 T2 + 2 T1 is a valid hand."""
    state = _make_drafting_state()
    store = _store_with_state(state)

    result = submit_draft(store, _card_store(), "test-draft", "alice", _VALID_HAND_A)
    assert result.players[0].hand == _VALID_HAND_A


def test_valid_hand_0t3_2t2_3t1_passes() -> None:
    """0 T3 + 2 T2 + 3 T1 is a valid hand."""
    state = _make_drafting_state()
    store = _store_with_state(state)

    # 0xT3 + 2xT2 + 3xT1
    hand = [_DEAL_A_KEYS[2], _DEAL_A_KEYS[3],  # T2, T2
            _DEAL_A_KEYS[5], _DEAL_A_KEYS[6], _DEAL_A_KEYS[7]]  # T1, T1, T1
    result = submit_draft(store, _card_store(), "test-draft", "alice", hand)
    assert result.players[0].hand == hand
