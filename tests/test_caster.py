"""Tests for Caster archetype: guaranteed Omen (+2 all comparisons).

Caster power: when activated, the Mists modifier is forced to +2 (Omen)
regardless of the actual die roll. The die is still rolled (for display/logging)
but has no mechanical effect. Once per game per player.
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
# Guaranteed Omen behaviour
# ---------------------------------------------------------------------------


class TestCasterGuaranteedOmen:
    @pytest.mark.parametrize("die_roll", [1, 2, 3, 4, 5, 6])
    def test_caster_always_yields_plus_two_modifier(self, die_roll: int):
        """Caster activation gives +2 modifier regardless of what the die rolls."""
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
        rng = mock_rng(die_roll)
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor}, rng)

        # 5+2=7 > 6 → should always capture
        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, (
            f"Neighbor should be captured with Omen (+2), die roll was {die_roll}"
        )

    def test_caster_fog_roll_still_gives_omen(self):
        """Even when die rolls 1 (Fog), Caster forces Omen (+2)."""
        placed = make_card("placed", n=3, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=4, w=1)
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

        # 3+2=5 > 4 → capture despite Fog roll
        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0

    def test_caster_mists_effect_is_omen_regardless_of_roll(self):
        """last_move.mists_effect is 'omen' even when die rolls 1."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        next_state = apply_intent(state, intent, {"card_a": card}, mock_rng(1))

        assert next_state.last_move is not None
        assert next_state.last_move.mists_effect == "omen"

    def test_caster_rolls_die_once(self):
        """Caster still rolls the die once (for display), not twice."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
        )
        rng = mock_rng(3)
        apply_intent(state, intent, {"card_a": card}, rng)
        assert rng.randint.call_count == 1, "Caster should only roll once"

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
        rng = mock_rng(3)
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
        next_state = apply_intent(state, intent, {"card_a": card}, mock_rng(2))
        assert next_state.players[1].archetype_used is False

    def test_caster_deterministic_with_seeded_rng(self):
        """With a real seeded RNG, results are deterministic."""
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
            apply_intent(state, intent, {"card_a": card}, mock_rng(3))

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
        state2 = apply_intent(state, intent1, lookup, mock_rng(3))

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
            apply_intent(state3, intent2, lookup, mock_rng(3))
