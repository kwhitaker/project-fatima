"""FastAPI dependency providers for storage layer.

Tests override these via app.dependency_overrides.
"""

from app.store import CardStore, GameStore
from app.store.memory import MemoryCardStore, MemoryGameStore

# Module-level defaults; replaced in tests via app.dependency_overrides
_game_store: GameStore = MemoryGameStore()
_card_store: CardStore = MemoryCardStore()


def get_game_store() -> GameStore:
    return _game_store


def get_card_store() -> CardStore:
    return _card_store
