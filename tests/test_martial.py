"""Tests for US-006: Martial archetype rotation.

Martial power: rotate the placed card once (N→E, E→S, S→W, W→N) before
Mists/captures are evaluated. Once per game per player.

Rotation mapping:
  new.n = old.w
  new.e = old.n
  new.s = old.e
  new.w = old.s
"""

from functools import partial

import pytest

from app.models.game import Archetype, BoardCell
from app.rules.archetypes import rotate_card_ccw, rotate_card_once
from app.rules.errors import (
    ArchetypeAlreadyUsedError,
    ArchetypeNotAvailableError,
    ArchetypePowerArgumentError,
)
from app.rules.reducer import PlacementIntent, apply_intent
from tests.conftest import make_card
from tests.conftest import make_state as _make_state

make_state = partial(_make_state, p0_archetype=Archetype.MARTIAL)


# ---------------------------------------------------------------------------
# Unit: rotate_card_once
# ---------------------------------------------------------------------------


class TestRotateCardOnce:
    def test_rotation_remaps_sides(self):
        """Rotating once maps N→E, E→S, S→W, W→N."""
        card = make_card("c", n=8, e=7, s=6, w=5)
        rotated = rotate_card_once(card)
        # new.n = old.w, new.e = old.n, new.s = old.e, new.w = old.s
        assert rotated.sides.n == 5
        assert rotated.sides.e == 8
        assert rotated.sides.s == 7
        assert rotated.sides.w == 6

    def test_rotation_preserves_other_fields(self):
        """Rotation only changes sides; card_key and metadata are unchanged."""
        card = make_card("my_card", n=3, e=4, s=5, w=6)
        rotated = rotate_card_once(card)
        assert rotated.card_key == "my_card"
        assert rotated.character_key == "my_card"
        assert rotated.tier == 1
        assert rotated.rarity == 50

    def test_rotation_does_not_mutate_original(self):
        """The original card definition is unchanged after rotation."""
        card = make_card("c", n=8, e=7, s=6, w=5)
        rotate_card_once(card)
        assert card.sides.n == 8
        assert card.sides.e == 7
        assert card.sides.s == 6
        assert card.sides.w == 5

    def test_four_rotations_restores_original(self):
        """Four rotations return the card to its original orientation."""
        card = make_card("c", n=1, e=2, s=3, w=4)
        result = card
        for _ in range(4):
            result = rotate_card_once(result)
        assert result.sides.n == card.sides.n
        assert result.sides.e == card.sides.e
        assert result.sides.s == card.sides.s
        assert result.sides.w == card.sides.w


# ---------------------------------------------------------------------------
# Integration: Martial rotation via apply_intent
# ---------------------------------------------------------------------------


class TestMartialRotationInReducer:
    def test_rotation_enables_capture_that_would_otherwise_miss(self):
        """Martial rotation lets the placed card capture with a side that was W."""
        # Placed card: N=1 (too weak), W=10 (strong, becomes N after rotation)
        # Neighbor at cell 1 (north of cell 4): S=5
        # Without rotation: N=1 vs S=5 → no capture
        # With rotation: N=10 vs S=5 → capture
        placed = make_card("placed", n=1, e=1, s=1, w=10)
        neighbor = make_card("neighbor", n=1, e=1, s=5, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(
            board=board,
            p0_hand=["placed"],
            p1_hand=["neighbor"],
            p0_archetype=Archetype.MARTIAL,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
        )
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor})
        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Neighbor should be captured"

    def test_no_rotation_without_flag(self):
        """Without use_archetype=True, the card is NOT rotated."""
        placed = make_card("placed", n=1, e=1, s=1, w=10)
        neighbor = make_card("neighbor", n=1, e=1, s=5, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(
            board=board,
            p0_hand=["placed"],
            p1_hand=["neighbor"],
            p0_archetype=Archetype.MARTIAL,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=False,
        )
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor})
        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 1, "Neighbor should NOT be captured"

    def test_archetype_used_set_to_true_after_use(self):
        """After using Martial, archetype_used is True for that player."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], p0_archetype=Archetype.MARTIAL)
        intent = PlacementIntent(
            player_index=0, card_key="card_a", cell_index=0, use_archetype=True
        )
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.players[0].archetype_used is True

    def test_archetype_used_stays_false_when_not_used(self):
        """When power is not activated, archetype_used stays False."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], p0_archetype=Archetype.MARTIAL)
        intent = PlacementIntent(
            player_index=0, card_key="card_a", cell_index=0, use_archetype=False
        )
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.players[0].archetype_used is False

    def test_opponent_archetype_used_unchanged(self):
        """Using the Martial power does not touch the opponent's archetype_used."""
        card = make_card("card_a")
        state = make_state(
            p0_hand=["card_a"],
            p0_archetype=Archetype.MARTIAL,
            p1_archetype=Archetype.MARTIAL,
        )
        intent = PlacementIntent(
            player_index=0, card_key="card_a", cell_index=0, use_archetype=True
        )
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.players[1].archetype_used is False


# ---------------------------------------------------------------------------
# Once-per-game enforcement
# ---------------------------------------------------------------------------


class TestMartialOncePerGame:
    def test_second_use_raises_archetype_already_used(self):
        """Attempting to use Martial twice raises ArchetypeAlreadyUsedError."""
        card_a = make_card("card_a")
        card_b = make_card("card_b")
        # Start with archetype_used=True to simulate it already being spent
        state = make_state(
            p0_hand=["card_a"],
            p0_archetype=Archetype.MARTIAL,
            p0_archetype_used=True,
        )
        intent = PlacementIntent(
            player_index=0, card_key="card_a", cell_index=0, use_archetype=True
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state, intent, {"card_a": card_a, "card_b": card_b})

    def test_sequential_usage_is_rejected_on_second_call(self):
        """Two consecutive moves both requesting Martial; second must fail."""
        card_a = make_card("card_a")
        card_b = make_card("card_b")
        state = make_state(
            p0_hand=["card_a", "card_b"],
            p1_hand=["dummy"],
            p0_archetype=Archetype.MARTIAL,
            current_player_index=0,
        )
        # First use — should succeed
        intent1 = PlacementIntent(
            player_index=0, card_key="card_a", cell_index=0, use_archetype=True
        )
        dummy_card = make_card("dummy")
        lookup = {"card_a": card_a, "card_b": card_b, "dummy": dummy_card}
        state2 = apply_intent(state, intent1, lookup)
        # Player 1 takes a turn
        intent_p1 = PlacementIntent(
            player_index=1, card_key="dummy", cell_index=1, use_archetype=False
        )
        state3 = apply_intent(state2, intent_p1, lookup)
        # Second use of Martial by player 0 — must fail
        intent2 = PlacementIntent(
            player_index=0, card_key="card_b", cell_index=2, use_archetype=True
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state3, intent2, lookup)


# ---------------------------------------------------------------------------
# Wrong archetype enforcement
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Unit: rotate_card_ccw
# ---------------------------------------------------------------------------


class TestRotateCardCcw:
    def test_ccw_rotation_remaps_sides(self):
        """CCW rotation maps N→W, E→N, S→E, W→S."""
        card = make_card("c", n=8, e=7, s=6, w=5)
        rotated = rotate_card_ccw(card)
        assert rotated.sides.n == 7  # old.e
        assert rotated.sides.e == 6  # old.s
        assert rotated.sides.s == 5  # old.w
        assert rotated.sides.w == 8  # old.n

    def test_cw_then_ccw_restores_original(self):
        """CW followed by CCW is identity."""
        card = make_card("c", n=1, e=2, s=3, w=4)
        result = rotate_card_ccw(rotate_card_once(card))
        assert result.sides.n == card.sides.n
        assert result.sides.e == card.sides.e
        assert result.sides.s == card.sides.s
        assert result.sides.w == card.sides.w

    def test_four_ccw_rotations_restores_original(self):
        """Four CCW rotations return the card to its original orientation."""
        card = make_card("c", n=1, e=2, s=3, w=4)
        result = card
        for _ in range(4):
            result = rotate_card_ccw(result)
        assert result.sides.n == card.sides.n
        assert result.sides.e == card.sides.e
        assert result.sides.s == card.sides.s
        assert result.sides.w == card.sides.w


# ---------------------------------------------------------------------------
# Integration: Martial direction choice via apply_intent
# ---------------------------------------------------------------------------


class TestMartialDirectionChoice:
    def test_cw_direction_uses_clockwise_rotation(self):
        """Explicit 'cw' direction produces clockwise rotation."""
        placed = make_card("placed", n=1, e=1, s=1, w=10)
        neighbor = make_card("neighbor", n=1, e=1, s=5, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["placed"], p1_hand=["neighbor"])
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            martial_rotation_direction="cw",
        )
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor})
        # CW: W=10 becomes N=10, vs neighbor S=5 → capture
        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0

    def test_ccw_direction_uses_counter_clockwise_rotation(self):
        """Explicit 'ccw' direction produces counter-clockwise rotation."""
        # CCW: E=10 becomes N=10 (new.n = old.e)
        placed = make_card("placed", n=1, e=10, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=5, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["placed"], p1_hand=["neighbor"])
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            martial_rotation_direction="ccw",
        )
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor})
        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0

    def test_none_direction_defaults_to_cw(self):
        """Missing direction (None) defaults to clockwise for backward compat."""
        placed = make_card("placed", n=1, e=1, s=1, w=10)
        neighbor = make_card("neighbor", n=1, e=1, s=5, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["placed"], p1_hand=["neighbor"])
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            # martial_rotation_direction is None by default
        )
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor})
        # Default CW: W=10 → N=10 vs neighbor S=5 → capture
        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0

    def test_invalid_direction_raises_argument_error(self):
        """Invalid direction string raises ArchetypePowerArgumentError."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            martial_rotation_direction="left",
        )
        with pytest.raises(ArchetypePowerArgumentError):
            apply_intent(state, intent, {"card_a": card})


# ---------------------------------------------------------------------------
# Wrong archetype enforcement
# ---------------------------------------------------------------------------


class TestMartialWrongArchetype:
    def test_no_archetype_cannot_use_rotation(self):
        """Player with no archetype cannot request use_archetype=True."""
        card = make_card("card_a")
        state = make_state(
            p0_hand=["card_a"],
            p0_archetype=None,
        )
        intent = PlacementIntent(
            player_index=0, card_key="card_a", cell_index=0, use_archetype=True
        )
        with pytest.raises(ArchetypeNotAvailableError):
            apply_intent(state, intent, {"card_a": card})
