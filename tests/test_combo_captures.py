"""Tests for US-029: chain/combo capture resolution.

Board layout (row-major, 0-indexed):
  0 1 2
  3 4 5
  6 7 8
"""

from app.models.cards import CardDefinition, CardSides
from app.models.game import BoardCell
from app.rules.captures import resolve_captures


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


class TestComboCaptures:
    def test_basic_two_step_combo(self):
        """Placed card captures B, then B (now owned) captures C via combo.

        Board row 0: [A(p0), B(p1), C(p1)]
        A: e=9 beats B's w=3 → initial capture
        B: e=8 beats C's w=2 → combo capture
        """
        card_a = make_card("a", n=5, e=9, s=5, w=5)
        card_b = make_card("b", n=5, e=8, s=5, w=3)
        card_c = make_card("c", n=5, e=5, s=5, w=2)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="b", owner=1)
        board[2] = BoardCell(card_key="c", owner=1)

        lookup = {"a": card_a, "b": card_b, "c": card_c}

        result, _ = resolve_captures(
            board,
            placed_index=0,
            placed_card=card_a,
            placed_owner=0,
            card_lookup=lookup,
        )

        assert result[1] is not None and result[1].owner == 0, "B captured by initial"
        assert result[2] is not None and result[2].owner == 0, "C captured via combo"

    def test_three_step_combo_chain(self):
        """Combo propagates three levels deep: A→B, B→C, C→D.

        Board:  [A(p0), B(p1), C(p1)]
                [  _  ,   _ , D(p1)]
        A: e=9 beats B's w=3
        B: e=9 beats C's w=3
        C: s=9 beats D's n=3
        """
        card_a = make_card("a", n=5, e=9, s=5, w=5)
        card_b = make_card("b", n=5, e=9, s=5, w=3)
        card_c = make_card("c", n=5, e=5, s=9, w=3)
        card_d = make_card("d", n=3, e=5, s=5, w=5)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="b", owner=1)
        board[2] = BoardCell(card_key="c", owner=1)
        board[5] = BoardCell(card_key="d", owner=1)

        lookup = {"a": card_a, "b": card_b, "c": card_c, "d": card_d}

        result, _ = resolve_captures(
            board,
            placed_index=0,
            placed_card=card_a,
            placed_owner=0,
            card_lookup=lookup,
        )

        assert result[1] is not None and result[1].owner == 0, "B captured (step 1)"
        assert result[2] is not None and result[2].owner == 0, "C captured (step 2 combo)"
        assert result[5] is not None and result[5].owner == 0, "D captured (step 3 combo)"

    def test_no_combo_when_initial_placement_fails_to_capture(self):
        """If the initial placement does not capture any card, no combo occurs."""
        card_a = make_card("a", n=5, e=3, s=5, w=5)  # e=3, too weak
        card_b = make_card("b", n=5, e=9, s=5, w=5)  # w=5 > placed e=3
        card_c = make_card("c", n=5, e=5, s=5, w=2)  # would be easy to combo-capture

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="b", owner=1)
        board[2] = BoardCell(card_key="c", owner=1)

        lookup = {"a": card_a, "b": card_b, "c": card_c}

        result, _ = resolve_captures(
            board,
            placed_index=0,
            placed_card=card_a,
            placed_owner=0,
            card_lookup=lookup,
        )

        assert result[1] is not None and result[1].owner == 1, "B not captured (weak initial)"
        assert result[2] is not None and result[2].owner == 1, "C not captured either"

    def test_mists_modifier_not_applied_to_combo_captures(self):
        """Mists modifier applies only to the initial placement; combos use printed stats.

        A: e=5, mists=+1 → effective east=6 > B's west=5 → initial capture
        B: printed e=4 vs C's printed w=4 → tie, NO combo capture
        If modifier was incorrectly applied to combo: B's e=5 > C's w=4 → wrong capture
        """
        card_a = make_card("a", n=5, e=5, s=5, w=5)
        card_b = make_card("b", n=5, e=4, s=5, w=5)
        card_c = make_card("c", n=5, e=5, s=5, w=4)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="b", owner=1)
        board[2] = BoardCell(card_key="c", owner=1)

        lookup = {"a": card_a, "b": card_b, "c": card_c}

        result, _ = resolve_captures(
            board,
            placed_index=0,
            placed_card=card_a,
            placed_owner=0,
            card_lookup=lookup,
            mists_modifier=1,
        )

        assert result[1] is not None and result[1].owner == 0, "B captured (5+1=6 > 5)"
        # Combo uses printed stats: B.e=4 == C.w=4, tie → no capture
        assert result[2] is not None
        assert result[2].owner == 1, "C not captured (no modifier in combo)"

    def test_presence_direction_not_applied_to_combo_captures(self):
        """Presence +1 applies only to the initial placement; combos use printed stats.

        A: e=5 + presence(e) +1 = 6 > B's w=5 → initial capture
        B: printed e=5 vs C's printed w=5 → tie, NO combo capture
        If presence were applied to combo: B's e=6 > C's w=5 → wrong capture
        """
        card_a = make_card("a", n=5, e=5, s=5, w=5)
        card_b = make_card("b", n=5, e=5, s=5, w=5)
        card_c = make_card("c", n=5, e=5, s=5, w=5)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="b", owner=1)
        board[2] = BoardCell(card_key="c", owner=1)

        lookup = {"a": card_a, "b": card_b, "c": card_c}

        result, _ = resolve_captures(
            board,
            placed_index=0,
            placed_card=card_a,
            placed_owner=0,
            card_lookup=lookup,
            presence_direction="e",
        )

        assert result[1] is not None and result[1].owner == 0, "B captured (presence: 5+1=6 > 5)"
        # Combo uses printed stats: B.e=5 == C.w=5, tie → no capture
        assert result[2] is not None
        assert result[2].owner == 1, "C not captured (no presence in combo)"

    def test_combo_does_not_recapture_own_cards(self):
        """Combo resolution never flips cards already owned by the placing player."""
        card_a = make_card("a", n=5, e=9, s=5, w=5)
        card_b = make_card("b", n=5, e=1, s=5, w=3)  # weak east — captured by A
        card_own = make_card("own", n=5, e=5, s=5, w=5)  # owned by player 0 at position 2

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="b", owner=1)
        board[2] = BoardCell(card_key="own", owner=0)  # already owned by player 0

        lookup = {"a": card_a, "b": card_b, "own": card_own}

        result, _ = resolve_captures(
            board,
            placed_index=0,
            placed_card=card_a,
            placed_owner=0,
            card_lookup=lookup,
        )

        assert result[1] is not None and result[1].owner == 0, "B captured by initial"
        # B (now player 0) has east=1 vs own's west=5 → no capture; owner check fires first
        assert result[2] is not None and result[2].owner == 0, "Own card stays owned by player 0"

    def test_multi_branch_combo(self):
        """Initial card captures two cards; each may trigger further combo captures.

        Board row 0: [A(p0), B(p1), C(p1)]
        Board row 1: [D(p1),   _  ,   _  ]
        A: e=9 captures B, s=9 captures D
        B: e=8 captures C (combo from B)
        D has no further capturable neighbors
        """
        card_a = make_card("a", n=5, e=9, s=9, w=5)
        card_b = make_card("b", n=5, e=8, s=5, w=3)
        card_c = make_card("c", n=5, e=5, s=5, w=2)
        card_d = make_card("d", n=3, e=5, s=5, w=5)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="b", owner=1)
        board[2] = BoardCell(card_key="c", owner=1)
        board[3] = BoardCell(card_key="d", owner=1)

        lookup = {"a": card_a, "b": card_b, "c": card_c, "d": card_d}

        result, _ = resolve_captures(
            board,
            placed_index=0,
            placed_card=card_a,
            placed_owner=0,
            card_lookup=lookup,
        )

        assert result[1] is not None and result[1].owner == 0, "B captured (initial east)"
        assert result[2] is not None and result[2].owner == 0, "C captured (combo from B)"
        assert result[3] is not None and result[3].owner == 0, "D captured (initial south)"

    def test_combo_is_deterministic(self):
        """Same input always produces the same combo output."""
        card_a = make_card("a", n=5, e=9, s=5, w=5)
        card_b = make_card("b", n=5, e=9, s=5, w=3)
        card_c = make_card("c", n=5, e=5, s=5, w=3)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="b", owner=1)
        board[2] = BoardCell(card_key="c", owner=1)

        lookup = {"a": card_a, "b": card_b, "c": card_c}

        result1, _ = resolve_captures(
            board, placed_index=0, placed_card=card_a, placed_owner=0, card_lookup=lookup
        )
        result2, _ = resolve_captures(
            board, placed_index=0, placed_card=card_a, placed_owner=0, card_lookup=lookup
        )

        assert result1 == result2, "Combo resolution must be deterministic"

    def test_combo_via_apply_intent(self):
        """Combo resolution works end-to-end through apply_intent (reducer)."""
        from app.models.game import GameState, GameStatus
        from app.rules.reducer import PlacementIntent, apply_intent

        card_a = make_card("a", n=5, e=9, s=5, w=5)
        card_b = make_card("b", n=5, e=8, s=5, w=3)
        card_c = make_card("c", n=5, e=5, s=5, w=2)

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="b", owner=1)
        board[2] = BoardCell(card_key="c", owner=1)

        state = GameState(
            game_id="test",
            status=GameStatus.ACTIVE,
            board=board,
        )
        lookup = {"a": card_a, "b": card_b, "c": card_c}
        intent = PlacementIntent(player_index=0, card_key="a", cell_index=0)

        next_state = apply_intent(state, intent, card_lookup=lookup)

        assert next_state.board[0] is not None and next_state.board[0].owner == 0, "A placed"
        assert next_state.board[1] is not None and next_state.board[1].owner == 0, "B captured"
        assert next_state.board[2] is not None
        assert next_state.board[2].owner == 0, "C captured via combo"
