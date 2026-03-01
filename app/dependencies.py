"""FastAPI dependency providers for storage layer.

Tests override these via app.dependency_overrides.

Production wiring:
- GameStore: SupabaseGameStore (persists to Supabase)
- CardStore: MemoryCardStore loaded from cards.jsonl at startup
"""

import os
from pathlib import Path

from app.store import CardStore, GameStore
from app.store.memory import MemoryCardStore, MemoryGameStore


def _build_game_store() -> GameStore:
    """Return SupabaseGameStore if env vars are set, else in-memory fallback."""
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        from app.store.supabase_store import SupabaseGameStore

        return SupabaseGameStore()
    return MemoryGameStore()


def _build_card_store() -> CardStore:
    """Return MemoryCardStore loaded from cards.jsonl."""
    from app.rules.cards import load_cards_from_file

    cards_path = Path(__file__).parent.parent / "cards.jsonl"
    cards, errors = load_cards_from_file(cards_path)
    if errors:
        import warnings

        for e in errors:
            warnings.warn(f"cards.jsonl line {e.line}: {e.message}", stacklevel=2)
    return MemoryCardStore(cards)


# Module-level singletons; replaced in tests via app.dependency_overrides
_game_store: GameStore = _build_game_store()
_card_store: CardStore = _build_card_store()


def get_game_store() -> GameStore:
    return _game_store


def get_card_store() -> CardStore:
    return _card_store
