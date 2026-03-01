"""Tests for US-GM-003: Plus rule — side-sum matching capture mechanic.

Board layout (row-major, 0-indexed):
  0 1 2
  3 4 5
  6 7 8

Plus rule: when placing a card, if 2+ adjacent opponent-owned cards each have
(placed card's attacking side value + that neighbor's defending side value) equal
to the same sum, all matching neighbors are captured immediately — regardless of
whether the placed side is greater. Sum uses raw printed values only (no Mists,
no elemental bonus).
"""

from random import Random

from app.models.cards import CardDefinition, CardSides
from app.models.game import BoardCell, GameState, GameStatus
from app.rules.captures import resolve_captures
from app.rules.reducer import PlacementIntent, apply_intent


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
    )


# ---------------------------------------------------------------------------
# resolve_captures: Plus rule pre-step
# ---------------------------------------------------------------------------


class TestPlusRule:
    def test_plus_triggers_two_matching_sums(self):
        """Plus fires when 2 adjacent opponent cards yield the same side-sum.

        Place at cell 4. Adjacency for cell 4:
          (1, "n", "s"), (3, "w", "e"), (5, "e", "w"), (7, "s", "n")

        placed.n=6, enemy1.s=7 → sum N: 6+7=13
        placed.w=3, enemy2.e=10 → sum W: 3+10=13
        Both sums equal 13 → Plus triggers; enemy1 and enemy2 captured.
        """
        placed = make_card("placed", n=6, e=5, s=5, w=3)
        enemy1 = make_card("enemy1", n=5, e=5, s=7, w=5)
        enemy2 = make_card("enemy2", n=5, e=10, s=5, w=5)

        board: list[BoardCell | None] = [None] * 9
        board[4] = BoardCell(card_key="placed", owner=0)
        board[1] = BoardCell(card_key="enemy1", owner=1)
        board[3] = BoardCell(card_key="enemy2", owner=1)

        lookup = {"placed": placed, "enemy1": enemy1, "enemy2": enemy2}
        new_board, plus_triggered = resolve_captures(board, 4, placed, 0, lookup)

        assert plus_triggered is True
        assert new_board[1] is not None and new_board[1].owner == 0, "enemy1 Plus-captured"
        assert new_board[3] is not None and new_board[3].owner == 0, "enemy2 Plus-captured"

    def test_plus_no_trigger_single_matching_pair(self):
        """Plus does NOT fire when only one adjacent sum (no second match).

        placed.n=6, enemy1.s=7 → sum N: 6+7=13
        placed.w=3, enemy2.e=9 → sum W: 3+9=12  (different)
        No matching pair → Plus does not fire.
        """
        placed = make_card("placed", n=6, e=5, s=5, w=3)
        enemy1 = make_card("enemy1", n=5, e=5, s=7, w=5)
        enemy2 = make_card("enemy2", n=5, e=9, s=5, w=5)

        board: list[BoardCell | None] = [None] * 9
        board[4] = BoardCell(card_key="placed", owner=0)
        board[1] = BoardCell(card_key="enemy1", owner=1)
        board[3] = BoardCell(card_key="enemy2", owner=1)

        lookup = {"placed": placed, "enemy1": enemy1, "enemy2": enemy2}
        new_board, plus_triggered = resolve_captures(board, 4, placed, 0, lookup)

        assert plus_triggered is False

    def test_plus_triggered_false_no_captures(self):
        """plus_triggered is False when no adjacent opponents at all."""
        placed = make_card("placed", n=6, e=5, s=5, w=3)
        board: list[BoardCell | None] = [None] * 9
        board[4] = BoardCell(card_key="placed", owner=0)

        lookup = {"placed": placed}
        _, plus_triggered = resolve_captures(board, 4, placed, 0, lookup)

        assert plus_triggered is False

    def test_plus_combo_chain_propagates(self):
        """Plus-captured cards trigger combo BFS with printed stats.

        Place at cell 0. Adjacency for cell 0: (1,"e","w"), (3,"s","n")
        placed.e=7, enemy1.w=6 → sum E: 7+6=13
        placed.s=3, enemy2.n=10 → sum S: 3+10=13
        Both match → Plus triggers; enemy1 and enemy2 captured.

        enemy1 (now owned by p0) is at cell 1. Its E=9 > enemy3.W=5 → combo capture at cell 2.
        """
        placed = make_card("placed", n=5, e=7, s=3, w=5)
        enemy1 = make_card("enemy1", n=5, e=9, s=5, w=6)
        enemy2 = make_card("enemy2", n=10, e=5, s=5, w=5)
        enemy3 = make_card("enemy3", n=5, e=5, s=5, w=5)

        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="placed", owner=0)
        board[1] = BoardCell(card_key="enemy1", owner=1)
        board[3] = BoardCell(card_key="enemy2", owner=1)
        board[2] = BoardCell(card_key="enemy3", owner=1)

        lookup = {"placed": placed, "enemy1": enemy1, "enemy2": enemy2, "enemy3": enemy3}
        new_board, plus_triggered = resolve_captures(board, 0, placed, 0, lookup)

        assert plus_triggered is True
        assert new_board[1] is not None and new_board[1].owner == 0, "enemy1 Plus-captured"
        assert new_board[3] is not None and new_board[3].owner == 0, "enemy2 Plus-captured"
        assert new_board[2] is not None and new_board[2].owner == 0, "enemy3 combo-captured via enemy1"

    def test_plus_and_standard_captures_coexist(self):
        """Plus captures some cells; standard comparison captures others.

        Place at cell 4.
        enemy1 at 1 and enemy3 at 3: sums match → Plus fires.
        enemy5 at 5: placed.e=8 > enemy5.w=5 → standard capture.
        enemy7 at 7: placed.s=2 not > enemy7.n=9 → no capture.
        """
        placed = make_card("placed", n=6, e=8, s=2, w=3)
        enemy1 = make_card("enemy1", n=5, e=5, s=7, w=5)  # sum N: 6+7=13
        enemy3 = make_card("enemy3", n=5, e=10, s=5, w=5)  # sum W: 3+10=13 → Plus
        enemy5 = make_card("enemy5", n=5, e=5, s=5, w=5)  # E: 8>5 → standard
        enemy7 = make_card("enemy7", n=9, e=5, s=5, w=5)  # S: 2<9 → no capture

        board: list[BoardCell | None] = [None] * 9
        board[4] = BoardCell(card_key="placed", owner=0)
        board[1] = BoardCell(card_key="enemy1", owner=1)
        board[3] = BoardCell(card_key="enemy3", owner=1)
        board[5] = BoardCell(card_key="enemy5", owner=1)
        board[7] = BoardCell(card_key="enemy7", owner=1)

        lookup = {
            "placed": placed,
            "enemy1": enemy1,
            "enemy3": enemy3,
            "enemy5": enemy5,
            "enemy7": enemy7,
        }
        new_board, plus_triggered = resolve_captures(board, 4, placed, 0, lookup)

        assert plus_triggered is True
        assert new_board[1] is not None and new_board[1].owner == 0, "Plus capture"
        assert new_board[3] is not None and new_board[3].owner == 0, "Plus capture"
        assert new_board[5] is not None and new_board[5].owner == 0, "Standard capture"
        assert new_board[7] is not None and new_board[7].owner == 1, "Not captured"

    def test_plus_ignores_mists_modifier_in_sum(self):
        """Mists modifier does not affect Plus sum calculation.

        Two cells with matching raw sums → Plus fires even with negative mists_modifier
        that would prevent standard capture of those cells.
        """
        placed = make_card("placed", n=6, e=5, s=5, w=3)
        enemy1 = make_card("enemy1", n=5, e=5, s=7, w=5)  # raw sum N: 6+7=13
        enemy2 = make_card("enemy2", n=5, e=10, s=5, w=5)  # raw sum W: 3+10=13

        board: list[BoardCell | None] = [None] * 9
        board[4] = BoardCell(card_key="placed", owner=0)
        board[1] = BoardCell(card_key="enemy1", owner=1)
        board[3] = BoardCell(card_key="enemy2", owner=1)

        lookup = {"placed": placed, "enemy1": enemy1, "enemy2": enemy2}
        # mists_modifier=-2 would suppress standard comparison (6-2=4, not > 7), but Plus uses raw
        new_board, plus_triggered = resolve_captures(
            board, 4, placed, 0, lookup, mists_modifier=-2
        )

        assert plus_triggered is True
        assert new_board[1] is not None and new_board[1].owner == 0, "Plus still captures"
        assert new_board[3] is not None and new_board[3].owner == 0, "Plus still captures"

    def test_plus_capture_does_not_need_attacker_to_win_comparison(self):
        """Plus captures even when placed card's side is LOWER than the defender's.

        placed.n=3, enemy1.s=7 → standard: 3 not > 7, no capture.
        placed.w=2, enemy2.e=8 → standard: 2 not > 8, no capture.
        But raw sums: 3+7=10 and 2+8=10 → Plus fires, both captured anyway.
        """
        placed = make_card("placed", n=3, e=5, s=5, w=2)
        enemy1 = make_card("enemy1", n=5, e=5, s=7, w=5)
        enemy2 = make_card("enemy2", n=5, e=8, s=5, w=5)

        board: list[BoardCell | None] = [None] * 9
        board[4] = BoardCell(card_key="placed", owner=0)
        board[1] = BoardCell(card_key="enemy1", owner=1)
        board[3] = BoardCell(card_key="enemy2", owner=1)

        lookup = {"placed": placed, "enemy1": enemy1, "enemy2": enemy2}
        new_board, plus_triggered = resolve_captures(board, 4, placed, 0, lookup)

        assert plus_triggered is True
        assert new_board[1] is not None and new_board[1].owner == 0
        assert new_board[3] is not None and new_board[3].owner == 0

    def test_plus_only_captures_opponent_cells(self):
        """Plus does not flip cells owned by the placing player."""
        placed = make_card("placed", n=6, e=5, s=5, w=3)
        # Same sums as the trigger test, but one cell is owned by placed_owner (0)
        own_card = make_card("own", n=5, e=5, s=7, w=5)  # would sum 13 if owned by p1
        enemy2 = make_card("enemy2", n=5, e=10, s=5, w=5)

        board: list[BoardCell | None] = [None] * 9
        board[4] = BoardCell(card_key="placed", owner=0)
        board[1] = BoardCell(card_key="own", owner=0)  # own card — not a Plus candidate
        board[3] = BoardCell(card_key="enemy2", owner=1)  # only one opponent → no Plus

        lookup = {"placed": placed, "own": own_card, "enemy2": enemy2}
        new_board, plus_triggered = resolve_captures(board, 4, placed, 0, lookup)

        assert plus_triggered is False
        assert new_board[1].owner == 0, "Own card unchanged"

    def test_plus_triggered_in_last_move_via_apply_intent(self):
        """plus_triggered=True is recorded in last_move when Plus fires via apply_intent."""
        placed = make_card("placed", n=6, e=5, s=5, w=3)
        enemy1 = make_card("enemy1", n=5, e=5, s=7, w=5)
        enemy2 = make_card("enemy2", n=5, e=10, s=5, w=5)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="enemy1", owner=1)
        board[3] = BoardCell(card_key="enemy2", owner=1)

        state = GameState(game_id="test", status=GameStatus.ACTIVE, board=board)
        intent = PlacementIntent(player_index=0, card_key="placed", cell_index=4)
        lookup = {"placed": placed, "enemy1": enemy1, "enemy2": enemy2}

        next_state = apply_intent(state, intent, card_lookup=lookup, rng=Random(42))

        assert next_state.last_move is not None
        assert next_state.last_move.plus_triggered is True

    def test_plus_not_triggered_in_last_move_via_apply_intent(self):
        """plus_triggered=False is recorded in last_move when Plus does not fire."""
        placed = make_card("placed", n=6, e=8, s=5, w=3)
        # Only one adjacent opponent (no match needed)
        enemy1 = make_card("enemy1", n=5, e=5, s=7, w=5)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="enemy1", owner=1)

        state = GameState(game_id="test", status=GameStatus.ACTIVE, board=board)
        intent = PlacementIntent(player_index=0, card_key="placed", cell_index=4)
        lookup = {"placed": placed, "enemy1": enemy1}

        next_state = apply_intent(state, intent, card_lookup=lookup, rng=Random(99))

        assert next_state.last_move is not None
        assert next_state.last_move.plus_triggered is False

    def test_plus_default_false_on_deserialization(self):
        """Existing LastMoveInfo snapshots without plus_triggered deserialize with False."""
        from app.models.game import LastMoveInfo

        lm = LastMoveInfo.model_validate(
            {
                "player_index": 0,
                "card_key": "card_a",
                "cell_index": 4,
                "mists_roll": 3,
                "mists_effect": "none",
                # no plus_triggered field — simulates old snapshot
            }
        )
        assert lm.plus_triggered is False

    def test_plus_three_way_match(self):
        """Plus fires (and captures all 3) when three adjacent cells share the same sum."""
        # Place at cell 4: adjacency has cells 1 (N), 3 (W), 5 (E), 7 (S)
        # Use three opponents with same sum; placed.n=5, placed.w=5, placed.e=5
        # enemy at 1: s=8 → sum N: 5+8=13
        # enemy at 3: e=8 → sum W: 5+8=13
        # enemy at 5: w=8 → sum E: 5+8=13
        placed = make_card("placed", n=5, e=5, s=5, w=5)
        enemy1 = make_card("enemy1", n=5, e=5, s=8, w=5)
        enemy3 = make_card("enemy3", n=5, e=8, s=5, w=5)
        enemy5 = make_card("enemy5", n=5, e=5, s=5, w=8)

        board: list[BoardCell | None] = [None] * 9
        board[4] = BoardCell(card_key="placed", owner=0)
        board[1] = BoardCell(card_key="enemy1", owner=1)
        board[3] = BoardCell(card_key="enemy3", owner=1)
        board[5] = BoardCell(card_key="enemy5", owner=1)

        lookup = {
            "placed": placed,
            "enemy1": enemy1,
            "enemy3": enemy3,
            "enemy5": enemy5,
        }
        new_board, plus_triggered = resolve_captures(board, 4, placed, 0, lookup)

        assert plus_triggered is True
        assert new_board[1] is not None and new_board[1].owner == 0
        assert new_board[3] is not None and new_board[3].owner == 0
        assert new_board[5] is not None and new_board[5].owner == 0
