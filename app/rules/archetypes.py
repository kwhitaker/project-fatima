"""Once-per-game archetype powers.

All functions here are pure: they take a card/state and return a new value
without side effects or I/O.
"""

from app.models.cards import CardDefinition, CardSides


def rotate_card_once(card: CardDefinition) -> CardDefinition:
    """Return a copy of *card* with sides rotated once clockwise.

    Rotation mapping (N→E→S→W→N means each value shifts one step clockwise):
      new.n = old.w
      new.e = old.n
      new.s = old.e
      new.w = old.s

    Printed stats are never mutated; the original card is unchanged.
    """
    rotated_sides = CardSides(
        n=card.sides.w,
        e=card.sides.n,
        s=card.sides.e,
        w=card.sides.s,
    )
    return card.model_copy(update={"sides": rotated_sides})


def apply_skulker_boost(card: CardDefinition, side: str) -> CardDefinition:
    """Return a copy of *card* with *side* increased by 3 for this placement.

    The boost affects comparisons only; the original card's printed stats
    are never mutated. *side* must be one of "n", "e", "s", "w".
    """
    sides_dict = card.sides.model_dump()
    sides_dict[side] += 3
    return card.model_copy(update={"sides": CardSides(**sides_dict)})
