"""Tests for Devout archetype: Ward.

Devout power: after placing a card, choose one of your cards already on the board.
That card is immune to capture (Plus, standard, combo) for the opponent's next
placement. The power is consumed immediately on activation (once per game).
"""

from functools import partial

import pytest

from app.models.game import Archetype, BoardCell
from app.rules.errors import ArchetypeAlreadyUsedError, ArchetypePowerArgumentError
from app.rules.reducer import PlacementIntent, apply_intent
from tests.conftest import make_card, mock_rng
from tests.conftest import make_state as _make_state

make_state = partial(_make_state, p0_archetype=Archetype.DEVOUT)


# ---------------------------------------------------------------------------
# Core ward protection
# ---------------------------------------------------------------------------


class TestDevoutWard:
    def test_warded_card_not_captured_by_higher_side(self):
        """Warded card survives even when opponent's attacking side is higher."""
        friendly = make_card("friendly", n=1, e=1, s=3, w=1)
        attacker = make_card("attacker", n=10, e=1, s=1, w=1)
        placed = make_card("placed", n=1, e=1, s=1, w=1)
        board: list[BoardCell | None] = [None] * 9
        # P0 has a card at cell 1
        board[1] = BoardCell(card_key="friendly", owner=0)
        lookup = {"friendly": friendly, "attacker": attacker, "placed": placed}

        # P0 places at cell 0, wards cell 1
        state = make_state(
            board=board,
            p0_hand=["placed"],
            p1_hand=["attacker"],
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=0,
            use_archetype=True,
            devout_ward_cell=1,
        )
        state2 = apply_intent(state, intent, lookup, mock_rng(3))
        assert state2.warded_cell == 1

        # P1 places attacker adjacent to warded cell (cell 4, N=10 vs friendly S=3)
        intent2 = PlacementIntent(
            player_index=1,
            card_key="attacker",
            cell_index=4,
            use_archetype=False,
        )
        state3 = apply_intent(state2, intent2, lookup, mock_rng(3))

        # Warded card should NOT be captured
        assert state3.board[1] is not None
        assert state3.board[1].owner == 0, "Warded card not captured"
        # Ward should be cleared after opponent's placement
        assert state3.warded_cell is None

    def test_warded_card_not_captured_by_plus_rule(self):
        """Warded card is immune to Plus rule capture."""
        # Set up: P0 has cards at cells 1 and 3 (adjacent to cell 4)
        # P1 places at cell 4 with sides that trigger Plus with cells 1 and 3
        # Cell 1 is warded, cell 3 is not
        card_at_1 = make_card("card1", n=1, e=1, s=4, w=1)  # S=4 faces cell 4's N
        card_at_3 = make_card("card3", n=1, e=6, s=1, w=1)  # E=6 faces cell 4's W
        p1_card = make_card("p1card", n=4, e=1, s=1, w=6)   # N=4+S=4=8, W=6+E=6=12... no
        # Plus: placed_side + neighbor_side must match for 2+ neighbors.
        # Cell 4 neighbors: cell 1 (N↔S), cell 3 (W↔E), cell 5 (E↔W), cell 7 (S↔N)
        # P1 places at cell 4: N faces cell 1's S, W faces cell 3's E
        # For Plus: p1card.N + card1.S = p1card.W + card3.E → 4+4 = 6+6? No, 8≠12
        # Let's make them equal: p1card.N=3, card1.S=5 → sum=8; p1card.W=2, card3.E=6 → sum=8
        card_at_1 = make_card("card1", n=1, e=1, s=5, w=1)
        card_at_3 = make_card("card3", n=1, e=6, s=1, w=1)
        p1_card = make_card("p1card", n=3, e=1, s=1, w=2)
        placed = make_card("placed", n=1, e=1, s=1, w=1)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="card1", owner=0)
        board[3] = BoardCell(card_key="card3", owner=0)
        lookup = {"card1": card_at_1, "card3": card_at_3, "p1card": p1_card, "placed": placed}

        # P0 places at cell 0, wards cell 1
        state = make_state(
            board=board,
            p0_hand=["placed"],
            p1_hand=["p1card"],
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=0,
            use_archetype=True,
            devout_ward_cell=1,
        )
        state2 = apply_intent(state, intent, lookup, mock_rng(3))

        # P1 places at cell 4 — Plus should fire (sum 8 for both), but cell 1 is warded
        intent2 = PlacementIntent(
            player_index=1,
            card_key="p1card",
            cell_index=4,
            use_archetype=False,
        )
        state3 = apply_intent(state2, intent2, lookup, mock_rng(3))

        # Cell 1 stays P0-owned (warded), cell 3 captured by Plus
        assert state3.board[1] is not None
        assert state3.board[1].owner == 0, "Warded cell not captured by Plus"
        assert state3.board[3] is not None
        assert state3.board[3].owner == 1, "Non-warded cell captured by Plus"

    def test_warded_card_not_captured_by_combo_chain(self):
        """Warded card is immune to combo/BFS capture."""
        # P0 has cards at cell 1 and cell 2
        # P1 places at cell 4, captures cell 1 (not warded) via normal capture
        # Cell 1's capture triggers combo check against cell 2 (warded)
        friendly1 = make_card("f1", n=1, e=1, s=3, w=1)  # at cell 1, S=3 faces cell 4 N
        friendly2 = make_card("f2", n=1, e=1, s=1, w=3)  # at cell 2, W=3 faces cell 1's E=1... hmm
        # Combo: after capturing cell 1, the newly captured card checks its neighbors.
        # f1 at cell 1 has E=1. Cell 2's W=3. So f1.E=1 vs f2.W=3 → 1 < 3, no combo capture.
        # Let's flip: f1.E=5, f2.W=3 → 5 > 3, combo captures cell 2.
        friendly1 = make_card("f1", n=1, e=5, s=3, w=1)
        friendly2 = make_card("f2", n=1, e=1, s=1, w=3)
        attacker = make_card("attk", n=4, e=1, s=1, w=1)  # N=4 vs f1.S=3 → capture
        placed = make_card("placed", n=1, e=1, s=1, w=1)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="f1", owner=0)
        board[2] = BoardCell(card_key="f2", owner=0)
        lookup = {"f1": friendly1, "f2": friendly2, "attk": attacker, "placed": placed}

        # P0 places at cell 0, wards cell 2
        state = make_state(
            board=board,
            p0_hand=["placed"],
            p1_hand=["attk"],
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=0,
            use_archetype=True,
            devout_ward_cell=2,
        )
        state2 = apply_intent(state, intent, lookup, mock_rng(3))

        # P1 places at cell 4: captures f1 at cell 1 (4 > 3), combo tries cell 2 (warded)
        intent2 = PlacementIntent(
            player_index=1,
            card_key="attk",
            cell_index=4,
            use_archetype=False,
        )
        state3 = apply_intent(state2, intent2, lookup, mock_rng(3))

        assert state3.board[1] is not None
        assert state3.board[1].owner == 1, "Cell 1 captured normally"
        assert state3.board[2] is not None
        assert state3.board[2].owner == 0, "Warded cell 2 not captured by combo"

    def test_ward_expires_after_one_opponent_placement(self):
        """Ward clears after one opponent placement; card is capturable next turn."""
        friendly = make_card("friendly", n=1, e=1, s=2, w=1)
        opp1 = make_card("opp1", n=1, e=1, s=1, w=1)  # harmless
        attacker = make_card("attk", n=5, e=1, s=1, w=1)  # will capture friendly
        placed = make_card("placed", n=1, e=1, s=1, w=1)
        dummy = make_card("dummy", n=1, e=1, s=1, w=1)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="friendly", owner=0)
        lookup = {
            "friendly": friendly, "opp1": opp1, "attk": attacker,
            "placed": placed, "dummy": dummy,
        }

        # P0 places, wards cell 1
        state = make_state(
            board=board,
            p0_hand=["placed", "dummy"],
            p1_hand=["opp1", "attk"],
        )
        intent = PlacementIntent(
            player_index=0, card_key="placed", cell_index=0,
            use_archetype=True, devout_ward_cell=1,
        )
        state2 = apply_intent(state, intent, lookup, mock_rng(3))

        # P1 places somewhere harmless — ward consumed
        intent2 = PlacementIntent(
            player_index=1, card_key="opp1", cell_index=2, use_archetype=False,
        )
        state3 = apply_intent(state2, intent2, lookup, mock_rng(3))
        assert state3.warded_cell is None

        # P0 places dummy
        intent3 = PlacementIntent(
            player_index=0, card_key="dummy", cell_index=6, use_archetype=False,
        )
        state4 = apply_intent(state3, intent3, lookup, mock_rng(3))

        # P1 places attacker at cell 4, N=5 vs friendly S=2 → should capture now
        intent4 = PlacementIntent(
            player_index=1, card_key="attk", cell_index=4, use_archetype=False,
        )
        state5 = apply_intent(state4, intent4, lookup, mock_rng(3))

        assert state5.board[1] is not None
        assert state5.board[1].owner == 1, "Card capturable after ward expired"


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestDevoutWardValidation:
    def test_cannot_ward_empty_cell(self):
        placed = make_card("placed")
        state = make_state(p0_hand=["placed"])
        intent = PlacementIntent(
            player_index=0, card_key="placed", cell_index=0,
            use_archetype=True, devout_ward_cell=5,
        )
        with pytest.raises(ArchetypePowerArgumentError, match="empty"):
            apply_intent(state, intent, {"placed": placed}, mock_rng(3))

    def test_cannot_ward_opponent_card(self):
        opp = make_card("opp")
        placed = make_card("placed")
        board: list[BoardCell | None] = [None] * 9
        board[5] = BoardCell(card_key="opp", owner=1)
        state = make_state(board=board, p0_hand=["placed"], p1_hand=["opp"])
        intent = PlacementIntent(
            player_index=0, card_key="placed", cell_index=0,
            use_archetype=True, devout_ward_cell=5,
        )
        with pytest.raises(ArchetypePowerArgumentError, match="opponent"):
            apply_intent(state, intent, {"placed": placed, "opp": opp}, mock_rng(3))

    def test_cannot_ward_cell_being_placed_into(self):
        placed = make_card("placed")
        state = make_state(p0_hand=["placed"])
        intent = PlacementIntent(
            player_index=0, card_key="placed", cell_index=4,
            use_archetype=True, devout_ward_cell=4,
        )
        with pytest.raises(ArchetypePowerArgumentError, match="placed into"):
            apply_intent(state, intent, {"placed": placed}, mock_rng(3))

    def test_ward_cell_out_of_range(self):
        placed = make_card("placed")
        state = make_state(p0_hand=["placed"])
        intent = PlacementIntent(
            player_index=0, card_key="placed", cell_index=0,
            use_archetype=True, devout_ward_cell=9,
        )
        with pytest.raises(ArchetypePowerArgumentError, match="0-8"):
            apply_intent(state, intent, {"placed": placed}, mock_rng(3))

    def test_ward_cell_none_raises(self):
        """Devout requires devout_ward_cell to be specified."""
        placed = make_card("placed")
        state = make_state(p0_hand=["placed"])
        intent = PlacementIntent(
            player_index=0, card_key="placed", cell_index=0,
            use_archetype=True,
            # devout_ward_cell not set (None)
        )
        with pytest.raises(ArchetypePowerArgumentError, match="0-8"):
            apply_intent(state, intent, {"placed": placed}, mock_rng(3))


# ---------------------------------------------------------------------------
# Power consumption
# ---------------------------------------------------------------------------


class TestDevoutPowerConsumption:
    def test_devout_consumed_on_activation(self):
        """Power is consumed immediately, not conditionally."""
        friendly = make_card("friendly")
        placed = make_card("placed")
        board: list[BoardCell | None] = [None] * 9
        board[5] = BoardCell(card_key="friendly", owner=0)
        state = make_state(board=board, p0_hand=["placed"])
        intent = PlacementIntent(
            player_index=0, card_key="placed", cell_index=0,
            use_archetype=True, devout_ward_cell=5,
        )
        lookup = {"placed": placed, "friendly": friendly}
        next_state = apply_intent(state, intent, lookup, mock_rng(3))
        assert next_state.players[0].archetype_used is True

    def test_second_use_raises(self):
        placed = make_card("placed")
        state = make_state(p0_hand=["placed"], p0_archetype_used=True)
        intent = PlacementIntent(
            player_index=0, card_key="placed", cell_index=0,
            use_archetype=True, devout_ward_cell=5,
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state, intent, {"placed": placed}, mock_rng(3))

    def test_last_move_shows_warded_cell(self):
        """LastMoveInfo includes warded_cell for frontend highlight."""
        friendly = make_card("friendly")
        placed = make_card("placed")
        board: list[BoardCell | None] = [None] * 9
        board[5] = BoardCell(card_key="friendly", owner=0)
        state = make_state(board=board, p0_hand=["placed"])
        intent = PlacementIntent(
            player_index=0, card_key="placed", cell_index=0,
            use_archetype=True, devout_ward_cell=5,
        )
        next_state = apply_intent(
            state, intent, {"placed": placed, "friendly": friendly}, mock_rng(3)
        )
        assert next_state.last_move is not None
        assert next_state.last_move.warded_cell == 5
        assert next_state.last_move.archetype_used_name == "devout"
