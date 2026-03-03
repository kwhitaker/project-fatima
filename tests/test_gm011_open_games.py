"""Tests for US-GM-011: open games in list + newest-first ordering."""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.auth import get_caller_id
from app.dependencies import get_card_store, get_game_store
from app.main import app
from app.models.cards import CardDefinition, CardSides
from app.store.memory import MemoryCardStore, MemoryGameStore


def _make_card(idx: int) -> CardDefinition:
    return CardDefinition(
        card_key=f"card_{idx:03d}",
        character_key=f"char_{idx:03d}",
        name=f"Card {idx}",
        version="v1",
        tier=1,
        rarity=15,
        is_named=False,
        sides=CardSides(n=4, e=4, s=4, w=4),
        set="test",
        element="shadow",
    )


_TEST_CARDS = [_make_card(i) for i in range(20)]


def _mock_caller_id(request: Request) -> str:
    return request.headers.get("X-User-Id", "test-user")


@pytest.fixture()
def client() -> TestClient:  # type: ignore[misc]
    game_store = MemoryGameStore()
    card_store = MemoryCardStore(cards=_TEST_CARDS)
    app.dependency_overrides[get_game_store] = lambda: game_store
    app.dependency_overrides[get_card_store] = lambda: card_store
    app.dependency_overrides[get_caller_id] = _mock_caller_id
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


def as_user(client: TestClient, user_id: str, method: str, path: str, **kwargs):  # type: ignore[no-untyped-def]
    return getattr(client, method)(path, headers={"X-User-Id": user_id}, **kwargs)


# ---------------------------------------------------------------------------
# Open games included in list for non-participants
# ---------------------------------------------------------------------------


def test_open_game_visible_to_non_participant(client: TestClient) -> None:
    """A WAITING game with 1 player appears in another user's game list."""
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]

    bob_games = as_user(client, "bob", "get", "/games").json()
    assert any(g["game_id"] == game_id for g in bob_games)


def test_own_waiting_game_not_duplicated(client: TestClient) -> None:
    """Creator's own WAITING game appears once (from own list, not open list)."""
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]

    alice_games = as_user(client, "alice", "get", "/games").json()
    ids = [g["game_id"] for g in alice_games]
    assert ids.count(game_id) == 1


# ---------------------------------------------------------------------------
# Exclusion rules
# ---------------------------------------------------------------------------


def test_active_game_not_in_open_list(client: TestClient) -> None:
    """ACTIVE games (2 players) do not appear as open games for third party."""
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    as_user(client, "bob", "post", f"/games/{game_id}/join", json={})

    charlie_games = as_user(client, "charlie", "get", "/games").json()
    assert not any(g["game_id"] == game_id for g in charlie_games)


def test_complete_game_not_in_open_list(client: TestClient) -> None:
    """COMPLETE games do not appear as open games."""
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    as_user(client, "bob", "post", f"/games/{game_id}/join", json={})
    # Forfeit to complete the game
    state = as_user(client, "alice", "get", f"/games/{game_id}").json()
    as_user(
        client,
        "alice",
        "post",
        f"/games/{game_id}/leave",
        json={"state_version": state["state_version"]},
    )

    charlie_games = as_user(client, "charlie", "get", "/games").json()
    assert not any(g["game_id"] == game_id for g in charlie_games)


# ---------------------------------------------------------------------------
# Sort order
# ---------------------------------------------------------------------------


def test_non_complete_games_before_complete(client: TestClient) -> None:
    """Non-complete (WAITING/ACTIVE) games appear before COMPLETE games."""
    # Create + complete a game (alice vs bob, alice forfeits)
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    completed_id = resp.json()["game_id"]
    as_user(client, "bob", "post", f"/games/{completed_id}/join", json={})
    state = as_user(client, "alice", "get", f"/games/{completed_id}").json()
    as_user(
        client,
        "alice",
        "post",
        f"/games/{completed_id}/leave",
        json={"state_version": state["state_version"]},
    )

    # Create a new WAITING game
    resp = as_user(client, "alice", "post", "/games", json={"seed": 2})
    waiting_id = resp.json()["game_id"]

    games = as_user(client, "alice", "get", "/games").json()
    statuses = [g["status"] for g in games]
    # WAITING should come before COMPLETE
    assert statuses.index("waiting") < statuses.index("complete")


def test_newest_first_within_status_group(client: TestClient) -> None:
    """Within non-complete games, newest game appears first."""
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    older_id = resp.json()["game_id"]

    resp = as_user(client, "alice", "post", "/games", json={"seed": 2})
    newer_id = resp.json()["game_id"]

    games = as_user(client, "alice", "get", "/games").json()
    ids = [g["game_id"] for g in games]
    assert ids.index(newer_id) < ids.index(older_id)


# ---------------------------------------------------------------------------
# created_at field
# ---------------------------------------------------------------------------


def test_created_at_set_on_new_game(client: TestClient) -> None:
    """Newly created games have a non-null created_at timestamp."""
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    assert resp.json()["created_at"] is not None


def test_created_at_present_in_list(client: TestClient) -> None:
    """created_at is included in the list response."""
    as_user(client, "alice", "post", "/games", json={"seed": 1})
    games = as_user(client, "alice", "get", "/games").json()
    assert games[0]["created_at"] is not None


# ---------------------------------------------------------------------------
# Open games show host info
# ---------------------------------------------------------------------------


def test_open_game_has_host_player(client: TestClient) -> None:
    """Open games in the list include the host player info."""
    as_user(client, "alice", "post", "/games", json={"seed": 1})
    bob_games = as_user(client, "bob", "get", "/games").json()
    open_game = bob_games[0]
    assert len(open_game["players"]) == 1
    assert open_game["players"][0]["player_id"] == "alice"
