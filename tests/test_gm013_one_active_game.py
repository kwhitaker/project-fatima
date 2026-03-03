"""Tests for US-GM-013: limit users to one non-complete game at a time.

Covers:
- Block create when caller has a WAITING game → 409 with existing game_id
- Block create when caller has an ACTIVE game → 409 with existing game_id
- Allow create when caller only has COMPLETE games
- Block join when caller has a WAITING game → 409 with existing game_id
- Block join when caller has an ACTIVE game → 409 with existing game_id
- Allow join when caller only has COMPLETE games
"""

from fastapi.testclient import TestClient


def as_user(client: TestClient, user_id: str, method: str, path: str, **kwargs):  # type: ignore[no-untyped-def]
    return getattr(client, method)(path, headers={"X-User-Id": user_id}, **kwargs)


def _complete_game(client: TestClient, creator: str, joiner: str, seed: int = 1) -> str:
    """Create, join, select archetypes, play all 9 moves to completion."""
    resp = as_user(client, creator, "post", "/games", json={"seed": seed})
    game_id = resp.json()["game_id"]
    as_user(client, joiner, "post", f"/games/{game_id}/join", json={})
    as_user(client, creator, "post", f"/games/{game_id}/archetype", json={"archetype": "martial"})
    as_user(client, joiner, "post", f"/games/{game_id}/archetype", json={"archetype": "devout"})

    # Play 9 moves
    for _ in range(9):
        state = as_user(client, creator, "get", f"/games/{game_id}").json()
        if state["status"] == "complete":
            return game_id
        cp = state["current_player_index"]
        player_id = creator if cp == 0 else joiner
        hand = state["players"][cp]["hand"]
        empty = [i for i, c in enumerate(state["board"]) if c is None]
        resp = as_user(
            client,
            player_id,
            "post",
            f"/games/{game_id}/moves",
            json={
                "card_key": hand[0],
                "cell_index": empty[0],
                "state_version": state["state_version"],
            },
        )
    return game_id


# ---------------------------------------------------------------------------
# Block create when caller has non-complete game
# ---------------------------------------------------------------------------


def test_create_blocked_when_caller_has_waiting_game(client: TestClient) -> None:
    """Creating a second game while already hosting a WAITING game returns 409."""
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    assert resp.status_code == 201
    existing_id = resp.json()["game_id"]

    resp = as_user(client, "alice", "post", "/games", json={"seed": 2})
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert existing_id in detail


def test_create_blocked_when_caller_has_active_game(client: TestClient) -> None:
    """Creating a new game while in an ACTIVE game returns 409."""
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    as_user(client, "bob", "post", f"/games/{game_id}/join", json={})

    # Alice now has an ACTIVE game
    resp = as_user(client, "alice", "post", "/games", json={"seed": 2})
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert game_id in detail


def test_create_allowed_when_only_complete_games(client: TestClient) -> None:
    """Creating a game is allowed when caller only has COMPLETE games."""
    _complete_game(client, "alice", "bob", seed=1)

    resp = as_user(client, "alice", "post", "/games", json={"seed": 99})
    assert resp.status_code == 201


def test_create_allowed_when_no_games(client: TestClient) -> None:
    """First game creation always succeeds."""
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Block join when caller has non-complete game
# ---------------------------------------------------------------------------


def test_join_blocked_when_caller_has_waiting_game(client: TestClient) -> None:
    """Joining another game while hosting a WAITING game returns 409."""
    # Alice creates a game (WAITING)
    as_user(client, "alice", "post", "/games", json={"seed": 1})

    # Bob creates a game
    resp = as_user(client, "bob", "post", "/games", json={"seed": 2})
    bob_game = resp.json()["game_id"]

    # Alice tries to join Bob's game — blocked
    resp = as_user(client, "alice", "post", f"/games/{bob_game}/join", json={})
    assert resp.status_code == 409
    detail = resp.json()["detail"].lower()
    # Detail should mention Alice's existing game
    assert "already" in detail or "non-complete" in detail


def test_join_blocked_when_caller_has_active_game(client: TestClient) -> None:
    """Joining a new game while in an ACTIVE game returns 409."""
    # Alice creates, Bob joins → ACTIVE
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]
    as_user(client, "bob", "post", f"/games/{game_id}/join", json={})

    # Charlie creates a game
    resp = as_user(client, "charlie", "post", "/games", json={"seed": 2})
    charlie_game = resp.json()["game_id"]

    # Alice tries to join Charlie's game — blocked
    resp = as_user(client, "alice", "post", f"/games/{charlie_game}/join", json={})
    assert resp.status_code == 409


def test_join_allowed_when_only_complete_games(client: TestClient) -> None:
    """Joining is allowed when caller only has COMPLETE games."""
    _complete_game(client, "alice", "bob", seed=1)

    # Charlie creates a game
    resp = as_user(client, "charlie", "post", "/games", json={"seed": 99})
    charlie_game = resp.json()["game_id"]

    resp = as_user(client, "alice", "post", f"/games/{charlie_game}/join", json={})
    assert resp.status_code == 200


def test_join_allowed_when_no_games(client: TestClient) -> None:
    """Joining is allowed when caller has no games at all."""
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    game_id = resp.json()["game_id"]

    resp = as_user(client, "bob", "post", f"/games/{game_id}/join", json={})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Error message includes existing game_id
# ---------------------------------------------------------------------------


def test_create_error_includes_existing_game_id(client: TestClient) -> None:
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    existing_id = resp.json()["game_id"]

    resp = as_user(client, "alice", "post", "/games", json={"seed": 2})
    assert resp.status_code == 409
    assert existing_id in resp.json()["detail"]


def test_join_error_includes_existing_game_id(client: TestClient) -> None:
    # Alice has a WAITING game
    resp = as_user(client, "alice", "post", "/games", json={"seed": 1})
    alice_game = resp.json()["game_id"]

    # Bob creates a game
    resp = as_user(client, "bob", "post", "/games", json={"seed": 2})
    bob_game = resp.json()["game_id"]

    # Alice tries to join Bob's game
    resp = as_user(client, "alice", "post", f"/games/{bob_game}/join", json={})
    assert resp.status_code == 409
    assert alice_game in resp.json()["detail"]
