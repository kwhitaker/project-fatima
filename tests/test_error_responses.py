"""Integration tests for standardized API error responses (US-026).

Verifies that each endpoint returns the correct status code for each error class:
- 422 on request validation errors (malformed/missing fields)
- 404 when game_id does not exist
- 403 when caller is not a game participant
- 409 on optimistic lock conflicts

All error responses must include a ``detail`` key in the JSON body.
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
    return CardDefinition(
        card_key=f"ec_{idx:03d}",
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


@pytest.fixture()
def client() -> TestClient:  # type: ignore[misc]
    game_store = MemoryGameStore()
    card_store = MemoryCardStore(cards=_TEST_CARDS)
    app.dependency_overrides[get_game_store] = lambda: game_store
    app.dependency_overrides[get_card_store] = lambda: card_store
    app.dependency_overrides[get_caller_id] = _mock_caller_id
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


def _as(client: TestClient, user: str, method: str, path: str, **kwargs):  # type: ignore[no-untyped-def]
    return getattr(client, method)(path, headers={"X-User-Id": user}, **kwargs)


def _active_game(client: TestClient) -> tuple[str, list[str], list[str], int, int]:
    """Create and return (game_id, p0_hand, p1_hand, state_version, first_player_index).

    Also selects archetypes for both players so that moves can be submitted immediately.
    state_version is the version after both archetype selections.
    """
    game_id = _as(client, "alice", "post", "/games", json={"seed": 1}).json()["game_id"]
    _as(client, "bob", "post", f"/games/{game_id}/join", json={})
    _as(client, "alice", "post", f"/games/{game_id}/archetype", json={"archetype": "martial"})
    data = _as(
        client, "bob", "post", f"/games/{game_id}/archetype", json={"archetype": "devout"}
    ).json()
    return (
        game_id,
        data["players"][0]["hand"],
        data["players"][1]["hand"],
        data["state_version"],
        data["current_player_index"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_error(resp: object, status: int) -> dict:  # type: ignore[type-arg]
    """Assert status code and that the body contains a ``detail`` key."""
    assert resp.status_code == status  # type: ignore[attr-defined]
    body = resp.json()  # type: ignore[attr-defined]
    assert "detail" in body, f"expected 'detail' key in error body, got: {body}"
    return body  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# 422 — request validation errors
# ---------------------------------------------------------------------------


class Test422RequestValidation:
    def test_create_game_wrong_seed_type(self, client: TestClient) -> None:
        resp = _as(client, "alice", "post", "/games", json={"seed": "not-an-int"})
        _assert_error(resp, 422)

    def test_move_missing_card_key(self, client: TestClient) -> None:
        game_id, _, _, sv, _ = _active_game(client)
        resp = _as(
            client,
            "alice",
            "post",
            f"/games/{game_id}/moves",
            json={"cell_index": 0, "state_version": sv},
        )
        _assert_error(resp, 422)

    def test_move_missing_cell_index(self, client: TestClient) -> None:
        game_id, p0_hand, _, sv, _ = _active_game(client)
        resp = _as(
            client,
            "alice",
            "post",
            f"/games/{game_id}/moves",
            json={"card_key": p0_hand[0], "state_version": sv},
        )
        _assert_error(resp, 422)

    def test_move_missing_state_version(self, client: TestClient) -> None:
        game_id, p0_hand, _, _, _ = _active_game(client)
        resp = _as(
            client,
            "alice",
            "post",
            f"/games/{game_id}/moves",
            json={"card_key": p0_hand[0], "cell_index": 0},
        )
        _assert_error(resp, 422)

    def test_archetype_invalid_value(self, client: TestClient) -> None:
        game_id, _, _, _, _ = _active_game(client)
        resp = _as(
            client,
            "alice",
            "post",
            f"/games/{game_id}/archetype",
            json={"archetype": "wizard"},
        )
        _assert_error(resp, 422)

    def test_invalid_move_wrong_turn_returns_422(self, client: TestClient) -> None:
        """Game-logic rule violations (InvalidMoveError) also map to 422."""
        game_id, p0_hand, p1_hand, sv, first_player_index = _active_game(client)
        # Send from the player whose turn it is NOT
        if first_player_index == 0:
            # alice (p0) goes first; bob tries to move → 422
            resp = _as(
                client,
                "bob",
                "post",
                f"/games/{game_id}/moves",
                json={"card_key": p1_hand[0], "cell_index": 0, "state_version": sv},
            )
        else:
            # bob (p1) goes first; alice tries to move → 422
            resp = _as(
                client,
                "alice",
                "post",
                f"/games/{game_id}/moves",
                json={"card_key": p0_hand[0], "cell_index": 0, "state_version": sv},
            )
        _assert_error(resp, 422)


# ---------------------------------------------------------------------------
# 404 — game not found
# ---------------------------------------------------------------------------


class Test404GameNotFound:
    def test_get_game(self, client: TestClient) -> None:
        _assert_error(_as(client, "alice", "get", "/games/no-such-id"), 404)

    def test_join_game(self, client: TestClient) -> None:
        resp = _as(client, "alice", "post", "/games/no-such-id/join", json={})
        _assert_error(resp, 404)

    def test_select_archetype(self, client: TestClient) -> None:
        resp = _as(
            client,
            "alice",
            "post",
            "/games/no-such-id/archetype",
            json={"archetype": "martial"},
        )
        _assert_error(resp, 404)

    def test_submit_move(self, client: TestClient) -> None:
        resp = _as(
            client,
            "alice",
            "post",
            "/games/no-such-id/moves",
            json={"card_key": "x", "cell_index": 0, "state_version": 0},
        )
        _assert_error(resp, 404)

    def test_leave_game(self, client: TestClient) -> None:
        resp = _as(
            client,
            "alice",
            "post",
            "/games/no-such-id/leave",
            json={"state_version": 0},
        )
        _assert_error(resp, 404)


# ---------------------------------------------------------------------------
# 403 — caller is not a game participant
# ---------------------------------------------------------------------------


class Test403NotParticipant:
    def test_select_archetype_non_participant(self, client: TestClient) -> None:
        game_id, _, _, _, _ = _active_game(client)
        resp = _as(
            client,
            "charlie",
            "post",
            f"/games/{game_id}/archetype",
            json={"archetype": "martial"},
        )
        _assert_error(resp, 403)

    def test_submit_move_non_participant(self, client: TestClient) -> None:
        game_id, p0_hand, _, sv, _ = _active_game(client)
        resp = _as(
            client,
            "charlie",
            "post",
            f"/games/{game_id}/moves",
            json={"card_key": p0_hand[0], "cell_index": 0, "state_version": sv},
        )
        _assert_error(resp, 403)

    def test_leave_game_non_participant(self, client: TestClient) -> None:
        game_id, _, _, sv, _ = _active_game(client)
        resp = _as(
            client,
            "charlie",
            "post",
            f"/games/{game_id}/leave",
            json={"state_version": sv},
        )
        _assert_error(resp, 403)


# ---------------------------------------------------------------------------
# 409 — optimistic lock conflict
# ---------------------------------------------------------------------------


class Test409Conflict:
    def test_submit_move_stale_version(self, client: TestClient) -> None:
        game_id, p0_hand, p1_hand, sv, first_player_index = _active_game(client)
        first_user = "alice" if first_player_index == 0 else "bob"
        first_hand = p0_hand if first_player_index == 0 else p1_hand
        # Advance the version by one move
        _as(
            client,
            first_user,
            "post",
            f"/games/{game_id}/moves",
            json={"card_key": first_hand[0], "cell_index": 4, "state_version": sv},
        )
        # Retry with stale version → 409
        resp = _as(
            client,
            first_user,
            "post",
            f"/games/{game_id}/moves",
            json={"card_key": first_hand[1], "cell_index": 0, "state_version": sv},
        )
        _assert_error(resp, 409)

    def test_leave_active_game_stale_version(self, client: TestClient) -> None:
        game_id, _, _, _, _ = _active_game(client)
        resp = _as(
            client,
            "alice",
            "post",
            f"/games/{game_id}/leave",
            json={"state_version": 9999},
        )
        _assert_error(resp, 409)

    def test_leave_waiting_game_stale_version(self, client: TestClient) -> None:
        game_id = _as(client, "alice", "post", "/games", json={}).json()["game_id"]
        resp = _as(
            client,
            "alice",
            "post",
            f"/games/{game_id}/leave",
            json={"state_version": 9999},
        )
        _assert_error(resp, 409)
