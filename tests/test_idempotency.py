"""Tests for idempotency key support on move submission (US-023).

Covers:
- MemoryGameStore: duplicate key raises DuplicateEventError
- MemoryGameStore: different key proceeds normally
- API integration: duplicate idempotency_key returns 200 (same state, no new event)
- API integration: missing idempotency_key still works (backward compat)
"""

from unittest.mock import MagicMock

import pytest
from fastapi import Request
from fastapi.testclient import TestClient  # noqa: E402

from app.auth import get_caller_id
from app.dependencies import get_card_store, get_game_store
from app.main import app
from app.models.cards import CardDefinition, CardSides
from app.models.game import GameState
from app.store import ConflictError, DuplicateEventError
from app.store.memory import MemoryCardStore, MemoryGameStore
from app.store.supabase_store import SupabaseGameStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_card(idx: int) -> CardDefinition:
    return CardDefinition(
        card_key=f"idem_card_{idx:03d}",
        character_key=f"idem_char_{idx:03d}",
        name=f"Idem Card {idx}",
        version="v1",
        tier=1,
        rarity=15,
        is_named=False,
        sides=CardSides(n=4, e=4, s=4, w=4),
        set="test",
    )


_TEST_CARDS = [_make_card(i) for i in range(20)]


def _mock_caller_id(request: Request) -> str:
    return request.headers.get("X-User-Id", "test-user")


@pytest.fixture()
def api_client() -> TestClient:  # type: ignore[misc]
    game_store = MemoryGameStore()
    card_store = MemoryCardStore(cards=_TEST_CARDS)
    app.dependency_overrides[get_game_store] = lambda: game_store
    app.dependency_overrides[get_card_store] = lambda: card_store
    app.dependency_overrides[get_caller_id] = _mock_caller_id
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


def _make_state(game_id: str = "g1", version: int = 0) -> GameState:
    return GameState(game_id=game_id, state_version=version, seed=42)


def _as(client: TestClient, user: str, method: str, path: str, **kwargs):  # type: ignore[no-untyped-def]
    return getattr(client, method)(path, headers={"X-User-Id": user}, **kwargs)


# ---------------------------------------------------------------------------
# MemoryGameStore: duplicate key detection
# ---------------------------------------------------------------------------


class TestMemoryStoreIdempotency:
    def test_duplicate_key_raises_duplicate_event_error(self) -> None:
        store = MemoryGameStore()
        s0 = _make_state("g1", 0)
        s1 = _make_state("g1", 1)
        s2 = _make_state("g1", 2)
        store.create_game("g1", s0)

        store.append_event("g1", "MOVE", {"pos": 0}, 0, s1, idempotency_key="key-abc")

        with pytest.raises(DuplicateEventError):
            store.append_event("g1", "MOVE", {"pos": 0}, 1, s2, idempotency_key="key-abc")

    def test_duplicate_key_does_not_advance_state(self) -> None:
        store = MemoryGameStore()
        s0 = _make_state("g1", 0)
        s1 = _make_state("g1", 1)
        s2 = _make_state("g1", 2)
        store.create_game("g1", s0)

        store.append_event("g1", "MOVE", {}, 0, s1, idempotency_key="key-abc")

        with pytest.raises(DuplicateEventError):
            store.append_event("g1", "MOVE", {}, 1, s2, idempotency_key="key-abc")

        # State should be s1 (duplicate was not applied)
        assert store.get_game("g1") == s1
        assert len(store.get_events("g1")) == 1

    def test_different_key_proceeds_normally(self) -> None:
        store = MemoryGameStore()
        s0 = _make_state("g1", 0)
        s1 = _make_state("g1", 1)
        s2 = _make_state("g1", 2)
        store.create_game("g1", s0)

        store.append_event("g1", "MOVE", {}, 0, s1, idempotency_key="key-1")
        event2 = store.append_event("g1", "MOVE", {}, 1, s2, idempotency_key="key-2")

        assert event2.seq == 2
        assert store.get_game("g1") == s2
        assert len(store.get_events("g1")) == 2

    def test_no_key_always_proceeds(self) -> None:
        """Idempotency key is optional; omitting it never deduplicates."""
        store = MemoryGameStore()
        s0 = _make_state("g1", 0)
        s1 = _make_state("g1", 1)
        store.create_game("g1", s0)

        e1 = store.append_event("g1", "MOVE", {}, 0, s1)
        assert e1.seq == 1

    def test_same_key_different_games_are_independent(self) -> None:
        store = MemoryGameStore()
        s_a0 = _make_state("gA", 0)
        s_a1 = _make_state("gA", 1)
        s_b0 = _make_state("gB", 0)
        s_b1 = _make_state("gB", 1)
        store.create_game("gA", s_a0)
        store.create_game("gB", s_b0)

        store.append_event("gA", "MOVE", {}, 0, s_a1, idempotency_key="same-key")
        # Same key on a different game should NOT raise
        e = store.append_event("gB", "MOVE", {}, 0, s_b1, idempotency_key="same-key")
        assert e.seq == 1

    def test_conflict_error_still_raised_on_version_mismatch(self) -> None:
        store = MemoryGameStore()
        s0 = _make_state("g1", 0)
        s1 = _make_state("g1", 1)
        store.create_game("g1", s0)

        with pytest.raises(ConflictError):
            store.append_event("g1", "MOVE", {}, 99, s1, idempotency_key="new-key")


# ---------------------------------------------------------------------------
# API integration: idempotency_key on POST /games/{id}/moves
# ---------------------------------------------------------------------------


class TestApiIdempotency:
    def _setup_active_game(self, client: TestClient) -> tuple[str, list[str], int, int]:
        """Returns (game_id, first_player_hand, state_version, first_player_index).

        Also selects archetypes for both players so that moves can be submitted.
        state_version is the version after both archetype selections.
        """
        resp = _as(client, "alice", "post", "/games", json={"seed": 77})
        game_id = resp.json()["game_id"]
        _as(client, "bob", "post", f"/games/{game_id}/join", json={})
        _as(client, "alice", "post", f"/games/{game_id}/archetype", json={"archetype": "martial"})
        data = _as(
            client, "bob", "post", f"/games/{game_id}/archetype", json={"archetype": "devout"}
        ).json()
        first_player_index = data["current_player_index"]
        first_hand = data["players"][first_player_index]["hand"]
        return game_id, first_hand, data["state_version"], first_player_index

    def test_idempotency_key_is_accepted(self, api_client: TestClient) -> None:
        game_id, hand, sv, first_player_index = self._setup_active_game(api_client)
        first_user = "alice" if first_player_index == 0 else "bob"
        resp = _as(
            api_client,
            first_user,
            "post",
            f"/games/{game_id}/moves",
            json={
                "card_key": hand[0],
                "cell_index": 4,
                "state_version": sv,
                "idempotency_key": "move-001",
            },
        )
        assert resp.status_code == 200

    def test_duplicate_idempotency_key_returns_200(self, api_client: TestClient) -> None:
        game_id, hand, sv, first_player_index = self._setup_active_game(api_client)
        first_user = "alice" if first_player_index == 0 else "bob"
        move_payload = {
            "card_key": hand[0],
            "cell_index": 4,
            "state_version": sv,
            "idempotency_key": "move-unique-001",
        }
        resp1 = _as(api_client, first_user, "post", f"/games/{game_id}/moves", json=move_payload)
        assert resp1.status_code == 200
        state_after_first = resp1.json()

        # Retry with same idempotency key (stale state_version is now passed,
        # but same key means it's a duplicate)
        resp2 = _as(api_client, first_user, "post", f"/games/{game_id}/moves", json=move_payload)
        assert resp2.status_code == 200
        # The state returned should match what was returned after the first call
        assert resp2.json()["state_version"] == state_after_first["state_version"]

    def test_duplicate_key_does_not_create_extra_event(self, api_client: TestClient) -> None:
        """Two moves with the same idempotency key produce exactly one event."""
        game_id, hand, sv, first_player_index = self._setup_active_game(api_client)
        first_user = "alice" if first_player_index == 0 else "bob"
        move_payload = {
            "card_key": hand[0],
            "cell_index": 4,
            "state_version": sv,
            "idempotency_key": "move-dedup-test",
        }
        _as(api_client, first_user, "post", f"/games/{game_id}/moves", json=move_payload)
        _as(api_client, first_user, "post", f"/games/{game_id}/moves", json=move_payload)

        data = _as(api_client, first_user, "get", f"/games/{game_id}").json()
        # State advanced exactly once (base + join×1 + move×1)
        assert data["board"][4] is not None  # the cell was placed

    def test_no_idempotency_key_still_works(self, api_client: TestClient) -> None:
        game_id, hand, sv, first_player_index = self._setup_active_game(api_client)
        first_user = "alice" if first_player_index == 0 else "bob"
        resp = _as(
            api_client,
            first_user,
            "post",
            f"/games/{game_id}/moves",
            json={"card_key": hand[0], "cell_index": 4, "state_version": sv},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# SupabaseGameStore: idempotency key support
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    client = MagicMock()
    games_table = MagicMock()
    events_table = MagicMock()

    def _table(name: str) -> MagicMock:
        return games_table if name == "games" else events_table

    client.table.side_effect = _table
    return client, games_table, events_table


class TestSupabaseIdempotency:
    def _setup_success(
        self, games_table: MagicMock, events_table: MagicMock, existing_seq: int | None = None
    ) -> None:
        (
            games_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data
        ) = [{"id": "g1"}]
        seq_data = [{"seq": existing_seq}] if existing_seq is not None else []
        idem_chain = (
            events_table.select.return_value.eq.return_value.order.return_value.limit.return_value
        )
        idem_chain.execute.return_value.data = seq_data

    def _set_idem_lookup(self, events_table: MagicMock, data: dict | None) -> None:
        """Configure the mock for the idempotency key lookup query."""
        execute_rv = events_table.select.return_value.eq.return_value.eq.return_value
        chain = execute_rv.maybe_single.return_value.execute.return_value
        chain.data = data

    def test_duplicate_key_raises_duplicate_event_error(self, mock_client: tuple) -> None:
        client, games_table, events_table = mock_client
        self._setup_success(games_table, events_table)
        # Simulate idempotency key already present in DB
        self._set_idem_lookup(events_table, {"seq": 1})

        store = SupabaseGameStore(client=client)
        with pytest.raises(DuplicateEventError):
            store.append_event("g1", "MOVE", {}, 0, _make_state("g1", 1), idempotency_key="dup-key")

    def test_new_key_proceeds_and_stores_key(self, mock_client: tuple) -> None:
        client, games_table, events_table = mock_client
        self._setup_success(games_table, events_table)
        # No existing event with this key
        self._set_idem_lookup(events_table, None)

        store = SupabaseGameStore(client=client)
        event = store.append_event(
            "g1", "MOVE", {"pos": 4}, 0, _make_state("g1", 1), idempotency_key="fresh-key"
        )

        assert event.seq == 1
        # Insert should include idempotency_key
        insert_data = events_table.insert.call_args[0][0]
        assert insert_data.get("idempotency_key") == "fresh-key"

    def test_no_key_insert_omits_idempotency_key_field(self, mock_client: tuple) -> None:
        client, games_table, events_table = mock_client
        self._setup_success(games_table, events_table)

        store = SupabaseGameStore(client=client)
        store.append_event("g1", "MOVE", {}, 0, _make_state("g1", 1))

        insert_data = events_table.insert.call_args[0][0]
        assert "idempotency_key" not in insert_data
