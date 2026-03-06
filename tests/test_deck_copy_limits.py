"""Tests for US-016: deal validator copy limits by rarity bucket."""

from app.models.cards import CardDefinition, CardSides
from app.rules.deck import validate_deal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COMMON_SIDES = CardSides(n=6, e=4, s=3, w=3)  # T1 common: sum=16, cap=6 ✓
UNCOMMON_SIDES = CardSides(n=6, e=5, s=4, w=3)  # T1 uncommon: sum=18, cap=7 ✓
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


def _valid_deal() -> list[CardDefinition]:
    """Return a valid 8-card deal: 3 T1 + 3 T2 + 2 T3 (all common, distinct keys)."""
    deal: list[CardDefinition] = []
    for i in range(3):
        deal.append(_card(f"t1_{i}", tier=1, rarity=15, sides=COMMON_SIDES))
    for i in range(3):
        deal.append(_card(f"t2_{i}", tier=2, rarity=15, sides=COMMON_SIDES))
    for i in range(2):
        deal.append(_card(f"t3_{i}", tier=3, rarity=15, sides=COMMON_SIDES))
    return deal


# ---------------------------------------------------------------------------
# Common: 2 copies allowed
# ---------------------------------------------------------------------------


def test_two_copies_common_passes() -> None:
    deal = _valid_deal()
    # Replace two T1 slots with same card_key (common allows 2 copies)
    deal[0] = _card("dup", tier=1, rarity=15, sides=COMMON_SIDES)
    deal[1] = _card("dup", tier=1, rarity=15, sides=COMMON_SIDES)
    assert validate_deal(deal) == []


def test_three_copies_common_fails() -> None:
    deal = _valid_deal()
    # Replace all three T1 slots with same card_key
    for i in range(3):
        deal[i] = _card("dup", tier=1, rarity=15, sides=COMMON_SIDES)
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "dup" in e and "copy" in e.lower()]
    assert len(copy_errs) == 1
    assert "3" in copy_errs[0]


# ---------------------------------------------------------------------------
# Uncommon: 2 copies allowed
# ---------------------------------------------------------------------------


def test_two_copies_uncommon_passes() -> None:
    deal = _valid_deal()
    deal[0] = _card("uc_dup", tier=1, rarity=60, sides=UNCOMMON_SIDES)
    deal[1] = _card("uc_dup", tier=1, rarity=60, sides=UNCOMMON_SIDES)
    assert validate_deal(deal) == []


def test_three_copies_uncommon_fails() -> None:
    deal = _valid_deal()
    for i in range(3):
        deal[i] = _card("uc_dup", tier=1, rarity=60, sides=UNCOMMON_SIDES)
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "uc_dup" in e and "copy" in e.lower()]
    assert len(copy_errs) == 1
    assert "3" in copy_errs[0]


# ---------------------------------------------------------------------------
# Rare: 1 copy allowed
# ---------------------------------------------------------------------------


def test_one_copy_rare_passes() -> None:
    deal = _valid_deal()
    deal[3] = _card("rare_dup", tier=2, rarity=80, sides=RARE_SIDES)
    assert validate_deal(deal) == []


def test_two_copies_rare_fails() -> None:
    deal = _valid_deal()
    deal[3] = _card("rare_dup", tier=2, rarity=80, sides=RARE_SIDES)
    deal[4] = _card("rare_dup", tier=2, rarity=80, sides=RARE_SIDES)
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "rare_dup" in e and "copy" in e.lower()]
    assert len(copy_errs) == 1
    assert "2" in copy_errs[0]


# ---------------------------------------------------------------------------
# Very rare: 1 copy allowed
# ---------------------------------------------------------------------------


def test_one_copy_very_rare_passes() -> None:
    deal = _valid_deal()
    deal[3] = _card("vr_dup", tier=2, rarity=92, sides=VERY_RARE_SIDES)
    assert validate_deal(deal) == []


def test_two_copies_very_rare_fails() -> None:
    deal = _valid_deal()
    deal[3] = _card("vr_dup", tier=2, rarity=92, sides=VERY_RARE_SIDES)
    deal[4] = _card("vr_dup", tier=2, rarity=92, sides=VERY_RARE_SIDES)
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "vr_dup" in e and "copy" in e.lower()]
    assert len(copy_errs) == 1
    assert "2" in copy_errs[0]


# ---------------------------------------------------------------------------
# Ultra: 1 copy allowed
# ---------------------------------------------------------------------------


def test_one_copy_ultra_passes() -> None:
    deal = _valid_deal()
    deal[-1] = _card("ultra_dup", tier=3, rarity=99, sides=ULTRA_SIDES)
    assert validate_deal(deal) == []


def test_two_copies_ultra_fails() -> None:
    # 2 copies of the same ultra card fails copy limit (ultra allows only 1 copy per card_key).
    # Rarity slot (ultra ≤ 2) is fine, but the copy-limit error should be present.
    deal = _valid_deal()
    deal[-1] = _card("ultra_dup", tier=3, rarity=99, sides=ULTRA_SIDES)
    deal[-2] = _card("ultra_dup", tier=3, rarity=99, sides=ULTRA_SIDES)
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "ultra_dup" in e and "copy" in e.lower()]
    assert len(copy_errs) == 1
    assert "2" in copy_errs[0]


# ---------------------------------------------------------------------------
# Error message content
# ---------------------------------------------------------------------------


def test_copy_error_message_is_actionable() -> None:
    deal = _valid_deal()
    for i in range(3):
        deal[i] = _card("my_card", tier=1, rarity=15, sides=COMMON_SIDES)
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "my_card" in e]
    assert len(copy_errs) == 1
    msg = copy_errs[0]
    # Message should mention the card_key, actual count, and max allowed
    assert "my_card" in msg
    assert "3" in msg
    assert "2" in msg


# ---------------------------------------------------------------------------
# Multiple distinct card_keys each violating limits
# ---------------------------------------------------------------------------


def test_two_distinct_copy_violations_both_reported() -> None:
    # 3 copies of alpha (T1) + 3 copies of beta (T2) + 2 filler (T3)
    deal = [
        _card("alpha", tier=1, rarity=15, sides=COMMON_SIDES),
        _card("alpha", tier=1, rarity=15, sides=COMMON_SIDES),
        _card("alpha", tier=1, rarity=15, sides=COMMON_SIDES),
        _card("beta", tier=2, rarity=15, sides=COMMON_SIDES),
        _card("beta", tier=2, rarity=15, sides=COMMON_SIDES),
        _card("beta", tier=2, rarity=15, sides=COMMON_SIDES),
        _card("t3_0", tier=3, rarity=15, sides=COMMON_SIDES),
        _card("t3_1", tier=3, rarity=15, sides=COMMON_SIDES),
    ]
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "copy" in e.lower()]
    assert len(copy_errs) == 2
    assert any("alpha" in e for e in copy_errs)
    assert any("beta" in e for e in copy_errs)


# ---------------------------------------------------------------------------
# Copy limit and rarity slot violations co-exist independently
# ---------------------------------------------------------------------------


def test_copy_limit_and_slot_limit_both_reported() -> None:
    # 2 copies of same rare card_key (copy violation) + 4 distinct rare cards (slot violation)
    # Spread rares across tiers to maintain tier validity
    deal = [
        _card("t1_0", tier=1, rarity=15, sides=COMMON_SIDES),  # T1 filler
        _card("r_t1", tier=1, rarity=80, sides=RARE_SIDES),  # T1 rare
        _card("rare_dup", tier=1, rarity=80, sides=RARE_SIDES),  # T1 rare (dup key)
        _card("rare_dup", tier=2, rarity=80, sides=RARE_SIDES),  # T2 rare (dup - copy err)
        _card("r_t2_0", tier=2, rarity=80, sides=RARE_SIDES),  # T2 rare
        _card("r_t2_1", tier=2, rarity=80, sides=RARE_SIDES),  # T2 rare
        _card("t3_0", tier=3, rarity=15, sides=COMMON_SIDES),  # T3 filler
        _card("t3_1", tier=3, rarity=15, sides=COMMON_SIDES),  # T3 filler
    ]
    errs = validate_deal(deal)
    assert any("rare_dup" in e and "copy" in e.lower() for e in errs)
    assert any("rare" in e and "very_rare" not in e and "copy" not in e.lower() for e in errs)
