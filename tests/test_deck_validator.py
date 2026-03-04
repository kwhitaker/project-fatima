"""Tests for US-015: deal validator (size, named uniqueness, rarity slots)."""

from app.models.cards import CardDefinition, CardSides
from app.rules.deck import DEAL_SIZE, validate_deal

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
    """Return a valid DEAL_SIZE-card deal (all common, distinct keys)."""
    return [_common(f"card_{i}") for i in range(DEAL_SIZE)]


# ---------------------------------------------------------------------------
# Deal size
# ---------------------------------------------------------------------------


def test_valid_deal_passes() -> None:
    assert validate_deal(_valid_deal()) == []


def test_undersized_deal_fails() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 1)]
    errs = validate_deal(deal)
    assert len(errs) == 1
    assert str(DEAL_SIZE) in errs[0]
    assert str(DEAL_SIZE - 1) in errs[0]


def test_oversized_deal_fails() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE + 1)]
    errs = validate_deal(deal)
    assert len(errs) == 1
    assert str(DEAL_SIZE) in errs[0]
    assert str(DEAL_SIZE + 1) in errs[0]


def test_empty_deal_fails() -> None:
    errs = validate_deal([])
    assert len(errs) == 1
    assert str(DEAL_SIZE) in errs[0]
    assert "0" in errs[0]


# ---------------------------------------------------------------------------
# Named character uniqueness
# ---------------------------------------------------------------------------


def test_single_named_card_passes() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 1)]
    deal.append(_common("hero_i", character_key="strahd", is_named=True))
    assert validate_deal(deal) == []


def test_two_named_cards_same_character_key_fails() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 2)]
    deal.append(_common("strahd_i", character_key="strahd", is_named=True))
    deal.append(_common("strahd_ii", character_key="strahd", is_named=True))
    errs = validate_deal(deal)
    assert len(errs) == 1
    assert "strahd" in errs[0]
    assert "2" in errs[0]


def test_three_named_copies_reports_count_three() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 3)]
    for suffix in ("i", "ii", "iii"):
        deal.append(_common(f"villain_{suffix}", character_key="villain", is_named=True))
    errs = validate_deal(deal)
    assert len(errs) == 1
    assert "3" in errs[0]
    assert "villain" in errs[0]


def test_unnamed_cards_same_character_key_allowed() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 2)]
    deal.append(_common("zombie_a", character_key="zombie", is_named=False))
    deal.append(_common("zombie_b", character_key="zombie", is_named=False))
    assert validate_deal(deal) == []


def test_two_different_named_characters_both_single_passes() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 2)]
    deal.append(_common("alpha_i", character_key="alpha", is_named=True))
    deal.append(_common("beta_i", character_key="beta", is_named=True))
    assert validate_deal(deal) == []


def test_two_different_named_characters_both_duplicated_reports_two_errors() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 4)]
    deal.append(_common("a_i", character_key="alpha", is_named=True))
    deal.append(_common("a_ii", character_key="alpha", is_named=True))
    deal.append(_common("b_i", character_key="beta", is_named=True))
    deal.append(_common("b_ii", character_key="beta", is_named=True))
    errs = validate_deal(deal)
    named_errs = [e for e in errs if "times" in e]
    assert len(named_errs) == 2
    assert any("alpha" in e for e in named_errs)
    assert any("beta" in e for e in named_errs)


# ---------------------------------------------------------------------------
# Rarity slots
# ---------------------------------------------------------------------------


def test_one_ultra_passes() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 1)]
    deal.append(_ultra("u1"))
    assert validate_deal(deal) == []


def test_two_ultra_fails() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 2)]
    deal.append(_ultra("u1"))
    deal.append(_ultra("u2"))
    errs = validate_deal(deal)
    assert len(errs) == 1
    assert "ultra" in errs[0]
    assert "2" in errs[0]


def test_two_very_rare_passes() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 2)]
    deal.append(_very_rare("vr1"))
    deal.append(_very_rare("vr2"))
    assert validate_deal(deal) == []


def test_three_very_rare_fails() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 3)]
    deal.append(_very_rare("vr1"))
    deal.append(_very_rare("vr2"))
    deal.append(_very_rare("vr3"))
    errs = validate_deal(deal)
    assert len(errs) == 1
    assert "very_rare" in errs[0]
    assert "3" in errs[0]


def test_three_rare_passes() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 3)]
    deal.append(_rare("r1"))
    deal.append(_rare("r2"))
    deal.append(_rare("r3"))
    assert validate_deal(deal) == []


def test_four_rare_fails() -> None:
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 4)]
    deal.append(_rare("r1"))
    deal.append(_rare("r2"))
    deal.append(_rare("r3"))
    deal.append(_rare("r4"))
    errs = validate_deal(deal)
    assert len(errs) == 1
    assert "rare" in errs[0]
    assert "very_rare" not in errs[0]
    assert "4" in errs[0]


def test_max_rarity_slots_combined_passes() -> None:
    # 1 ultra + 2 very_rare + 3 rare + 1 common = 7
    deal = [_common("c_0")]
    deal.append(_ultra("u1"))
    deal.append(_very_rare("vr1"))
    deal.append(_very_rare("vr2"))
    deal.append(_rare("r1"))
    deal.append(_rare("r2"))
    deal.append(_rare("r3"))
    assert validate_deal(deal) == []


def test_multiple_slot_violations_reported_independently() -> None:
    # 2 ultra + 3 very_rare + 4 rare = 9 (oversized + slot violations)
    deal = [_ultra("u1"), _ultra("u2")]
    deal.append(_very_rare("vr1"))
    deal.append(_very_rare("vr2"))
    deal.append(_very_rare("vr3"))
    deal.append(_rare("r1"))
    deal.append(_rare("r2"))
    deal.append(_rare("r3"))
    deal.append(_rare("r4"))
    errs = validate_deal(deal)
    assert any("ultra" in e for e in errs)
    assert any("very_rare" in e for e in errs)
    assert any("rare" in e and "very_rare" not in e for e in errs)


# ---------------------------------------------------------------------------
# Multiple error categories together
# ---------------------------------------------------------------------------


def test_size_and_named_violation_both_reported() -> None:
    # DEAL_SIZE+1 cards (size) + 2 copies of same named character
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE - 1)]
    deal.append(_common("named_a", character_key="hero", is_named=True))
    deal.append(_common("named_b", character_key="hero", is_named=True))
    errs = validate_deal(deal)
    assert any(str(DEAL_SIZE + 1) in e for e in errs)
    assert any("hero" in e for e in errs)


def test_size_and_rarity_violation_both_reported() -> None:
    # DEAL_SIZE+2 cards (size) + 2 ultra (rarity slot)
    deal = [_common(f"c_{i}") for i in range(DEAL_SIZE)]
    deal.append(_ultra("u1"))
    deal.append(_ultra("u2"))
    errs = validate_deal(deal)
    assert any(str(DEAL_SIZE + 2) in e for e in errs)
    assert any("ultra" in e for e in errs)
