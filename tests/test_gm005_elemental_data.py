"""Tests for US-GM-005: elemental card data and model.

Covers:
- CardDefinition accepts valid elements
- CardDefinition rejects invalid/missing element
- card loader (load_cards_from_lines) rejects invalid/missing element
- All cards in cards.jsonl have valid elements
"""

import json
from pathlib import Path

import pytest

from app.models.cards import CardDefinition, CardSides
from app.rules.cards import load_cards_from_lines

# ---------------------------------------------------------------------------
# Helper to build a minimal valid card JSON string
# ---------------------------------------------------------------------------

_BASE_SIDES = {"n": 6, "e": 4, "s": 3, "w": 3}


def _card_line(element: str | None = "blood", *, card_key: str = "zombie_i") -> str:
    obj: dict = {
        "card_key": card_key,
        "character_key": "zombie",
        "name": "Zombie",
        "version": "Shambling Dead",
        "tier": 1,
        "rarity": 15,
        "is_named": False,
        "sides": _BASE_SIDES,
        "set": "barovia_v1",
        "tags": ["undead"],
    }
    if element is not None:
        obj["element"] = element
    return json.dumps(obj)


# ---------------------------------------------------------------------------
# CardDefinition model tests
# ---------------------------------------------------------------------------


class TestCardDefinitionElement:
    def test_valid_element_blood(self) -> None:
        card = CardDefinition(
            card_key="zombie_i",
            character_key="zombie",
            name="Zombie",
            version="Shambling Dead",
            tier=1,
            rarity=15,
            is_named=False,
            sides=CardSides(n=6, e=4, s=3, w=3),
            set="barovia_v1",
            tags=[],
            element="blood",
        )
        assert card.element == "blood"

    @pytest.mark.parametrize("elem", ["blood", "holy", "arcane", "shadow", "nature"])
    def test_all_valid_elements_accepted(self, elem: str) -> None:
        card = CardDefinition(
            card_key="zombie_i",
            character_key="zombie",
            name="Zombie",
            version="v",
            tier=1,
            rarity=15,
            is_named=False,
            sides=CardSides(n=6, e=4, s=3, w=3),
            set="barovia_v1",
            tags=[],
            element=elem,  # type: ignore[arg-type]
        )
        assert card.element == elem

    def test_invalid_element_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CardDefinition(
                card_key="zombie_i",
                character_key="zombie",
                name="Zombie",
                version="v",
                tier=1,
                rarity=15,
                is_named=False,
                sides=CardSides(n=6, e=4, s=3, w=3),
                set="barovia_v1",
                tags=[],
                element="fire",  # type: ignore[arg-type]
            )

    def test_missing_element_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CardDefinition(
                card_key="zombie_i",
                character_key="zombie",
                name="Zombie",
                version="v",
                tier=1,
                rarity=15,
                is_named=False,
                sides=CardSides(n=6, e=4, s=3, w=3),
                set="barovia_v1",
                tags=[],
                # element omitted
            )  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Card loader tests
# ---------------------------------------------------------------------------


class TestCardLoaderElement:
    def test_valid_element_loads(self) -> None:
        cards, errors = load_cards_from_lines([_card_line("nature")])
        assert errors == []
        assert len(cards) == 1
        assert cards[0].element == "nature"

    def test_invalid_element_rejected(self) -> None:
        cards, errors = load_cards_from_lines([_card_line("fire")])
        assert len(errors) == 1
        assert cards == []
        assert "element" in errors[0].message.lower() or "schema" in errors[0].message.lower()

    def test_missing_element_rejected(self) -> None:
        cards, errors = load_cards_from_lines([_card_line(None)])
        assert len(errors) == 1
        assert cards == []

    @pytest.mark.parametrize("elem", ["blood", "holy", "arcane", "shadow", "nature"])
    def test_each_valid_element_loads(self, elem: str) -> None:
        cards, errors = load_cards_from_lines([_card_line(elem, card_key=f"z_{elem}_i")])
        assert errors == [], f"element '{elem}' should load without errors"
        assert cards[0].element == elem


# ---------------------------------------------------------------------------
# Real cards.jsonl integration test
# ---------------------------------------------------------------------------


class TestRealCardsJsonl:
    def test_all_cards_have_valid_elements(self) -> None:
        cards_file = Path("cards.jsonl")
        cards, errors = load_cards_from_lines(cards_file.read_text().splitlines())
        assert errors == [], f"cards.jsonl errors: {errors}"
        valid_elements = {"blood", "holy", "arcane", "shadow", "nature"}
        for card in cards:
            assert card.element in valid_elements, (
                f"Card {card.card_key} has invalid element '{card.element}'"
            )

    def test_all_65_cards_loaded(self) -> None:
        cards_file = Path("cards.jsonl")
        cards, errors = load_cards_from_lines(cards_file.read_text().splitlines())
        assert errors == []
        assert len(cards) == 65, f"Expected 65 cards, got {len(cards)}"
