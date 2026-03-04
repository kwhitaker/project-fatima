"""Tests for US-UXP-023: auto-complete statistically decided games.

With hand-in-score (total 10 points = 9 cells + hand cards), a player wins
early when their minimum possible final score >= 6.  The first player ends
with 0 hand cards, the second player ends with 1.

First player clinch:  cells >= 6 + empty_cells  (hand_end=0)
Second player clinch: cells >= 5 + empty_cells  (hand_end=1)

Early finish is suppressed when the losing player still has an unspent
archetype power (they might use it to swing captures on their remaining turn).
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


def _make_state(
    board: list[BoardCell | None],
    current_player: int = 0,
    archetypes_used: bool = True,
) -> GameState:
    """Build an ACTIVE game state with two players and the given board.

    archetypes_used defaults to True so the early-finish check is eligible.
    Set to False to test that unspent archetypes suppress early finish.
    """
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
            PlayerState(player_id="p0", hand=p0_hand, archetype_used=archetypes_used),
            PlayerState(player_id="p1", hand=p1_hand, archetype_used=archetypes_used),
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

    def test_early_finish_first_player_clinches(self):
        """First player (p0) owns 7 cells with 1 empty → min_score = 7-1+0 = 6 → clinched."""
        board: list[BoardCell | None] = [
            cell("c0", 0),
            cell("c1", 0),
            cell("c2", 0),
            cell("c3", 0),
            cell("c4", 0),
            cell("c5", 0),
            cell("c6", 1),
            None,
            None,
        ]
        state = GameState(
            game_id="test-early",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["c8"], archetype_used=True),
                PlayerState(player_id="p1", hand=["c9", "c7"], archetype_used=True),
            ],
            board=board,
            current_player_index=0,
            starting_player_index=0,
            seed=42,
        )
        extra_cards = {**CARDS, "c7": make_card("c7"), "c8": make_card("c8"), "c9": make_card("c9")}
        result = apply_intent(
            state, PlacementIntent(player_index=0, card_key="c8", cell_index=7), extra_cards
        )
        assert result.status == GameStatus.COMPLETE
        assert result.result is not None
        assert result.result.winner == 0
        assert result.result.early_finish is True
        assert result.result.is_draw is False

    def test_early_finish_second_player_clinches(self):
        """Second player (p1) owns 6 cells with 1 empty → min_score = 6-1+1 = 6 → clinched."""
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
                PlayerState(player_id="p0", hand=["c8"], archetype_used=True),
                PlayerState(player_id="p1", hand=["c9"], archetype_used=True),
            ],
            board=board,
            current_player_index=1,
            starting_player_index=0,  # p1 is second player → hand_end=1
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

    def test_first_player_6_cells_1_empty_not_clinched(self):
        """First player has 6 cells, 1 empty: min_score = 6-1+0 = 5 < 6 → not clinched.

        The hand bonus for the second player means the first player needs 7+ cells
        with 1 empty to clinch.
        """
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
        state = GameState(
            game_id="test-early",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["c8"], archetype_used=True),
                PlayerState(player_id="p1", hand=["c9"], archetype_used=True),
            ],
            board=board,
            current_player_index=0,
            starting_player_index=0,
            seed=42,
        )
        extra_cards = {**CARDS, "c8": make_card("c8"), "c9": make_card("c9")}
        result = apply_intent(
            state, PlacementIntent(player_index=0, card_key="c8", cell_index=7), extra_cards
        )
        # 6 cells, 1 empty: min_score = 6-1+0 = 5, opponent could tie → not clinched
        assert result.status == GameStatus.ACTIVE
        assert result.result is None

    def test_no_early_finish_when_not_clinched(self):
        """5 cells for first player with 3 empty: min_score = 5-3+0 = 2 → not clinched."""
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
        assert result.status == GameStatus.ACTIVE
        assert result.result is None

    def test_normal_finish_has_early_finish_false(self):
        """When the board fills normally, early_finish defaults to False."""
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
        # First player (p0) places the 9th card, second player (p1) keeps 1 in hand
        state = GameState(
            game_id="test-early",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["c9"]),
                PlayerState(player_id="p1", hand=["kept"]),
            ],
            board=board,
            current_player_index=0,
            starting_player_index=0,
            seed=42,
        )
        extra_cards = {**CARDS, "c9": make_card("c9"), "kept": make_card("kept")}
        result = apply_intent(
            state, PlacementIntent(player_index=0, card_key="c9", cell_index=8), extra_cards
        )
        assert result.status == GameStatus.COMPLETE
        assert result.result is not None
        assert result.result.early_finish is False
        # p0: 6 cells + 0 hand = 6, p1: 3 cells + 1 hand = 4 → p0 wins
        assert result.result.winner == 0

    def test_early_finish_with_capture_creating_clinch(self):
        """A capture can push the placing player over the clinch threshold.

        p0 (first player) places at cell 4, captures cells 5 and 7.
        After: p0 has 7 cells, 1 empty. min_score = 7-1+0 = 6 → clinched.
        """
        high_card = make_card("high", n=3, e=3, s=3, w=3)
        low_card = make_card("low", n=1, e=1, s=1, w=1)
        lookup = {
            "high": high_card,
            "low": low_card,
            **{f"c{i}": make_card(f"c{i}") for i in range(10)},
        }

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
        state = GameState(
            game_id="test-capture-clinch",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["high"], archetype_used=True),
                PlayerState(player_id="p1", hand=["c8"], archetype_used=True),
            ],
            board=board,
            current_player_index=0,
            starting_player_index=0,
            seed=42,
        )
        result = apply_intent(
            state, PlacementIntent(player_index=0, card_key="high", cell_index=4), lookup
        )
        assert result.status == GameStatus.COMPLETE
        assert result.result is not None
        assert result.result.early_finish is True
        assert result.result.winner == 0

    def test_no_early_finish_when_opponent_has_unspent_archetype(self):
        """Early finish is suppressed when the losing player has an unspent archetype.

        Same board as test_early_finish_first_player_clinches (p0 would clinch
        with 7 cells + 1 empty), but p1 still has their archetype power.
        The archetype could swing captures, so the game must continue.
        """
        board: list[BoardCell | None] = [
            cell("c0", 0),
            cell("c1", 0),
            cell("c2", 0),
            cell("c3", 0),
            cell("c4", 0),
            cell("c5", 0),
            cell("c6", 1),
            None,
            None,
        ]
        state = GameState(
            game_id="test-early",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["c8"], archetype_used=True),
                PlayerState(player_id="p1", hand=["c9", "c7"], archetype_used=False),
            ],
            board=board,
            current_player_index=0,
            starting_player_index=0,
            seed=42,
        )
        extra_cards = {**CARDS, "c7": make_card("c7"), "c8": make_card("c8"), "c9": make_card("c9")}
        result = apply_intent(
            state, PlacementIntent(player_index=0, card_key="c8", cell_index=7), extra_cards
        )
        # p1 still has archetype → mercy suppressed, game continues
        assert result.status == GameStatus.ACTIVE
        assert result.result is None

    def test_early_finish_when_winner_has_unspent_archetype(self):
        """Early finish still triggers when only the *winning* player has an unspent archetype.

        The losing player (opponent of the clincher) has already used their power,
        so there's no possible swing — mercy is valid.
        """
        board: list[BoardCell | None] = [
            cell("c0", 0),
            cell("c1", 0),
            cell("c2", 0),
            cell("c3", 0),
            cell("c4", 0),
            cell("c5", 0),
            cell("c6", 1),
            None,
            None,
        ]
        state = GameState(
            game_id="test-early",
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="p0", hand=["c8"], archetype_used=False),
                PlayerState(player_id="p1", hand=["c9", "c7"], archetype_used=True),
            ],
            board=board,
            current_player_index=0,
            starting_player_index=0,
            seed=42,
        )
        extra_cards = {**CARDS, "c7": make_card("c7"), "c8": make_card("c8"), "c9": make_card("c9")}
        result = apply_intent(
            state, PlacementIntent(player_index=0, card_key="c8", cell_index=7), extra_cards
        )
        # p1 (the loser) has used their archetype → mercy triggers
        assert result.status == GameStatus.COMPLETE
        assert result.result is not None
        assert result.result.winner == 0
        assert result.result.early_finish is True
