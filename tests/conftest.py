"""Shared test fixtures and helpers.

Pytest auto-discovers fixtures here. Plain helpers need explicit imports::

    from tests.conftest import _make_card, make_card, make_state, mock_rng, _TEST_CARDS
"""

from unittest.mock import MagicMock

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.auth import get_caller_id
from app.dependencies import get_card_store, get_game_store
from app.main import app
from app.models.cards import CardDefinition, CardSides
from app.models.game import Archetype, BoardCell, GameState, GameStatus, PlayerState
from app.store.memory import MemoryCardStore, MemoryGameStore

# ---------------------------------------------------------------------------
# Plain helpers (import explicitly: ``from tests.conftest import ...``)
# ---------------------------------------------------------------------------


def _make_card(idx: int) -> CardDefinition:
    """Minimal valid test card: sides 4/4/4/4, tier-1, common rarity."""
    return CardDefinition(
        card_key=f"test_card_{idx:03d}",
        character_key=f"char_{idx:03d}",
        name=f"Test Card {idx}",
        version="v1",
        tier=1,
        rarity=15,
        is_named=False,
        sides=CardSides(n=4, e=4, s=4, w=4),
        set="test",
        element="shadow",
    )


_TEST_CARDS = [_make_card(i) for i in range(20)]


def make_card(
    key: str,
    n: int = 5,
    e: int = 5,
    s: int = 5,
    w: int = 5,
) -> CardDefinition:
    """Card factory for rules-engine tests with customizable sides."""
    return CardDefinition(
        card_key=key,
        character_key=key,
        name=key,
        version="1.0",
        tier=1,
        rarity=50,
        is_named=False,
        sides=CardSides(n=n, e=e, s=s, w=w),
        set="test",
        element="shadow",
    )


def make_state(
    board: list[BoardCell | None] | None = None,
    p0_hand: list[str] | None = None,
    p1_hand: list[str] | None = None,
    p0_archetype: Archetype | None = None,
    p0_archetype_used: bool = False,
    p1_archetype: Archetype | None = None,
    current_player_index: int = 0,
) -> GameState:
    """Build a GameState with sensible defaults for rules-engine tests."""
    players = [
        PlayerState(
            player_id="p0",
            archetype=p0_archetype,
            hand=p0_hand or [],
            archetype_used=p0_archetype_used,
        ),
        PlayerState(
            player_id="p1",
            archetype=p1_archetype,
            hand=p1_hand or [],
        ),
    ]
    return GameState(
        game_id="test-game",
        status=GameStatus.ACTIVE,
        players=players,
        current_player_index=current_player_index,
        board=board if board is not None else [None] * 9,
    )


def mock_rng(*rolls: int) -> MagicMock:
    """Return a mock rng whose randint calls return *rolls* in sequence."""
    rng = MagicMock()
    rng.randint.side_effect = list(rolls)
    return rng


def _mock_caller_id(request: Request) -> str:
    """Test auth: read user identity from X-User-Id header."""
    return request.headers.get("X-User-Id", "test-user")


# ---------------------------------------------------------------------------
# Fixtures (auto-discovered by pytest)
# ---------------------------------------------------------------------------


@pytest.fixture()
def game_store() -> MemoryGameStore:
    return MemoryGameStore()


@pytest.fixture()
def client(game_store: MemoryGameStore) -> TestClient:  # type: ignore[misc]
    card_store = MemoryCardStore(cards=_TEST_CARDS)
    app.dependency_overrides[get_game_store] = lambda: game_store
    app.dependency_overrides[get_card_store] = lambda: card_store
    app.dependency_overrides[get_caller_id] = _mock_caller_id
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()
