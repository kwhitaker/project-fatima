"""Tests for US-004: Mists randomness modifier.

Each placement rolls 1d6:
  1 (Fog)  → -2 modifier on all comparisons
  6 (Omen) → +2 modifier on all comparisons
  2-5      → no modifier
"""

from random import Random
from unittest.mock import MagicMock

from app.models.cards import CardDefinition, CardSides
from app.models.game import BoardCell, GameState, GameStatus
from app.rules.reducer import PlacementIntent, apply_intent, mists_modifier_from_roll

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_card(key: str, n: int, e: int, s: int, w: int) -> CardDefinition:
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


def make_state(board: list[BoardCell | None] | None = None) -> GameState:
    return GameState(
        game_id="test-game",
        status=GameStatus.ACTIVE,
        board=board if board is not None else [None] * 9,
    )


# ---------------------------------------------------------------------------
# mists_modifier_from_roll: mapping from die result to comparison modifier
# ---------------------------------------------------------------------------


class TestMistsModifierFromRoll:
    def test_fog_roll_gives_minus_two(self):
        assert mists_modifier_from_roll(1) == -2

    def test_omen_roll_gives_plus_two(self):
        assert mists_modifier_from_roll(6) == 2

    def test_roll_two_is_neutral(self):
        assert mists_modifier_from_roll(2) == 0

    def test_roll_three_is_neutral(self):
        assert mists_modifier_from_roll(3) == 0

    def test_roll_four_is_neutral(self):
        assert mists_modifier_from_roll(4) == 0

    def test_roll_five_is_neutral(self):
        assert mists_modifier_from_roll(5) == 0


# ---------------------------------------------------------------------------
# apply_intent + Mists integration
# ---------------------------------------------------------------------------


class TestApplyIntentWithMists:
    def test_fog_suppresses_capture(self):
        """Roll=1 (Fog, -2) turns a would-be capture into a miss → no flip."""
        # placed W=6 vs enemy E=5: normally captures; with -2 → 6-2=4 < 5, no capture
        enemy = make_card("enemy", n=5, e=5, s=5, w=5)
        placed = make_card("near", n=5, e=5, s=5, w=6)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="enemy", owner=1)

        rng = MagicMock()
        rng.randint.return_value = 1  # Fog

        state = make_state(board=board)
        intent = PlacementIntent(player_index=0, card_key="near", cell_index=1)
        next_state = apply_intent(state, intent, {"enemy": enemy, "near": placed}, rng=rng)

        assert next_state.board[0] is not None
        assert next_state.board[0].owner == 1, "Fog suppressed the capture"

    def test_omen_enables_capture_from_tie(self):
        """Roll=6 (Omen, +2) pushes a tie over the threshold → capture."""
        # placed W=5 vs enemy E=5: normally a tie; with +2 → 5+2=7 > 5, capture
        enemy = make_card("enemy", n=5, e=5, s=5, w=5)
        placed = make_card("tie", n=5, e=5, s=5, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="enemy", owner=1)

        rng = MagicMock()
        rng.randint.return_value = 6  # Omen

        state = make_state(board=board)
        intent = PlacementIntent(player_index=0, card_key="tie", cell_index=1)
        next_state = apply_intent(state, intent, {"enemy": enemy, "tie": placed}, rng=rng)

        assert next_state.board[0] is not None
        assert next_state.board[0].owner == 0, "Omen enabled the capture"

    def test_neutral_roll_no_effect(self):
        """Roll=3 (neutral) leaves comparisons unchanged."""
        # placed W=6 vs enemy E=5: captures without modifier; also captures with 0 modifier
        enemy = make_card("enemy", n=5, e=5, s=5, w=5)
        placed = make_card("mid", n=5, e=5, s=5, w=6)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="enemy", owner=1)

        rng = MagicMock()
        rng.randint.return_value = 3  # neutral

        state = make_state(board=board)
        intent = PlacementIntent(player_index=0, card_key="mid", cell_index=1)
        next_state = apply_intent(state, intent, {"enemy": enemy, "mid": placed}, rng=rng)

        assert next_state.board[0] is not None
        assert next_state.board[0].owner == 0, "Normal capture proceeds unaffected"

    def test_all_neutral_rolls_produce_no_modifier(self):
        """Rolls 2-5 all leave comparisons unmodified (tie stays a tie)."""
        enemy = make_card("enemy", n=5, e=5, s=5, w=5)
        placed = make_card("tie", n=5, e=5, s=5, w=5)
        lookup = {"enemy": enemy, "tie": placed}

        for roll in (2, 3, 4, 5):
            board: list[BoardCell | None] = [None] * 9
            board[0] = BoardCell(card_key="enemy", owner=1)
            rng = MagicMock()
            rng.randint.return_value = roll

            state = make_state(board=board)
            intent = PlacementIntent(player_index=0, card_key="tie", cell_index=1)
            next_state = apply_intent(state, intent, lookup, rng=rng)

            assert next_state.board[0] is not None
            assert next_state.board[0].owner == 1, f"Roll={roll}: tie should not capture"

    def test_rng_randint_called_with_1_6(self):
        """apply_intent calls rng.randint(1, 6) exactly once per placement."""
        card = make_card("card", n=5, e=5, s=5, w=5)
        rng = MagicMock()
        rng.randint.return_value = 4

        state = make_state()
        intent = PlacementIntent(player_index=0, card_key="card", cell_index=0)
        apply_intent(state, intent, {"card": card}, rng=rng)

        rng.randint.assert_called_once_with(1, 6)

    def test_seeded_rng_gives_deterministic_outcome(self):
        """Same seed → same board result."""
        enemy = make_card("enemy", n=5, e=5, s=5, w=5)
        placed = make_card("mid", n=5, e=5, s=5, w=5)
        lookup = {"enemy": enemy, "mid": placed}

        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="enemy", owner=1)
        state = make_state(board=board)
        intent = PlacementIntent(player_index=0, card_key="mid", cell_index=1)

        result1 = apply_intent(state, intent, lookup, rng=Random(42))
        result2 = apply_intent(state, intent, lookup, rng=Random(42))

        assert result1.board == result2.board

    def test_no_rng_uses_zero_modifier(self):
        """When rng=None, modifier defaults to 0 (no Mists effect)."""
        # placed W=6 vs enemy E=5: should capture with modifier=0
        enemy = make_card("enemy", n=5, e=5, s=5, w=5)
        placed = make_card("near", n=5, e=5, s=5, w=6)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="enemy", owner=1)

        state = make_state(board=board)
        intent = PlacementIntent(player_index=0, card_key="near", cell_index=1)
        next_state = apply_intent(state, intent, {"enemy": enemy, "near": placed}, rng=None)

        assert next_state.board[0] is not None
        assert next_state.board[0].owner == 0, "No rng → no modifier → normal capture"
