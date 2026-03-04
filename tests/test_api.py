"""Integration tests for the game API endpoints.

Uses an in-memory store and mocked auth injected via dependency_overrides.
The mock auth dependency reads the X-User-Id header so individual requests
can impersonate different users.
"""

from fastapi.testclient import TestClient


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


# ---------------------------------------------------------------------------
# Full happy path: create → join → archetype → play moves
# ---------------------------------------------------------------------------


def test_full_happy_path(client: TestClient) -> None:
    # 1. Alice creates (auto-joined as player 1 in WAITING state)
    resp = _alice(client, "post", "/games", json={"seed": 100})
    assert resp.status_code == 201
    game_id = resp.json()["game_id"]

    # 2. Bob joins → drafting, deals assigned
    resp = _bob(client, "post", f"/games/{game_id}/join", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "drafting"
    assert len(data["players"]) == 2
    alice_deal = data["players"][0]["deal"]
    bob_deal = data["players"][1]["deal"]
    assert len(alice_deal) == 7
    assert len(bob_deal) == 7

    # 3. Both players submit draft (pick first 5 cards)
    resp = _alice(
        client, "post", f"/games/{game_id}/draft",
        json={"selected_cards": alice_deal[:5]},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "drafting"  # Bob hasn't drafted yet

    resp = _bob(
        client, "post", f"/games/{game_id}/draft",
        json={"selected_cards": bob_deal[:5]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"  # Both drafted → active

    alice_hand = data["players"][0]["hand"]
    bob_hand = data["players"][1]["hand"]
    assert len(alice_hand) == 5
    assert len(bob_hand) == 5

    # Determine who goes first (depends on seed)
    first_player_index = data["current_player_index"]
    first_hand = alice_hand if first_player_index == 0 else bob_hand
    second_user = "bob" if first_player_index == 0 else "alice"
    second_hand = bob_hand if first_player_index == 0 else alice_hand
    second_player_index = 1 - first_player_index

    # 4. Select archetypes (both players)
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
        _alice(
            client,
            "post",
            f"/games/{game_id}/moves",
            json={
                "card_key": first_hand[0],
                "cell_index": 4,
                "state_version": state_version,
            },
        )
        if first_client_method == "alice"
        else _bob(
            client,
            "post",
            f"/games/{game_id}/moves",
            json={
                "card_key": first_hand[0],
                "cell_index": 4,
                "state_version": state_version,
            },
        )
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
        _bob(
            client,
            "post",
            f"/games/{game_id}/moves",
            json={
                "card_key": second_hand[0],
                "cell_index": 0,
                "state_version": state_version,
            },
        )
        if second_user == "bob"
        else _alice(
            client,
            "post",
            f"/games/{game_id}/moves",
            json={
                "card_key": second_hand[0],
                "cell_index": 0,
                "state_version": state_version,
            },
        )
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["board"][0] is not None
    assert data["board"][0]["owner"] == second_player_index


# ---------------------------------------------------------------------------
# Error cases (unique to this file — duplicated scenarios live in
# test_error_responses.py which tests them more systematically)
# ---------------------------------------------------------------------------


def test_cannot_join_twice(client: TestClient) -> None:
    resp = _alice(client, "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    # Alice tries to join her own game again — blocked by active-game constraint (409)
    resp = _alice(client, "post", f"/games/{game_id}/join", json={})
    assert resp.status_code == 409


def test_archetype_already_selected_returns_400(client: TestClient) -> None:
    resp = _alice(client, "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    _bob(client, "post", f"/games/{game_id}/join", json={})
    _alice(client, "post", f"/games/{game_id}/archetype", json={"archetype": "martial"})
    resp = _alice(client, "post", f"/games/{game_id}/archetype", json={"archetype": "caster"})
    assert resp.status_code == 400
