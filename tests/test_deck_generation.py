"""Tests for US-018: seeded deck generation producing two matched legal decks."""

import pytest

from app.models.cards import CardDefinition, CardSides
from app.rules.cards import rarity_bucket
from app.rules.deck import (
    DEAL_SIZE,
    DEFAULT_COST_TOLERANCE,
    DeckGenerationError,
    deck_cost,
    generate_matched_deals,
    validate_deal,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIDES_T1_COMMON = CardSides(n=4, e=4, s=4, w=4)  # sum=16 == budget, all <= cap=6
_SIDES_T1_RARE = CardSides(n=7, e=5, s=5, w=3)  # sum=20 == budget, all <= cap=8
_SIDES_T3_ULTRA = CardSides(n=10, e=9, s=7, w=6)  # sum=32 == budget, all <= cap=10


def _card(
    card_key: str,
    *,
    tier: int = 1,
    rarity: int = 15,
    sides: CardSides = _SIDES_T1_COMMON,
    is_named: bool = False,
    character_key: str = "npc",
) -> CardDefinition:
    return CardDefinition(
        card_key=card_key,
        character_key=character_key,
        name="Test",
        version="v1",
        tier=tier,
        rarity=rarity,
        is_named=is_named,
        sides=sides,
        set="test",
        element="shadow",
    )


def _make_pool(n: int, prefix: str = "c") -> list[CardDefinition]:
    """Return n unique cards spread across tiers 1-3 for deal generation.

    Cycles through tiers so the MAX_PER_TIER constraint is satisfiable.
    All cards are common rarity (no rarity-slot pressure).
    """
    tiers = [1, 2, 3]
    return [_card(f"{prefix}{i:03d}", tier=tiers[i % 3]) for i in range(n)]


# ---------------------------------------------------------------------------
# Basic size + validity
# ---------------------------------------------------------------------------


def test_generates_two_deals_of_seven() -> None:
    pool = _make_pool(25)
    a, b = generate_matched_deals(pool, seed=42)
    assert len(a) == DEAL_SIZE
    assert len(b) == DEAL_SIZE


def test_generated_decks_pass_validation() -> None:
    pool = _make_pool(25)
    a, b = generate_matched_deals(pool, seed=42)
    assert validate_deal(a) == []
    assert validate_deal(b) == []


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_seed_produces_same_decks() -> None:
    pool = _make_pool(25)
    a1, b1 = generate_matched_deals(pool, seed=7)
    a2, b2 = generate_matched_deals(pool, seed=7)
    assert [c.card_key for c in a1] == [c.card_key for c in a2]
    assert [c.card_key for c in b1] == [c.card_key for c in b2]


def test_different_seeds_produce_different_decks() -> None:
    pool = _make_pool(25)
    a1, _ = generate_matched_deals(pool, seed=1)
    a2, _ = generate_matched_deals(pool, seed=2)
    # Different shuffles of 25 cards → different subsets
    assert {c.card_key for c in a1} != {c.card_key for c in a2}


# ---------------------------------------------------------------------------
# Cost tolerance matching
# ---------------------------------------------------------------------------


def test_cost_within_default_tolerance() -> None:
    pool = _make_pool(25)
    a, b = generate_matched_deals(pool, seed=42)
    assert abs(deck_cost(a) - deck_cost(b)) <= DEFAULT_COST_TOLERANCE


def test_balanced_pool_costs_are_equal() -> None:
    # Multi-tier pool with equal tier counts → alternating assignment keeps costs equal
    pool = _make_pool(25)
    a, b = generate_matched_deals(pool, seed=42)
    assert deck_cost(a) == deck_cost(b)


def test_mixed_pool_costs_within_tolerance() -> None:
    # 1 ultra (cost=32) + 19 common (cost=16):
    # one deal gets the ultra → diff = 32 + 6*16 - 7*16 = 16 <= 20
    pool = [_card("ultra0", tier=3, rarity=99, sides=_SIDES_T3_ULTRA)] + _make_pool(19)
    a, b = generate_matched_deals(pool, seed=42, tolerance=20)
    assert abs(deck_cost(a) - deck_cost(b)) <= 20


def test_cost_imbalance_raises_deck_generation_error() -> None:
    # 1 ultra + 19 common produces diff=16; tolerance=0 rejects it
    pool = [_card("ultra0", tier=3, rarity=99, sides=_SIDES_T3_ULTRA)] + _make_pool(19)
    with pytest.raises(DeckGenerationError, match="tolerance"):
        generate_matched_deals(pool, seed=42, tolerance=0)


# ---------------------------------------------------------------------------
# Insufficient pool
# ---------------------------------------------------------------------------


def test_insufficient_pool_raises() -> None:
    # 10 unique ultra cards: slot limit = 1 ultra per deal, so deals stay at 1 card each
    pool = [_card(f"ultra{i}", tier=3, rarity=99, sides=_SIDES_T3_ULTRA) for i in range(10)]
    with pytest.raises(DeckGenerationError, match="fill"):
        generate_matched_deals(pool, seed=42)


def test_empty_pool_raises() -> None:
    with pytest.raises(DeckGenerationError):
        generate_matched_deals([], seed=42)


def test_too_small_pool_raises() -> None:
    # 3 unique common card_keys: each deal can have at most 2 copies each = 6 max,
    # can't reach DEAL_SIZE (7).
    pool = _make_pool(3)
    with pytest.raises(DeckGenerationError):
        generate_matched_deals(pool, seed=42)


# ---------------------------------------------------------------------------
# Deck composition rules are honored in the output
# ---------------------------------------------------------------------------


def test_rare_slot_limit_honored() -> None:
    # 8 rare + 20 common: each deck may hold at most 3 rare cards
    pool = [
        _card(f"rare{i}", tier=1, rarity=80, sides=_SIDES_T1_RARE) for i in range(8)
    ] + _make_pool(20)
    a, b = generate_matched_deals(pool, seed=42)
    assert sum(1 for c in a if rarity_bucket(c.rarity) == "rare") <= 3
    assert sum(1 for c in b if rarity_bucket(c.rarity) == "rare") <= 3


def test_tier_diversity_honored() -> None:
    # No single tier may exceed MAX_PER_TIER (3) cards per deal
    from app.rules.deck import MAX_PER_TIER

    pool = _make_pool(30)
    a, b = generate_matched_deals(pool, seed=42)
    for tier in [1, 2, 3]:
        assert sum(1 for c in a if c.tier == tier) <= MAX_PER_TIER
        assert sum(1 for c in b if c.tier == tier) <= MAX_PER_TIER


def test_named_uniqueness_honored() -> None:
    # 2 named "strahd" cards: each deck may hold at most 1
    named_a = _card("named_a", is_named=True, character_key="strahd")
    named_b = _card("named_b", is_named=True, character_key="strahd")
    pool = [named_a, named_b] + _make_pool(22)
    a, b = generate_matched_deals(pool, seed=42)
    assert sum(1 for c in a if c.character_key == "strahd") <= 1
    assert sum(1 for c in b if c.character_key == "strahd") <= 1
