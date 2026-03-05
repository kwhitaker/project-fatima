"""Tests for US-SP-006: Greedy (Rahadin) AI strategy — one-ply evaluation.

Covers:
- Greedy picks capture over non-capture
- Greedy uses archetype when it would flip an extra card
- Greedy breaks ties randomly (seeded)
"""

from random import Random

from app.models.game import (
    AIDifficulty,
    Archetype,
    BoardCell,
    GameState,
    GameStatus,
    PlayerState,
)
from app.rules.ai import choose_move
from app.services.game_service import AI_PLAYER_ID
from tests.conftest import make_card


def _ai_game_state(
    board: list[BoardCell | None] | None = None,
    ai_hand: list[str] | None = None,
    human_hand: list[str] | None = None,
    ai_archetype: Archetype | None = None,
    ai_archetype_used: bool = False,
    current_player_index: int = 1,
    seed: int = 42,
    board_elements: list[str] | None = None,
) -> GameState:
    """Build a GameState for AI testing with AI as player index 1."""
    return GameState(
        game_id="test-ai",
        status=GameStatus.ACTIVE,
        seed=seed,
        current_player_index=current_player_index,
        board=board if board is not None else [None] * 9,
        board_elements=board_elements,
        players=[
            PlayerState(
                player_id="human",
                player_type="human",
                hand=human_hand or [],
                archetype=Archetype.MARTIAL,
                archetype_used=True,
            ),
            PlayerState(
                player_id=AI_PLAYER_ID,
                player_type="ai",
                ai_difficulty=AIDifficulty.MEDIUM,
                hand=ai_hand if ai_hand is not None else ["c1", "c2", "c3", "c4", "c5"],
                archetype=ai_archetype,
                archetype_used=ai_archetype_used,
            ),
        ],
    )


class TestGreedyPicksCaptureOverNonCapture:
    """Greedy should always pick the move that captures the most cells."""

    def test_captures_when_possible(self) -> None:
        """With one weak opponent card adjacent to cell 1, greedy should place there."""
        # Opponent card at cell 0, weak sides (1,1,1,1)
        # AI has a strong card (9,9,9,9) → placing at cell 1 captures cell 0
        board: list[BoardCell | None] = [BoardCell(card_key="weak", owner=0)] + [None] * 8
        state = _ai_game_state(board=board, ai_hand=["strong"])
        lookup = {
            "weak": make_card("weak", n=1, e=1, s=1, w=1),
            "strong": make_card("strong", n=9, e=9, s=9, w=9),
        }
        intent = choose_move(state, 1, AIDifficulty.MEDIUM, lookup, Random(1))
        # Greedy must pick a cell adjacent to cell 0 (cells 1 or 3)
        assert intent.cell_index in {1, 3}

    def test_prefers_double_capture_over_single(self) -> None:
        """Cell 4 (center) can capture two opponents vs cell 2 capturing one."""
        board: list[BoardCell | None] = [None] * 9
        # Opponent cards at cells 1 and 3 (weak), AI can capture both from cell 4
        board[1] = BoardCell(card_key="w1", owner=0)
        board[3] = BoardCell(card_key="w2", owner=0)
        state = _ai_game_state(board=board, ai_hand=["strong"])
        lookup = {
            "w1": make_card("w1", n=1, e=1, s=1, w=1),
            "w2": make_card("w2", n=1, e=1, s=1, w=1),
            "strong": make_card("strong", n=9, e=9, s=9, w=9),
        }
        intent = choose_move(state, 1, AIDifficulty.MEDIUM, lookup, Random(1))
        assert intent.cell_index == 4  # center captures both


class TestGreedyUsesArchetype:
    """Greedy uses archetype when it would result in more owned cells."""

    def test_skulker_flips_extra_card(self) -> None:
        """Skulker boosting a weak side lets the AI capture an otherwise uncapturable card."""
        # AI card: n=7,e=1,s=7,w=7. Opponent at cell 0 has e=1 (captured by W=7).
        # Opponent at cell 2 has w=3. AI card e=1 < 3 → no capture without skulker.
        # With skulker boost east: e=1+3=4 > 3 → captures opp_right too.
        board: list[BoardCell | None] = [None] * 9
        board[0] = BoardCell(card_key="opp_left", owner=0)  # adjacent to cell 1 via W
        board[2] = BoardCell(card_key="opp_right", owner=0)  # adjacent to cell 1 via E
        state = _ai_game_state(
            board=board,
            ai_hand=["attacker"],
            ai_archetype=Archetype.SKULKER,
        )
        lookup = {
            "opp_left": make_card("opp_left", n=5, e=1, s=5, w=5),
            "opp_right": make_card("opp_right", n=5, e=5, s=5, w=3),
            "attacker": make_card("attacker", n=7, e=1, s=7, w=7),
        }
        intent = choose_move(state, 1, AIDifficulty.MEDIUM, lookup, Random(1))
        # With skulker boost on east: e=1+3=4 > 3 → captures opp_right too
        # Greedy should use archetype and boost east
        assert intent.use_archetype
        assert intent.skulker_boost_side == "e"
        assert intent.cell_index == 1

    def test_no_archetype_when_already_used(self) -> None:
        """Greedy doesn't try archetype when already used."""
        board: list[BoardCell | None] = [BoardCell(card_key="weak", owner=0)] + [None] * 8
        state = _ai_game_state(
            board=board,
            ai_hand=["strong"],
            ai_archetype=Archetype.SKULKER,
            ai_archetype_used=True,
        )
        lookup = {
            "weak": make_card("weak", n=1, e=1, s=1, w=1),
            "strong": make_card("strong", n=9, e=9, s=9, w=9),
        }
        intent = choose_move(state, 1, AIDifficulty.MEDIUM, lookup, Random(1))
        assert not intent.use_archetype


class TestGreedyTiebreaking:
    """Greedy breaks ties randomly using the seeded RNG."""

    def test_different_seeds_can_produce_different_choices(self) -> None:
        """When multiple moves tie on ownership count, the seed determines which is chosen."""
        # Two opponent cards equidistant: cell 0 and cell 2, both capturable from cells 1 and 1
        # Actually let's use: empty board, AI has two cards both placing anywhere gives same score
        # Simplest: empty board, AI has 2 cards, all placements score equally (0 captures).
        state = _ai_game_state(ai_hand=["c1", "c2"])
        lookup = {
            "c1": make_card("c1", n=5, e=5, s=5, w=5),
            "c2": make_card("c2", n=5, e=5, s=5, w=5),
        }
        choices = set()
        for seed in range(50):
            intent = choose_move(state, 1, AIDifficulty.MEDIUM, lookup, Random(seed))
            choices.add((intent.card_key, intent.cell_index))
        # With 2 cards x 9 cells = 18 possible moves and random tiebreaking, we should see variety
        assert len(choices) > 1

    def test_deterministic_with_same_seed(self) -> None:
        """Same seed produces the same choice."""
        state = _ai_game_state(ai_hand=["c1", "c2"])
        lookup = {
            "c1": make_card("c1", n=5, e=5, s=5, w=5),
            "c2": make_card("c2", n=5, e=5, s=5, w=5),
        }
        intent1 = choose_move(state, 1, AIDifficulty.MEDIUM, lookup, Random(42))
        intent2 = choose_move(state, 1, AIDifficulty.MEDIUM, lookup, Random(42))
        assert intent1.card_key == intent2.card_key
        assert intent1.cell_index == intent2.cell_index


class TestGreedyMartialArchetype:
    """Greedy evaluates Martial (CW/CCW rotation) when it helps."""

    def test_martial_rotation_captures_more(self) -> None:
        """Martial rotation lets AI capture a card it otherwise couldn't."""
        # Fill most of the board so only cell 1 is empty.
        # Opponent at cell 4 with n=3. AI card: n=1, e=7, s=1, w=1.
        # Cell 1's S faces cell 4's N. Without rotation: S=1 < N=3, no capture.
        # CW rotation: n→e, e→s, s→w, w→n → S=7 > 3 → capture!
        board: list[BoardCell | None] = [BoardCell(card_key="fill", owner=1)] * 9
        board[1] = None
        board[4] = BoardCell(card_key="opp", owner=0)
        state = _ai_game_state(
            board=board,
            ai_hand=["attacker"],
            ai_archetype=Archetype.MARTIAL,
        )
        lookup = {
            "opp": make_card("opp", n=3, e=5, s=5, w=5),
            "fill": make_card("fill"),
            "attacker": make_card("attacker", n=1, e=7, s=1, w=1),
        }
        intent = choose_move(state, 1, AIDifficulty.MEDIUM, lookup, Random(1))
        # Should use martial CW rotation to get S=7 > 3, capturing cell 4
        assert intent.use_archetype
        assert intent.cell_index == 1
        assert intent.martial_rotation_direction == "cw"
