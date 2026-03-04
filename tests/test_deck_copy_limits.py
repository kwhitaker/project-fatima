"""Tests for US-016: deal validator copy limits by rarity bucket."""

from app.models.cards import CardDefinition, CardSides
from app.rules.deck import DEAL_SIZE, validate_deal

# ---------------------------------------------------------------------------
# Helpers (same side values as test_deck_validator.py)
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


def _common(n: int, card_key: str | None = None) -> CardDefinition:
    key = card_key if card_key is not None else f"common_{n}"
    return _card(key, tier=1, rarity=15, sides=COMMON_SIDES)


def _uncommon(n: int, card_key: str | None = None) -> CardDefinition:
    key = card_key if card_key is not None else f"uncommon_{n}"
    return _card(key, tier=1, rarity=60, sides=UNCOMMON_SIDES)


def _rare(n: int, card_key: str | None = None) -> CardDefinition:
    key = card_key if card_key is not None else f"rare_{n}"
    return _card(key, tier=2, rarity=80, sides=RARE_SIDES)


def _very_rare(n: int, card_key: str | None = None) -> CardDefinition:
    key = card_key if card_key is not None else f"vrare_{n}"
    return _card(key, tier=2, rarity=92, sides=VERY_RARE_SIDES)


def _ultra(n: int, card_key: str | None = None) -> CardDefinition:
    key = card_key if card_key is not None else f"ultra_{n}"
    return _card(key, tier=3, rarity=99, sides=ULTRA_SIDES)


# ---------------------------------------------------------------------------
# Common: 2 copies allowed
# ---------------------------------------------------------------------------


def test_two_copies_common_passes() -> None:
    deal = [_common(i) for i in range(DEAL_SIZE - 2)]
    deal.append(_card("dup", tier=1, rarity=15, sides=COMMON_SIDES))
    deal.append(_card("dup", tier=1, rarity=15, sides=COMMON_SIDES))
    assert validate_deal(deal) == []


def test_three_copies_common_fails() -> None:
    deal = [_common(i) for i in range(DEAL_SIZE - 3)]
    for _ in range(3):
        deal.append(_card("dup", tier=1, rarity=15, sides=COMMON_SIDES))
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "dup" in e and "copy" in e.lower()]
    assert len(copy_errs) == 1
    assert "3" in copy_errs[0]


# ---------------------------------------------------------------------------
# Uncommon: 2 copies allowed
# ---------------------------------------------------------------------------


def test_two_copies_uncommon_passes() -> None:
    deal = [_common(i) for i in range(DEAL_SIZE - 2)]
    deal.append(_card("uc_dup", tier=1, rarity=60, sides=UNCOMMON_SIDES))
    deal.append(_card("uc_dup", tier=1, rarity=60, sides=UNCOMMON_SIDES))
    assert validate_deal(deal) == []


def test_three_copies_uncommon_fails() -> None:
    deal = [_common(i) for i in range(DEAL_SIZE - 3)]
    for _ in range(3):
        deal.append(_card("uc_dup", tier=1, rarity=60, sides=UNCOMMON_SIDES))
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "uc_dup" in e and "copy" in e.lower()]
    assert len(copy_errs) == 1
    assert "3" in copy_errs[0]


# ---------------------------------------------------------------------------
# Rare: 1 copy allowed
# ---------------------------------------------------------------------------


def test_one_copy_rare_passes() -> None:
    deal = [_common(i) for i in range(DEAL_SIZE - 1)]
    deal.append(_card("rare_dup", tier=2, rarity=80, sides=RARE_SIDES))
    assert validate_deal(deal) == []


def test_two_copies_rare_fails() -> None:
    deal = [_common(i) for i in range(DEAL_SIZE - 2)]
    deal.append(_card("rare_dup", tier=2, rarity=80, sides=RARE_SIDES))
    deal.append(_card("rare_dup", tier=2, rarity=80, sides=RARE_SIDES))
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "rare_dup" in e and "copy" in e.lower()]
    assert len(copy_errs) == 1
    assert "2" in copy_errs[0]


# ---------------------------------------------------------------------------
# Very rare: 1 copy allowed
# ---------------------------------------------------------------------------


def test_one_copy_very_rare_passes() -> None:
    deal = [_common(i) for i in range(DEAL_SIZE - 1)]
    deal.append(_card("vr_dup", tier=2, rarity=92, sides=VERY_RARE_SIDES))
    assert validate_deal(deal) == []


def test_two_copies_very_rare_fails() -> None:
    deal = [_common(i) for i in range(DEAL_SIZE - 2)]
    deal.append(_card("vr_dup", tier=2, rarity=92, sides=VERY_RARE_SIDES))
    deal.append(_card("vr_dup", tier=2, rarity=92, sides=VERY_RARE_SIDES))
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "vr_dup" in e and "copy" in e.lower()]
    assert len(copy_errs) == 1
    assert "2" in copy_errs[0]


# ---------------------------------------------------------------------------
# Ultra: 1 copy allowed
# ---------------------------------------------------------------------------


def test_one_copy_ultra_passes() -> None:
    deal = [_common(i) for i in range(DEAL_SIZE - 1)]
    deal.append(_card("ultra_dup", tier=3, rarity=99, sides=ULTRA_SIDES))
    assert validate_deal(deal) == []


def test_two_copies_ultra_fails() -> None:
    # Normally 2 ultra would also fail the rarity slot check (ultra ≤ 1),
    # but we verify the copy-limit error is also present.
    deal = [_common(i) for i in range(DEAL_SIZE - 2)]
    deal.append(_card("ultra_dup", tier=3, rarity=99, sides=ULTRA_SIDES))
    deal.append(_card("ultra_dup", tier=3, rarity=99, sides=ULTRA_SIDES))
    errs = validate_deal(deal)
    copy_errs = [e for e in errs if "ultra_dup" in e and "copy" in e.lower()]
    assert len(copy_errs) == 1
    assert "2" in copy_errs[0]


# ---------------------------------------------------------------------------
# Error message content
# ---------------------------------------------------------------------------


def test_copy_error_message_is_actionable() -> None:
    deal = [_common(i) for i in range(DEAL_SIZE - 3)]
    for _ in range(3):
        deal.append(_card("my_card", tier=1, rarity=15, sides=COMMON_SIDES))
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
    # Need DEAL_SIZE cards total: some filler + 3 alpha + 3 beta
    # DEAL_SIZE - 6 filler + 3 alpha + 3 beta = DEAL_SIZE + 0 (7-6=1 filler)
    deal = [_common(i) for i in range(DEAL_SIZE - 6)]
    for _ in range(3):
        deal.append(_card("alpha", tier=1, rarity=15, sides=COMMON_SIDES))
    for _ in range(3):
        deal.append(_card("beta", tier=1, rarity=15, sides=COMMON_SIDES))
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
    # Total rare = 6, need filler to reach DEAL_SIZE
    deal = [_common(i) for i in range(DEAL_SIZE - 6)]
    deal.append(_card("rare_dup", tier=2, rarity=80, sides=RARE_SIDES))
    deal.append(_card("rare_dup", tier=2, rarity=80, sides=RARE_SIDES))
    deal.append(_rare(1))
    deal.append(_rare(2))
    deal.append(_rare(3))
    deal.append(_rare(4))
    errs = validate_deal(deal)
    assert any("rare_dup" in e and "copy" in e.lower() for e in errs)
    assert any("rare" in e and "very_rare" not in e and "copy" not in e.lower() for e in errs)
