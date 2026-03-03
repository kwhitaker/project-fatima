"""Tests for US-UXP-023: auto-complete statistically decided games.

When one player owns enough cells that the opponent cannot reach majority (5+)
even by capturing all remaining cells, the game ends early with early_finish=True.
"""

from app.models.cards import CardDefinition, CardSides
from app.models.game import BoardCell, GameState, GameStatus, PlayerState
from app.rules.reducer import PlacementIntent, apply_intent


def make_card(key: str, n: int = 1, e: int = 1, s: int = 1, w: int = 1) -> CardDefinition:
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


def cell(key: str, owner: int) -> BoardCell:
    return BoardCell(card_key=key, owner=owner)


# Cards with low sides so no captures happen (all 1s)
CARDS = {f"c{i}": make_card(f"c{i}") for i in range(10)}


def _make_state(board: list[BoardCell | None], current_player: int = 0) -> GameState:
    """Build an ACTIVE game state with two players and the given board."""
    # Figure out which cards are on the board and which remain in hand
    p0_on_board = [b.card_key for b in board if b is not None and b.owner == 0]
    p1_on_board = [b.card_key for b in board if b is not None and b.owner == 1]
    all_keys = [f"c{i}" for i in range(10)]
    # Assign first 5 keys to p0, next 5 to p1 as starting hands
    p0_hand = [k for k in all_keys[:5] if k not in p0_on_board]
    p1_hand = [k for k in all_keys[5:] if k not in p1_on_board]
    return GameState(
        game_id="test-early",
        status=GameStatus.ACTIVE,
        players=[
            PlayerState(player_id="p0", hand=p0_hand),
            PlayerState(player_id="p1", hand=p1_hand),
        ],
        board=board,
        current_player_index=current_player,
        seed=42,
    )


class TestEarlyFinish:
    def test_no_early_finish_normal_game(self):
        """A normal placement with no clinch doesn't trigger early finish."""
        # Board: 2 cells for p0, 2 for p1, 5 empty — no one is close to clinching
        board: list[BoardCell | None] = [
            cell("c0", 0),
            cell("c1", 0),
            None,
            cell("c5", 1),
            cell("c6", 1),
            None,
            None,
            None,
            None,
        ]
        state = _make_state(board, current_player=0)
        result = apply_intent(
            state, PlacementIntent(player_index=0, card_key="c2", cell_index=2), CARDS
        )
        assert result.status == GameStatus.ACTIVE
        assert result.result is None

    def test_early_finish_p0_clinches(self):
        """P0 owns 6 cells with 1 empty → 6 >= 5+1 → clinched."""
        # p0 has 5 cells, p1 has 2, 2 empty. p0 places → 6 owned, 1 empty.
        # 6 >= 5 + 1 = 6 → clinched!
        board: list[BoardCell | None] = [
            cell("c0", 0),
            cell("c1", 0),
            cell("c2", 0),
            cell("c3", 0),
            cell("c4", 0),
            cell("c5", 1),
            cell("c6", 1),
            None,
            None,
        ]
        # p0 needs a card not on board — use c9 (we'll add to hand)
        state = GameState(
            game_id="test-early",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["c8"]),
                PlayerState(player_id="p1", hand=["c9"]),
            ],
            board=board,
            current_player_index=0,
            seed=42,
        )
        extra_cards = {**CARDS, "c8": make_card("c8"), "c9": make_card("c9")}
        result = apply_intent(
            state, PlacementIntent(player_index=0, card_key="c8", cell_index=7), extra_cards
        )
        assert result.status == GameStatus.COMPLETE
        assert result.result is not None
        assert result.result.winner == 0
        assert result.result.early_finish is True
        assert result.result.is_draw is False

    def test_early_finish_p1_clinches(self):
        """Player 1 clinches when they own enough cells."""
        board: list[BoardCell | None] = [
            cell("c0", 1),
            cell("c1", 1),
            cell("c2", 1),
            cell("c3", 1),
            cell("c4", 1),
            cell("c5", 0),
            cell("c6", 0),
            None,
            None,
        ]
        state = GameState(
            game_id="test-early",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["c8"]),
                PlayerState(player_id="p1", hand=["c9"]),
            ],
            board=board,
            current_player_index=1,
            seed=42,
        )
        extra_cards = {**CARDS, "c8": make_card("c8"), "c9": make_card("c9")}
        result = apply_intent(
            state, PlacementIntent(player_index=1, card_key="c9", cell_index=7), extra_cards
        )
        assert result.status == GameStatus.COMPLETE
        assert result.result is not None
        assert result.result.winner == 1
        assert result.result.early_finish is True

    def test_no_early_finish_when_not_clinched(self):
        """5 cells for one player with 3 empty is not enough: 5 < 5+3=8."""
        board: list[BoardCell | None] = [
            cell("c0", 0),
            cell("c1", 0),
            cell("c2", 0),
            cell("c3", 0),
            cell("c5", 1),
            None,
            None,
            None,
            None,
        ]
        state = _make_state(board, current_player=0)
        result = apply_intent(
            state, PlacementIntent(player_index=0, card_key="c4", cell_index=5), CARDS
        )
        # p0 now has 5 cells, 3 empty: 5 < 5+3 = 8, not clinched
        assert result.status == GameStatus.ACTIVE
        assert result.result is None

    def test_normal_finish_has_early_finish_false(self):
        """When the board fills normally, early_finish defaults to False."""
        # Fill 8 cells, place the 9th
        board: list[BoardCell | None] = [
            cell("c0", 0),
            cell("c1", 0),
            cell("c2", 0),
            cell("c3", 0),
            cell("c4", 0),
            cell("c5", 1),
            cell("c6", 1),
            cell("c7", 1),
            None,
        ]
        state = GameState(
            game_id="test-early",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=[]),
                PlayerState(player_id="p1", hand=["c9"]),
            ],
            board=board,
            current_player_index=1,
            seed=42,
        )
        extra_cards = {**CARDS, "c7": make_card("c7"), "c9": make_card("c9")}
        result = apply_intent(
            state, PlacementIntent(player_index=1, card_key="c9", cell_index=8), extra_cards
        )
        assert result.status == GameStatus.COMPLETE
        assert result.result is not None
        assert result.result.early_finish is False
        # p0: 5, p1: 4 → p0 wins
        assert result.result.winner == 0

    def test_early_finish_with_capture_creating_clinch(self):
        """A capture can push the placing player over the clinch threshold."""
        # p0 places a card that captures one of p1's cards, reaching the clinch
        # Board: p0 has 4 cells, p1 has 2, 3 empty.
        # p0 places and captures 1 of p1's → p0 has 6, p1 has 1, 2 empty
        # 6 >= 5 + 2 = 7? No.
        # p0 has 4, p1 has 3, 2 empty. p0 places + captures 2
        # → p0 has 7, p1 has 1, 1 empty
        # 7 >= 5 + 1 = 6 → clinched!

        # Use cards where p0's card has high sides to capture p1's cards
        high_card = make_card("high", n=3, e=3, s=3, w=3)
        low_card = make_card("low", n=1, e=1, s=1, w=1)
        lookup = {
            "high": high_card,
            "low": low_card,
            **{f"c{i}": make_card(f"c{i}") for i in range(10)},
        }

        # Layout (3x3):
        # [p0:c0] [p0:c1] [p0:c2]
        # [p0:c3] [empty]  [p1:low]  ← p0 places "high" at cell 4, captures cell 5 (east)
        # [empty]  [p1:low] [p1:c9]
        # After: p0 has 5+captured, check if clinch
        board: list[BoardCell | None] = [
            cell("c0", 0),
            cell("c1", 0),
            cell("c2", 0),
            cell("c3", 0),
            None,
            cell("low", 1),
            None,
            cell("low", 1),
            cell("c9", 1),
        ]
        # Actually this might not work because cell 7 also has p1 low card.
        # Let me make high card beat low card: high.e=3 vs low.w=1 → capture cell 5
        # Also high.s=3 vs low(cell7).n=1 → capture cell 7
        # After: p0 has 4+1(placed)+2(captured)=7, p1 has 1, 1 empty
        # 7 >= 5 + 1 = 6 → clinched!
        state = GameState(
            game_id="test-capture-clinch",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["high"]),
                PlayerState(player_id="p1", hand=["c8"]),
            ],
            board=board,
            current_player_index=0,
            seed=42,
        )
        result = apply_intent(
            state, PlacementIntent(player_index=0, card_key="high", cell_index=4), lookup
        )
        assert result.status == GameStatus.COMPLETE
        assert result.result is not None
        assert result.result.early_finish is True
        assert result.result.winner == 0
