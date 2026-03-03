"""Board topology for the 3×3 grid.

Board layout (row-major, 0-indexed):
  0 1 2
  3 4 5
  6 7 8

Exports the adjacency mapping used by captures and reducer modules.
"""

# Maps cell index → list of (neighbor_index, attacking_side, defending_side)
# attacking_side: which side of the source card faces the neighbor
# defending_side: which side of the neighbor card faces the source
ADJACENCY: dict[int, list[tuple[int, str, str]]] = {
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


def get_adjacent_indices(cell_index: int) -> set[int]:
    """Return the set of cell indices adjacent to the given cell."""
    return {nb[0] for nb in ADJACENCY[cell_index]}
