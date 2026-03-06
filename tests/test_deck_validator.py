"""Tests for US-015: deal validator (size, tier slots, named uniqueness, rarity slots)."""

from app.models.cards import CardDefinition, CardSides
from app.rules.deck import DEAL_SIZE, DEAL_TIER_SLOTS, validate_deal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COMMON_SIDES = CardSides(n=6, e=4, s=3, w=3)  # T1 common: sum=16, cap=6 ✓
RARE_SIDES = CardSides(n=7, e=6, s=6, w=5)  # T2 rare: sum=24, cap=9 ✓
VERY_RARE_SIDES = CardSides(n=7, e=7, s=7, w=5)  # T2 very_rare: sum=26, cap=10 ✓
ULTRA_SIDES = CardSides(n=10, e=8, s=8, w=6)  # T3 ultra: sum=32, cap=10 ✓


def _card(
    card_key: str,
    *,
    character_key: str = "generic",
    is_named: bool = False,
    tier: int = 1,
    rarity: int = 15,
    sides: CardSides = COMMON_SIDES,
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


def _common(card_key: str, **kwargs: object) -> CardDefinition:
    return _card(card_key, tier=1, rarity=15, sides=COMMON_SIDES, **kwargs)  # type: ignore[arg-type]


def _rare(card_key: str, **kwargs: object) -> CardDefinition:
    return _card(card_key, tier=2, rarity=75, sides=RARE_SIDES, **kwargs)  # type: ignore[arg-type]


def _very_rare(card_key: str, **kwargs: object) -> CardDefinition:
    return _card(card_key, tier=2, rarity=90, sides=VERY_RARE_SIDES, **kwargs)  # type: ignore[arg-type]


def _ultra(card_key: str, **kwargs: object) -> CardDefinition:
    return _card(card_key, tier=3, rarity=100, sides=ULTRA_SIDES, **kwargs)  # type: ignore[arg-type]


def _valid_deal() -> list[CardDefinition]:
    """Return a valid DEAL_SIZE-card deal: 3 T1 + 3 T2 + 2 T3 (all common)."""
    deal: list[CardDefinition] = []
    for i in range(3):
        deal.append(_common(f"t1_{i}"))
    for i in range(3):
        deal.append(_card(f"t2_{i}", tier=2, rarity=15, sides=COMMON_SIDES))
    for i in range(2):
        deal.append(_card(f"t3_{i}", tier=3, rarity=15, sides=COMMON_SIDES))
    return deal


# ---------------------------------------------------------------------------
# Deal size
# ---------------------------------------------------------------------------


def test_valid_deal_passes() -> None:
    assert validate_deal(_valid_deal()) == []


def test_undersized_deal_fails() -> None:
    deal = _valid_deal()[:DEAL_SIZE - 1]
    errs = validate_deal(deal)
    assert any(str(DEAL_SIZE) in e and str(DEAL_SIZE - 1) in e for e in errs)


def test_oversized_deal_fails() -> None:
    deal = _valid_deal() + [_common("extra")]
    errs = validate_deal(deal)
    assert any(str(DEAL_SIZE) in e and str(DEAL_SIZE + 1) in e for e in errs)


def test_empty_deal_fails() -> None:
    errs = validate_deal([])
    assert any(str(DEAL_SIZE) in e and "0" in e for e in errs)


# ---------------------------------------------------------------------------
# Tier slots
# ---------------------------------------------------------------------------


def test_correct_tier_distribution_passes() -> None:
    assert validate_deal(_valid_deal()) == []


def test_wrong_tier_distribution_fails() -> None:
    # All T1 common: T2=0, T3=0 → tier errors
    deal = [_common(f"all_t1_{i}") for i in range(DEAL_SIZE)]
    errs = validate_deal(deal)
    tier_errs = [e for e in errs if "Tier" in e]
    assert len(tier_errs) >= 2  # T2 and T3 wrong


def test_both_deals_have_exact_tier_slots() -> None:
    """Tier slot counts must match DEAL_TIER_SLOTS exactly."""
    deal = _valid_deal()
    for tier, required in DEAL_TIER_SLOTS.items():
        assert sum(1 for c in deal if c.tier == tier) == required


# ---------------------------------------------------------------------------
# Named character uniqueness
# ---------------------------------------------------------------------------


def test_single_named_card_passes() -> None:
    deal = _valid_deal()
    deal[0] = _common("hero_i", character_key="strahd", is_named=True)
    assert validate_deal(deal) == []


def test_two_named_cards_same_character_key_fails() -> None:
    deal = _valid_deal()
    deal[0] = _common("strahd_i", character_key="strahd", is_named=True)
    deal[1] = _common("strahd_ii", character_key="strahd", is_named=True)
    errs = validate_deal(deal)
    named_errs = [e for e in errs if "strahd" in e and "times" in e]
    assert len(named_errs) == 1
    assert "2" in named_errs[0]


def test_three_named_copies_reports_count_three() -> None:
    deal = _valid_deal()
    for i, suffix in enumerate(("i", "ii", "iii")):
        deal[i] = _common(f"villain_{suffix}", character_key="villain", is_named=True)
    errs = validate_deal(deal)
    named_errs = [e for e in errs if "villain" in e and "times" in e]
    assert len(named_errs) == 1
    assert "3" in named_errs[0]


def test_unnamed_cards_same_character_key_allowed() -> None:
    deal = _valid_deal()
    deal[0] = _common("zombie_a", character_key="zombie", is_named=False)
    deal[1] = _common("zombie_b", character_key="zombie", is_named=False)
    assert validate_deal(deal) == []


def test_two_different_named_characters_both_single_passes() -> None:
    deal = _valid_deal()
    deal[0] = _common("alpha_i", character_key="alpha", is_named=True)
    deal[1] = _common("beta_i", character_key="beta", is_named=True)
    assert validate_deal(deal) == []


def test_two_different_named_characters_both_duplicated_reports_two_errors() -> None:
    deal = _valid_deal()
    deal[0] = _common("a_i", character_key="alpha", is_named=True)
    deal[1] = _common("a_ii", character_key="alpha", is_named=True)
    deal[2] = _common("b_i", character_key="beta", is_named=True)
    # Replace a T2 slot to keep tier counts valid
    deal[3] = _card(
        "b_ii", tier=2, rarity=15, sides=COMMON_SIDES,
        character_key="beta", is_named=True,
    )
    errs = validate_deal(deal)
    named_errs = [e for e in errs if "times" in e]
    assert len(named_errs) == 2
    assert any("alpha" in e for e in named_errs)
    assert any("beta" in e for e in named_errs)


# ---------------------------------------------------------------------------
# Rarity slots
# ---------------------------------------------------------------------------


def test_one_ultra_passes() -> None:
    deal = _valid_deal()
    # Replace one T3 common with T3 ultra
    deal[-1] = _ultra("u1")
    assert validate_deal(deal) == []


def test_two_ultra_passes() -> None:
    deal = _valid_deal()
    # Replace both T3 slots with ultra — allowed (limit is 2)
    deal[-1] = _ultra("u1")
    deal[-2] = _ultra("u2")
    assert validate_deal(deal) == []


def test_two_very_rare_passes() -> None:
    deal = _valid_deal()
    # Replace two T2 common with T2 very_rare
    deal[3] = _very_rare("vr1")
    deal[4] = _very_rare("vr2")
    assert validate_deal(deal) == []


def test_three_very_rare_fails() -> None:
    deal = _valid_deal()
    # Replace all three T2 slots with very_rare
    deal[3] = _very_rare("vr1")
    deal[4] = _very_rare("vr2")
    deal[5] = _very_rare("vr3")
    errs = validate_deal(deal)
    vr_errs = [e for e in errs if "very_rare" in e]
    assert len(vr_errs) == 1
    assert "3" in vr_errs[0]


def test_three_rare_passes() -> None:
    deal = _valid_deal()
    # Replace all three T2 slots with rare
    deal[3] = _rare("r1")
    deal[4] = _rare("r2")
    deal[5] = _rare("r3")
    assert validate_deal(deal) == []


def test_four_rare_fails() -> None:
    # 4 rare cards: 3 T2 rare + 1 T1 rare (rarity is independent of tier)
    deal = _valid_deal()
    deal[0] = _card("r_t1", tier=1, rarity=75, sides=RARE_SIDES)  # T1 rare
    deal[3] = _rare("r1")
    deal[4] = _rare("r2")
    deal[5] = _rare("r3")
    errs = validate_deal(deal)
    rare_errs = [e for e in errs if "rare" in e and "very_rare" not in e]
    assert len(rare_errs) == 1
    assert "4" in rare_errs[0]


def test_max_rarity_slots_combined_passes() -> None:
    # 1 ultra (T3) + 2 very_rare (T2) + 1 rare (T2) + 2 rare (T1) + 1 common (T1) + 1 common (T3)
    # Tier distribution: T1=3, T2=3, T3=2 ✓
    # Rarity: 1 ultra, 2 very_rare, 3 rare ✓
    deal = [
        _common("c_0"),  # T1 common
        _card("r_t1_0", tier=1, rarity=75, sides=RARE_SIDES),  # T1 rare
        _card("r_t1_1", tier=1, rarity=75, sides=RARE_SIDES),  # T1 rare
        _very_rare("vr1"),  # T2 very_rare
        _very_rare("vr2"),  # T2 very_rare
        _rare("r1"),  # T2 rare
        _ultra("u1"),  # T3 ultra
        _card("t3_c", tier=3, rarity=15, sides=COMMON_SIDES),  # T3 common
    ]
    assert validate_deal(deal) == []


def test_multiple_slot_violations_reported_independently() -> None:
    # 3 ultra + 3 very_rare + 4 rare = 10 cards (oversized + all 3 slot violations)
    deal = [
        _card("r_t1_0", tier=1, rarity=75, sides=RARE_SIDES),  # T1 rare
        _card("r_t1_1", tier=1, rarity=75, sides=RARE_SIDES),  # T1 rare
        _card("r_t1_2", tier=1, rarity=75, sides=RARE_SIDES),  # T1 rare
        _card("r_t1_3", tier=1, rarity=75, sides=RARE_SIDES),  # T1 rare (4th → violation)
        _very_rare("vr1"),  # T2 very_rare
        _very_rare("vr2"),  # T2 very_rare
        _very_rare("vr3"),  # T2 very_rare (3rd → violation)
        _ultra("u1"),  # T3 ultra
        _ultra("u2"),  # T3 ultra
        _ultra("u3"),  # T3 ultra (3rd → violation)
    ]
    errs = validate_deal(deal)
    assert any("ultra" in e for e in errs)
    assert any("very_rare" in e for e in errs)
    assert any("rare" in e and "very_rare" not in e for e in errs)


# ---------------------------------------------------------------------------
# Multiple error categories together
# ---------------------------------------------------------------------------


def test_size_and_named_violation_both_reported() -> None:
    # DEAL_SIZE+1 cards + 2 copies of same named character
    deal = _valid_deal()
    deal[0] = _common("named_a", character_key="hero", is_named=True)
    deal.append(_common("named_b", character_key="hero", is_named=True))
    errs = validate_deal(deal)
    assert any(str(DEAL_SIZE + 1) in e for e in errs)
    assert any("hero" in e for e in errs)


def test_size_and_rarity_violation_both_reported() -> None:
    # DEAL_SIZE+3 cards + 3 ultra
    deal = _valid_deal()
    deal.append(_ultra("u1"))
    deal.append(_ultra("u2"))
    deal.append(_ultra("u3"))
    errs = validate_deal(deal)
    assert any(str(DEAL_SIZE + 3) in e for e in errs)
    assert any("ultra" in e for e in errs)
