"""Deck validator: size, named character uniqueness, and rarity slot limits.

Operates on a list of CardDefinition objects already loaded and schema-validated
by load_cards_from_lines / load_cards_from_file.  Returns a list of human-readable
error strings (empty = passes).
"""

from app.models.cards import CardDefinition
from app.rules.cards import rarity_bucket

# Rarity slot maxima per CARDS_SPEC.md: ultra ≤ 1, very_rare ≤ 2, rare ≤ 3.
_RARITY_SLOT_LIMITS: dict[str, int] = {
    "ultra": 1,
    "very_rare": 2,
    "rare": 3,
}


def validate_deck(cards: list[CardDefinition]) -> list[str]:
    """Validate a 10-card deck against deck-composition rules.

    Checks:
    - Exactly 10 cards.
    - Named uniqueness: at most one card per character_key when is_named is True.
    - Rarity slots: ultra ≤ 1, very_rare ≤ 2, rare ≤ 3.

    Returns a list of human-readable error strings (empty = valid).
    """
    errors: list[str] = []

    # --- deck size ---
    if len(cards) != 10:
        errors.append(f"Deck must contain exactly 10 cards; got {len(cards)}")

    # --- named character uniqueness ---
    named_counts: dict[str, int] = {}
    for card in cards:
        if card.is_named:
            named_counts[card.character_key] = named_counts.get(card.character_key, 0) + 1
    for character_key, count in named_counts.items():
        if count > 1:
            errors.append(
                f"Named character '{character_key}' appears {count} times; only 1 allowed per deck"
            )

    # --- rarity slots ---
    slot_counts: dict[str, int] = {}
    for card in cards:
        bucket = rarity_bucket(card.rarity)
        if bucket in _RARITY_SLOT_LIMITS:
            slot_counts[bucket] = slot_counts.get(bucket, 0) + 1
    for bucket, limit in _RARITY_SLOT_LIMITS.items():
        count = slot_counts.get(bucket, 0)
        if count > limit:
            errors.append(f"Too many {bucket} cards: {count} in deck, max {limit}")

    return errors
