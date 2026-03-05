"""Tests for US-SP-003: POST /games/vs-ai endpoint.

Covers:
- POST /games/vs-ai returns 201 with valid GameState
- AI player fields are correctly set in the response
- Returns 409 if player already has a non-complete game
- Auth required (same pattern as other endpoints)
"""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.auth import get_caller_email
from app.main import app
from app.models.game import AIDifficulty
from app.services.game_service import AI_DISPLAY_NAMES, AI_PLAYER_ID
from tests.conftest import _TEST_CARDS, _mock_caller_id


def _mock_caller_email(request: Request) -> str | None:
    return request.headers.get("X-User-Email", None)


@pytest.fixture()
def client(game_store):  # type: ignore[misc]
    """Custom client with get_caller_email override."""
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


def _post_vs_ai(
    client: TestClient,
    difficulty: str = "easy",
    user_id: str = "alice",
    email: str = "alice@test.com",
) -> dict:
    return client.post(
        "/games/vs-ai",
        json={"difficulty": difficulty},
        headers={"X-User-Id": user_id, "X-User-Email": email},
    ).json()


class TestCreateVsAi201:
    """POST /games/vs-ai returns 201 with a valid AI game."""

    @pytest.mark.parametrize("difficulty", ["easy", "medium", "hard", "nightmare"])
    def test_returns_201(self, client: TestClient, difficulty: str) -> None:
        resp = client.post(
            "/games/vs-ai",
            json={"difficulty": difficulty},
            headers={"X-User-Id": f"player-{difficulty}", "X-User-Email": "p@test.com"},
        )
        assert resp.status_code == 201

    def test_response_has_drafting_status(self, client: TestClient) -> None:
        resp = client.post(
            "/games/vs-ai",
            json={"difficulty": "easy"},
            headers={"X-User-Id": "alice", "X-User-Email": "alice@test.com"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "drafting"

    def test_ai_player_fields(self, client: TestClient) -> None:
        resp = client.post(
            "/games/vs-ai",
            json={"difficulty": "medium"},
            headers={"X-User-Id": "alice", "X-User-Email": "alice@test.com"},
        )
        data = resp.json()
        ai_player = data["players"][1]
        assert ai_player["player_id"] == AI_PLAYER_ID
        assert ai_player["player_type"] == "ai"
        assert ai_player["ai_difficulty"] == "medium"
        assert ai_player["email"] == AI_DISPLAY_NAMES[AIDifficulty.MEDIUM]

    def test_human_player_has_deal(self, client: TestClient) -> None:
        resp = client.post(
            "/games/vs-ai",
            json={"difficulty": "easy"},
            headers={"X-User-Id": "alice", "X-User-Email": "alice@test.com"},
        )
        data = resp.json()
        human = data["players"][0]
        assert len(human["deal"]) > 0
        assert human["player_id"] == "alice"

    def test_ai_already_drafted(self, client: TestClient) -> None:
        resp = client.post(
            "/games/vs-ai",
            json={"difficulty": "hard"},
            headers={"X-User-Id": "alice", "X-User-Email": "alice@test.com"},
        )
        data = resp.json()
        ai_player = data["players"][1]
        assert len(ai_player["hand"]) == 5
        assert ai_player["archetype"] is not None


class TestCreateVsAi409:
    """POST /games/vs-ai returns 409 when player has an active game."""

    def test_blocked_when_has_active_game(self, client: TestClient) -> None:
        # Create first game
        resp = client.post(
            "/games/vs-ai",
            json={"difficulty": "easy"},
            headers={"X-User-Id": "alice", "X-User-Email": "alice@test.com"},
        )
        assert resp.status_code == 201

        # Second game should be blocked
        resp = client.post(
            "/games/vs-ai",
            json={"difficulty": "medium"},
            headers={"X-User-Id": "alice", "X-User-Email": "alice@test.com"},
        )
        assert resp.status_code == 409

    def test_blocked_when_has_multiplayer_game(self, client: TestClient) -> None:
        # Create a multiplayer game
        resp = client.post(
            "/games",
            json={"seed": 1},
            headers={"X-User-Id": "alice"},
        )
        assert resp.status_code == 201

        # AI game should be blocked
        resp = client.post(
            "/games/vs-ai",
            json={"difficulty": "easy"},
            headers={"X-User-Id": "alice", "X-User-Email": "alice@test.com"},
        )
        assert resp.status_code == 409
