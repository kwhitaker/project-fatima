"""cards.jsonl loader, schema validator, and balance enforcer.

Parses JSON Lines, validates each card against CardDefinition, enforces
card_key uniqueness, and checks (tier, rarity-bucket) sum budgets and
per-side caps per CARDS_SPEC.md.

Returns all valid cards plus a list of errors with 1-indexed line numbers
and human-readable messages.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from app.models.cards import CardDefinition

# ---------------------------------------------------------------------------
# Rarity buckets
# ---------------------------------------------------------------------------

# (low, high, bucket_name) — ranges are inclusive
_BUCKET_RANGES: list[tuple[int, int, str]] = [
    (1, 49, "common"),
    (50, 74, "uncommon"),
    (75, 89, "rare"),
    (90, 96, "very_rare"),
    (97, 100, "ultra"),
]


def rarity_bucket(rarity: int) -> str:
    """Derive the rarity bucket name from a numeric rarity value (1..100)."""
    for lo, hi, name in _BUCKET_RANGES:
        if lo <= rarity <= hi:
            return name
    raise ValueError(f"rarity {rarity} is outside 1..100")


# ---------------------------------------------------------------------------
# Stat budgets: (tier, bucket) -> (sum_budget, side_cap)
# ---------------------------------------------------------------------------

STAT_BUDGETS: dict[tuple[int, str], tuple[int, int]] = {
    (1, "common"): (16, 6),
    (1, "uncommon"): (18, 7),
    (1, "rare"): (20, 8),
    (1, "very_rare"): (22, 9),
    (1, "ultra"): (24, 9),
    (2, "common"): (20, 7),
    (2, "uncommon"): (22, 8),
    (2, "rare"): (24, 9),
    (2, "very_rare"): (26, 10),
    (2, "ultra"): (28, 10),
    (3, "common"): (24, 8),
    (3, "uncommon"): (26, 9),
    (3, "rare"): (28, 10),
    (3, "very_rare"): (30, 10),
    (3, "ultra"): (32, 10),
}


def validate_card_balance(card: CardDefinition) -> list[str]:
    """Check a card's sides against (tier, bucket) sum budget and per-side cap.

    Returns a list of human-readable error strings (empty list = passes).
    """
    bucket = rarity_bucket(card.rarity)
    sum_budget, side_cap = STAT_BUDGETS[(card.tier, bucket)]

    side_values = [card.sides.n, card.sides.e, card.sides.s, card.sides.w]
    total = sum(side_values)

    messages: list[str] = []

    if total < sum_budget:
        messages.append(
            f"sides sum {total} is below budget {sum_budget} "
            f"for tier {card.tier} {bucket}"
        )

    for name, val in zip("nesw", side_values):
        if val > side_cap:
            messages.append(
                f"side '{name}' value {val} exceeds cap {side_cap} "
                f"for tier {card.tier} {bucket}"
            )

    return messages


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


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

        # --- balance: sum budget + per-side cap ---
        balance_errors = validate_card_balance(card)
        if balance_errors:
            errors.append(
                CardLoadError(
                    line=lineno,
                    message="Balance error: " + "; ".join(balance_errors),
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
