"""Tests for POST /games/{id}/leave endpoint (US-028).

Covers:
- ACTIVE forfeit: append game_forfeited event, mark other player as winner
- WAITING delete: sole player leaves, game is removed
- Error cases: 404, 403, 409, 400
- Idempotency for ACTIVE forfeits
- delete_game store methods (MemoryGameStore + SupabaseGameStore via mock)
"""

from unittest.mock import MagicMock

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.auth import get_caller_id
from app.dependencies import get_card_store, get_game_store
from app.main import app
from app.models.cards import CardDefinition, CardSides
from app.store import ConflictError
from app.store.memory import MemoryCardStore, MemoryGameStore
from app.store.supabase_store import SupabaseGameStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_card(idx: int) -> CardDefinition:
    return CardDefinition(
        card_key=f"tc_{idx:03d}",
        character_key=f"ch_{idx:03d}",
        name=f"Card {idx}",
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


def _as(client: TestClient, user: str, method: str, path: str, **kwargs):  # type: ignore[no-untyped-def]
    return getattr(client, method)(path, headers={"X-User-Id": user}, **kwargs)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def game_store() -> MemoryGameStore:
    return MemoryGameStore()


@pytest.fixture()
def client(game_store: MemoryGameStore) -> TestClient:  # type: ignore[misc]
    card_store = MemoryCardStore(cards=_TEST_CARDS)
    app.dependency_overrides[get_game_store] = lambda: game_store
    app.dependency_overrides[get_card_store] = lambda: card_store
    app.dependency_overrides[get_caller_id] = _mock_caller_id
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


def _create_active_game(client: TestClient) -> tuple[str, str, str]:
    """Create an active game; p1 creates (auto-joins), p2 joins.

    Returns (game_id, p1_id, p2_id).
    """
    game_id = _as(client, "p1", "post", "/games", json={}).json()["game_id"]
    _as(client, "p2", "post", f"/games/{game_id}/join", json={})
    return game_id, "p1", "p2"


def _create_waiting_game(client: TestClient) -> tuple[str, str]:
    """Create a waiting game with one player. Returns (game_id, player_id)."""
    game_id = _as(client, "p1", "post", "/games", json={}).json()["game_id"]
    return game_id, "p1"


# ---------------------------------------------------------------------------
# ACTIVE forfeit tests
# ---------------------------------------------------------------------------


def test_leave_active_game_returns_complete_state(client: TestClient) -> None:
    game_id, p1, _p2 = _create_active_game(client)
    sv = _as(client, p1, "get", f"/games/{game_id}").json()["state_version"]

    resp = _as(client, p1, "post", f"/games/{game_id}/leave", json={"state_version": sv})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "complete"
    assert body["result"]["is_draw"] is False
    # p1 is index 0; p2 (index 1) wins
    assert body["result"]["winner"] == 1


def test_leave_active_game_appends_forfeited_event(
    client: TestClient, game_store: MemoryGameStore
) -> None:
    game_id, p1, p2 = _create_active_game(client)
    sv = _as(client, p1, "get", f"/games/{game_id}").json()["state_version"]

    _as(client, p1, "post", f"/games/{game_id}/leave", json={"state_version": sv})

    events = game_store.get_events(game_id)
    event_types = [e.event_type for e in events]
    assert "game_forfeited" in event_types

    forfeit = next(e for e in events if e.event_type == "game_forfeited")
    assert forfeit.payload["forfeit_by"] == p1
    assert forfeit.payload["winner"] == p2


def test_leave_active_game_second_player_can_forfeit(client: TestClient) -> None:
    game_id, _p1, p2 = _create_active_game(client)
    sv = _as(client, p2, "get", f"/games/{game_id}").json()["state_version"]

    resp = _as(client, p2, "post", f"/games/{game_id}/leave", json={"state_version": sv})

    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["winner"] == 0  # p1 (index 0) wins when p2 forfeits


# ---------------------------------------------------------------------------
# WAITING delete tests
# ---------------------------------------------------------------------------


def test_leave_waiting_game_returns_204(client: TestClient) -> None:
    game_id, p1 = _create_waiting_game(client)
    sv = _as(client, p1, "get", f"/games/{game_id}").json()["state_version"]

    resp = _as(client, p1, "post", f"/games/{game_id}/leave", json={"state_version": sv})

    assert resp.status_code == 204
    assert resp.content == b""


def test_leave_waiting_game_deletes_game(client: TestClient) -> None:
    game_id, p1 = _create_waiting_game(client)
    sv = _as(client, p1, "get", f"/games/{game_id}").json()["state_version"]

    _as(client, p1, "post", f"/games/{game_id}/leave", json={"state_version": sv})

    assert _as(client, p1, "get", f"/games/{game_id}").status_code == 404


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_leave_nonexistent_game_returns_404(client: TestClient) -> None:
    resp = _as(client, "p1", "post", "/games/no-such/leave", json={"state_version": 0})
    assert resp.status_code == 404


def test_leave_game_unknown_player_returns_403(client: TestClient) -> None:
    game_id, _p1, _p2 = _create_active_game(client)
    sv = _as(client, "p1", "get", f"/games/{game_id}").json()["state_version"]

    resp = _as(client, "stranger", "post", f"/games/{game_id}/leave", json={"state_version": sv})
    assert resp.status_code == 403


def test_leave_active_game_version_conflict_returns_409(client: TestClient) -> None:
    game_id, p1, _p2 = _create_active_game(client)

    resp = _as(client, p1, "post", f"/games/{game_id}/leave", json={"state_version": 9999})
    assert resp.status_code == 409


def test_leave_waiting_game_version_conflict_returns_409(client: TestClient) -> None:
    game_id, p1 = _create_waiting_game(client)

    resp = _as(client, p1, "post", f"/games/{game_id}/leave", json={"state_version": 9999})
    assert resp.status_code == 409


def test_leave_complete_game_returns_400(client: TestClient) -> None:
    game_id, p1, _p2 = _create_active_game(client)
    sv = _as(client, p1, "get", f"/games/{game_id}").json()["state_version"]
    # Forfeit the game
    _as(client, p1, "post", f"/games/{game_id}/leave", json={"state_version": sv})
    # Try to leave the now-complete game
    sv2 = _as(client, "p2", "get", f"/games/{game_id}").json()["state_version"]
    resp = _as(client, "p2", "post", f"/games/{game_id}/leave", json={"state_version": sv2})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_leave_active_game_idempotency(client: TestClient) -> None:
    game_id, p1, _p2 = _create_active_game(client)
    sv = _as(client, p1, "get", f"/games/{game_id}").json()["state_version"]

    payload = {"state_version": sv, "idempotency_key": "leave-001"}

    resp1 = _as(client, p1, "post", f"/games/{game_id}/leave", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "complete"

    # Retry with stale version — idempotency_key matches, returns current state
    stale_payload = {**payload, "state_version": 999}
    resp2 = _as(client, p1, "post", f"/games/{game_id}/leave", json=stale_payload)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "complete"


# ---------------------------------------------------------------------------
# MemoryGameStore.delete_game unit tests
# ---------------------------------------------------------------------------


class TestMemoryGameStoreDeleteGame:
    def test_delete_removes_game(self) -> None:
        store = MemoryGameStore()
        from app.models.game import GameState

        state = GameState(game_id="g1", state_version=0)
        store.create_game("g1", state)
        store.delete_game("g1", expected_version=0)
        assert store.get_game("g1") is None

    def test_delete_removes_events(self) -> None:
        store = MemoryGameStore()
        from app.models.game import GameState

        state = GameState(game_id="g1", state_version=0)
        store.create_game("g1", state)
        new_state = GameState(game_id="g1", state_version=1)
        store.append_event("g1", "e", {}, expected_version=0, new_state=new_state)
        store.delete_game("g1", expected_version=1)
        # After deletion, get_events returns [] for unknown game
        assert store.get_events("g1") == []

    def test_delete_missing_game_raises_key_error(self) -> None:
        store = MemoryGameStore()
        with pytest.raises(KeyError):
            store.delete_game("missing", expected_version=0)

    def test_delete_wrong_version_raises_conflict(self) -> None:
        store = MemoryGameStore()
        from app.models.game import GameState

        store.create_game("g1", GameState(game_id="g1", state_version=0))
        with pytest.raises(ConflictError):
            store.delete_game("g1", expected_version=99)

    def test_delete_state_unchanged_after_conflict(self) -> None:
        store = MemoryGameStore()
        from app.models.game import GameState

        store.create_game("g1", GameState(game_id="g1", state_version=0))
        with pytest.raises(ConflictError):
            store.delete_game("g1", expected_version=99)
        assert store.get_game("g1") is not None


# ---------------------------------------------------------------------------
# SupabaseGameStore.delete_game unit tests (mocked)
# ---------------------------------------------------------------------------


class TestSupabaseGameStoreDeleteGame:
    def _make_store_and_table(self) -> tuple[SupabaseGameStore, MagicMock]:
        client_mock = MagicMock()
        games_table = MagicMock()
        client_mock.table.side_effect = lambda name: games_table if name == "games" else MagicMock()
        store = SupabaseGameStore(client=client_mock)
        return store, games_table

    def test_delete_success(self) -> None:
        store, games_table = self._make_store_and_table()
        # DELETE returns one row → success
        chain = games_table.delete.return_value.eq.return_value.eq.return_value
        chain.execute.return_value.data = [{"id": "g1"}]

        store.delete_game("g1", expected_version=2)  # should not raise

    def test_delete_missing_game_raises_key_error(self) -> None:
        store, games_table = self._make_store_and_table()
        # DELETE returns empty → need follow-up check
        delete_chain = MagicMock()
        delete_chain.execute.return_value.data = []
        games_table.delete.return_value.eq.return_value.eq.return_value = delete_chain

        # follow-up select: game does not exist
        select_chain = MagicMock()
        select_chain.execute.return_value.data = None
        games_table.select.return_value.eq.return_value.maybe_single.return_value = select_chain

        with pytest.raises(KeyError):
            store.delete_game("g1", expected_version=2)

    def test_delete_version_conflict_raises_conflict_error(self) -> None:
        store, games_table = self._make_store_and_table()
        # DELETE returns empty
        delete_chain = MagicMock()
        delete_chain.execute.return_value.data = []
        games_table.delete.return_value.eq.return_value.eq.return_value = delete_chain

        # follow-up select: game exists with different version
        select_chain = MagicMock()
        select_chain.execute.return_value.data = {"state_version": 5}
        games_table.select.return_value.eq.return_value.maybe_single.return_value = select_chain

        with pytest.raises(ConflictError):
            store.delete_game("g1", expected_version=2)
