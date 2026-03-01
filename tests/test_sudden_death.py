"""Tests for US-012: Sudden Death rounds with cap.

A full-board tie triggers a Sudden Death round: players' new hands are
built from the cards they own on the board, the board resets, and round
counters increment.  After 3 Sudden Death rounds the game ends as a draw.

NOTE: With 9 cells and integer ownership, a genuine tie at board-full is
mathematically impossible in normal play (9 is odd → one player always has
at least 5 cells).  The SD transition logic is therefore tested by calling
begin_sudden_death_round directly with constructed states rather than
driving it through apply_intent.
"""

import pytest

from app.models.game import (
    Archetype,
    BoardCell,
    GameState,
    GameStatus,
    PlayerState,
)
from app.rules.reducer import begin_sudden_death_round

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def cell(key: str, owner: int) -> BoardCell:
    return BoardCell(card_key=key, owner=owner)


def make_full_board_state(
    *,
    p0_cells: int = 5,
    p1_cells: int = 4,
    sudden_death_rounds_used: int = 0,
    round_number: int = 1,
    p0_archetype_used: bool = False,
    p1_archetype_used: bool = False,
) -> GameState:
    """Build a board-full GameState with p0_cells owned by p0 and p1_cells by p1.

    Cards are named c0..c8; the first p0_cells belong to player 0,
    the remainder to player 1.  Requires p0_cells + p1_cells == 9.
    """
    assert p0_cells + p1_cells == 9, "Total cells must equal 9"
    p0_board: list[BoardCell | None] = [cell(f"c{i}", 0) for i in range(p0_cells)]
    board: list[BoardCell | None] = p0_board + [cell(f"c{i}", 1) for i in range(p0_cells, 9)]
    return GameState(
        game_id="test-sd",
        status=GameStatus.ACTIVE,
        round_number=round_number,
        sudden_death_rounds_used=sudden_death_rounds_used,
        players=[
            PlayerState(
                player_id="p0",
                hand=[],
                archetype=Archetype.MARTIAL,
                archetype_used=p0_archetype_used,
            ),
            PlayerState(
                player_id="p1",
                hand=[],
                archetype=Archetype.SKULKER,
                archetype_used=p1_archetype_used,
            ),
        ],
        board=board,
        current_player_index=1,  # non-zero so we can verify the alternation
        starting_player_index=0,  # p0 started the main game
    )


# ---------------------------------------------------------------------------
# Transition: basic state mutations
# ---------------------------------------------------------------------------


class TestBeginSuddenDeathRound:
    def test_increments_round_number(self):
        new_state = begin_sudden_death_round(make_full_board_state())
        assert new_state.round_number == 2

    def test_increments_sudden_death_rounds_used(self):
        new_state = begin_sudden_death_round(make_full_board_state())
        assert new_state.sudden_death_rounds_used == 1

    def test_resets_board_to_empty(self):
        new_state = begin_sudden_death_round(make_full_board_state())
        assert len(new_state.board) == 9
        assert all(c is None for c in new_state.board)

    def test_status_is_active(self):
        new_state = begin_sudden_death_round(make_full_board_state())
        assert new_state.status == GameStatus.ACTIVE

    def test_result_is_none(self):
        new_state = begin_sudden_death_round(make_full_board_state())
        assert new_state.result is None

    def test_current_player_alternates_in_sd(self):
        """SD round 1 (round 2) gives the turn to the other starting player.

        With starting_player_index=0 and round_number becoming 2:
        new_starting = (0 + 2 - 1) % 2 = 1
        """
        state = make_full_board_state()
        assert state.starting_player_index == 0  # default
        new_state = begin_sudden_death_round(state)
        assert new_state.current_player_index == 1

    def test_game_id_preserved(self):
        new_state = begin_sudden_death_round(make_full_board_state())
        assert new_state.game_id == "test-sd"

    def test_state_version_not_bumped(self):
        """begin_sudden_death_round does not bump state_version; caller owns that."""
        state = make_full_board_state()
        original_version = state.state_version
        new_state = begin_sudden_death_round(state)
        assert new_state.state_version == original_version


# ---------------------------------------------------------------------------
# Card carryover: hands rebuilt from board ownership
# ---------------------------------------------------------------------------


class TestCardCarryover:
    def test_player0_hand_matches_owned_cells(self):
        """p0 owned c0..c4 (5 cells) → new hand contains exactly those keys."""
        state = make_full_board_state(p0_cells=5, p1_cells=4)
        new_state = begin_sudden_death_round(state)
        assert sorted(new_state.players[0].hand) == [f"c{i}" for i in range(5)]

    def test_player1_hand_matches_owned_cells(self):
        """p1 owned c5..c8 (4 cells) → new hand contains exactly those keys."""
        state = make_full_board_state(p0_cells=5, p1_cells=4)
        new_state = begin_sudden_death_round(state)
        assert sorted(new_state.players[1].hand) == [f"c{i}" for i in range(5, 9)]

    def test_all_9_cards_distributed(self):
        """All 9 board cards appear across the two new hands (no card lost)."""
        state = make_full_board_state(p0_cells=5, p1_cells=4)
        new_state = begin_sudden_death_round(state)
        combined = set(new_state.players[0].hand) | set(new_state.players[1].hand)
        assert combined == {f"c{i}" for i in range(9)}

    def test_no_cards_duplicated_across_players(self):
        """No card appears in both hands."""
        state = make_full_board_state(p0_cells=5, p1_cells=4)
        new_state = begin_sudden_death_round(state)
        p0 = set(new_state.players[0].hand)
        p1 = set(new_state.players[1].hand)
        assert p0.isdisjoint(p1)

    def test_asymmetric_ownership_p0_sweeps(self):
        """If p0 owns all 9 cards, p0 gets all 9, p1 gets none."""
        board: list[BoardCell | None] = [cell(f"c{i}", 0) for i in range(9)]
        state = make_full_board_state(p0_cells=5, p1_cells=4)
        state = state.model_copy(update={"board": board})
        new_state = begin_sudden_death_round(state)
        assert len(new_state.players[0].hand) == 9
        assert new_state.players[1].hand == []

    def test_archetype_used_not_reset(self):
        """archetype_used is preserved (once-per-game power persists across SD rounds)."""
        state = make_full_board_state(p0_archetype_used=True, p1_archetype_used=False)
        new_state = begin_sudden_death_round(state)
        assert new_state.players[0].archetype_used is True
        assert new_state.players[1].archetype_used is False

    def test_archetype_preserved(self):
        """Archetype identity is unchanged."""
        state = make_full_board_state()
        new_state = begin_sudden_death_round(state)
        assert new_state.players[0].archetype == Archetype.MARTIAL
        assert new_state.players[1].archetype == Archetype.SKULKER


# ---------------------------------------------------------------------------
# Cap: after 3 Sudden Death rounds, result is draw
# ---------------------------------------------------------------------------


class TestSuddenDeathCap:
    def test_cap_at_3_returns_complete_draw(self):
        """With 3 SD rounds already used, the next call sets COMPLETE + draw."""
        state = make_full_board_state(sudden_death_rounds_used=3)
        new_state = begin_sudden_death_round(state)
        assert new_state.status == GameStatus.COMPLETE
        assert new_state.result is not None
        assert new_state.result.is_draw is True
        assert new_state.result.winner is None

    def test_cap_at_3_does_not_increment_counters(self):
        """When cap is reached, round_number and sudden_death_rounds_used are not incremented."""
        state = make_full_board_state(sudden_death_rounds_used=3, round_number=4)
        new_state = begin_sudden_death_round(state)
        assert new_state.round_number == 4
        assert new_state.sudden_death_rounds_used == 3

    def test_cap_at_3_board_not_reset(self):
        """Board is not cleared when cap forces a draw — game is simply over."""
        state = make_full_board_state(sudden_death_rounds_used=3)
        new_state = begin_sudden_death_round(state)
        # Board unchanged (still full — we returned COMPLETE without a reset)
        assert all(c is not None for c in new_state.board)

    def test_2_sd_rounds_still_active(self):
        """With 2 SD rounds used, the transition produces a new active round (round 3 → 4)."""
        state = make_full_board_state(sudden_death_rounds_used=2, round_number=3)
        new_state = begin_sudden_death_round(state)
        assert new_state.status == GameStatus.ACTIVE
        assert new_state.sudden_death_rounds_used == 3
        assert new_state.round_number == 4

    @pytest.mark.parametrize(
        "used,expected_status",
        [
            (0, GameStatus.ACTIVE),
            (1, GameStatus.ACTIVE),
            (2, GameStatus.ACTIVE),
            (3, GameStatus.COMPLETE),
        ],
    )
    def test_cap_boundary_parametrized(self, used: int, expected_status: GameStatus):
        state = make_full_board_state(sudden_death_rounds_used=used)
        new_state = begin_sudden_death_round(state)
        assert new_state.status == expected_status

    def test_consecutive_sd_transitions_end_in_draw(self):
        """Three consecutive SD transitions; the fourth attempt produces a draw."""
        state = make_full_board_state(sudden_death_rounds_used=0, round_number=1)

        for expected_round in range(2, 5):  # rounds 2, 3, 4
            new_state = begin_sudden_death_round(state)
            assert new_state.status == GameStatus.ACTIVE
            assert new_state.round_number == expected_round
            # Rebuild a full board for the next iteration
            full_board: list[BoardCell | None] = [
                BoardCell(card_key=f"c{i}", owner=(0 if i < 5 else 1)) for i in range(9)
            ]
            state = new_state.model_copy(update={"board": full_board})

        # Now sudden_death_rounds_used == 3; next call hits the cap
        final_state = begin_sudden_death_round(state)
        assert final_state.status == GameStatus.COMPLETE
        assert final_state.result is not None
        assert final_state.result.is_draw is True
