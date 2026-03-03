"""Tests for US-UX-004: archetype selection is unskippable; moves blocked until chosen.

Covers:
- Backend rejects move submission (422) when player has not selected an archetype
- Backend allows move submission after archetype is selected
- ArchetypeNotSelectedError is an InvalidMoveError subclass
- The error message contains actionable detail
"""

from fastapi.testclient import TestClient

from app.rules.errors import ArchetypeNotSelectedError, InvalidMoveError


def _as(client: TestClient, user: str, method: str, path: str, **kwargs):  # type: ignore[no-untyped-def]
    return getattr(client, method)(path, headers={"X-User-Id": user}, **kwargs)


def _create_active_game(client: TestClient) -> tuple[str, str, str]:
    game_id = _as(client, "p1", "post", "/games", json={}).json()["game_id"]
    _as(client, "p2", "post", f"/games/{game_id}/join", json={})
    return game_id, "p1", "p2"


# ---------------------------------------------------------------------------
# Error class tests
# ---------------------------------------------------------------------------


def test_archetype_not_selected_error_is_invalid_move_error() -> None:
    err = ArchetypeNotSelectedError("must select archetype")
    assert isinstance(err, InvalidMoveError)


def test_archetype_not_selected_error_message() -> None:
    msg = "You must select an archetype before placing cards."
    err = ArchetypeNotSelectedError(msg)
    assert str(err) == msg


# ---------------------------------------------------------------------------
# Backend: move rejected (422) when no archetype selected
# ---------------------------------------------------------------------------


def test_move_without_archetype_returns_422(client: TestClient) -> None:
    game_id, p1, _p2 = _create_active_game(client)
    # Determine who goes first and which hand they have
    game = _as(client, p1, "get", f"/games/{game_id}").json()
    first_player = "p1" if game["current_player_index"] == 0 else "p2"
    first_index = game["current_player_index"]
    card_key = game["players"][first_index]["hand"][0]

    res = _as(
        client,
        first_player,
        "post",
        f"/games/{game_id}/moves",
        json={
            "card_key": card_key,
            "cell_index": 0,
            "state_version": game["state_version"],
        },
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert "archetype" in detail.lower()


def test_move_without_archetype_detail_is_actionable(client: TestClient) -> None:
    """The 422 detail must contain enough information for the client to act on it."""
    game_id, p1, _p2 = _create_active_game(client)
    game = _as(client, p1, "get", f"/games/{game_id}").json()
    first_player = "p1" if game["current_player_index"] == 0 else "p2"
    first_index = game["current_player_index"]
    card_key = game["players"][first_index]["hand"][0]

    res = _as(
        client,
        first_player,
        "post",
        f"/games/{game_id}/moves",
        json={
            "card_key": card_key,
            "cell_index": 0,
            "state_version": game["state_version"],
        },
    )
    detail: str = res.json()["detail"]
    # Must mention archetype selection is required
    assert "archetype" in detail.lower()
    # Must not be a generic server error message
    assert "500" not in detail


# ---------------------------------------------------------------------------
# Backend: move succeeds after archetype is selected
# ---------------------------------------------------------------------------


def test_move_succeeds_after_archetype_selected(client: TestClient) -> None:
    game_id, p1, _p2 = _create_active_game(client)
    game = _as(client, p1, "get", f"/games/{game_id}").json()
    first_player = "p1" if game["current_player_index"] == 0 else "p2"
    first_index = game["current_player_index"]
    card_key = game["players"][first_index]["hand"][0]

    # Select archetype first
    arch_res = _as(
        client,
        first_player,
        "post",
        f"/games/{game_id}/archetype",
        json={"archetype": "martial"},
    )
    assert arch_res.status_code == 200

    # Now submit move — should succeed
    move_res = _as(
        client,
        first_player,
        "post",
        f"/games/{game_id}/moves",
        json={
            "card_key": card_key,
            "cell_index": 0,
            "state_version": arch_res.json()["state_version"],
        },
    )
    assert move_res.status_code == 200


def test_second_player_move_also_blocked_without_archetype(client: TestClient) -> None:
    """Both players must select an archetype; the non-active player is also blocked."""
    game_id, _p1, _p2 = _create_active_game(client)
    game = _as(client, "p1", "get", f"/games/{game_id}").json()

    # Determine which player goes second
    first_index = game["current_player_index"]
    second_player = "p2" if first_index == 0 else "p1"
    second_index = 1 - first_index

    # Select archetype for the first player and make their move
    first_player = "p1" if first_index == 0 else "p2"
    card_p1 = game["players"][first_index]["hand"][0]
    arch1 = _as(
        client,
        first_player,
        "post",
        f"/games/{game_id}/archetype",
        json={"archetype": "devout"},
    )
    assert arch1.status_code == 200

    move1 = _as(
        client,
        first_player,
        "post",
        f"/games/{game_id}/moves",
        json={
            "card_key": card_p1,
            "cell_index": 0,
            "state_version": arch1.json()["state_version"],
        },
    )
    assert move1.status_code == 200

    # Now it's the second player's turn — they have no archetype yet
    state_after_move = move1.json()
    card_p2 = state_after_move["players"][second_index]["hand"][0]

    res = _as(
        client,
        second_player,
        "post",
        f"/games/{game_id}/moves",
        json={
            "card_key": card_p2,
            "cell_index": 1,
            "state_version": state_after_move["state_version"],
        },
    )
    assert res.status_code == 422
    assert "archetype" in res.json()["detail"].lower()
