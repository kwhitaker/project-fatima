"""Tests for US-UX-008: GET /cards endpoint for UI card rendering.

Covers:
- GET /cards returns 200 with a list of card definitions
- Each card includes card_key, name, version, and sides (n/e/s/w)
- Card values match what is in the store
- Empty store returns an empty list
- Endpoint requires authentication (caller_id)
"""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.auth import get_caller_id
from app.dependencies import get_card_store, get_game_store
from app.main import app
from app.models.cards import CardDefinition, CardSides
from app.store.memory import MemoryCardStore, MemoryGameStore

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
        sides=CardSides(n=4, e=5, s=3, w=2),
        set="test",
        element="shadow",
    )


def _mock_caller_id(request: Request) -> str:
    return request.headers.get("X-User-Id", "test-user")


def _get(client: TestClient, path: str, user: str = "test-user"):  # type: ignore[no-untyped-def]
    return client.get(path, headers={"X-User-Id": user})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> TestClient:  # type: ignore[misc]
    cards = [_make_card(i) for i in range(3)]
    card_store = MemoryCardStore(cards=cards)
    app.dependency_overrides[get_card_store] = lambda: card_store
    app.dependency_overrides[get_game_store] = lambda: MemoryGameStore()
    app.dependency_overrides[get_caller_id] = _mock_caller_id
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


@pytest.fixture()
def empty_client() -> TestClient:  # type: ignore[misc]
    app.dependency_overrides[get_card_store] = lambda: MemoryCardStore(cards=[])
    app.dependency_overrides[get_game_store] = lambda: MemoryGameStore()
    app.dependency_overrides[get_caller_id] = _mock_caller_id
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: endpoint exists and returns correct structure
# ---------------------------------------------------------------------------


def test_list_cards_returns_200(client: TestClient) -> None:
    res = _get(client, "/cards")
    assert res.status_code == 200


def test_list_cards_returns_list(client: TestClient) -> None:
    res = _get(client, "/cards")
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 3


def test_list_cards_includes_required_fields(client: TestClient) -> None:
    res = _get(client, "/cards")
    card = res.json()[0]
    assert "card_key" in card
    assert "name" in card
    assert "version" in card
    assert "sides" in card
    sides = card["sides"]
    assert "n" in sides
    assert "e" in sides
    assert "s" in sides
    assert "w" in sides


def test_list_cards_returns_correct_values(client: TestClient) -> None:
    res = _get(client, "/cards")
    cards_by_key = {c["card_key"]: c for c in res.json()}
    assert "tc_000" in cards_by_key
    assert "tc_001" in cards_by_key
    assert "tc_002" in cards_by_key
    c = cards_by_key["tc_000"]
    assert c["name"] == "Card 0"
    assert c["version"] == "v1"
    assert c["sides"] == {"n": 4, "e": 5, "s": 3, "w": 2}


def test_list_cards_empty_store_returns_empty_list(empty_client: TestClient) -> None:
    res = _get(empty_client, "/cards")
    assert res.status_code == 200
    assert res.json() == []


def test_list_cards_requires_auth() -> None:
    """Without auth, endpoint returns 401 (no caller_id override, no Bearer token)."""
    app.dependency_overrides[get_card_store] = lambda: MemoryCardStore(cards=[])
    app.dependency_overrides[get_game_store] = lambda: MemoryGameStore()
    # Intentionally NOT overriding get_caller_id — real dep raises 401 with no header
    try:
        fresh_client = TestClient(app, raise_server_exceptions=False)
        res = fresh_client.get("/cards")  # no Authorization header
        assert res.status_code == 401
    finally:
        app.dependency_overrides.clear()
