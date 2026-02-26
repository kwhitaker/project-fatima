"""Tests for US-017: weighted deck cost function."""

from app.models.cards import CardDefinition, CardSides
from app.rules.deck import card_cost, deck_cost

# ---------------------------------------------------------------------------
# Card factory
# ---------------------------------------------------------------------------


def _card(*, card_key: str = "c", tier: int, rarity: int, sides: CardSides) -> CardDefinition:
    return CardDefinition(
        card_key=card_key,
        character_key="x",
        name="Test",
        version="v1",
        tier=tier,
        rarity=rarity,
        is_named=False,
        sides=sides,
        set="test",
    )


# Sides per (tier, bucket) — meet budget and cap exactly.
T1_COMMON = CardSides(n=6, e=4, s=3, w=3)  # T1 common:    budget=16, cap=6
T1_UNCOMMON = CardSides(n=6, e=5, s=4, w=3)  # T1 uncommon:  budget=18, cap=7
T1_RARE = CardSides(n=7, e=5, s=5, w=3)  # T1 rare:      budget=20, cap=8
T1_VR = CardSides(n=7, e=6, s=5, w=4)  # T1 very_rare: budget=22, cap=9
T1_ULTRA = CardSides(n=8, e=6, s=6, w=4)  # T1 ultra:     budget=24, cap=9

T2_COMMON = CardSides(n=7, e=5, s=5, w=3)  # T2 common:    budget=20, cap=7
T2_UNCOMMON = CardSides(n=7, e=6, s=5, w=4)  # T2 uncommon:  budget=22, cap=8
T2_RARE = CardSides(n=7, e=7, s=6, w=4)  # T2 rare:      budget=24, cap=9
T2_VR = CardSides(n=8, e=7, s=7, w=4)  # T2 very_rare: budget=26, cap=10
T2_ULTRA = CardSides(n=9, e=8, s=7, w=4)  # T2 ultra:     budget=28, cap=10

T3_COMMON = CardSides(n=7, e=7, s=6, w=4)  # T3 common:    budget=24, cap=8
T3_UNCOMMON = CardSides(n=8, e=7, s=7, w=4)  # T3 uncommon:  budget=26, cap=9
T3_RARE = CardSides(n=8, e=8, s=7, w=5)  # T3 rare:      budget=28, cap=10
T3_VR = CardSides(n=9, e=8, s=8, w=5)  # T3 very_rare: budget=30, cap=10
T3_ULTRA = CardSides(n=10, e=9, s=7, w=6)  # T3 ultra:     budget=32, cap=10


# ---------------------------------------------------------------------------
# card_cost ordering: higher tier => higher cost (same bucket)
# ---------------------------------------------------------------------------


def test_higher_tier_common_costs_more() -> None:
    c1 = _card(card_key="c1", tier=1, rarity=15, sides=T1_COMMON)
    c2 = _card(card_key="c2", tier=2, rarity=15, sides=T2_COMMON)
    c3 = _card(card_key="c3", tier=3, rarity=15, sides=T3_COMMON)
    assert card_cost(c1) < card_cost(c2) < card_cost(c3)


def test_higher_tier_rare_costs_more() -> None:
    c1 = _card(card_key="c1", tier=1, rarity=80, sides=T1_RARE)
    c2 = _card(card_key="c2", tier=2, rarity=80, sides=T2_RARE)
    c3 = _card(card_key="c3", tier=3, rarity=80, sides=T3_RARE)
    assert card_cost(c1) < card_cost(c2) < card_cost(c3)


def test_higher_tier_ultra_costs_more() -> None:
    c1 = _card(card_key="c1", tier=1, rarity=99, sides=T1_ULTRA)
    c2 = _card(card_key="c2", tier=2, rarity=99, sides=T2_ULTRA)
    c3 = _card(card_key="c3", tier=3, rarity=99, sides=T3_ULTRA)
    assert card_cost(c1) < card_cost(c2) < card_cost(c3)


# ---------------------------------------------------------------------------
# card_cost ordering: higher rarity bucket => higher cost (same tier)
# ---------------------------------------------------------------------------


def test_higher_bucket_t1_costs_more() -> None:
    cards = [
        _card(card_key="common", tier=1, rarity=15, sides=T1_COMMON),
        _card(card_key="uncommon", tier=1, rarity=60, sides=T1_UNCOMMON),
        _card(card_key="rare", tier=1, rarity=80, sides=T1_RARE),
        _card(card_key="vr", tier=1, rarity=92, sides=T1_VR),
        _card(card_key="ultra", tier=1, rarity=99, sides=T1_ULTRA),
    ]
    costs = [card_cost(c) for c in cards]
    assert costs == sorted(costs)
    assert len(set(costs)) == 5  # all distinct


def test_higher_bucket_t2_costs_more() -> None:
    cards = [
        _card(card_key="common", tier=2, rarity=15, sides=T2_COMMON),
        _card(card_key="uncommon", tier=2, rarity=60, sides=T2_UNCOMMON),
        _card(card_key="rare", tier=2, rarity=80, sides=T2_RARE),
        _card(card_key="vr", tier=2, rarity=92, sides=T2_VR),
        _card(card_key="ultra", tier=2, rarity=99, sides=T2_ULTRA),
    ]
    costs = [card_cost(c) for c in cards]
    assert costs == sorted(costs)
    assert len(set(costs)) == 5


def test_higher_bucket_t3_costs_more() -> None:
    cards = [
        _card(card_key="common", tier=3, rarity=15, sides=T3_COMMON),
        _card(card_key="uncommon", tier=3, rarity=60, sides=T3_UNCOMMON),
        _card(card_key="rare", tier=3, rarity=80, sides=T3_RARE),
        _card(card_key="vr", tier=3, rarity=92, sides=T3_VR),
        _card(card_key="ultra", tier=3, rarity=99, sides=T3_ULTRA),
    ]
    costs = [card_cost(c) for c in cards]
    assert costs == sorted(costs)
    assert len(set(costs)) == 5


# ---------------------------------------------------------------------------
# Known cost values (cost = sum_budget from STAT_BUDGETS)
# ---------------------------------------------------------------------------


def test_t1_common_card_cost_is_16() -> None:
    c = _card(tier=1, rarity=15, sides=T1_COMMON)
    assert card_cost(c) == 16


def test_t1_ultra_card_cost_is_24() -> None:
    c = _card(tier=1, rarity=99, sides=T1_ULTRA)
    assert card_cost(c) == 24


def test_t2_very_rare_card_cost_is_26() -> None:
    c = _card(tier=2, rarity=92, sides=T2_VR)
    assert card_cost(c) == 26


def test_t3_ultra_card_cost_is_32() -> None:
    c = _card(tier=3, rarity=99, sides=T3_ULTRA)
    assert card_cost(c) == 32


# ---------------------------------------------------------------------------
# deck_cost = sum of card costs
# ---------------------------------------------------------------------------


def test_deck_cost_is_sum_of_card_costs() -> None:
    cards = [_card(card_key=f"c{i}", tier=1, rarity=15, sides=T1_COMMON) for i in range(10)]
    assert deck_cost(cards) == sum(card_cost(c) for c in cards)


def test_all_common_t1_deck_cost_is_160() -> None:
    cards = [_card(card_key=f"c{i}", tier=1, rarity=15, sides=T1_COMMON) for i in range(10)]
    assert deck_cost(cards) == 160  # 10 * 16


def test_deck_cost_mixed_cards() -> None:
    cards = (
        [_card(card_key=f"cm{i}", tier=1, rarity=15, sides=T1_COMMON) for i in range(7)]
        + [_card(card_key=f"uc{i}", tier=1, rarity=60, sides=T1_UNCOMMON) for i in range(2)]
        + [_card(card_key="r0", tier=2, rarity=80, sides=T2_RARE)]
    )
    expected = 7 * 16 + 2 * 18 + 24
    assert deck_cost(cards) == expected


def test_deck_cost_empty_list() -> None:
    assert deck_cost([]) == 0


# ---------------------------------------------------------------------------
# Global ordering: T3 ultra is pricier than T1 common
# ---------------------------------------------------------------------------


def test_t3_ultra_is_more_expensive_than_t1_common() -> None:
    cheap = _card(tier=1, rarity=15, sides=T1_COMMON)
    expensive = _card(tier=3, rarity=99, sides=T3_ULTRA)
    assert card_cost(cheap) < card_cost(expensive)
