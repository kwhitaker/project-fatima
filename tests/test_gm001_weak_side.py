"""Tests for US-GM-001: weak-side card rule.

Every card must have at least one side ≤ 3 (min(sides) ≤ 3).
Cards where all four sides are ≥ 4 must fail validation.
"""

import json

import pytest

from app.models.cards import CardDefinition, CardSides
from app.rules.cards import load_cards_from_lines, validate_card_balance


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


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
    )


def _card_line(tier: int, rarity: int, n: int, e: int, s: int, w: int, key: str = "t") -> str:
    return json.dumps(
        {
            "card_key": key,
            "character_key": key,
            "name": "T",
            "version": "v",
            "tier": tier,
            "rarity": rarity,
            "is_named": False,
            "sides": {"n": n, "e": e, "s": s, "w": w},
            "set": "s",
        }
    )


# ---------------------------------------------------------------------------
# validate_card_balance — weak-side passing cases
# ---------------------------------------------------------------------------


def test_weak_side_passes_when_n_is_low() -> None:
    # n=1 satisfies weak-side rule
    card = _make_card(1, 15, n=1, e=6, s=5, w=4)
    errs = validate_card_balance(card)
    assert not any("weak" in e.lower() for e in errs)


def test_weak_side_passes_when_e_is_low() -> None:
    card = _make_card(1, 15, n=6, e=2, s=5, w=4)
    errs = validate_card_balance(card)
    assert not any("weak" in e.lower() for e in errs)


def test_weak_side_passes_when_s_is_low() -> None:
    card = _make_card(1, 15, n=6, e=4, s=3, w=4)
    errs = validate_card_balance(card)
    assert not any("weak" in e.lower() for e in errs)


def test_weak_side_passes_when_w_is_low() -> None:
    # T1 common (budget=16, cap=6): n=6, e=4, s=3, w=3 → sum=16, min=3
    card = _make_card(1, 15, n=6, e=4, s=3, w=3)
    errs = validate_card_balance(card)
    assert errs == []


def test_weak_side_passes_exactly_at_boundary_three() -> None:
    # min=3 is the allowed boundary
    card = _make_card(1, 15, n=6, e=4, s=3, w=3)
    errs = validate_card_balance(card)
    assert not any("weak" in e.lower() for e in errs)


# ---------------------------------------------------------------------------
# validate_card_balance — weak-side failing cases
# ---------------------------------------------------------------------------


def test_weak_side_fails_when_all_sides_are_four() -> None:
    # T1 uncommon (budget=18, cap=7): all sides=4, sum=16 < 18 also fails budget
    # but we specifically want weak-side error present
    card = _make_card(1, 60, n=5, e=5, s=4, w=4)  # sum=18, min=4
    errs = validate_card_balance(card)
    assert any("weak" in e.lower() for e in errs)


def test_weak_side_fails_returns_weak_side_message() -> None:
    # T1 uncommon (budget=18, cap=7): n=6, e=5, s=4, w=4, sum=19≥18 ok, min=4
    card = _make_card(1, 60, n=6, e=5, s=4, w=4)  # sum=19, min=4
    errs = validate_card_balance(card)
    assert len(errs) == 1
    assert "weak" in errs[0].lower()


def test_weak_side_fails_when_min_is_five() -> None:
    # T2 rare (budget=24, cap=9): n=7, e=6, s=6, w=5 → sum=24, min=5
    card = _make_card(2, 80, n=7, e=6, s=6, w=5)
    errs = validate_card_balance(card)
    assert any("weak" in e.lower() for e in errs)


def test_weak_side_fails_for_ultra_card_with_high_min() -> None:
    # T3 ultra (budget=32, cap=10): all high → min=6
    card = _make_card(3, 100, n=10, e=9, s=7, w=6)
    errs = validate_card_balance(card)
    assert any("weak" in e.lower() for e in errs)


def test_weak_side_and_budget_can_both_fail() -> None:
    # T1 uncommon (budget=18, cap=7): n=5, e=5, s=4, w=4 → sum=18 ok, min=4 → weak fails
    # n=5, e=4, s=4, w=4 → sum=17 < 18 AND min=4 → both fail
    card = _make_card(1, 60, n=5, e=4, s=4, w=4)
    errs = validate_card_balance(card)
    assert any("weak" in e.lower() for e in errs)
    assert any("budget" in e.lower() for e in errs)


# ---------------------------------------------------------------------------
# load_cards_from_lines — weak-side integration
# ---------------------------------------------------------------------------


def test_loader_rejects_card_with_all_sides_four() -> None:
    # T1 uncommon, all sides=4 → min=4, weak-side violation
    line = _card_line(1, 60, n=6, e=5, s=4, w=4)  # sum=19, min=4
    cards, errors = load_cards_from_lines([line])
    assert len(cards) == 0
    assert len(errors) == 1
    assert "weak" in errors[0].message.lower()


def test_loader_accepts_card_with_one_side_at_three() -> None:
    # T1 uncommon, w=3 satisfies weak-side
    line = _card_line(1, 60, n=7, e=5, s=3, w=3)  # sum=18, min=3
    cards, errors = load_cards_from_lines([line])
    assert errors == []
    assert len(cards) == 1


def test_loader_weak_side_error_does_not_affect_subsequent_valid_cards() -> None:
    bad = _card_line(1, 60, n=6, e=5, s=4, w=4, key="bad")  # min=4
    good = _card_line(1, 60, n=7, e=5, s=3, w=3, key="good")  # min=3, sum=18
    cards, errors = load_cards_from_lines([bad, good])
    assert len(errors) == 1
    assert len(cards) == 1
    assert cards[0].card_key == "good"


# ---------------------------------------------------------------------------
# Real cards.jsonl passes weak-side rule
# ---------------------------------------------------------------------------


def test_real_cards_jsonl_passes_weak_side_rule() -> None:
    """All cards in the repo's cards.jsonl must satisfy min(sides) <= 3."""
    from pathlib import Path

    lines = Path("cards.jsonl").read_text(encoding="utf-8").splitlines()
    cards, errors = load_cards_from_lines(lines)
    assert errors == [], f"cards.jsonl validation errors: {errors}"
    for card in cards:
        sides = [card.sides.n, card.sides.e, card.sides.s, card.sides.w]
        assert min(sides) <= 3, (
            f"Card {card.card_key!r} violates weak-side rule: sides={sides}"
        )
