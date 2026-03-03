"""Tests for US-009: Devout archetype Fog negation.

Devout power: if the Mists roll is Fog (1), treat it as no modifier for this
placement. If the roll is not Fog, Devout does nothing. Once per game per player.
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
        """Devout neutralizes Fog so a tie becomes a no-effect instead of a miss.

        Setup: placed N=5 vs neighbor S=5.
        Without Devout + Fog roll: 5-1=4 < 5 → no capture.
        With Devout + Fog roll: modifier zeroed → 5 == 5 → still no capture (strict >).

        Use a marginal case where Fog would prevent capture:
        placed N=6 vs neighbor S=6.
        Fog: 6-1=5 < 6 → no capture.
        Devout negates Fog: 6+0=6 == 6 → still no capture (strict >).

        Better: placed N=7 vs neighbor S=6.
        Fog: 7-1=6 == 6 → no capture.
        Devout negates: 7+0=7 > 6 → capture!
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
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor}, rng)

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Neighbor should be captured (Fog negated)"

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
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor}, rng)

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 1, "Fog should prevent capture without Devout"

    def test_non_fog_roll_unaffected(self):
        """When roll is not Fog, Devout changes nothing — normal modifier applies.

        placed N=5 vs neighbor S=5; roll=6 (Omen, +1): 5+1=6 > 5 → capture.
        """
        placed = make_card("placed", n=5, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=5, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["placed"], p1_hand=["neighbor"])
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
        )
        rng = mock_rng(6)  # Omen roll
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor}, rng)

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Omen should cause capture even with Devout"

    def test_neutral_roll_unaffected(self):
        """Roll 2-5 → modifier 0 regardless of Devout; outcome unchanged."""
        placed = make_card("placed", n=5, e=1, s=1, w=1)
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
        rng = mock_rng(3)  # neutral roll
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor}, rng)

        # 5+0=5 not > 6 → no capture
        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 1, "Neutral roll: no capture expected"

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

        assert rng.randint.call_count == 1, "Devout should consume exactly one Mists roll"

    def test_archetype_used_set_after_devout_activation(self):
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        next_state = apply_intent(state, intent, {"card_a": card}, mock_rng(3))
        assert next_state.players[0].archetype_used is True

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

    def test_devout_without_rng_marks_archetype_used(self):
        """Power is spent even when rng is None."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        next_state = apply_intent(state, intent, {"card_a": card}, rng=None)
        assert next_state.players[0].archetype_used is True


# ---------------------------------------------------------------------------
# Once-per-game enforcement
# ---------------------------------------------------------------------------


class TestDevoutOncePerGame:
    def test_second_use_raises_archetype_already_used(self):
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

    def test_sequential_usage_is_rejected_on_second_call(self):
        card_a = make_card("card_a")
        card_b = make_card("card_b")
        dummy = make_card("dummy")
        state = make_state(
            p0_hand=["card_a", "card_b"],
            p1_hand=["dummy"],
            p0_archetype=Archetype.DEVOUT,
        )
        lookup = {"card_a": card_a, "card_b": card_b, "dummy": dummy}

        # First use — should succeed
        intent1 = PlacementIntent(
            player_index=0, card_key="card_a", cell_index=0, use_archetype=True
        )
        state2 = apply_intent(state, intent1, lookup, mock_rng(1))

        # Player 1 takes a turn
        intent_p1 = PlacementIntent(
            player_index=1, card_key="dummy", cell_index=1, use_archetype=False
        )
        state3 = apply_intent(state2, intent_p1, lookup, mock_rng(3))

        # Second use of Devout by player 0 — must fail
        intent2 = PlacementIntent(
            player_index=0, card_key="card_b", cell_index=2, use_archetype=True
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state3, intent2, lookup, mock_rng(1))

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
        next_state = apply_intent(state, intent, {"card_a": card}, mock_rng(2))
        assert next_state.players[1].archetype_used is False
