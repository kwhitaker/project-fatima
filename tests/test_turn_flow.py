"""Tests for US-005: turn flow and move validation.

The reducer must:
  - Reject a move from the wrong player (WrongPlayerTurnError)
  - Reject a card not in the player's hand (CardNotInHandError)
  - Reject placement on an occupied cell (OccupiedCellError)
  - Advance the turn after a legal placement
"""

import pytest

from app.models.game import BoardCell
from app.rules.errors import CardNotInHandError, OccupiedCellError, WrongPlayerTurnError
from app.rules.reducer import PlacementIntent, apply_intent
from tests.conftest import make_card, make_state

# ---------------------------------------------------------------------------
# Wrong-player-turn validation
# ---------------------------------------------------------------------------


class TestTurnValidation:
    def test_wrong_player_turn_rejected(self):
        """Reducer raises WrongPlayerTurnError when it is not the player's turn."""
        card = make_card("card_a")
        # current_player_index=0 but intent is from player 1
        state = make_state(p0_hand=[], p1_hand=["card_a"], current_player_index=0)
        intent = PlacementIntent(player_index=1, card_key="card_a", cell_index=0)
        with pytest.raises(WrongPlayerTurnError):
            apply_intent(state, intent, {"card_a": card})

    def test_correct_player_turn_accepted(self):
        """Reducer accepts a move from the correct player."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], current_player_index=0)
        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=0)
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.board[0] is not None

    def test_turn_advances_from_player0_to_player1(self):
        """After player 0 places, current_player_index becomes 1."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], current_player_index=0)
        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=0)
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.current_player_index == 1

    def test_turn_advances_from_player1_to_player0(self):
        """After player 1 places, current_player_index becomes 0."""
        card = make_card("card_b")
        state = make_state(p1_hand=["card_b"], current_player_index=1)
        intent = PlacementIntent(player_index=1, card_key="card_b", cell_index=0)
        next_state = apply_intent(state, intent, {"card_b": card})
        assert next_state.current_player_index == 0


# ---------------------------------------------------------------------------
# Card-not-in-hand validation
# ---------------------------------------------------------------------------


class TestHandValidation:
    def test_card_not_in_hand_rejected(self):
        """Reducer raises CardNotInHandError when the card is not in the player's hand."""
        card = make_card("card_a")
        state = make_state(p0_hand=[], current_player_index=0)
        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=0)
        with pytest.raises(CardNotInHandError):
            apply_intent(state, intent, {"card_a": card})

    def test_card_removed_from_hand_after_placement(self):
        """After placement, the played card is no longer in the player's hand."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a", "card_b"], current_player_index=0)
        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=0)
        next_state = apply_intent(state, intent, {"card_a": card})
        assert "card_a" not in next_state.players[0].hand

    def test_other_cards_remain_in_hand(self):
        """Other cards in the player's hand are unaffected by the placement."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a", "card_b"], current_player_index=0)
        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=0)
        next_state = apply_intent(state, intent, {"card_a": card})
        assert "card_b" in next_state.players[0].hand

    def test_opponent_hand_unchanged_after_placement(self):
        """The opponent's hand is unaffected by the other player's placement."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], p1_hand=["card_x"], current_player_index=0)
        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=0)
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.players[1].hand == ["card_x"]


# ---------------------------------------------------------------------------
# Occupied-cell validation
# ---------------------------------------------------------------------------


class TestOccupiedCellValidation:
    def test_occupied_cell_rejected(self):
        """Reducer raises OccupiedCellError when the target cell is already occupied."""
        card = make_card("card_a")
        existing = make_card("existing")
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="existing", owner=1)
        state = make_state(board=board, p0_hand=["card_a"], current_player_index=0)
        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=0)
        with pytest.raises(OccupiedCellError):
            apply_intent(state, intent, {"card_a": card, "existing": existing})

    def test_empty_cell_accepted(self):
        """Reducer accepts placement on an empty cell."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], current_player_index=0)
        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=4)
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.board[4] is not None


# ---------------------------------------------------------------------------
# Full placement flow
# ---------------------------------------------------------------------------


class TestFullPlacementFlow:
    def test_valid_placement_updates_all_state(self):
        """A legal placement updates the board, removes the card, and advances the turn."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], p1_hand=["card_b"], current_player_index=0)
        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=4)
        next_state = apply_intent(state, intent, {"card_a": card})

        assert next_state.board[4] is not None
        assert next_state.board[4].card_key == "card_a"
        assert next_state.board[4].owner == 0
        assert "card_a" not in next_state.players[0].hand
        assert next_state.current_player_index == 1
        assert next_state.state_version == state.state_version + 1

    def test_original_state_not_mutated(self):
        """apply_intent does not mutate the original GameState."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], current_player_index=0)
        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=0)
        apply_intent(state, intent, {"card_a": card})

        assert state.board[0] is None, "Original board must not be mutated"
        assert "card_a" in state.players[0].hand, "Original hand must not be mutated"
        assert state.current_player_index == 0, "Original turn index must not be mutated"
