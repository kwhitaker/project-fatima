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
