"""Tests for US-GM-006: Elemental system — game state, rules engine, and API.

Board layout (row-major, 0-indexed):
  0 1 2
  3 4 5
  6 7 8

Elemental rule: placing a card on a matching element cell gives +1 to all its
sides for that placement's initial comparisons.
- Combo chain cards receive NO elemental bonus (zero modifiers, printed stats only).
- Plus rule sum calculations ignore elemental bonus (raw printed values only).
- board_elements=None (old snapshots) → elemental bonus is 0 for all placements.
"""

from random import Random
from unittest.mock import MagicMock

from app.models.cards import CardDefinition, CardSides
from app.models.game import BoardCell, GameState, GameStatus, LastMoveInfo
from app.rules.reducer import PlacementIntent, apply_intent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_card(
    key: str, n: int, e: int, s: int, w: int, element: str = "shadow"
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
        element=element,
    )


def neutral_rng() -> MagicMock:
    """Return a mock RNG that always rolls 3 (neutral Mists, no modifier)."""
    rng = MagicMock()
    rng.randint.return_value = 3
    return rng


def state_with_elements(
    board: list[BoardCell | None],
    board_elements: list[str] | None,
) -> GameState:
    return GameState(
        game_id="test",
        status=GameStatus.ACTIVE,
        board=board,
        board_elements=board_elements,
    )


# ---------------------------------------------------------------------------
# Elemental bonus: match gives +1
# ---------------------------------------------------------------------------


class TestElementalBonusCapture:
    def test_match_gives_plus1_and_enables_capture(self) -> None:
        """Elemental match (+1) tips a tie into a capture.

        placed.n=5, enemy.s=5 → normally 5 > 5 is False (no capture).
        Cell 4 element "blood" matches placed.element "blood" → bonus +1.
        Effective: 5+1=6 > 5 → capture.

        Adjacency for cell 4: (1,"n","s"), (3,"w","e"), (5,"e","w"), (7,"s","n")
        """
        placed = make_card("placed", n=5, e=1, s=1, w=1, element="blood")
        enemy = make_card("enemy", n=1, e=1, s=5, w=1, element="shadow")

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="enemy", owner=1)

        board_elements = ["shadow"] * 9
        board_elements[4] = "blood"  # cell 4 matches placed card's element

        state = state_with_elements(board, board_elements)
        intent = PlacementIntent(player_index=0, card_key="placed", cell_index=4)
        lookup = {"placed": placed, "enemy": enemy}

        next_state = apply_intent(state, intent, lookup, rng=neutral_rng())

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "Elemental bonus enabled capture"

    def test_mismatch_gives_no_bonus(self) -> None:
        """Non-matching element cell → no bonus → tie stays a tie.

        placed.n=5, enemy.s=5 → 5 > 5 is False.
        Cell 4 element "shadow" ≠ placed.element "blood" → no bonus.
        """
        placed = make_card("placed", n=5, e=1, s=1, w=1, element="blood")
        enemy = make_card("enemy", n=1, e=1, s=5, w=1, element="shadow")

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="enemy", owner=1)

        board_elements = ["shadow"] * 9  # cell 4 = "shadow" ≠ "blood"

        state = state_with_elements(board, board_elements)
        intent = PlacementIntent(player_index=0, card_key="placed", cell_index=4)
        lookup = {"placed": placed, "enemy": enemy}

        next_state = apply_intent(state, intent, lookup, rng=neutral_rng())

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 1, "No elemental bonus → no capture"

    def test_board_elements_none_gives_no_bonus(self) -> None:
        """Old snapshot with board_elements=None → elemental bonus is 0.

        placed.n=5, enemy.s=5 → tie with no bonus → no capture.
        """
        placed = make_card("placed", n=5, e=1, s=1, w=1, element="blood")
        enemy = make_card("enemy", n=1, e=1, s=5, w=1, element="shadow")

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="enemy", owner=1)

        state = state_with_elements(board, board_elements=None)  # old snapshot
        intent = PlacementIntent(player_index=0, card_key="placed", cell_index=4)
        lookup = {"placed": placed, "enemy": enemy}

        next_state = apply_intent(state, intent, lookup, rng=neutral_rng())

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 1, "board_elements=None → no bonus → no capture"


# ---------------------------------------------------------------------------
# elemental_triggered in last_move
# ---------------------------------------------------------------------------


class TestElementalTriggered:
    def test_elemental_triggered_true_on_match(self) -> None:
        """last_move.elemental_triggered is True when card element matches cell."""
        placed = make_card("placed", n=5, e=1, s=1, w=1, element="blood")
        board_elements = ["shadow"] * 9
        board_elements[4] = "blood"  # match

        state = state_with_elements([None] * 9, board_elements)
        intent = PlacementIntent(player_index=0, card_key="placed", cell_index=4)

        next_state = apply_intent(state, intent, {"placed": placed}, rng=neutral_rng())

        assert next_state.last_move is not None
        assert next_state.last_move.elemental_triggered is True

    def test_elemental_triggered_false_on_mismatch(self) -> None:
        """last_move.elemental_triggered is False when element does not match."""
        placed = make_card("placed", n=5, e=1, s=1, w=1, element="blood")
        board_elements = ["shadow"] * 9  # all shadow, no match for "blood" at cell 4

        state = state_with_elements([None] * 9, board_elements)
        intent = PlacementIntent(player_index=0, card_key="placed", cell_index=4)

        next_state = apply_intent(state, intent, {"placed": placed}, rng=neutral_rng())

        assert next_state.last_move is not None
        assert next_state.last_move.elemental_triggered is False

    def test_elemental_triggered_false_when_board_elements_none(self) -> None:
        """last_move.elemental_triggered is False when board_elements is None."""
        placed = make_card("placed", n=5, e=1, s=1, w=1, element="blood")

        state = state_with_elements([None] * 9, board_elements=None)
        intent = PlacementIntent(player_index=0, card_key="placed", cell_index=4)

        next_state = apply_intent(state, intent, {"placed": placed}, rng=neutral_rng())

        assert next_state.last_move is not None
        assert next_state.last_move.elemental_triggered is False

    def test_elemental_triggered_default_false_in_old_snapshot(self) -> None:
        """Existing LastMoveInfo without elemental_triggered deserializes with False."""
        lm = LastMoveInfo.model_validate(
            {
                "player_index": 0,
                "card_key": "card_a",
                "cell_index": 4,
                "mists_roll": 3,
                "mists_effect": "none",
                # no elemental_triggered — old snapshot
            }
        )
        assert lm.elemental_triggered is False


# ---------------------------------------------------------------------------
# Combo chain has no elemental bonus
# ---------------------------------------------------------------------------


class TestComboNoElementalBonus:
    def test_combo_chain_has_no_elemental_bonus(self) -> None:
        """BFS combo captures use printed stats only — no elemental bonus.

        Setup (cell 4 = "blood", placed.element = "blood" → +1 initial bonus):
          placed at 4: n=5, e=1, s=1, w=1 → effective n=6 (with +1 bonus)
          enemy1 at 1: n=1, e=5, s=5, w=1 → captured (6>5)
          enemy2 at 2: n=1, e=1, s=1, w=5 → combo candidate from enemy1

        After enemy1 captured, combo (no elemental):
          enemy1.e=5 vs enemy2.w=5 → 5 > 5 = False → NO combo capture.

        If elemental were (incorrectly) applied to combos, enemy1 at cell 1
        (board_elements[1]="blood") would get +1, making 6>5 → wrong capture.
        """
        placed = make_card("placed", n=5, e=1, s=1, w=1, element="blood")
        enemy1 = make_card("enemy1", n=1, e=5, s=5, w=1, element="arcane")
        enemy2 = make_card("enemy2", n=1, e=1, s=1, w=5, element="blood")

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="enemy1", owner=1)
        board[2] = BoardCell(card_key="enemy2", owner=1)

        board_elements = ["shadow"] * 9
        board_elements[4] = "blood"   # placed card matches → +1 initial
        board_elements[1] = "blood"   # enemy1's cell is blood (combo should ignore this)

        state = state_with_elements(board, board_elements)
        intent = PlacementIntent(player_index=0, card_key="placed", cell_index=4)
        lookup = {"placed": placed, "enemy1": enemy1, "enemy2": enemy2}

        next_state = apply_intent(state, intent, lookup, rng=neutral_rng())

        assert next_state.board[1] is not None
        assert next_state.board[1].owner == 0, "enemy1 captured by elemental bonus (+1)"
        assert next_state.board[2] is not None
        assert next_state.board[2].owner == 1, "enemy2 NOT combo-captured (combo has no elemental)"


# ---------------------------------------------------------------------------
# Plus rule ignores elemental bonus in sum calculation
# ---------------------------------------------------------------------------


class TestPlusIgnoresElemental:
    def test_plus_sums_use_raw_values_not_elemental(self) -> None:
        """Plus rule sum uses raw printed values; elemental bonus (via mists_modifier) is excluded.

        placed (blood) at cell 4 (blood → +1 elemental):
          Plus sums use raw: placed.n=6, enemy1.s=7 → sum 13; placed.w=3, enemy2.e=10 → sum 13.
          Sums match → Plus fires → both captured.
        The elemental bonus (+1 to mists_modifier) does not affect sum calculation.
        """
        placed = make_card("placed", n=6, e=5, s=5, w=3, element="blood")
        enemy1 = make_card("enemy1", n=5, e=5, s=7, w=5, element="shadow")
        enemy2 = make_card("enemy2", n=5, e=10, s=5, w=5, element="shadow")

        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="enemy1", owner=1)
        board[3] = BoardCell(card_key="enemy2", owner=1)

        board_elements = ["shadow"] * 9
        board_elements[4] = "blood"  # match → elemental +1 on initial comparisons (not Plus sums)

        state = state_with_elements(board, board_elements)
        intent = PlacementIntent(player_index=0, card_key="placed", cell_index=4)
        lookup = {"placed": placed, "enemy1": enemy1, "enemy2": enemy2}

        next_state = apply_intent(state, intent, lookup, rng=neutral_rng())

        assert next_state.last_move is not None
        assert next_state.last_move.plus_triggered is True
        assert next_state.board[1] is not None and next_state.board[1].owner == 0, "enemy1 Plus-captured"
        assert next_state.board[3] is not None and next_state.board[3].owner == 0, "enemy2 Plus-captured"


# ---------------------------------------------------------------------------
# board_elements serialization
# ---------------------------------------------------------------------------


class TestBoardElementsSerialization:
    def test_board_elements_serializes_correctly(self) -> None:
        """board_elements is serialized and deserialized correctly in GameState."""
        elements = ["blood", "holy", "arcane", "shadow", "nature", "blood", "holy", "arcane", "shadow"]
        state = GameState(game_id="test", board_elements=elements)

        data = state.model_dump()
        assert data["board_elements"] == elements

        restored = GameState.model_validate(data)
        assert restored.board_elements == elements

    def test_board_elements_absent_in_old_snapshot_deserializes_as_none(self) -> None:
        """board_elements absent from old snapshot deserializes as None."""
        state = GameState.model_validate(
            {
                "game_id": "old-game",
                "seed": 0,
                "status": "waiting",
                "board": [None] * 9,
                # no board_elements field
            }
        )
        assert state.board_elements is None


# ---------------------------------------------------------------------------
# board_elements generated deterministically on game join
# ---------------------------------------------------------------------------


class TestBoardElementsGeneration:
    def test_board_elements_set_when_second_player_joins(self) -> None:
        """board_elements is set deterministically when second player joins."""
        from app.models.game import PlayerState
        from app.services.game_service import join_game
        from app.store.memory import MemoryCardStore, MemoryGameStore

        cards = [
            CardDefinition(
                card_key=f"test_card_{i:03d}",
                character_key=f"char_{i:03d}",
                name=f"Test Card {i}",
                version="v1",
                tier=1,
                rarity=15,
                is_named=False,
                sides=CardSides(n=4, e=4, s=3, w=5),
                set="test",
                element="shadow",
            )
            for i in range(20)
        ]

        seed = 42
        game_store = MemoryGameStore()
        card_store = MemoryCardStore(cards=cards)
        initial_state = GameState(
            game_id="test-join-game",
            seed=seed,
            status=GameStatus.WAITING,
            players=[PlayerState(player_id="alice")],
        )
        game_store.create_game("test-join-game", initial_state)

        new_state = join_game(game_store, card_store, "test-join-game", "bob")

        assert new_state.board_elements is not None, "board_elements set after second player joins"
        assert len(new_state.board_elements) == 9, "9 elements for 9 cells"
        assert all(
            e in ("blood", "holy", "arcane", "shadow", "nature")
            for e in new_state.board_elements
        ), "all elements are valid"

        # Verify determinism: same seed → same board_elements
        expected = Random(seed).choices(["blood", "holy", "arcane", "shadow", "nature"], k=9)
        assert new_state.board_elements == expected

    def test_board_elements_not_set_when_first_player_joins(self) -> None:
        """board_elements is None while game is still in WAITING state (1 player)."""
        from app.services.game_service import create_game
        from app.store.memory import MemoryCardStore, MemoryGameStore

        game_store = MemoryGameStore()
        card_store = MemoryCardStore(cards=[])

        new_state = create_game(game_store, card_store, "alice", seed=42)
        assert new_state.board_elements is None, "board_elements not set in WAITING state"
