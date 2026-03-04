"""Tests for US-UX-002: expose participant emails in GameState.

Covers:
- POST /games stores creator email in PlayerState
- POST /games/:id/join stores joiner email in PlayerState
- GET /games/:id returns player email fields
- GET /games returns player email fields
- Email is None when not provided (backward compat)
- Spectator blocking is not weakened
"""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.auth import get_caller_email
from app.main import app
from tests.conftest import _TEST_CARDS, _mock_caller_id


def _mock_caller_email(request: Request) -> str | None:
    return request.headers.get("X-User-Email", None)


@pytest.fixture()
def client(game_store):  # type: ignore[misc]
    """Custom client that also overrides get_caller_email."""
    from app.auth import get_caller_id as _get_caller_id
    from app.dependencies import get_card_store, get_game_store
    from app.store.memory import MemoryCardStore

    card_store = MemoryCardStore(cards=_TEST_CARDS)
    app.dependency_overrides[get_game_store] = lambda: game_store
    app.dependency_overrides[get_card_store] = lambda: card_store
    app.dependency_overrides[_get_caller_id] = _mock_caller_id
    app.dependency_overrides[get_caller_email] = _mock_caller_email
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


def as_user(
    client: TestClient,
    user_id: str,
    method: str,
    path: str,
    email: str | None = None,
    **kwargs,
):  # type: ignore[no-untyped-def]
    headers: dict[str, str] = {"X-User-Id": user_id}
    if email is not None:
        headers["X-User-Email"] = email
    return getattr(client, method)(path, headers=headers, **kwargs)


# ---------------------------------------------------------------------------
# Email stored on create
# ---------------------------------------------------------------------------


def test_create_game_stores_creator_email(client: TestClient) -> None:
    resp = as_user(client, "alice", "post", "/games", email="alice@test.com", json={"seed": 1})
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["players"]) == 1
    assert data["players"][0]["player_id"] == "alice"
    assert data["players"][0]["email"] == "alice@test.com"


def test_create_game_email_none_when_not_provided(client: TestClient) -> None:
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    assert resp.status_code == 201
    data = resp.json()
    assert data["players"][0]["email"] is None


# ---------------------------------------------------------------------------
# Email stored on join
# ---------------------------------------------------------------------------


def test_join_game_stores_joiner_email(client: TestClient) -> None:
    resp = as_user(client, "alice", "post", "/games", email="alice@test.com", json={"seed": 1})
    game_id = resp.json()["game_id"]
    resp = as_user(client, "bob", "post", f"/games/{game_id}/join", email="bob@test.com", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["players"][0]["email"] == "alice@test.com"
    assert data["players"][1]["email"] == "bob@test.com"


def test_join_game_preserves_creator_email(client: TestClient) -> None:
    """Creator's email must survive the deck-dealing update in join."""
    resp = as_user(client, "alice", "post", "/games", email="alice@example.org", json={"seed": 42})
    game_id = resp.json()["game_id"]
    resp = as_user(client, "bob", "post", f"/games/{game_id}/join", json={})
    data = resp.json()
    assert data["players"][0]["email"] == "alice@example.org"


# ---------------------------------------------------------------------------
# GET /games/:id returns emails
# ---------------------------------------------------------------------------


def test_get_game_returns_player_emails(client: TestClient) -> None:
    resp = as_user(client, "alice", "post", "/games", email="alice@test.com", json={"seed": 1})
    game_id = resp.json()["game_id"]
    as_user(client, "bob", "post", f"/games/{game_id}/join", email="bob@test.com", json={})

    resp = as_user(client, "alice", "get", f"/games/{game_id}", email="alice@test.com")
    assert resp.status_code == 200
    data = resp.json()
    emails = {p["player_id"]: p["email"] for p in data["players"]}
    assert emails["alice"] == "alice@test.com"
    assert emails["bob"] == "bob@test.com"


# ---------------------------------------------------------------------------
# GET /games list returns emails
# ---------------------------------------------------------------------------


def test_list_games_returns_player_emails(client: TestClient) -> None:
    resp = as_user(client, "alice", "post", "/games", email="alice@test.com", json={"seed": 1})
    game_id = resp.json()["game_id"]
    as_user(client, "bob", "post", f"/games/{game_id}/join", email="bob@test.com", json={})

    resp = as_user(client, "alice", "get", "/games", email="alice@test.com")
    assert resp.status_code == 200
    games = resp.json()
    game = next(g for g in games if g["game_id"] == game_id)
    emails = {p["player_id"]: p["email"] for p in game["players"]}
    assert emails["alice"] == "alice@test.com"
    assert emails["bob"] == "bob@test.com"


# ---------------------------------------------------------------------------
# Spectator blocking is not weakened
# ---------------------------------------------------------------------------


def test_spectator_still_blocked_on_active_game(client: TestClient) -> None:
    resp = as_user(client, "alice", "post", "/games", email="alice@test.com", json={"seed": 1})
    game_id = resp.json()["game_id"]
    resp = as_user(client, "bob", "post", f"/games/{game_id}/join", email="bob@test.com", json={})

    # After join, game is drafting (non-waiting) — spectators should be blocked
    assert resp.json()["status"] == "drafting"

    # Charlie (non-participant) is blocked
    resp = as_user(client, "charlie", "get", f"/games/{game_id}")
    assert resp.status_code == 403
