"""Tests for Caster archetype Mists reroll (best of two).

Caster power: roll the Mists die twice and keep the better (higher) result.
Higher is always better: 1=Fog (−2) is worst, 6=Omen (+2) is best.
Once per game per player.
"""

from functools import partial

import pytest

from app.models.game import Archetype, BoardCell
from app.rules.errors import ArchetypeAlreadyUsedError
from app.rules.reducer import PlacementIntent, apply_intent
from tests.conftest import make_card, mock_rng
from tests.conftest import make_state as _make_state

make_state = partial(_make_state, p0_archetype=Archetype.CASTER)


# ---------------------------------------------------------------------------
# Best-of-two reroll behaviour
# ---------------------------------------------------------------------------


class TestCasterReroll:
    def test_caster_best_of_two_picks_higher_roll(self):
        """Caster rolls twice and keeps the higher (better) result.

        Setup: placed N=6 vs neighbor S=6.
        First roll = 1 (Fog, −2): 6−2=4 < 6 → no capture.
        Second roll = 6 (Omen, +2): 6+2=8 > 6 → capture.
        max(1, 6) = 6 → Omen used → capture should occur.
        """
        placed = make_card("placed", n=6, e=1, s=1, w=1)
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
        rng = mock_rng(1, 6)  # first=Fog, second=Omen → max picks Omen
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor}, rng)

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Neighbor should be captured (Omen from best-of-two)"

    def test_caster_keeps_first_when_higher(self):
        """When first roll is better, best-of-two keeps it.

        Setup: placed N=4 vs neighbor S=5.
        First roll = 6 (Omen, +2): 4+2=6 > 5 → capture.
        Second roll = 1 (Fog, −2): 4−2=2 < 5 → no capture.
        max(6, 1) = 6 → Omen kept → capture should occur.
        """
        placed = make_card("placed", n=4, e=1, s=1, w=1)
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
        rng = mock_rng(6, 1)  # first=Omen, second=Fog → max keeps Omen
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor}, rng)

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Neighbor captured (Omen kept from first roll)"
        assert rng.randint.call_count == 2, "Caster should trigger exactly two die rolls"

    def test_without_caster_uses_only_one_roll(self):
        """Non-Caster placement consumes exactly one Mists roll."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], p0_archetype=Archetype.MARTIAL)
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=False,
        )
        rng = mock_rng(3, 3)  # provide two values; only one should be consumed
        apply_intent(state, intent, {"card_a": card}, rng)

        assert rng.randint.call_count == 1, "Non-Caster should only roll once"

    def test_caster_without_rng_marks_archetype_used(self):
        """Caster power is spent even when rng is None (no Mists in this context)."""
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

    def test_archetype_used_set_after_caster_activation(self):
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        next_state = apply_intent(state, intent, {"card_a": card}, mock_rng(3, 4))
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

    def test_opponent_archetype_used_unchanged(self):
        card = make_card("card_a")
        state = make_state(
            p0_hand=["card_a"],
            p0_archetype=Archetype.CASTER,
            p1_archetype=Archetype.CASTER,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        next_state = apply_intent(state, intent, {"card_a": card}, mock_rng(2, 4))
        assert next_state.players[1].archetype_used is False

    def test_caster_deterministic_with_seeded_rng(self):
        """Best-of-two with a real seeded RNG produces deterministic results."""
        from random import Random

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
        lookup = {"placed": placed, "neighbor": neighbor}

        # Run twice with same seed → same outcome
        result1 = apply_intent(state, intent, lookup, Random(42))
        result2 = apply_intent(state, intent, lookup, Random(42))

        assert result1.board[1] is not None
        assert result2.board[1] is not None
        assert result1.board[1].owner == result2.board[1].owner


# ---------------------------------------------------------------------------
# Once-per-game enforcement
# ---------------------------------------------------------------------------


class TestCasterOncePerGame:
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
            apply_intent(state, intent, {"card_a": card}, mock_rng(3, 4))

    def test_sequential_usage_is_rejected_on_second_call(self):
        card_a = make_card("card_a")
        card_b = make_card("card_b")
        dummy = make_card("dummy")
        state = make_state(
            p0_hand=["card_a", "card_b"],
            p1_hand=["dummy"],
            p0_archetype=Archetype.CASTER,
        )
        lookup = {"card_a": card_a, "card_b": card_b, "dummy": dummy}

        # First use — should succeed
        intent1 = PlacementIntent(
            player_index=0, card_key="card_a", cell_index=0, use_archetype=True
        )
        state2 = apply_intent(state, intent1, lookup, mock_rng(3, 4))

        # Player 1 takes a turn
        intent_p1 = PlacementIntent(
            player_index=1, card_key="dummy", cell_index=1, use_archetype=False
        )
        state3 = apply_intent(state2, intent_p1, lookup, mock_rng(3))

        # Second use of Caster by player 0 — must fail
        intent2 = PlacementIntent(
            player_index=0, card_key="card_b", cell_index=2, use_archetype=True
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state3, intent2, lookup, mock_rng(3, 4))
