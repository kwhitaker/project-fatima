"""Tests for app.rules.board — 3×3 grid adjacency."""

import pytest

from app.rules.board import ADJACENCY, get_adjacent_indices


class TestGetAdjacentIndices:
    """Verify neighbor counts and indices for corners, edges, and center."""

    @pytest.mark.parametrize(
        "cell, expected",
        [
            (0, {1, 3}),
            (2, {1, 5}),
            (6, {3, 7}),
            (8, {5, 7}),
        ],
        ids=["top-left", "top-right", "bottom-left", "bottom-right"],
    )
    def test_corner_cells_have_two_neighbors(self, cell: int, expected: set[int]) -> None:
        assert get_adjacent_indices(cell) == expected

    @pytest.mark.parametrize(
        "cell, expected",
        [
            (1, {0, 2, 4}),
            (3, {0, 4, 6}),
            (5, {2, 4, 8}),
            (7, {4, 6, 8}),
        ],
        ids=["top-edge", "left-edge", "right-edge", "bottom-edge"],
    )
    def test_edge_cells_have_three_neighbors(self, cell: int, expected: set[int]) -> None:
        assert get_adjacent_indices(cell) == expected

    def test_center_cell_has_four_neighbors(self) -> None:
        assert get_adjacent_indices(4) == {1, 3, 5, 7}


class TestAdjacencyCompleteness:
    """Verify the ADJACENCY dict covers all 9 cells with correct side pairings."""

    def test_all_nine_cells_present(self) -> None:
        assert set(ADJACENCY.keys()) == set(range(9))

    def test_side_pairings_are_symmetric(self) -> None:
        """If cell A lists (B, 'e', 'w'), then cell B must list (A, 'w', 'e')."""
        opposite = {"n": "s", "s": "n", "e": "w", "w": "e"}
        for cell, neighbors in ADJACENCY.items():
            for nb_index, atk_side, def_side in neighbors:
                reverse = [(i, a, d) for i, a, d in ADJACENCY[nb_index] if i == cell]
                assert len(reverse) == 1, (
                    f"Cell {nb_index} should reference cell {cell} exactly once"
                )
                rev_atk, rev_def = reverse[0][1], reverse[0][2]
                assert rev_atk == def_side
                assert rev_def == atk_side
                assert atk_side == opposite[def_side]
