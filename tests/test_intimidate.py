"""Tests for US-UXP-016: Intimidate archetype — debuff opponent's facing side.

Intimidate power: after placing a card, choose one adjacent opponent card.
That card's facing side is replaced with min(n,e,s,w) for this comparison only.
Once per game per player.
"""

from unittest.mock import MagicMock

import pytest

from app.models.cards import CardDefinition, CardSides
from app.models.game import Archetype, BoardCell, GameState, GameStatus, PlayerState
from app.rules.errors import ArchetypeAlreadyUsedError, ArchetypePowerArgumentError
from app.rules.reducer import PlacementIntent, apply_intent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_card(
    key: str,
    n: int = 5,
    e: int = 5,
    s: int = 5,
    w: int = 5,
) -> CardDefinition:
    return CardDefinition(
        card_key=key,
        character_key=key,
        name=key,
        version="1.0",
        tier=1,
        rarity=50,
        is_named=False,
        sides=CardSides(n=n, e=e, s=s, w=w),
        set="test",
        element="shadow",
    )


def make_state(
    board: list[BoardCell | None] | None = None,
    p0_hand: list[str] | None = None,
    p1_hand: list[str] | None = None,
    p0_archetype: Archetype | None = Archetype.INTIMIDATE,
    p0_archetype_used: bool = False,
    p1_archetype: Archetype | None = None,
    current_player_index: int = 0,
) -> GameState:
    players = [
        PlayerState(
            player_id="p0",
            archetype=p0_archetype,
            hand=p0_hand or [],
            archetype_used=p0_archetype_used,
        ),
        PlayerState(
            player_id="p1",
            archetype=p1_archetype,
            hand=p1_hand or [],
        ),
    ]
    return GameState(
        game_id="test-game",
        status=GameStatus.ACTIVE,
        players=players,
        current_player_index=current_player_index,
        board=board if board is not None else [None] * 9,
    )


def mock_rng(*rolls: int) -> MagicMock:
    rng = MagicMock()
    rng.randint.side_effect = list(rolls)
    return rng


# ---------------------------------------------------------------------------
# Intimidate debuff behaviour
# ---------------------------------------------------------------------------


class TestIntimidateDebuff:
    def test_debuff_enables_capture(self):
        """Intimidate replaces neighbor's facing side with its min side, enabling capture.

        Setup: placed at cell 4, neighbor at cell 1 (north).
        Placed N=4, neighbor S=5 (would normally lose: 4 < 5).
        Neighbor sides: n=1, e=1, s=5, w=1 → min=1.
        With Intimidate on cell 1: neighbor's S becomes min=1 → 4 > 1 → capture.
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
            intimidate_target_cell=1,
        )
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor})

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Neighbor should be captured via Intimidate debuff"

    def test_debuff_only_affects_targeted_neighbor(self):
        """Intimidate only debuffs the targeted neighbor, not others.

        Placed at cell 4 with neighbors north (cell 1) and east (cell 5).
        Placed N=4, E=3.
        Cell 1 neighbor S=5, min=1. Intimidate targets cell 1: S becomes 1 → 4 > 1 → capture.
        Cell 5 neighbor W=5, not targeted → 3 < 5 → no capture.
        Sums differ (4+5=9 vs 3+5=8) so Plus rule does not fire.
        """
        placed = make_card("placed", n=4, e=3, s=1, w=1)
        neighbor_n = make_card("neighbor_n", n=1, e=1, s=5, w=1)
        neighbor_e = make_card("neighbor_e", n=1, e=1, s=1, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor_n", owner=1)
        board[5] = BoardCell(card_key="neighbor_e", owner=1)

        state = make_state(board=board, p0_hand=["placed"], p1_hand=["neighbor_n"])
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            intimidate_target_cell=1,
        )
        lookup = {
            "placed": placed,
            "neighbor_n": neighbor_n,
            "neighbor_e": neighbor_e,
        }
        next_state = apply_intent(state, intent, lookup)

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "North neighbor should be captured (intimidated)"
        assert next_state.board[5] is not None
        assert next_state.board[5].owner == 1, "East neighbor should NOT be captured (not targeted)"

    def test_without_intimidate_no_capture(self):
        """Control: same scenario without Intimidate — placed card loses."""
        placed = make_card("placed", n=4, e=1, s=1, w=1)
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
        assert next_state.board[1].owner == 1, "Without Intimidate: no capture (4 < 5)"

    def test_debuff_combined_with_mists_modifier(self):
        """Intimidate debuff and Mists modifier stack (Mists on placed card, debuff on neighbor).

        Placed at cell 4, neighbor at cell 1. Placed N=2, neighbor S=5, min=1.
        Fog roll (-2): placed side becomes 2-2=0. Intimidate debuffs neighbor S→1.
        0 < 1 → still no capture (Fog overwhelms).
        """
        placed = make_card("placed", n=2, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=5, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["placed"], p1_hand=["neighbor"])
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            intimidate_target_cell=1,
        )
        rng = mock_rng(1)  # Fog roll: -2
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor}, rng)

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 1, "Fog overwhelms Intimidate debuff: no capture"

    def test_debuff_with_omen_enables_capture(self):
        """Intimidate + Omen: placed side boosted, neighbor debuffed.

        Placed N=1, neighbor S=5, min=1. Omen (+2): placed becomes 1+2=3.
        Intimidate debuffs S→1. 3 > 1 → capture.
        """
        placed = make_card("placed", n=1, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=5, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["placed"], p1_hand=["neighbor"])
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            intimidate_target_cell=1,
        )
        rng = mock_rng(6)  # Omen roll: +2
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor}, rng)

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Omen + Intimidate: capture expected"

    def test_archetype_used_set_after_activation(self):
        placed = make_card("placed", n=1, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=5, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["placed"])
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            intimidate_target_cell=1,
        )
        next_state = apply_intent(
            state, intent, {"placed": placed, "neighbor": neighbor}
        )
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
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.players[0].archetype_used is False

    def test_opponent_archetype_used_unchanged(self):
        placed = make_card("placed", n=1, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=5, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(
            board=board,
            p0_hand=["placed"],
            p0_archetype=Archetype.INTIMIDATE,
            p1_archetype=Archetype.INTIMIDATE,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            intimidate_target_cell=1,
        )
        next_state = apply_intent(
            state, intent, {"placed": placed, "neighbor": neighbor}
        )
        assert next_state.players[1].archetype_used is False


# ---------------------------------------------------------------------------
# Validation: invalid targets
# ---------------------------------------------------------------------------


class TestIntimidateValidation:
    def test_missing_target_raises_error(self):
        """Intimidate with no target cell raises ArchetypePowerArgumentError."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            intimidate_target_cell=None,
        )
        with pytest.raises(ArchetypePowerArgumentError):
            apply_intent(state, intent, {"card_a": card})

    def test_invalid_cell_index_raises_error(self):
        """Intimidate with out-of-range target raises ArchetypePowerArgumentError."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            intimidate_target_cell=9,
        )
        with pytest.raises(ArchetypePowerArgumentError):
            apply_intent(state, intent, {"card_a": card})

    def test_non_adjacent_target_raises_error(self):
        """Intimidate targeting a non-adjacent cell raises ArchetypePowerArgumentError.

        Place at cell 0, target cell 8 (diagonal, not adjacent).
        """
        card = make_card("card_a")
        neighbor = make_card("neighbor")
        board: list[BoardCell | None] = [None] * 9
        board[8] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            intimidate_target_cell=8,
        )
        with pytest.raises(ArchetypePowerArgumentError, match="not adjacent"):
            apply_intent(state, intent, {"card_a": card, "neighbor": neighbor})

    def test_empty_target_cell_raises_error(self):
        """Intimidate targeting an empty cell raises ArchetypePowerArgumentError."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        # Cell 1 is adjacent to cell 0, but empty
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            intimidate_target_cell=1,
        )
        with pytest.raises(ArchetypePowerArgumentError, match="empty"):
            apply_intent(state, intent, {"card_a": card})

    def test_own_card_target_raises_error(self):
        """Intimidate targeting your own card raises ArchetypePowerArgumentError."""
        card = make_card("card_a")
        own_card = make_card("own_card")
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="own_card", owner=0)  # Player 0's card

        state = make_state(board=board, p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            intimidate_target_cell=1,
        )
        with pytest.raises(ArchetypePowerArgumentError, match="your own card"):
            apply_intent(state, intent, {"card_a": card, "own_card": own_card})


# ---------------------------------------------------------------------------
# Once-per-game enforcement
# ---------------------------------------------------------------------------


class TestIntimidateOncePerGame:
    def test_second_use_raises_archetype_already_used(self):
        placed = make_card("placed", n=1, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=5, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["placed"], p0_archetype_used=True)
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            intimidate_target_cell=1,
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state, intent, {"placed": placed, "neighbor": neighbor})

    def test_sequential_usage_rejected_on_second_call(self):
        placed_a = make_card("card_a", n=4, e=1, s=1, w=1)
        placed_b = make_card("card_b", n=4, e=1, s=1, w=1)
        dummy = make_card("dummy")
        neighbor_n = make_card("neighbor_n", n=1, e=1, s=5, w=1)
        neighbor_s = make_card("neighbor_s", n=5, e=1, s=1, w=1)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor_n", owner=1)

        state = make_state(
            board=board,
            p0_hand=["card_a", "card_b"],
            p1_hand=["dummy"],
            p0_archetype=Archetype.INTIMIDATE,
        )
        lookup = {
            "card_a": placed_a,
            "card_b": placed_b,
            "dummy": dummy,
            "neighbor_n": neighbor_n,
            "neighbor_s": neighbor_s,
        }

        # First use — should succeed
        intent1 = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=4,
            use_archetype=True,
            intimidate_target_cell=1,
        )
        state2 = apply_intent(state, intent1, lookup)

        # Player 1 takes a turn
        intent_p1 = PlacementIntent(
            player_index=1, card_key="dummy", cell_index=6, use_archetype=False
        )
        state3 = apply_intent(state2, intent_p1, lookup)

        # Place neighbor at cell 7 (south of cell 4) for second Intimidate attempt
        state3_board = list(state3.board)
        state3_board[7] = BoardCell(card_key="neighbor_s", owner=1)
        state3 = state3.model_copy(update={"board": state3_board})

        # Second use of Intimidate by player 0 — must fail
        intent2 = PlacementIntent(
            player_index=0,
            card_key="card_b",
            cell_index=8,
            use_archetype=True,
            intimidate_target_cell=7,
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state3, intent2, lookup)
