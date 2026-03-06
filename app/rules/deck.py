"""Deck validator: size, named character uniqueness, rarity slot limits, copy limits.

Operates on a list of CardDefinition objects already loaded and schema-validated
by load_cards_from_lines / load_cards_from_file.  Returns a list of human-readable
error strings (empty = passes).
"""

import random

from app.models.cards import CardDefinition
from app.rules.cards import STAT_BUDGETS, rarity_bucket

# Hand/deal sizing constants.
DEAL_SIZE = 8   # Cards dealt to each player before draft
HAND_SIZE = 5   # Cards kept after draft selection

# Exact tier distribution required in every deal.
DEAL_TIER_SLOTS: dict[int, int] = {3: 2, 2: 3, 1: 3}

# Hand tier limits: max cards of each tier allowed in a drafted hand of 5.
# T1 is unconstrained (no entry needed).
HAND_TIER_LIMITS: dict[int, int] = {3: 1, 2: 2}

# Rarity slot maxima per CARDS_SPEC.md: ultra ≤ 2, very_rare ≤ 2, rare ≤ 3.
_RARITY_SLOT_LIMITS: dict[str, int] = {
    "ultra": 2,
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


def validate_deal(cards: list[CardDefinition]) -> list[str]:
    """Validate a deal against composition rules.

    Checks:
    - Exactly DEAL_SIZE (8) cards.
    - Tier slots: exactly {3:2, 2:3, 1:3}.
    - Named uniqueness: at most one card per character_key when is_named is True.
    - Rarity slots: ultra ≤ 2, very_rare ≤ 2, rare ≤ 3.

    Returns a list of human-readable error strings (empty = valid).
    """
    errors: list[str] = []

    # --- deal size ---
    if len(cards) != DEAL_SIZE:
        errors.append(f"Deal must contain exactly {DEAL_SIZE} cards; got {len(cards)}")

    # --- tier slots ---
    tier_counts: dict[int, int] = {}
    for card in cards:
        tier_counts[card.tier] = tier_counts.get(card.tier, 0) + 1
    for tier, required in DEAL_TIER_SLOTS.items():
        actual = tier_counts.get(tier, 0)
        if actual != required:
            errors.append(
                f"Tier {tier} requires exactly {required} cards; got {actual}"
            )

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


def validate_hand_tiers(
    selected_keys: list[str],
    card_lookup: dict[str, CardDefinition],
) -> list[str]:
    """Validate that a drafted hand respects HAND_TIER_LIMITS.

    Returns a list of human-readable error strings (empty = valid).
    """
    errors: list[str] = []
    tier_counts: dict[int, int] = {}
    for key in selected_keys:
        card = card_lookup.get(key)
        if card is None:
            continue
        tier_counts[card.tier] = tier_counts.get(card.tier, 0) + 1
    for tier, limit in HAND_TIER_LIMITS.items():
        count = tier_counts.get(tier, 0)
        if count > limit:
            errors.append(
                f"Too many Tier {tier} cards: {count} selected, max {limit}"
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


# ---------------------------------------------------------------------------
# Seeded deck generation
# ---------------------------------------------------------------------------

DEFAULT_COST_TOLERANCE = 20


class DeckGenerationError(Exception):
    """Raised when deck generation fails (pool insufficient or costs out of tolerance)."""


def _can_add_to_deal(deal: list[CardDefinition], card: CardDefinition) -> bool:
    """Return True if adding card to deal would not violate composition rules."""
    if len(deal) >= DEAL_SIZE:
        return False

    # Named character uniqueness
    if card.is_named and any(c.character_key == card.character_key for c in deal):
        return False

    # Rarity slot limit (ultra ≤ 2, very_rare ≤ 2, rare ≤ 3)
    bucket = rarity_bucket(card.rarity)
    if bucket in _RARITY_SLOT_LIMITS:
        if sum(1 for c in deal if rarity_bucket(c.rarity) == bucket) >= _RARITY_SLOT_LIMITS[bucket]:
            return False

    # Copy limit per card_key
    limit = COPY_LIMITS[bucket]
    if sum(1 for c in deal if c.card_key == card.card_key) >= limit:
        return False

    # Tier slot limit
    tier_limit = DEAL_TIER_SLOTS.get(card.tier, 0)
    if sum(1 for c in deal if c.tier == card.tier) >= tier_limit:
        return False

    return True


def generate_matched_deals(
    pool: list[CardDefinition],
    seed: int,
    tolerance: int = DEFAULT_COST_TOLERANCE,
) -> tuple[list[CardDefinition], list[CardDefinition]]:
    """Generate two DEAL_SIZE-card deals from pool that pass validation and are cost-balanced.

    Builds deals by filling exact tier slots: for each tier (3, 2, 1), draws
    from the shuffled pool respecting rarity/copy/named constraints, alternating
    between deals for balance.

    Raises DeckGenerationError if the pool cannot fill both deals or if the
    resulting cost difference exceeds tolerance.
    """
    rng = random.Random(seed)
    shuffled = pool[:]
    rng.shuffle(shuffled)

    # Group cards by tier, then sort each group by cost descending for even distribution.
    by_tier: dict[int, list[CardDefinition]] = {1: [], 2: [], 3: []}
    for card in shuffled:
        if card.tier in by_tier:
            by_tier[card.tier].append(card)
    for tier_cards in by_tier.values():
        tier_cards.sort(key=card_cost, reverse=True)

    deals: list[list[CardDefinition]] = [[], []]

    # Fill tier slots: process highest tier first for better cost balancing.
    for tier in (3, 2, 1):
        slots_needed = DEAL_TIER_SLOTS[tier]
        target = 0
        for card in by_tier[tier]:
            tier_full_0 = sum(1 for c in deals[0] if c.tier == tier) >= slots_needed
            tier_full_1 = sum(1 for c in deals[1] if c.tier == tier) >= slots_needed
            if tier_full_0 and tier_full_1:
                break
            for idx in (target, 1 - target):
                tier_count = sum(1 for c in deals[idx] if c.tier == tier)
                if tier_count < slots_needed and _can_add_to_deal(deals[idx], card):
                    deals[idx].append(card)
                    target = 1 - idx
                    break

    deal_a, deal_b = deals[0], deals[1]

    if len(deal_a) != DEAL_SIZE or len(deal_b) != DEAL_SIZE:
        raise DeckGenerationError(
            f"Could not fill both deals from pool of {len(pool)} cards "
            f"(filled {len(deal_a)} and {len(deal_b)})"
        )

    cost_diff = abs(deck_cost(deal_a) - deck_cost(deal_b))
    if cost_diff > tolerance:
        raise DeckGenerationError(f"Deck cost imbalance {cost_diff} exceeds tolerance {tolerance}")

    return deal_a, deal_b
