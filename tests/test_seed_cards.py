"""Unit tests for scripts/seed_cards.py.

Validates that:
- card_to_row produces the correct flat dict shape for the cards table
- seed_cards calls upsert with the correct rows
- seed_cards returns errors when cards.jsonl has invalid entries
- No real Supabase credentials are required (client is mocked)
"""

from pathlib import Path
from unittest.mock import MagicMock

from app.models.cards import CardDefinition, CardSides
from scripts.seed_cards import card_to_row, seed_cards

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_LINE = (
    '{"card_key":"zombie_i","character_key":"zombie","name":"Zombie",'
    '"version":"Shambling Dead","tier":1,"rarity":15,"is_named":false,'
    '"sides":{"n":6,"e":4,"s":3,"w":3},"set":"barovia_v1","tags":["undead"]}'
)

_VALID_LINE_2 = (
    '{"card_key":"skeleton_i","character_key":"skeleton","name":"Skeleton",'
    '"version":"Rattling Bones","tier":1,"rarity":18,"is_named":false,'
    '"sides":{"n":5,"e":5,"s":4,"w":2},"set":"barovia_v1","tags":["undead"]}'
)


def _make_card(**overrides: object) -> CardDefinition:
    defaults: dict[str, object] = {
        "card_key": "zombie_i",
        "character_key": "zombie",
        "name": "Zombie",
        "version": "Shambling Dead",
        "tier": 1,
        "rarity": 15,
        "is_named": False,
        "sides": CardSides(n=6, e=4, s=3, w=3),
        "set": "barovia_v1",
        "tags": ["undead"],
    }
    defaults.update(overrides)
    return CardDefinition(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# card_to_row
# ---------------------------------------------------------------------------


class TestCardToRow:
    def test_flat_sides_extracted(self) -> None:
        card = _make_card()
        row = card_to_row(card)
        assert row["n"] == 6
        assert row["e"] == 4
        assert row["s"] == 3
        assert row["w"] == 3

    def test_definition_is_full_json_dict(self) -> None:
        card = _make_card()
        row = card_to_row(card)
        assert isinstance(row["definition"], dict)
        assert row["definition"]["card_key"] == "zombie_i"
        assert row["definition"]["sides"] == {"n": 6, "e": 4, "s": 3, "w": 3}

    def test_all_expected_columns_present(self) -> None:
        row = card_to_row(_make_card())
        expected = {
            "card_key",
            "character_key",
            "name",
            "version",
            "tier",
            "rarity",
            "is_named",
            "n",
            "e",
            "s",
            "w",
            "set",
            "tags",
            "definition",
        }
        assert set(row.keys()) == expected

    def test_tags_preserved(self) -> None:
        card = _make_card(tags=["undead", "generic"])
        row = card_to_row(card)
        assert row["tags"] == ["undead", "generic"]

    def test_is_named_false(self) -> None:
        row = card_to_row(_make_card(is_named=False))
        assert row["is_named"] is False

    def test_is_named_true(self) -> None:
        row = card_to_row(_make_card(is_named=True))
        assert row["is_named"] is True


# ---------------------------------------------------------------------------
# seed_cards
# ---------------------------------------------------------------------------


class TestSeedCards:
    def test_upsert_called_on_cards_table(self, tmp_path: Path) -> None:
        cards_file = tmp_path / "cards.jsonl"
        cards_file.write_text(_VALID_LINE + "\n")
        client = MagicMock()

        count, errors = seed_cards(client, cards_file)

        assert errors == []
        assert count == 1
        client.table.assert_called_once_with("cards")
        client.table.return_value.upsert.assert_called_once()
        client.table.return_value.upsert.return_value.execute.assert_called_once()

    def test_upsert_row_shape(self, tmp_path: Path) -> None:
        cards_file = tmp_path / "cards.jsonl"
        cards_file.write_text(_VALID_LINE + "\n")
        client = MagicMock()

        seed_cards(client, cards_file)

        call_args = client.table.return_value.upsert.call_args
        rows: list[dict[str, object]] = call_args[0][0]
        assert len(rows) == 1
        assert rows[0]["card_key"] == "zombie_i"
        assert rows[0]["n"] == 6

    def test_multiple_cards_all_upserted(self, tmp_path: Path) -> None:
        cards_file = tmp_path / "cards.jsonl"
        cards_file.write_text(_VALID_LINE + "\n" + _VALID_LINE_2 + "\n")
        client = MagicMock()

        count, errors = seed_cards(client, cards_file)

        assert errors == []
        assert count == 2
        rows = client.table.return_value.upsert.call_args[0][0]
        assert len(rows) == 2
        assert {r["card_key"] for r in rows} == {"zombie_i", "skeleton_i"}

    def test_validation_errors_returned_no_upsert(self, tmp_path: Path) -> None:
        cards_file = tmp_path / "cards.jsonl"
        cards_file.write_text("not valid json\n")
        client = MagicMock()

        count, errors = seed_cards(client, cards_file)

        assert count == 0
        assert len(errors) == 1
        assert "Line 1" in errors[0]
        client.table.assert_not_called()

    def test_empty_file_returns_zero_no_upsert(self, tmp_path: Path) -> None:
        cards_file = tmp_path / "cards.jsonl"
        cards_file.write_text("")
        client = MagicMock()

        count, errors = seed_cards(client, cards_file)

        assert count == 0
        assert errors == []
        client.table.assert_not_called()

    def test_blank_lines_skipped(self, tmp_path: Path) -> None:
        cards_file = tmp_path / "cards.jsonl"
        cards_file.write_text("\n" + _VALID_LINE + "\n\n")
        client = MagicMock()

        count, errors = seed_cards(client, cards_file)

        assert count == 1
        assert errors == []

    def test_error_message_contains_line_number(self, tmp_path: Path) -> None:
        cards_file = tmp_path / "cards.jsonl"
        # First line valid, second invalid JSON
        cards_file.write_text(_VALID_LINE + "\nbad json\n")
        client = MagicMock()

        count, errors = seed_cards(client, cards_file)

        assert count == 0
        assert any("Line 2" in e for e in errors)

    def test_uses_real_cards_jsonl(self) -> None:
        """Ensure cards.jsonl in the repo itself validates and can be seeded."""
        cards_file = Path("cards.jsonl")
        client = MagicMock()

        count, errors = seed_cards(client, cards_file)

        assert errors == [], f"cards.jsonl has validation errors: {errors}"
        assert count > 0
