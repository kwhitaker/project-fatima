"""Pure capture resolution for card placements on the 3×3 board.

Board layout (row-major, 0-indexed):
  0 1 2
  3 4 5
  6 7 8

For a card placed at `placed_index`, adjacent cells are examined.
The placed card's touching side is compared against the neighbor's
opposing side (N↔S, E↔W). Strict greater-than triggers a capture.
"""

from app.models.cards import CardDefinition
from app.models.game import BoardCell

# Maps cell index → list of (neighbor_index, placed_side, neighbor_side)
# placed_side: which side of the placed card is used for comparison
# neighbor_side: which side of the neighbor card is used for comparison
_ADJACENCY: dict[int, list[tuple[int, str, str]]] = {
    0: [(1, "e", "w"), (3, "s", "n")],
    1: [(0, "w", "e"), (2, "e", "w"), (4, "s", "n")],
    2: [(1, "w", "e"), (5, "s", "n")],
    3: [(0, "n", "s"), (4, "e", "w"), (6, "s", "n")],
    4: [(1, "n", "s"), (3, "w", "e"), (5, "e", "w"), (7, "s", "n")],
    5: [(2, "n", "s"), (4, "w", "e"), (8, "s", "n")],
    6: [(3, "n", "s"), (7, "e", "w")],
    7: [(4, "n", "s"), (6, "w", "e"), (8, "e", "w")],
    8: [(5, "n", "s"), (7, "w", "e")],
}


def resolve_captures(
    board: list[BoardCell | None],
    placed_index: int,
    placed_card: CardDefinition,
    placed_owner: int,
    card_lookup: dict[str, CardDefinition],
    mists_modifier: int = 0,
    presence_direction: str | None = None,
) -> list[BoardCell | None]:
    """Return a new board with ownership flipped for all captured cards (including combos).

    The placed card's comparisons use mists_modifier and presence_direction.
    Newly-captured cards trigger combo resolution using printed stats only — no modifiers.
    Combo propagation continues via BFS until no new captures occur.

    A card is captured when the attacker's touching side (+ any applicable modifier)
    is strictly greater than the defender's opposing side.
    Printed stats never change; modifiers are ephemeral and scoped to the initial placement.
    """
    new_board: list[BoardCell | None] = list(board)

    # Queue entries: (source_index, source_card, mist_mod, presence_dir)
    # Initial entry: placed card with full modifiers.
    # Combo entries: captured cards with no modifiers (printed stats only).
    queue: list[tuple[int, CardDefinition, int, str | None]] = [
        (placed_index, placed_card, mists_modifier, presence_direction)
    ]

    while queue:
        src_index, src_card, mist_mod, pres_dir = queue.pop(0)

        for neighbor_index, placed_side, neighbor_side in _ADJACENCY[src_index]:
            neighbor_cell = new_board[neighbor_index]
            if neighbor_cell is None or neighbor_cell.owner == placed_owner:
                continue

            neighbor_def = card_lookup[neighbor_cell.card_key]
            src_value = getattr(src_card.sides, placed_side) + mist_mod
            if pres_dir and placed_side == pres_dir:
                src_value += 1
            neighbor_value = getattr(neighbor_def.sides, neighbor_side)

            if src_value > neighbor_value:
                new_board[neighbor_index] = BoardCell(
                    card_key=neighbor_cell.card_key,
                    owner=placed_owner,
                )
                # Captured card participates in combo; use printed stats only.
                queue.append((neighbor_index, neighbor_def, 0, None))

    return new_board
