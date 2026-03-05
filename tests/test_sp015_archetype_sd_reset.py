"""Tests for US-SP-015: archetype powers reset each Sudden Death round.

After a Sudden Death transition, both players should have archetype_used=False
so they can use their once-per-round power again in the new round.
"""

from app.models.game import Archetype, GameStatus
from app.rules.reducer import begin_sudden_death_round
from tests.test_sudden_death import make_full_board_state


class TestArchetypeResetOnSuddenDeath:
    """archetype_used resets to False for both players on SD transition."""

    def test_both_used_reset_to_false(self):
        """When both players used archetypes, both reset on SD."""
        state = make_full_board_state(
            p0_archetype_used=True, p1_archetype_used=True
        )
        new_state = begin_sudden_death_round(state)
        assert new_state.players[0].archetype_used is False
        assert new_state.players[1].archetype_used is False

    def test_one_used_one_unused_both_reset(self):
        """Even if only one player used their archetype, both reset."""
        state = make_full_board_state(
            p0_archetype_used=True, p1_archetype_used=False
        )
        new_state = begin_sudden_death_round(state)
        assert new_state.players[0].archetype_used is False
        assert new_state.players[1].archetype_used is False

    def test_neither_used_stays_false(self):
        """If neither used their archetype, both remain False (no regression)."""
        state = make_full_board_state(
            p0_archetype_used=False, p1_archetype_used=False
        )
        new_state = begin_sudden_death_round(state)
        assert new_state.players[0].archetype_used is False
        assert new_state.players[1].archetype_used is False

    def test_archetype_identity_preserved_after_reset(self):
        """The archetype type itself is not changed by the reset."""
        state = make_full_board_state(
            p0_archetype_used=True, p1_archetype_used=True
        )
        new_state = begin_sudden_death_round(state)
        assert new_state.players[0].archetype == Archetype.MARTIAL
        assert new_state.players[1].archetype == Archetype.SKULKER


class TestArchetypeUsableInSuddenDeathRound:
    """Player can actually use their archetype again in an SD round."""

    def test_player_can_use_archetype_in_sd_round(self):
        """After SD transition with used archetype, player gets a fresh archetype."""
        state = make_full_board_state(
            p0_archetype_used=True, p1_archetype_used=True,
        )
        new_state = begin_sudden_death_round(state)
        # Both players can use archetype again
        assert new_state.players[0].archetype_used is False
        assert new_state.players[1].archetype_used is False
        # Round number confirms we're in SD
        assert new_state.round_number == 2

    def test_consecutive_sd_rounds_reset_archetype_each_time(self):
        """Archetype resets on every SD transition, not just the first."""
        state = make_full_board_state(
            p0_archetype_used=True, p1_archetype_used=True,
            sudden_death_rounds_used=1, round_number=2,
        )
        new_state = begin_sudden_death_round(state)
        assert new_state.players[0].archetype_used is False
        assert new_state.players[1].archetype_used is False
        assert new_state.round_number == 3

    def test_sd_cap_draw_does_not_reset_archetype(self):
        """When SD cap is reached (draw), archetype_used is NOT reset (game is over)."""
        state = make_full_board_state(
            sudden_death_rounds_used=3,
            p0_archetype_used=True,
            p1_archetype_used=True,
        )
        new_state = begin_sudden_death_round(state)
        assert new_state.status == GameStatus.COMPLETE
        # archetype_used is irrelevant on a complete game, but should be unchanged
        assert new_state.players[0].archetype_used is True
        assert new_state.players[1].archetype_used is True


class TestAIArchetypeInSuddenDeath:
    """AI checks archetype_used per move, so resetting it enables AI archetype use in SD."""

    def test_ai_archetype_available_after_sd(self):
        """After SD transition, AI player's archetype_used is False (usable)."""
        state = make_full_board_state(
            p0_archetype_used=True, p1_archetype_used=True
        )
        # Simulate p1 as AI
        p1 = state.players[1].model_copy(
            update={"player_type": "ai", "ai_difficulty": "medium"}
        )
        state = state.model_copy(
            update={"players": [state.players[0], p1]}
        )
        new_state = begin_sudden_death_round(state)
        assert new_state.players[1].archetype_used is False
        assert new_state.players[1].player_type == "ai"
