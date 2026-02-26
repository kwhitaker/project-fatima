"""Deck validator: size, named character uniqueness, rarity slot limits, copy limits.

Operates on a list of CardDefinition objects already loaded and schema-validated
by load_cards_from_lines / load_cards_from_file.  Returns a list of human-readable
error strings (empty = passes).
"""

from app.models.cards import CardDefinition
from app.rules.cards import STAT_BUDGETS, rarity_bucket

# Rarity slot maxima per CARDS_SPEC.md: ultra ≤ 1, very_rare ≤ 2, rare ≤ 3.
_RARITY_SLOT_LIMITS: dict[str, int] = {
    "ultra": 1,
    "very_rare": 2,
    "rare": 3,
}

# Copy limits per card_key, driven by rarity bucket.
# Default: common/uncommon allow 2 copies; higher buckets allow 1.
COPY_LIMITS: dict[str, int] = {
    "common": 2,
    "uncommon": 2,
    "rare": 1,
    "very_rare": 1,
    "ultra": 1,
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

    # --- copy limits ---
    key_counts: dict[str, int] = {}
    key_bucket: dict[str, str] = {}
    for card in cards:
        key_counts[card.card_key] = key_counts.get(card.card_key, 0) + 1
        key_bucket[card.card_key] = rarity_bucket(card.rarity)
    for card_key, count in key_counts.items():
        limit = COPY_LIMITS[key_bucket[card_key]]
        if count > limit:
            errors.append(
                f"Copy limit exceeded for '{card_key}': {count} copies in deck, "
                f"max {limit} for {key_bucket[card_key]} bucket"
            )

    return errors


# ---------------------------------------------------------------------------
# Deck cost (weighted sum for fairness matching)
# ---------------------------------------------------------------------------


def card_cost(card: CardDefinition) -> int:
    """Return the weighted cost of a single card.

    Cost equals the stat sum_budget for the card's (tier, rarity bucket) from
    STAT_BUDGETS.  Higher tier and higher rarity bucket produce higher costs,
    giving a simple, deterministic strength signal used for fairness matching.
    """
    bucket = rarity_bucket(card.rarity)
    sum_budget, _ = STAT_BUDGETS[(card.tier, bucket)]
    return sum_budget


def deck_cost(cards: list[CardDefinition]) -> int:
    """Return the total weighted cost of a list of cards (sum of card_cost values)."""
    return sum(card_cost(c) for c in cards)
