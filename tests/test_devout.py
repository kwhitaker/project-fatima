"""Tests for Devout archetype conditional Fog negation.

Devout power: if the Mists roll is Fog (1), negate it (modifier → 0) and consume
the power. If the roll is NOT Fog, the power is NOT consumed — the player can
activate it again on a subsequent turn. Once per game per player (consumed only
on actual Fog).
"""

from functools import partial

import pytest

from app.models.game import Archetype, BoardCell
from app.rules.errors import ArchetypeAlreadyUsedError
from app.rules.reducer import PlacementIntent, apply_intent
from tests.conftest import make_card, mock_rng
from tests.conftest import make_state as _make_state

make_state = partial(_make_state, p0_archetype=Archetype.DEVOUT)


# ---------------------------------------------------------------------------
# Fog negation behaviour
# ---------------------------------------------------------------------------


class TestDevoutFogNegation:
    def test_fog_negated_enables_capture(self):
        """Devout neutralizes Fog so a capture that Fog would prevent succeeds.

        placed N=7 vs neighbor S=6. Fog: 7−2=5 < 6 → no capture.
        Devout negates: 7+0=7 > 6 → capture.
        """
        placed = make_card("placed", n=7, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=6, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["placed"], p1_hand=["neighbor"])
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
        )
        rng = mock_rng(1)  # Fog roll
        next_state = apply_intent(
            state, intent, {"placed": placed, "neighbor": neighbor}, rng
        )

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Fog negated → capture"

    def test_fog_roll_consumes_power(self):
        """When Devout activates and Fog rolls, the power IS consumed."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        next_state = apply_intent(state, intent, {"card_a": card}, mock_rng(1))
        assert next_state.players[0].archetype_used is True

    def test_fog_without_devout_prevents_capture(self):
        """Control: same scenario without Devout — Fog prevents the capture."""
        placed = make_card("placed", n=7, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=6, w=1)
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
        rng = mock_rng(1)  # Fog roll
        next_state = apply_intent(
            state, intent, {"placed": placed, "neighbor": neighbor}, rng
        )

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 1, "Fog prevents capture without Devout"

    def test_non_fog_roll_does_not_consume_power(self):
        """When Devout activates on a non-Fog roll, power is NOT consumed."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        next_state = apply_intent(state, intent, {"card_a": card}, mock_rng(6))
        assert next_state.players[0].archetype_used is False

    def test_neutral_roll_does_not_consume_power(self):
        """Roll 2-5 → power NOT consumed, can retry."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        next_state = apply_intent(state, intent, {"card_a": card}, mock_rng(3))
        assert next_state.players[0].archetype_used is False

    def test_devout_can_retry_until_fog_triggers(self):
        """Devout can activate multiple turns; consumed only when Fog rolls."""
        card_a = make_card("card_a")
        card_b = make_card("card_b")
        card_c = make_card("card_c")
        dummy1 = make_card("dummy1")
        dummy2 = make_card("dummy2")
        lookup = {
            "card_a": card_a,
            "card_b": card_b,
            "card_c": card_c,
            "dummy1": dummy1,
            "dummy2": dummy2,
        }

        state = make_state(
            p0_hand=["card_a", "card_b", "card_c"],
            p1_hand=["dummy1", "dummy2"],
        )

        # Turn 1: Devout activated, roll=3 (neutral) → NOT consumed
        intent1 = PlacementIntent(
            player_index=0, card_key="card_a", cell_index=0, use_archetype=True
        )
        state2 = apply_intent(state, intent1, lookup, mock_rng(3))
        assert state2.players[0].archetype_used is False

        # P1 turn
        intent_p1 = PlacementIntent(
            player_index=1, card_key="dummy1", cell_index=1, use_archetype=False
        )
        state3 = apply_intent(state2, intent_p1, lookup, mock_rng(3))

        # Turn 2: Devout activated again, roll=6 (Omen) → NOT consumed
        intent2 = PlacementIntent(
            player_index=0, card_key="card_b", cell_index=2, use_archetype=True
        )
        state4 = apply_intent(state3, intent2, lookup, mock_rng(6))
        assert state4.players[0].archetype_used is False

        # P1 turn
        intent_p1b = PlacementIntent(
            player_index=1, card_key="dummy2", cell_index=3, use_archetype=False
        )
        state5 = apply_intent(state4, intent_p1b, lookup, mock_rng(3))

        # Turn 3: Devout activated, roll=1 (Fog) → consumed!
        intent3 = PlacementIntent(
            player_index=0, card_key="card_c", cell_index=4, use_archetype=True
        )
        state6 = apply_intent(state5, intent3, lookup, mock_rng(1))
        assert state6.players[0].archetype_used is True

    def test_devout_consumes_only_one_roll(self):
        """Devout does not roll again; only one die is consumed."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        rng = mock_rng(1, 3)  # two values; only one should be consumed
        apply_intent(state, intent, {"card_a": card}, rng)

        assert rng.randint.call_count == 1

    def test_archetype_used_stays_false_when_not_activated(self):
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=False,
        )
        next_state = apply_intent(state, intent, {"card_a": card}, mock_rng(3))
        assert next_state.players[0].archetype_used is False

    def test_opponent_archetype_used_unchanged(self):
        card = make_card("card_a")
        state = make_state(
            p0_hand=["card_a"],
            p0_archetype=Archetype.DEVOUT,
            p1_archetype=Archetype.DEVOUT,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        next_state = apply_intent(state, intent, {"card_a": card}, mock_rng(1))
        assert next_state.players[1].archetype_used is False


# ---------------------------------------------------------------------------
# Once-per-game enforcement (after Fog consumes it)
# ---------------------------------------------------------------------------


class TestDevoutOncePerGame:
    def test_second_use_after_fog_raises(self):
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], p0_archetype_used=True)
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state, intent, {"card_a": card}, mock_rng(1))

    def test_sequential_fog_consumption_then_rejected(self):
        card_a = make_card("card_a")
        card_b = make_card("card_b")
        dummy = make_card("dummy")
        state = make_state(
            p0_hand=["card_a", "card_b"],
            p1_hand=["dummy"],
            p0_archetype=Archetype.DEVOUT,
        )
        lookup = {"card_a": card_a, "card_b": card_b, "dummy": dummy}

        # First use with Fog roll → consumed
        intent1 = PlacementIntent(
            player_index=0, card_key="card_a", cell_index=0, use_archetype=True
        )
        state2 = apply_intent(state, intent1, lookup, mock_rng(1))
        assert state2.players[0].archetype_used is True

        # Player 1 takes a turn
        intent_p1 = PlacementIntent(
            player_index=1, card_key="dummy", cell_index=1, use_archetype=False
        )
        state3 = apply_intent(state2, intent_p1, lookup, mock_rng(3))

        # Second use — must fail
        intent2 = PlacementIntent(
            player_index=0, card_key="card_b", cell_index=2, use_archetype=True
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state3, intent2, lookup, mock_rng(1))
