"""Integration tests for the game API endpoints (US-020).

Uses an in-memory store injected via dependency_overrides; no Supabase required.
"""

import pytest
from fastapi.testclient import TestClient

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


@pytest.fixture()
def client() -> TestClient:  # type: ignore[misc]
    game_store = MemoryGameStore()
    card_store = MemoryCardStore(cards=_TEST_CARDS)
    app.dependency_overrides[get_game_store] = lambda: game_store
    app.dependency_overrides[get_card_store] = lambda: card_store
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Basic smoke tests
# ---------------------------------------------------------------------------


def test_create_game(client: TestClient) -> None:
    resp = client.post("/games", json={"seed": 42})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "waiting"
    assert data["seed"] == 42
    assert data["game_id"]


def test_create_game_random_seed(client: TestClient) -> None:
    resp = client.post("/games", json={})
    assert resp.status_code == 201
    data = resp.json()
    assert isinstance(data["seed"], int)


def test_get_game_not_found(client: TestClient) -> None:
    resp = client.get("/games/nonexistent-id")
    assert resp.status_code == 404


def test_join_nonexistent_game(client: TestClient) -> None:
    resp = client.post("/games/bad-id/join", json={"player_id": "alice"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Full happy path: create → join → archetype → play moves
# ---------------------------------------------------------------------------


def test_full_happy_path(client: TestClient) -> None:
    # 1. Create
    resp = client.post("/games", json={"seed": 100})
    assert resp.status_code == 201
    game_id = resp.json()["game_id"]

    # 2. Player 1 joins — still waiting
    resp = client.post(f"/games/{game_id}/join", json={"player_id": "alice"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "waiting"
    assert len(data["players"]) == 1

    # 3. Player 2 joins → active, hands dealt
    resp = client.post(f"/games/{game_id}/join", json={"player_id": "bob"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert len(data["players"]) == 2
    alice_hand = data["players"][0]["hand"]
    bob_hand = data["players"][1]["hand"]
    assert len(alice_hand) == 10
    assert len(bob_hand) == 10

    # 4. Select archetypes
    resp = client.post(
        f"/games/{game_id}/archetype",
        json={"player_id": "alice", "archetype": "martial"},
    )
    assert resp.status_code == 200
    resp = client.post(
        f"/games/{game_id}/archetype",
        json={"player_id": "bob", "archetype": "skulker"},
    )
    assert resp.status_code == 200

    # 5. GET returns correct state
    resp = client.get(f"/games/{game_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["players"][0]["archetype"] == "martial"
    assert data["players"][1]["archetype"] == "skulker"
    state_version = data["state_version"]

    # 6. Alice plays (player_index 0, centre cell)
    resp = client.post(
        f"/games/{game_id}/moves",
        json={
            "player_id": "alice",
            "card_key": alice_hand[0],
            "cell_index": 4,
            "state_version": state_version,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["board"][4] is not None
    assert data["board"][4]["owner"] == 0
    state_version = data["state_version"]

    # 7. Bob plays
    resp = client.post(
        f"/games/{game_id}/moves",
        json={
            "player_id": "bob",
            "card_key": bob_hand[0],
            "cell_index": 0,
            "state_version": state_version,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["board"][0] is not None
    assert data["board"][0]["owner"] == 1


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_409_on_stale_state_version(client: TestClient) -> None:
    resp = client.post("/games", json={"seed": 42})
    game_id = resp.json()["game_id"]
    client.post(f"/games/{game_id}/join", json={"player_id": "alice"})
    client.post(f"/games/{game_id}/join", json={"player_id": "bob"})

    resp = client.get(f"/games/{game_id}")
    data = resp.json()
    alice_hand = data["players"][0]["hand"]
    state_version = data["state_version"]

    # First move with correct version → success
    resp = client.post(
        f"/games/{game_id}/moves",
        json={
            "player_id": "alice",
            "card_key": alice_hand[0],
            "cell_index": 4,
            "state_version": state_version,
        },
    )
    assert resp.status_code == 200

    # Retry with same (now stale) version → 409
    resp = client.post(
        f"/games/{game_id}/moves",
        json={
            "player_id": "alice",
            "card_key": alice_hand[1],
            "cell_index": 0,
            "state_version": state_version,
        },
    )
    assert resp.status_code == 409


def test_cannot_join_twice(client: TestClient) -> None:
    resp = client.post("/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    client.post(f"/games/{game_id}/join", json={"player_id": "alice"})
    resp = client.post(f"/games/{game_id}/join", json={"player_id": "alice"})
    assert resp.status_code == 400


def test_archetype_unknown_player_returns_403(client: TestClient) -> None:
    resp = client.post("/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    client.post(f"/games/{game_id}/join", json={"player_id": "alice"})
    client.post(f"/games/{game_id}/join", json={"player_id": "bob"})
    resp = client.post(
        f"/games/{game_id}/archetype",
        json={"player_id": "charlie", "archetype": "martial"},
    )
    assert resp.status_code == 403


def test_move_unknown_player_returns_403(client: TestClient) -> None:
    resp = client.post("/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    client.post(f"/games/{game_id}/join", json={"player_id": "alice"})
    client.post(f"/games/{game_id}/join", json={"player_id": "bob"})
    resp = client.get(f"/games/{game_id}")
    sv = resp.json()["state_version"]
    resp = client.post(
        f"/games/{game_id}/moves",
        json={
            "player_id": "charlie",
            "card_key": "test_card_000",
            "cell_index": 0,
            "state_version": sv,
        },
    )
    assert resp.status_code == 403


def test_wrong_turn_returns_422(client: TestClient) -> None:
    resp = client.post("/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    client.post(f"/games/{game_id}/join", json={"player_id": "alice"})
    client.post(f"/games/{game_id}/join", json={"player_id": "bob"})
    resp = client.get(f"/games/{game_id}")
    data = resp.json()
    bob_hand = data["players"][1]["hand"]
    sv = data["state_version"]

    # Bob tries to go first (alice's turn) → 422
    resp = client.post(
        f"/games/{game_id}/moves",
        json={
            "player_id": "bob",
            "card_key": bob_hand[0],
            "cell_index": 0,
            "state_version": sv,
        },
    )
    assert resp.status_code == 422


def test_archetype_already_selected_returns_400(client: TestClient) -> None:
    resp = client.post("/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    client.post(f"/games/{game_id}/join", json={"player_id": "alice"})
    client.post(f"/games/{game_id}/join", json={"player_id": "bob"})
    client.post(
        f"/games/{game_id}/archetype",
        json={"player_id": "alice", "archetype": "martial"},
    )
    resp = client.post(
        f"/games/{game_id}/archetype",
        json={"player_id": "alice", "archetype": "caster"},
    )
    assert resp.status_code == 400
