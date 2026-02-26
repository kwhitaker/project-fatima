"""Tests for US-010: Presence archetype single-comparison boost.

Presence power: choose one adjacent direction (n/e/s/w) and get +1 only for
that single comparison this placement. Once per game per player.
Applied as +1 to the placed card's side value for the chosen direction before
evaluating capture (notes: "Default: applied as +1 to placed side value for
the chosen comparison before evaluating capture.")
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
    )


def make_state(
    board: list[BoardCell | None] | None = None,
    p0_hand: list[str] | None = None,
    p1_hand: list[str] | None = None,
    p0_archetype: Archetype | None = Archetype.PRESENCE,
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
# Single-comparison boost behaviour
# ---------------------------------------------------------------------------


class TestPresenceBoost:
    def test_boost_in_chosen_direction_enables_capture(self):
        """Presence +1 in north direction converts a tie into a capture.

        Setup: placed N=5 vs neighbor S=5. Without boost: 5 == 5 → no capture.
        With Presence north boost: 5+1=6 > 5 → capture.
        Board: neighbor at cell 1 (north of cell 4), placed at cell 4.
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
            presence_boost_direction="n",
        )
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor})

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Neighbor north should be captured"

    def test_boost_only_in_chosen_direction_not_others(self):
        """Presence +1 applies only to the chosen direction; other comparisons unaffected.

        Placed at cell 4 with neighbors to the north (cell 1) and east (cell 5).
        placed N=5, E=5 vs neighbor_n S=5 and neighbor_e W=5.
        Boost direction = "n": north gets +1 (5+1=6 > 5 → capture), east stays 5 == 5 (no capture).
        """
        placed = make_card("placed", n=5, e=5, s=1, w=1)
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
            presence_boost_direction="n",
        )
        lookup = {
            "placed": placed,
            "neighbor_n": neighbor_n,
            "neighbor_e": neighbor_e,
        }
        next_state = apply_intent(state, intent, lookup)

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "North neighbor should be captured (boosted)"
        assert next_state.board[5] is not None
        assert next_state.board[5].owner == 1, "East neighbor should NOT be captured (no boost)"

    def test_boost_in_east_direction(self):
        """Presence works correctly for the east direction.

        placed E=5 vs neighbor_e W=5. Boost "e": 5+1=6 > 5 → capture.
        Board: placed at cell 3, east neighbor at cell 4.
        """
        placed = make_card("placed", n=1, e=5, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=1, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[4] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["placed"], p1_hand=["neighbor"])
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=3,
            use_archetype=True,
            presence_boost_direction="e",
        )
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor})

        assert next_state.board[4] is not None
        assert next_state.board[4].owner == 0, "East neighbor should be captured"

    def test_boost_without_presence_no_capture(self):
        """Control: same scenario without Presence — tie means no capture."""
        placed = make_card("placed", n=5, e=1, s=1, w=1)
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
        assert next_state.board[1].owner == 1, "Tie without Presence: no capture"

    def test_missing_direction_raises_argument_error(self):
        """Presence with no direction argument raises ArchetypePowerArgumentError."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            presence_boost_direction=None,
        )
        with pytest.raises(ArchetypePowerArgumentError):
            apply_intent(state, intent, {"card_a": card})

    def test_invalid_direction_raises_argument_error(self):
        """Presence with invalid direction raises ArchetypePowerArgumentError."""
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            presence_boost_direction="x",
        )
        with pytest.raises(ArchetypePowerArgumentError):
            apply_intent(state, intent, {"card_a": card})

    def test_boost_combined_with_mists_modifier(self):
        """Presence +1 and mists_modifier stack on the chosen direction.

        placed N=5 vs neighbor S=7. Omen roll (+1) + Presence north (+1):
        5+1+1=7 == 7 → no capture (strict >).
        Increase placed N to 6: 6+1+1=8 > 7 → capture.
        """
        placed = make_card("placed", n=6, e=1, s=1, w=1)
        neighbor = make_card("neighbor", n=1, e=1, s=7, w=1)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="neighbor", owner=1)

        state = make_state(board=board, p0_hand=["placed"], p1_hand=["neighbor"])
        intent = PlacementIntent(
            player_index=0,
            card_key="placed",
            cell_index=4,
            use_archetype=True,
            presence_boost_direction="n",
        )
        rng = mock_rng(6)  # Omen roll: +1
        next_state = apply_intent(state, intent, {"placed": placed, "neighbor": neighbor}, rng)

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Presence + Omen combined: capture expected"

    def test_archetype_used_set_after_presence_activation(self):
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"])
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            presence_boost_direction="n",
        )
        next_state = apply_intent(state, intent, {"card_a": card})
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
        card = make_card("card_a")
        state = make_state(
            p0_hand=["card_a"],
            p0_archetype=Archetype.PRESENCE,
            p1_archetype=Archetype.PRESENCE,
        )
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            presence_boost_direction="n",
        )
        next_state = apply_intent(state, intent, {"card_a": card})
        assert next_state.players[1].archetype_used is False


# ---------------------------------------------------------------------------
# Once-per-game enforcement
# ---------------------------------------------------------------------------


class TestPresenceOncePerGame:
    def test_second_use_raises_archetype_already_used(self):
        card = make_card("card_a")
        state = make_state(p0_hand=["card_a"], p0_archetype_used=True)
        intent = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            presence_boost_direction="n",
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state, intent, {"card_a": card})

    def test_sequential_usage_is_rejected_on_second_call(self):
        card_a = make_card("card_a")
        card_b = make_card("card_b")
        dummy = make_card("dummy")
        state = make_state(
            p0_hand=["card_a", "card_b"],
            p1_hand=["dummy"],
            p0_archetype=Archetype.PRESENCE,
        )
        lookup = {"card_a": card_a, "card_b": card_b, "dummy": dummy}

        # First use — should succeed
        intent1 = PlacementIntent(
            player_index=0,
            card_key="card_a",
            cell_index=0,
            use_archetype=True,
            presence_boost_direction="n",
        )
        state2 = apply_intent(state, intent1, lookup)

        # Player 1 takes a turn
        intent_p1 = PlacementIntent(
            player_index=1, card_key="dummy", cell_index=1, use_archetype=False
        )
        state3 = apply_intent(state2, intent_p1, lookup)

        # Second use of Presence by player 0 — must fail
        intent2 = PlacementIntent(
            player_index=0,
            card_key="card_b",
            cell_index=2,
            use_archetype=True,
            presence_boost_direction="s",
        )
        with pytest.raises(ArchetypeAlreadyUsedError):
            apply_intent(state3, intent2, lookup)
