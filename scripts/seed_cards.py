"""Seed cards.jsonl into the Supabase cards table.

Uses SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables.
Run directly:
    uv run python scripts/seed_cards.py [path/to/cards.jsonl]

If no path is provided, defaults to cards.jsonl in the current directory.
Prints a summary; exits non-zero if validation errors are found.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from app.models.cards import CardDefinition
from app.rules.cards import load_cards_from_file


def card_to_row(card: CardDefinition) -> dict[str, Any]:
    """Convert a CardDefinition to a flat dict matching the cards table schema."""
    return {
        "card_key": card.card_key,
        "character_key": card.character_key,
        "name": card.name,
        "version": card.version,
        "tier": card.tier,
        "rarity": card.rarity,
        "is_named": card.is_named,
        "n": card.sides.n,
        "e": card.sides.e,
        "s": card.sides.s,
        "w": card.sides.w,
        "set": card.set,
        "tags": card.tags,
        "definition": card.model_dump(mode="json"),
    }


def seed_cards(client: Any, cards_file: Path | str) -> tuple[int, list[str]]:
    """Load, validate, and upsert cards from a .jsonl file.

    Returns (upsert_count, error_messages).
    If error_messages is non-empty, no upsert was performed.
    """
    cards, errors = load_cards_from_file(cards_file)

    if errors:
        return 0, [f"Line {e.line}: {e.message}" for e in errors]

    if not cards:
        return 0, []

    rows = [card_to_row(c) for c in cards]
    client.table("cards").upsert(rows).execute()
    return len(rows), []


if __name__ == "__main__":
    from supabase import create_client  # type: ignore[import-untyped]

    _url = os.environ["SUPABASE_URL"]
    _key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    _client = create_client(_url, _key)

    _cards_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cards.jsonl")

    _count, _errs = seed_cards(_client, _cards_file)

    if _errs:
        for _msg in _errs:
            print(f"ERROR: {_msg}", file=sys.stderr)
        sys.exit(1)

    print(f"Upserted {_count} cards.")
