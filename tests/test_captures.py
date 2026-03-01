"""Tests for US-003: placement + capture resolution."""

from app.models.cards import CardDefinition, CardSides
from app.models.game import BoardCell, GameState, GameStatus
from app.rules.captures import resolve_captures
from app.rules.reducer import PlacementIntent, apply_intent

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
    )


def make_state(board: list[BoardCell | None] | None = None) -> GameState:
    return GameState(
        game_id="test-game",
        status=GameStatus.ACTIVE,
        board=board if board is not None else [None] * 9,
    )


def rc(
    board: list[BoardCell | None],
    placed_index: int,
    placed_card: CardDefinition,
    placed_owner: int,
    lookup: dict[str, CardDefinition],
    mists_modifier: int = 0,
) -> list[BoardCell | None]:
    """Thin wrapper to keep call sites short."""
    result_board, _ = resolve_captures(
        board,
        placed_index=placed_index,
        placed_card=placed_card,
        placed_owner=placed_owner,
        card_lookup=lookup,
        mists_modifier=mists_modifier,
    )
    return result_board


# Board layout:
#  0 1 2
#  3 4 5
#  6 7 8


# ---------------------------------------------------------------------------
# resolve_captures: directional comparisons
# ---------------------------------------------------------------------------


class TestResolveCaptures:
    def test_east_capture(self):
        """Placed card at cell 1 captures cell 0 via E→W comparison."""
        # Card at cell 0: enemy, E side = 3
        enemy = make_card("enemy", n=5, e=3, s=5, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="enemy", owner=1)
        # Placed at cell 1 with W side = 7 > enemy's E side 3
        placed = make_card("strong", n=5, e=5, s=5, w=7)
        lookup = {"enemy": enemy, "strong": placed}

        result = rc(board, placed_index=1, placed_card=placed, placed_owner=0, lookup=lookup)

        assert result[0] is not None
        assert result[0].owner == 0, "Enemy at cell 0 should be captured"

    def test_west_capture(self):
        """Placed card at cell 1 captures cell 2 via W→E comparison."""
        enemy = make_card("enemy", n=5, e=5, s=5, w=3)
        board: list[BoardCell | None] = [None] * 9
        board[2] = BoardCell(card_key="enemy", owner=1)
        placed = make_card("strong", n=5, e=7, s=5, w=5)
        lookup = {"enemy": enemy, "strong": placed}

        result = rc(board, placed_index=1, placed_card=placed, placed_owner=0, lookup=lookup)

        assert result[2] is not None
        assert result[2].owner == 0, "Enemy at cell 2 should be captured"

    def test_south_capture(self):
        """Placed card at cell 1 captures cell 4 via S→N comparison."""
        enemy = make_card("enemy", n=2, e=5, s=5, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[4] = BoardCell(card_key="enemy", owner=1)
        placed = make_card("strong", n=5, e=5, s=9, w=5)
        lookup = {"enemy": enemy, "strong": placed}

        result = rc(board, placed_index=1, placed_card=placed, placed_owner=0, lookup=lookup)

        assert result[4] is not None
        assert result[4].owner == 0, "Enemy at cell 4 should be captured"

    def test_north_capture(self):
        """Placed card at cell 4 captures cell 1 via N→S comparison."""
        enemy = make_card("enemy", n=5, e=5, s=2, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="enemy", owner=1)
        placed = make_card("strong", n=9, e=5, s=5, w=5)
        lookup = {"enemy": enemy, "strong": placed}

        result = rc(board, placed_index=4, placed_card=placed, placed_owner=0, lookup=lookup)

        assert result[1] is not None
        assert result[1].owner == 0, "Enemy at cell 1 should be captured"

    def test_no_capture_on_tie(self):
        """Equal values do not trigger a capture."""
        enemy = make_card("enemy", n=5, e=5, s=5, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="enemy", owner=1)
        placed = make_card("weak", n=5, e=5, s=5, w=5)
        lookup = {"enemy": enemy, "weak": placed}

        result = rc(board, placed_index=1, placed_card=placed, placed_owner=0, lookup=lookup)

        assert result[0] is not None
        assert result[0].owner == 1, "Equal value should not capture"

    def test_no_capture_of_lower_value(self):
        """Weaker placed card does not capture a stronger neighbor."""
        enemy = make_card("strong_enemy", n=5, e=9, s=5, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="strong_enemy", owner=1)
        placed = make_card("weak", n=5, e=5, s=5, w=3)
        lookup = {"strong_enemy": enemy, "weak": placed}

        result = rc(board, placed_index=1, placed_card=placed, placed_owner=0, lookup=lookup)

        assert result[0] is not None
        assert result[0].owner == 1, "Weaker card should not capture"

    def test_no_capture_of_own_card(self):
        """Does not flip own cards even if the touching side is higher."""
        own = make_card("own", n=5, e=1, s=5, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="own", owner=0)
        placed = make_card("strong", n=5, e=5, s=5, w=9)
        lookup = {"own": own, "strong": placed}

        result = rc(board, placed_index=1, placed_card=placed, placed_owner=0, lookup=lookup)

        assert result[0] is not None
        assert result[0].owner == 0, "Own card should not be captured"

    def test_multiple_captures_in_one_placement(self):
        """A single placement can capture multiple adjacent enemy cards."""
        enemy_n = make_card("enemy_n", n=5, e=5, s=1, w=5)
        enemy_w = make_card("enemy_w", n=5, e=1, s=5, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="enemy_n", owner=1)
        board[3] = BoardCell(card_key="enemy_w", owner=1)
        placed = make_card("strong", n=8, e=5, s=5, w=8)
        lookup = {"enemy_n": enemy_n, "enemy_w": enemy_w, "strong": placed}

        result = rc(board, placed_index=4, placed_card=placed, placed_owner=0, lookup=lookup)

        assert result[1] is not None and result[1].owner == 0, "North enemy captured"
        assert result[3] is not None and result[3].owner == 0, "West enemy captured"

    def test_empty_adjacent_cells_ignored(self):
        """Placement in a corner with no neighbors only touches relevant sides."""
        board: list[BoardCell | None] = [None] * 9
        placed = make_card("card", n=5, e=5, s=5, w=5)
        lookup = {"card": placed}

        result = rc(board, placed_index=0, placed_card=placed, placed_owner=0, lookup=lookup)

        # No captures, no exceptions
        assert all(cell is None for cell in result)

    def test_mists_modifier_enables_capture(self):
        """Positive mists modifier can push placed side over the threshold."""
        # Without modifier: placed W=5 vs enemy E=5 → tie, no capture
        # With modifier +1: placed W=5+1=6 vs enemy E=5 → capture
        enemy = make_card("enemy", n=5, e=5, s=5, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="enemy", owner=1)
        placed = make_card("mid", n=5, e=5, s=5, w=5)
        lookup = {"enemy": enemy, "mid": placed}

        result = rc(
            board,
            placed_index=1,
            placed_card=placed,
            placed_owner=0,
            lookup=lookup,
            mists_modifier=1,
        )

        assert result[0] is not None
        assert result[0].owner == 0

    def test_mists_modifier_prevents_capture(self):
        """Negative mists modifier can suppress a capture."""
        # Without modifier: placed W=6 vs enemy E=5 → capture
        # With modifier -1: placed W=6-1=5 vs enemy E=5 → tie, no capture
        enemy = make_card("enemy", n=5, e=5, s=5, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="enemy", owner=1)
        placed = make_card("mid", n=5, e=5, s=5, w=6)
        lookup = {"enemy": enemy, "mid": placed}

        result = rc(
            board,
            placed_index=1,
            placed_card=placed,
            placed_owner=0,
            lookup=lookup,
            mists_modifier=-1,
        )

        assert result[0] is not None
        assert result[0].owner == 1

    def test_deterministic_outcome(self):
        """Same input always produces same output."""
        enemy = make_card("enemy", n=5, e=3, s=5, w=5)
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="enemy", owner=1)
        placed = make_card("strong", n=5, e=5, s=5, w=7)
        lookup = {"enemy": enemy, "strong": placed}

        result1 = rc(board, placed_index=1, placed_card=placed, placed_owner=0, lookup=lookup)
        result2 = rc(board, placed_index=1, placed_card=placed, placed_owner=0, lookup=lookup)

        assert result1[0] == result2[0]


# ---------------------------------------------------------------------------
# apply_intent: placement + capture via reducer
# ---------------------------------------------------------------------------


class TestApplyIntent:
    def test_places_card_on_board(self):
        """apply_intent places the card on the correct cell."""
        card = make_card("card_a", n=5, e=5, s=5, w=5)
        lookup = {"card_a": card}
        state = make_state()

        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=4)
        next_state = apply_intent(state, intent, card_lookup=lookup)

        assert next_state.board[4] is not None
        assert next_state.board[4].card_key == "card_a"
        assert next_state.board[4].owner == 0

    def test_captures_resolved_after_placement(self):
        """apply_intent resolves captures for the placed card."""
        enemy = make_card("enemy", n=5, e=3, s=5, w=5)
        placed_card = make_card("strong", n=5, e=5, s=5, w=7)
        lookup = {"enemy": enemy, "strong": placed_card}

        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="enemy", owner=1)
        state = make_state(board=board)

        intent = PlacementIntent(player_index=0, card_key="strong", cell_index=1)
        next_state = apply_intent(state, intent, card_lookup=lookup)

        assert next_state.board[0] is not None
        assert next_state.board[0].owner == 0, "Enemy should be captured"

    def test_state_version_increments(self):
        """apply_intent bumps state_version by 1."""
        card = make_card("card_a", n=5, e=5, s=5, w=5)
        lookup = {"card_a": card}
        state = make_state()
        assert state.state_version == 0

        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=0)
        next_state = apply_intent(state, intent, card_lookup=lookup)

        assert next_state.state_version == 1

    def test_original_state_unchanged(self):
        """apply_intent does not mutate the original state."""
        card = make_card("card_a", n=5, e=5, s=5, w=5)
        lookup = {"card_a": card}
        state = make_state()

        intent = PlacementIntent(player_index=0, card_key="card_a", cell_index=4)
        apply_intent(state, intent, card_lookup=lookup)

        assert state.board[4] is None, "Original state board must not be mutated"
