"""Tests for US-007: Skulker archetype side boost.

Skulker power: add +3 to one chosen side (n/e/s/w) for comparisons this
placement only. Once per game per player.

The choice is made at placement time (not after seeing results).
"""

from functools import partial

import pytest

from app.models.game import Archetype, BoardCell
from app.rules.archetypes import apply_skulker_boost
from app.rules.errors import (
    ArchetypeAlreadyUsedError,
    ArchetypePowerArgumentError,
)
from app.rules.reducer import PlacementIntent, apply_intent
from tests.conftest import make_card
from tests.conftest import make_state as _make_state

make_state = partial(_make_state, p0_archetype=Archetype.SKULKER)


# ---------------------------------------------------------------------------
# Unit: apply_skulker_boost
# ---------------------------------------------------------------------------


class TestApplySkulkerBoost:
    def test_boosts_chosen_side_by_three(self):
        card = make_card("c", n=5, e=3, s=7, w=2)
        boosted = apply_skulker_boost(card, "n")
        assert boosted.sides.n == 8

    def test_other_sides_unchanged(self):
        card = make_card("c", n=5, e=3, s=7, w=2)
        boosted = apply_skulker_boost(card, "n")
        assert boosted.sides.e == 3
        assert boosted.sides.s == 7
        assert boosted.sides.w == 2

    def test_boost_each_side(self):
        """Boost applies correctly to every possible side."""
        for side in ("n", "e", "s", "w"):
            card = make_card("c", n=5, e=3, s=7, w=2)
            boosted = apply_skulker_boost(card, side)
            assert getattr(boosted.sides, side) == getattr(card.sides, side) + 3

    def test_does_not_mutate_original(self):
        card = make_card("c", n=5, e=5, s=5, w=5)
        apply_skulker_boost(card, "n")
        assert card.sides.n == 5

    def test_preserves_metadata(self):
        card = make_card("my_card", n=3, e=4, s=5, w=6)
        boosted = apply_skulker_boost(card, "e")
        assert boosted.card_key == "my_card"
        assert boosted.tier == 1
        assert boosted.rarity == 50


# ---------------------------------------------------------------------------
# Integration: Skulker boost via apply_intent
# ---------------------------------------------------------------------------


class TestSkulkerBoostInReducer:
    def test_boost_enables_capture_that_would_otherwise_miss(self):
        """Skulker +3 on N turns a losing comparison into a winning one."""
        # Placed N=3 vs neighbor S=4 → no capture (3 < 4)
        # With +3 on N: 6 > 4 → capture
        placed = make_card("placed", n=3, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=4, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(
            board=board,
            p0_hand=["placed"],
            p1_hand=["neighbor"],
            p0_archetype=Archetype.SKULKER,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            skulker_boost_side="n",
        )
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor})
        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Neighbor should be captured after boost"

    def test_boost_does_not_affect_other_comparison_sides(self):
        """Skulker boost on N does not change W-side comparison result."""
        # Place at cell 4; neighbor at cell 3 (to the west, uses W vs E)
        # Placed W=3 vs neighbor E=4 → no capture (3 < 4)
        # Boost is on N only; W comparison is unaffected
        placed = make_card("placed", n=1, e=1, s=1, w=3)
        neighbor = make_card("neighbor", n=1, e=4, s=1, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[3] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(
            board=board,
            p0_hand=["placed"],
            p1_hand=["neighbor"],
            p0_archetype=Archetype.SKULKER,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            skulker_boost_side="n",  # boost N, not W
        )
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor})
        assert next_state.board[3] is not None
        assert next_state.board[3].owner == 1, "West neighbor should NOT be captured"

    def test_boost_scope_is_this_placement_only(self):
        """After a Skulker move, the card in card_lookup retains original stats."""
        # Verify that card_lookup is not modified (original card unchanged)
        placed = make_card("placed", n=3, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=4, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(
            board=board,
            p0_hand=["placed"],
            p1_hand=["neighbor"],
            p0_archetype=Archetype.SKULKER,
        )
        lookup = {"placed": placed, "neighbor": neighbor}
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            skulker_boost_side="n",
        )
        apply_intent(state, intent, lookup)
        # Original card in lookup is unchanged
        assert lookup["placed"].sides.n == 3

    def test_archetype_used_set_after_skulker_activation(self):
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], p0_archetype=Archetype.SKULKER)
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            skulker_boost_side="n",
        )
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.players[0].archetype_used is True

    def test_archetype_used_stays_false_when_not_activated(self):
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], p0_archetype=Archetype.SKULKER)
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=False,
        )
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.players[0].archetype_used is False

    def test_opponent_archetype_used_unchanged(self):
        card = make_card("card_a")
        state = make_state(
            p0_hand=["card_a"],
            p0_archetype=Archetype.SKULKER,
            p1_archetype=Archetype.SKULKER,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            skulker_boost_side="e",
        )
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.players[1].archetype_used is False


# ---------------------------------------------------------------------------
# Once-per-game enforcement
# ---------------------------------------------------------------------------


class TestSkulkerOncePerGame:
    def test_second_use_raises_archetype_already_used(self):
        """Attempting to use Skulker when already used raises ArchetypeAlreadyUsedError."""
        card_a = make_card("card_a")
        state = make_state(
            p0_hand=["card_a"],
            p0_archetype=Archetype.SKULKER,
            p0_archetype_used=True,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            skulker_boost_side="n",
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state, intent, {"card_a": card_a})

    def test_sequential_usage_is_rejected_on_second_call(self):
        """Two consecutive moves both requesting Skulker; second must fail."""
        card_a = make_card("card_a")
        card_b = make_card("card_b")
        dummy = make_card("dummy")
        state = make_state(
            p0_hand=["card_a", "card_b"],
            p1_hand=["dummy"],
            p0_archetype=Archetype.SKULKER,
        )
        lookup = {"card_a": card_a, "card_b": card_b, "dummy": dummy}

        # First use — should succeed
        intent1 = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            skulker_boost_side="s",
        )
        state2 = apply_intent(state, intent1, lookup)

        # Player 1 takes a turn
        intent_p1 = PlacementIntent(
            player_index=1, card_key="dummy", cell_index=1, use_archetype=False
        )
        state3 = apply_intent(state2, intent_p1, lookup)

        # Second use of Skulker by player 0 — must fail
        intent2 = PlacementIntent(
            player_index=0,
            card_key="card_b",
            cell_index=2,
            use_archetype=True,
            skulker_boost_side="e",
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state3, intent2, lookup)


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


class TestSkulkerArgumentValidation:
    def test_missing_boost_side_raises_argument_error(self):
        """use_archetype=True without skulker_boost_side raises ArchetypePowerArgumentError."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], p0_archetype=Archetype.SKULKER)
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            # skulker_boost_side is None by default
        )
        with pytest.raises(ArchetypePowerArgumentError):
            apply_intent(state, intent, {"card_a": card})

    def test_invalid_side_string_raises_argument_error(self):
        """An unrecognized side string raises ArchetypePowerArgumentError."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], p0_archetype=Archetype.SKULKER)
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            skulker_boost_side="x",
        )
        with pytest.raises(ArchetypePowerArgumentError):
            apply_intent(state, intent, {"card_a": card})
