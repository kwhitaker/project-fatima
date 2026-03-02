"""Tests for cards.jsonl loader — schema validation and card_key uniqueness."""

import json

from app.rules.cards import CardLoadError, load_cards_from_lines

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

VALID_CARD = {
    "card_key": "zombie_i",
    "character_key": "zombie",
    "name": "Zombie",
    "version": "Shambling Dead",
    "tier": 1,
    "rarity": 15,
    "is_named": False,
    "sides": {"n": 6, "e": 4, "s": 3, "w": 3},
    "set": "barovia_200y_v1",
    "tags": ["undead"],
    "element": "shadow",
}

VALID_CARD_2 = {
    "card_key": "skeleton_i",
    "character_key": "skeleton",
    "name": "Skeleton",
    "version": "Rattling Bones",
    "tier": 1,
    "rarity": 18,
    "is_named": False,
    "sides": {"n": 5, "e": 5, "s": 4, "w": 2},
    "set": "barovia_200y_v1",
    "element": "shadow",
}


def _lines(*objs: dict) -> list[str]:
    return [json.dumps(obj) for obj in objs]


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------


def test_load_single_valid_card():
    cards, errors = load_cards_from_lines(_lines(VALID_CARD))
    assert len(errors) == 0
    assert len(cards) == 1
    assert cards[0].card_key == "zombie_i"


def test_load_multiple_valid_cards():
    cards, errors = load_cards_from_lines(_lines(VALID_CARD, VALID_CARD_2))
    assert len(errors) == 0
    assert len(cards) == 2


def test_empty_lines_are_skipped():
    lines = ["", json.dumps(VALID_CARD), "   ", json.dumps(VALID_CARD_2)]
    cards, errors = load_cards_from_lines(lines)
    assert len(errors) == 0
    assert len(cards) == 2


def test_empty_input_returns_empty():
    cards, errors = load_cards_from_lines([])
    assert cards == []
    assert errors == []


def test_tags_optional():
    card = {k: v for k, v in VALID_CARD.items() if k != "tags"}
    cards, errors = load_cards_from_lines(_lines(card))
    assert len(errors) == 0
    assert cards[0].tags == []


# ---------------------------------------------------------------------------
# schema failures — missing fields
# ---------------------------------------------------------------------------


def test_missing_required_field_card_key():
    bad = {k: v for k, v in VALID_CARD.items() if k != "card_key"}
    cards, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1
    assert errors[0].line == 1
    assert "card_key" in errors[0].message


def test_missing_required_field_sides():
    bad = {k: v for k, v in VALID_CARD.items() if k != "sides"}
    cards, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1
    assert errors[0].line == 1
    assert "sides" in errors[0].message


def test_missing_sub_field_sides_n():
    bad = dict(VALID_CARD)
    bad["sides"] = {"e": 4, "s": 3, "w": 3}
    cards, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1
    assert errors[0].line == 1


# ---------------------------------------------------------------------------
# schema failures — wrong types
# ---------------------------------------------------------------------------


def test_wrong_type_rarity_string():
    bad = {**VALID_CARD, "rarity": "high"}
    _, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1
    assert errors[0].line == 1
    assert "rarity" in errors[0].message


def test_wrong_type_tier_float():
    bad = {**VALID_CARD, "tier": 1.5}
    _, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1
    assert errors[0].line == 1


# ---------------------------------------------------------------------------
# schema failures — value range
# ---------------------------------------------------------------------------


def test_side_value_too_high():
    bad = {**VALID_CARD, "sides": {"n": 11, "e": 4, "s": 3, "w": 3}}
    _, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1
    assert errors[0].line == 1


def test_side_value_too_low():
    bad = {**VALID_CARD, "sides": {"n": 0, "e": 4, "s": 3, "w": 3}}
    _, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1
    assert errors[0].line == 1


def test_rarity_out_of_range_zero():
    bad = {**VALID_CARD, "rarity": 0}
    _, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1


def test_rarity_out_of_range_101():
    bad = {**VALID_CARD, "rarity": 101}
    _, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1


def test_tier_out_of_range_zero():
    bad = {**VALID_CARD, "tier": 0}
    _, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1


def test_tier_out_of_range_four():
    bad = {**VALID_CARD, "tier": 4}
    _, errors = load_cards_from_lines(_lines(bad))
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# card_key uniqueness
# ---------------------------------------------------------------------------


def test_duplicate_card_key_reported():
    dupe = {**VALID_CARD_2, "card_key": "zombie_i"}  # same key as VALID_CARD
    _, errors = load_cards_from_lines(_lines(VALID_CARD, dupe))
    assert len(errors) == 1
    assert errors[0].line == 2
    assert "zombie_i" in errors[0].message
    assert "duplicate" in errors[0].message.lower()


def test_duplicate_card_key_not_added_to_results():
    dupe = {**VALID_CARD_2, "card_key": "zombie_i"}
    cards, errors = load_cards_from_lines(_lines(VALID_CARD, dupe))
    assert len(cards) == 1
    assert len(errors) == 1


def test_triple_duplicate_reports_both_duplicates():
    dupe1 = {**VALID_CARD_2, "card_key": "zombie_i"}
    dupe2 = {**VALID_CARD_2, "card_key": "zombie_i", "character_key": "other"}
    _, errors = load_cards_from_lines(_lines(VALID_CARD, dupe1, dupe2))
    assert len(errors) == 2
    assert errors[0].line == 2
    assert errors[1].line == 3


# ---------------------------------------------------------------------------
# line number accuracy
# ---------------------------------------------------------------------------


def test_error_line_number_with_empty_lines_before():
    bad = {**VALID_CARD, "rarity": 0}
    lines = ["", json.dumps(VALID_CARD_2), "", json.dumps(bad)]
    _, errors = load_cards_from_lines(lines)
    assert len(errors) == 1
    # physical line 4 (1-indexed) contains the bad card
    assert errors[0].line == 4


def test_invalid_json_line_reports_error():
    lines = [json.dumps(VALID_CARD), "not-json", json.dumps(VALID_CARD_2)]
    cards, errors = load_cards_from_lines(lines)
    assert len(errors) == 1
    assert errors[0].line == 2
    assert "json" in errors[0].message.lower()
    # valid cards still loaded
    assert len(cards) == 2


# ---------------------------------------------------------------------------
# CardLoadError dataclass basics
# ---------------------------------------------------------------------------


def test_card_load_error_fields():
    err = CardLoadError(line=3, message="something went wrong")
    assert err.line == 3
    assert err.message == "something went wrong"
