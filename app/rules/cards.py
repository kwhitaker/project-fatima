"""cards.jsonl loader and schema validator.

Parses JSON Lines, validates each card against CardDefinition, and enforces
card_key uniqueness. Returns all valid cards plus a list of errors with
1-indexed line numbers and human-readable messages.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from app.models.cards import CardDefinition


@dataclass
class CardLoadError:
    line: int
    message: str


def load_cards_from_lines(
    lines: list[str],
) -> tuple[list[CardDefinition], list[CardLoadError]]:
    """Validate a sequence of JSON Lines strings.

    Returns (valid_cards, errors).  Empty lines (after stripping) are skipped
    but still counted for accurate line numbers.
    """
    cards: list[CardDefinition] = []
    errors: list[CardLoadError] = []
    seen_keys: dict[str, int] = {}  # card_key -> first line number

    for lineno, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped:
            continue

        # --- JSON parse ---
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            errors.append(
                CardLoadError(line=lineno, message=f"Invalid JSON: {exc.msg}")
            )
            continue

        # --- Pydantic schema validation ---
        try:
            card = CardDefinition.model_validate(obj)
        except PydanticValidationError as exc:
            # Collect field names from the first error location for the message.
            field_names = ", ".join(
                ".".join(str(loc) for loc in e["loc"]) for e in exc.errors()
            )
            errors.append(
                CardLoadError(
                    line=lineno,
                    message=f"Schema error on field(s) [{field_names}]: "
                    + "; ".join(e["msg"] for e in exc.errors()),
                )
            )
            continue

        # --- card_key uniqueness ---
        if card.card_key in seen_keys:
            errors.append(
                CardLoadError(
                    line=lineno,
                    message=(
                        f"Duplicate card_key '{card.card_key}' "
                        f"(first seen on line {seen_keys[card.card_key]})"
                    ),
                )
            )
            continue

        seen_keys[card.card_key] = lineno
        cards.append(card)

    return cards, errors


def load_cards_from_file(
    path: Path | str,
) -> tuple[list[CardDefinition], list[CardLoadError]]:
    """Load and validate a cards.jsonl file from disk."""
    return load_cards_from_lines(Path(path).read_text(encoding="utf-8").splitlines())
