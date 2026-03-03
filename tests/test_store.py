"""Integration tests for GameStore/CardStore interfaces and in-memory implementations."""

import pytest

from app.models.cards import CardDefinition, CardSides
from app.models.game import GameState, GameStatus, PlayerState
from app.store import ConflictError
from app.store.memory import MemoryCardStore, MemoryGameStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_state(game_id: str, version: int = 0) -> GameState:
    return GameState(game_id=game_id, state_version=version)


def make_card(card_key: str = "card_a") -> CardDefinition:
    return CardDefinition(
        card_key=card_key,
        character_key="char_a",
        name="Card A",
        version="v1",
        tier=1,
        rarity=15,
        is_named=False,
        sides=CardSides(n=4, e=4, s=4, w=4),
        set="base",
        element="shadow",
    )


# ---------------------------------------------------------------------------
# MemoryGameStore tests
# ---------------------------------------------------------------------------


class TestMemoryGameStore:
    def test_create_and_get_game(self) -> None:
        store = MemoryGameStore()
        state = make_state("g1")
        store.create_game("g1", state)
        assert store.get_game("g1") == state

    def test_get_nonexistent_game_returns_none(self) -> None:
        store = MemoryGameStore()
        assert store.get_game("missing") is None

    def test_append_event_updates_state(self) -> None:
        store = MemoryGameStore()
        store.create_game("g1", make_state("g1", version=0))
        new_state = make_state("g1", version=1)
        store.append_event("g1", "move", {"x": 1}, expected_version=0, new_state=new_state)
        assert store.get_game("g1") == new_state

    def test_append_event_returns_event_with_correct_fields(self) -> None:
        store = MemoryGameStore()
        store.create_game("g1", make_state("g1"))
        event = store.append_event(
            "g1", "move", {"x": 1}, expected_version=0, new_state=make_state("g1", 1)
        )
        assert event.seq == 1
        assert event.game_id == "g1"
        assert event.event_type == "move"
        assert event.payload == {"x": 1}

    def test_seq_increments_across_events(self) -> None:
        store = MemoryGameStore()
        store.create_game("g1", make_state("g1"))
        e1 = store.append_event("g1", "e1", {}, expected_version=0, new_state=make_state("g1", 1))
        e2 = store.append_event("g1", "e2", {}, expected_version=1, new_state=make_state("g1", 2))
        assert e1.seq == 1
        assert e2.seq == 2

    def test_seq_is_independent_per_game(self) -> None:
        store = MemoryGameStore()
        store.create_game("g1", make_state("g1"))
        store.create_game("g2", make_state("g2"))
        store.append_event("g1", "e", {}, expected_version=0, new_state=make_state("g1", 1))
        e = store.append_event("g2", "e", {}, expected_version=0, new_state=make_state("g2", 1))
        assert e.seq == 1  # g2 starts at seq=1 independently

    def test_append_event_wrong_version_raises_conflict(self) -> None:
        store = MemoryGameStore()
        store.create_game("g1", make_state("g1", version=0))
        with pytest.raises(ConflictError):
            store.append_event("g1", "move", {}, expected_version=5, new_state=make_state("g1", 1))

    def test_append_event_to_missing_game_raises_key_error(self) -> None:
        store = MemoryGameStore()
        with pytest.raises(KeyError):
            store.append_event(
                "missing", "move", {}, expected_version=0, new_state=make_state("missing", 1)
            )

    def test_state_unchanged_after_conflict(self) -> None:
        store = MemoryGameStore()
        store.create_game("g1", make_state("g1", version=0))
        with pytest.raises(ConflictError):
            store.append_event("g1", "bad", {}, expected_version=99, new_state=make_state("g1", 1))
        assert store.get_game("g1").state_version == 0  # type: ignore[union-attr]

    def test_correct_version_succeeds_after_failed_attempt(self) -> None:
        store = MemoryGameStore()
        store.create_game("g1", make_state("g1", version=0))
        with pytest.raises(ConflictError):
            store.append_event("g1", "bad", {}, expected_version=99, new_state=make_state("g1", 1))
        # Correct version should still succeed
        store.append_event("g1", "good", {}, expected_version=0, new_state=make_state("g1", 1))
        assert store.get_game("g1").state_version == 1  # type: ignore[union-attr]

    def test_get_events_returns_all_in_order(self) -> None:
        store = MemoryGameStore()
        store.create_game("g1", make_state("g1"))
        store.append_event("g1", "e1", {"n": 1}, expected_version=0, new_state=make_state("g1", 1))
        store.append_event("g1", "e2", {"n": 2}, expected_version=1, new_state=make_state("g1", 2))
        events = store.get_events("g1")
        assert len(events) == 2
        assert events[0].seq == 1
        assert events[1].seq == 2

    def test_get_events_returns_independent_copy(self) -> None:
        store = MemoryGameStore()
        store.create_game("g1", make_state("g1"))
        events = store.get_events("g1")
        events.append(object())  # type: ignore[arg-type]
        assert len(store.get_events("g1")) == 0

    def test_get_events_unknown_game_returns_empty(self) -> None:
        store = MemoryGameStore()
        assert store.get_events("missing") == []


# ---------------------------------------------------------------------------
# MemoryCardStore tests
# ---------------------------------------------------------------------------


class TestMemoryCardStore:
    def test_get_existing_card(self) -> None:
        card = make_card("c1")
        store = MemoryCardStore([card])
        assert store.get_card("c1") == card

    def test_get_nonexistent_card_returns_none(self) -> None:
        store = MemoryCardStore([])
        assert store.get_card("missing") is None

    def test_list_cards_returns_all(self) -> None:
        cards = [make_card("c1"), make_card("c2")]
        store = MemoryCardStore(cards)
        listed = store.list_cards()
        assert len(listed) == 2
        assert {c.card_key for c in listed} == {"c1", "c2"}

    def test_list_cards_returns_independent_copy(self) -> None:
        store = MemoryCardStore([make_card("c1")])
        listed = store.list_cards()
        listed.append(make_card("c2"))
        assert len(store.list_cards()) == 1

    def test_empty_card_store(self) -> None:
        store = MemoryCardStore()
        assert store.list_cards() == []
        assert store.get_card("x") is None


# ---------------------------------------------------------------------------
# Integration: in-memory store + reducer
# ---------------------------------------------------------------------------


class TestIntegrationWithReducer:
    def test_full_move_flow_with_store(self) -> None:
        from random import Random

        from app.rules.reducer import PlacementIntent, apply_intent

        card = make_card("c1")
        card_lookup = {"c1": card}

        initial = GameState(
            game_id="g1",
            state_version=0,
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["c1"]),
                PlayerState(player_id="p1", hand=[]),
            ],
        )
        store = MemoryGameStore()
        store.create_game("g1", initial)

        intent = PlacementIntent(player_index=0, card_key="c1", cell_index=4)
        new_state = apply_intent(initial, intent, card_lookup, Random(42))

        store.append_event(
            "g1",
            "placement",
            {"player_index": 0, "card_key": "c1", "cell_index": 4},
            expected_version=0,
            new_state=new_state,
        )

        stored = store.get_game("g1")
        assert stored is not None
        assert stored.state_version == 1
        assert stored.board[4] is not None
        assert stored.board[4].card_key == "c1"

        events = store.get_events("g1")
        assert len(events) == 1
        assert events[0].event_type == "placement"
        assert events[0].seq == 1

    def test_optimistic_lock_prevents_double_apply(self) -> None:
        """Simulates two concurrent requests: only the first should succeed."""
        from random import Random

        from app.rules.reducer import PlacementIntent, apply_intent

        card_a = make_card("c_a")
        card_b = make_card("c_b")
        card_lookup = {"c_a": card_a, "c_b": card_b}

        initial = GameState(
            game_id="g2",
            state_version=0,
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["c_a"]),
                PlayerState(player_id="p1", hand=["c_b"]),
            ],
        )
        store = MemoryGameStore()
        store.create_game("g2", initial)

        # Both requests read state_version=0
        intent_a = PlacementIntent(player_index=0, card_key="c_a", cell_index=0)
        new_state_a = apply_intent(initial, intent_a, card_lookup, Random(1))

        # First request commits successfully
        store.append_event("g2", "placement", {}, expected_version=0, new_state=new_state_a)
        assert store.get_game("g2").state_version == 1  # type: ignore[union-attr]

        # Second request with stale version is rejected
        intent_b = PlacementIntent(player_index=0, card_key="c_a", cell_index=1)
        new_state_b = apply_intent(initial, intent_b, card_lookup, Random(2))
        with pytest.raises(ConflictError):
            store.append_event("g2", "placement", {}, expected_version=0, new_state=new_state_b)

        # State reflects only the first move
        assert store.get_game("g2").state_version == 1  # type: ignore[union-attr]
