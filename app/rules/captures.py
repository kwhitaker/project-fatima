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
from app.rules.board import ADJACENCY


def resolve_captures(
    board: list[BoardCell | None],
    placed_index: int,
    placed_card: CardDefinition,
    placed_owner: int,
    card_lookup: dict[str, CardDefinition],
    mists_modifier: int = 0,
    intimidate_target_cell: int | None = None,
    warded_cell: int | None = None,
) -> tuple[list[BoardCell | None], bool]:
    """Return a new board with ownership flipped for all captured cards (including combos),
    and a bool indicating whether the Plus rule fired.

    Plus rule (pre-step): if 2+ adjacent opponent-owned cards each yield the same
    sum (placed card's attacking side + neighbor's defending side, raw printed values
    only — no Mists modifier, no elemental bonus), all matching neighbors are captured
    immediately and added to the BFS combo queue with zero modifiers.

    After the Plus pre-step, standard comparison captures run via BFS for all remaining
    adjacent opponent cards (including the initial placed card's comparisons).

    Combo propagation continues via BFS until no new captures occur. The placed card's
    initial comparisons use mists_modifier and intimidate_target_cell; newly-captured cards
    trigger combo resolution using printed stats only — no modifiers.

    Printed stats never change; modifiers are ephemeral and scoped to the initial placement.
    """
    new_board: list[BoardCell | None] = list(board)
    plus_triggered = False

    # --- Plus rule pre-step ---
    # Compute raw side-sums for each adjacent opponent-owned cell.
    # Group by sum; if any sum appears 2+ times, capture all matching cells.
    sum_to_neighbors: dict[int, list[tuple[int, str]]] = {}  # sum → [(neighbor_idx, card_key)]
    for neighbor_index, placed_side, neighbor_side in ADJACENCY[placed_index]:
        neighbor_cell = new_board[neighbor_index]
        if neighbor_cell is None or neighbor_cell.owner == placed_owner:
            continue
        attacking_raw = getattr(placed_card.sides, placed_side)
        defending_raw = getattr(card_lookup[neighbor_cell.card_key].sides, neighbor_side)
        s = attacking_raw + defending_raw
        sum_to_neighbors.setdefault(s, []).append((neighbor_index, neighbor_cell.card_key))

    # Queue entries: (source_index, source_card, mist_mod, intim_target)
    # Initial entry: placed card with full modifiers.
    # Combo entries: captured cards with no modifiers (printed stats only).
    queue: list[tuple[int, CardDefinition, int, int | None]] = [
        (placed_index, placed_card, mists_modifier, intimidate_target_cell)
    ]

    for s, matches in sum_to_neighbors.items():
        if len(matches) >= 2:
            plus_triggered = True
            for neighbor_index, neighbor_card_key in matches:
                if neighbor_index == warded_cell:
                    continue  # warded card immune to Plus capture
                neighbor_def = card_lookup[neighbor_card_key]
                new_board[neighbor_index] = BoardCell(
                    card_key=neighbor_card_key,
                    owner=placed_owner,
                )
                queue.append((neighbor_index, neighbor_def, 0, None))

    # --- Standard BFS ---
    while queue:
        src_index, src_card, mist_mod, intim_target = queue.pop(0)

        for neighbor_index, placed_side, neighbor_side in ADJACENCY[src_index]:
            neighbor_cell = new_board[neighbor_index]
            if neighbor_cell is None or neighbor_cell.owner == placed_owner:
                continue

            neighbor_def = card_lookup[neighbor_cell.card_key]
            src_value = getattr(src_card.sides, placed_side) + mist_mod
            neighbor_value = getattr(neighbor_def.sides, neighbor_side)
            if intim_target is not None and neighbor_index == intim_target:
                neighbor_value = max(neighbor_value - 3, 1)

            if src_value > neighbor_value and neighbor_index != warded_cell:
                new_board[neighbor_index] = BoardCell(
                    card_key=neighbor_cell.card_key,
                    owner=placed_owner,
                )
                # Captured card participates in combo; use printed stats only.
                queue.append((neighbor_index, neighbor_def, 0, None))

    return new_board, plus_triggered
