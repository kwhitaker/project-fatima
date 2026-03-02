"""Tests for US-014: rarity bucket derivation and balance enforcement."""

import json

import pytest

from app.models.cards import CardDefinition, CardSides
from app.rules.cards import (
    STAT_BUDGETS,
    load_cards_from_lines,
    rarity_bucket,
    validate_card_balance,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _card(tier: int, rarity: int, sides: dict[str, int], **kwargs) -> dict:
    return {
        "card_key": kwargs.get("card_key", "test_card"),
        "character_key": kwargs.get("character_key", "test"),
        "name": "Test",
        "version": "v1",
        "tier": tier,
        "rarity": rarity,
        "is_named": False,
        "sides": sides,
        "set": "test_set",
        "element": "shadow",
    }


def _lines(*objs: dict) -> list[str]:
    return [json.dumps(obj) for obj in objs]


def _make_card(tier: int, rarity: int, n: int, e: int, s: int, w: int) -> CardDefinition:
    return CardDefinition(
        card_key="t",
        character_key="t",
        name="T",
        version="v",
        tier=tier,
        rarity=rarity,
        is_named=False,
        sides=CardSides(n=n, e=e, s=s, w=w),
        set="s",
        element="shadow",
    )


# ---------------------------------------------------------------------------
# rarity_bucket boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rarity,expected",
    [
        (1, "common"),
        (25, "common"),
        (49, "common"),
        (50, "uncommon"),
        (62, "uncommon"),
        (74, "uncommon"),
        (75, "rare"),
        (82, "rare"),
        (89, "rare"),
        (90, "very_rare"),
        (93, "very_rare"),
        (96, "very_rare"),
        (97, "ultra"),
        (99, "ultra"),
        (100, "ultra"),
    ],
)
def test_rarity_bucket_boundaries(rarity: int, expected: str) -> None:
    assert rarity_bucket(rarity) == expected


# ---------------------------------------------------------------------------
# STAT_BUDGETS completeness
# ---------------------------------------------------------------------------


def test_stat_budgets_covers_all_tiers_and_buckets() -> None:
    buckets = ["common", "uncommon", "rare", "very_rare", "ultra"]
    for tier in (1, 2, 3):
        for bucket in buckets:
            assert (tier, bucket) in STAT_BUDGETS, f"Missing ({tier}, {bucket})"


# ---------------------------------------------------------------------------
# validate_card_balance — passing cases
# ---------------------------------------------------------------------------


def test_balance_passes_tier1_common_exact_budget() -> None:
    # T1 common: (16, cap 6). Sum=16, max side=6
    card = _make_card(1, 15, n=6, e=4, s=3, w=3)
    assert validate_card_balance(card) == []


def test_balance_passes_tier1_common_above_budget() -> None:
    # T1 common: (16, cap 6). Sum=18 > 16, max side=6
    card = _make_card(1, 10, n=6, e=6, s=3, w=3)
    assert validate_card_balance(card) == []


def test_balance_passes_tier3_ultra_example() -> None:
    # Strahd III: T3 ultra (32, cap 10), sum=32, min side=3 (weak-side compliant)
    card = CardDefinition(
        card_key="strahd_iii",
        character_key="strahd_von_zarovich",
        name="Strahd",
        version="III",
        tier=3,
        rarity=100,
        is_named=True,
        sides=CardSides(n=10, e=10, s=9, w=3),
        set="barovia",
        element="blood",
    )
    assert validate_card_balance(card) == []


def test_balance_passes_tier2_very_rare() -> None:
    # T2 very_rare: (26, cap 10). Sum=26, max=10, min side=3 (weak-side compliant)
    card = _make_card(2, 95, n=10, e=7, s=6, w=3)
    assert validate_card_balance(card) == []


# ---------------------------------------------------------------------------
# validate_card_balance — sum budget failures
# ---------------------------------------------------------------------------


def test_balance_fails_sum_below_budget_tier1_common() -> None:
    # T1 common budget=16; sides sum to 15
    card = _make_card(1, 1, n=5, e=4, s=3, w=3)
    errs = validate_card_balance(card)
    assert len(errs) == 1
    assert "budget" in errs[0].lower()
    assert "15" in errs[0]


def test_balance_fails_sum_below_budget_tier2_rare() -> None:
    # T2 rare budget=24; sides sum to 23, min side=3 so only budget fails
    card = _make_card(2, 80, n=7, e=6, s=7, w=3)
    errs = validate_card_balance(card)
    assert len(errs) == 1
    assert "budget" in errs[0].lower()


def test_balance_fails_sum_below_budget_tier3_uncommon() -> None:
    # T3 uncommon budget=26; sides sum to 25, min side=3 so only budget fails
    card = _make_card(3, 60, n=7, e=7, s=8, w=3)
    errs = validate_card_balance(card)
    assert len(errs) == 1
    assert "budget" in errs[0].lower()


# ---------------------------------------------------------------------------
# validate_card_balance — side cap failures
# ---------------------------------------------------------------------------


def test_balance_fails_side_exceeds_cap_tier1_common() -> None:
    # T1 common cap=6; side n=7 exceeds cap (sum=17 >= 16 so only cap fails)
    card = _make_card(1, 15, n=7, e=4, s=3, w=3)
    errs = validate_card_balance(card)
    assert len(errs) == 1
    assert "cap" in errs[0].lower()
    assert "'n'" in errs[0]


def test_balance_fails_multiple_sides_exceed_cap() -> None:
    # T1 uncommon cap=7; n=8 e=8 both exceed cap (sum=18 >= 18, budget ok)
    card = _make_card(1, 60, n=8, e=8, s=1, w=1)
    errs = validate_card_balance(card)
    assert len(errs) == 2
    assert all("cap" in e.lower() for e in errs)


def test_balance_fails_both_sum_and_cap() -> None:
    # T2 uncommon (22, cap 8); n=9 exceeds cap, sum=9+2+2+2=15 below budget 22
    card = _make_card(2, 55, n=9, e=2, s=2, w=2)
    errs = validate_card_balance(card)
    assert len(errs) == 2
    assert any("budget" in e.lower() for e in errs)
    assert any("cap" in e.lower() for e in errs)


# ---------------------------------------------------------------------------
# load_cards_from_lines — balance errors integrated
# ---------------------------------------------------------------------------


def test_loader_rejects_card_with_sum_below_budget() -> None:
    # T1 common budget=16; sides sum to 15
    bad = _card(1, 15, {"n": 5, "e": 4, "s": 3, "w": 3})
    cards, errors = load_cards_from_lines(_lines(bad))
    assert len(cards) == 0
    assert len(errors) == 1
    assert errors[0].line == 1
    assert "budget" in errors[0].message.lower()


def test_loader_rejects_card_with_side_exceeds_cap() -> None:
    # T1 common cap=6; n=7 (sum=17 >= 16, only cap fails)
    bad = _card(1, 15, {"n": 7, "e": 4, "s": 3, "w": 3})
    cards, errors = load_cards_from_lines(_lines(bad))
    assert len(cards) == 0
    assert len(errors) == 1
    assert errors[0].line == 1
    assert "cap" in errors[0].message.lower()


def test_loader_accepts_valid_balance_card() -> None:
    # T1 common budget=16 cap=6; sum=16 max=6
    good = _card(1, 15, {"n": 6, "e": 4, "s": 3, "w": 3})
    cards, errors = load_cards_from_lines(_lines(good))
    assert len(errors) == 0
    assert len(cards) == 1


def test_loader_balance_error_has_correct_line_number() -> None:
    good = _card(1, 15, {"n": 6, "e": 4, "s": 3, "w": 3}, card_key="good_card")
    bad = _card(1, 15, {"n": 5, "e": 4, "s": 3, "w": 3}, card_key="bad_card")
    cards, errors = load_cards_from_lines(_lines(good, bad))
    assert len(cards) == 1
    assert len(errors) == 1
    assert errors[0].line == 2


def test_loader_balance_reports_all_violations_in_message() -> None:
    # T2 uncommon (22, cap 8); n=9 exceeds cap, sum=15 below budget
    bad = _card(2, 55, {"n": 9, "e": 2, "s": 2, "w": 2})
    _, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1
    assert "budget" in errors[0].message.lower()
    assert "cap" in errors[0].message.lower()


def test_loader_balance_error_does_not_affect_subsequent_valid_cards() -> None:
    bad = _card(1, 15, {"n": 5, "e": 4, "s": 3, "w": 3}, card_key="bad_card")
    good = _card(1, 15, {"n": 6, "e": 4, "s": 3, "w": 3}, card_key="good_card")
    cards, errors = load_cards_from_lines(_lines(bad, good))
    assert len(errors) == 1
    assert len(cards) == 1
    assert cards[0].card_key == "good_card"
