"""Integration tests for the game API endpoints.

Uses an in-memory store and mocked auth injected via dependency_overrides.
The mock auth dependency reads the X-User-Id header so individual requests
can impersonate different users.
"""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.auth import get_caller_id
from app.dependencies import get_card_store, get_game_store
from app.main import app
from app.models.cards import CardDefinition, CardSides
from app.store.memory import MemoryCardStore, MemoryGameStore


def _make_card(idx: int) -> CardDefinition:
    """Minimal valid common/tier-1 card: sides sum=16 (budget), each ≤ 6 (cap)."""
    return CardDefinition(
        card_key=f"test_card_{idx:03d}",
        character_key=f"char_{idx:03d}",
        name=f"Test Card {idx}",
        version="v1",
        tier=1,
        rarity=15,  # common bucket (1–49)
        is_named=False,
        sides=CardSides(n=4, e=4, s=4, w=4),
        set="test",
    )


# 20 unique cards → generate_matched_decks can fill two 10-card decks
_TEST_CARDS = [_make_card(i) for i in range(20)]


def _mock_caller_id(request: Request) -> str:
    """Test auth: read user identity from X-User-Id header."""
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


def _alice(client: TestClient, method: str, path: str, **kwargs):  # type: ignore[no-untyped-def]
    return getattr(client, method)(path, headers={"X-User-Id": "alice"}, **kwargs)


def _bob(client: TestClient, method: str, path: str, **kwargs):  # type: ignore[no-untyped-def]
    return getattr(client, method)(path, headers={"X-User-Id": "bob"}, **kwargs)


# ---------------------------------------------------------------------------
# Basic smoke tests
# ---------------------------------------------------------------------------


def test_create_game(client: TestClient) -> None:
    resp = _alice(client, "post", "/games", json={"seed": 42})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "waiting"
    assert data["seed"] == 42
    assert data["game_id"]
    # Creator is auto-joined as player 1
    assert len(data["players"]) == 1
    assert data["players"][0]["player_id"] == "alice"


def test_create_game_random_seed(client: TestClient) -> None:
    resp = _alice(client, "post", "/games", json={})
    assert resp.status_code == 201
    data = resp.json()
    assert isinstance(data["seed"], int)


def test_get_game_not_found(client: TestClient) -> None:
    resp = _alice(client, "get", "/games/nonexistent-id")
    assert resp.status_code == 404


def test_join_nonexistent_game(client: TestClient) -> None:
    resp = _bob(client, "post", "/games/bad-id/join", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Full happy path: create → join → archetype → play moves
# ---------------------------------------------------------------------------


def test_full_happy_path(client: TestClient) -> None:
    # 1. Alice creates (auto-joined as player 1 in WAITING state)
    resp = _alice(client, "post", "/games", json={"seed": 100})
    assert resp.status_code == 201
    game_id = resp.json()["game_id"]

    # 2. Bob joins → active, hands dealt
    resp = _bob(client, "post", f"/games/{game_id}/join", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert len(data["players"]) == 2
    alice_hand = data["players"][0]["hand"]
    bob_hand = data["players"][1]["hand"]
    assert len(alice_hand) == 10
    assert len(bob_hand) == 10

    # Determine who goes first (depends on seed)
    first_player_index = data["current_player_index"]
    first_hand = alice_hand if first_player_index == 0 else bob_hand
    second_user = "bob" if first_player_index == 0 else "alice"
    second_hand = bob_hand if first_player_index == 0 else alice_hand
    second_player_index = 1 - first_player_index

    # 3. Select archetypes (both players)
    resp = _alice(client, "post", f"/games/{game_id}/archetype", json={"archetype": "martial"})
    assert resp.status_code == 200
    resp = _bob(client, "post", f"/games/{game_id}/archetype", json={"archetype": "skulker"})
    assert resp.status_code == 200

    # 4. GET returns correct state
    resp = _alice(client, "get", f"/games/{game_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["players"][0]["archetype"] == "martial"
    assert data["players"][1]["archetype"] == "skulker"
    state_version = data["state_version"]

    # 5. First player plays
    first_client_method = "alice" if first_player_index == 0 else "bob"
    resp = (
        _alice(client, "post", f"/games/{game_id}/moves", json={
            "card_key": first_hand[0],
            "cell_index": 4,
            "state_version": state_version,
        })
        if first_client_method == "alice"
        else _bob(client, "post", f"/games/{game_id}/moves", json={
            "card_key": first_hand[0],
            "cell_index": 4,
            "state_version": state_version,
        })
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["board"][4] is not None
    assert data["board"][4]["owner"] == first_player_index
    # last_move should be populated with mists info
    assert data["last_move"] is not None
    assert data["last_move"]["mists_roll"] in range(1, 7)
    assert data["last_move"]["mists_effect"] in ("fog", "omen", "none", "fog_negated")
    state_version = data["state_version"]

    # 6. Second player plays
    resp = (
        _bob(client, "post", f"/games/{game_id}/moves", json={
            "card_key": second_hand[0],
            "cell_index": 0,
            "state_version": state_version,
        })
        if second_user == "bob"
        else _alice(client, "post", f"/games/{game_id}/moves", json={
            "card_key": second_hand[0],
            "cell_index": 0,
            "state_version": state_version,
        })
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["board"][0] is not None
    assert data["board"][0]["owner"] == second_player_index


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_409_on_stale_state_version(client: TestClient) -> None:
    resp = _alice(client, "post", "/games", json={"seed": 42})
    game_id = resp.json()["game_id"]
    _bob(client, "post", f"/games/{game_id}/join", json={})

    resp = _alice(client, "get", f"/games/{game_id}")
    data = resp.json()
    state_version = data["state_version"]
    first_player_index = data["current_player_index"]
    first_hand = data["players"][first_player_index]["hand"]

    # First move with correct version → success
    first_user_fn = _alice if first_player_index == 0 else _bob
    resp = first_user_fn(
        client,
        "post",
        f"/games/{game_id}/moves",
        json={"card_key": first_hand[0], "cell_index": 4, "state_version": state_version},
    )
    assert resp.status_code == 200

    # Retry with same (now stale) version → 409
    resp = first_user_fn(
        client,
        "post",
        f"/games/{game_id}/moves",
        json={"card_key": first_hand[1], "cell_index": 0, "state_version": state_version},
    )
    assert resp.status_code == 409


def test_cannot_join_twice(client: TestClient) -> None:
    resp = _alice(client, "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    # Alice tries to join her own game again
    resp = _alice(client, "post", f"/games/{game_id}/join", json={})
    assert resp.status_code == 400


def test_archetype_unknown_player_returns_403(client: TestClient) -> None:
    resp = _alice(client, "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    _bob(client, "post", f"/games/{game_id}/join", json={})
    # Charlie is not in the game
    resp = client.post(
        f"/games/{game_id}/archetype",
        headers={"X-User-Id": "charlie"},
        json={"archetype": "martial"},
    )
    assert resp.status_code == 403


def test_move_unknown_player_returns_403(client: TestClient) -> None:
    resp = _alice(client, "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    _bob(client, "post", f"/games/{game_id}/join", json={})
    resp = _alice(client, "get", f"/games/{game_id}")
    sv = resp.json()["state_version"]
    resp = client.post(
        f"/games/{game_id}/moves",
        headers={"X-User-Id": "charlie"},
        json={"card_key": "test_card_000", "cell_index": 0, "state_version": sv},
    )
    assert resp.status_code == 403


def test_wrong_turn_returns_422(client: TestClient) -> None:
    resp = _alice(client, "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    _bob(client, "post", f"/games/{game_id}/join", json={})
    resp = _alice(client, "get", f"/games/{game_id}")
    data = resp.json()
    sv = data["state_version"]
    first_player_index = data["current_player_index"]

    # Second player tries to go first → 422
    second_hand = data["players"][1 - first_player_index]["hand"]
    second_user_fn = _bob if first_player_index == 0 else _alice
    resp = second_user_fn(
        client,
        "post",
        f"/games/{game_id}/moves",
        json={"card_key": second_hand[0], "cell_index": 0, "state_version": sv},
    )
    assert resp.status_code == 422


def test_archetype_already_selected_returns_400(client: TestClient) -> None:
    resp = _alice(client, "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    _bob(client, "post", f"/games/{game_id}/join", json={})
    _alice(client, "post", f"/games/{game_id}/archetype", json={"archetype": "martial"})
    resp = _alice(client, "post", f"/games/{game_id}/archetype", json={"archetype": "caster"})
    assert resp.status_code == 400
