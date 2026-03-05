"""Tests for US-SP-005: Novice (Ireena) AI strategy — semi-random placement.

Covers:
- Novice returns valid moves (card in hand, cell empty)
- Novice prefers obvious captures most of the time
- Novice sometimes makes suboptimal choices (noise)
- Archetype usage is inconsistent (sometimes used, sometimes not)
"""

from random import Random

import pytest

from app.models.game import (
    AIDifficulty,
    Archetype,
    BoardCell,
    GameState,
    GameStatus,
    PlayerState,
)
from app.rules.ai import (
    _novice_should_skip_archetype,
    _score_placement,
    choose_move,
)
from app.rules.reducer import PlacementIntent
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
            ),
            PlayerState(
                player_id=AI_PLAYER_ID,
                player_type="ai",
                ai_difficulty=AIDifficulty.EASY,
                hand=ai_hand if ai_hand is not None else ["c1", "c2", "c3", "c4", "c5"],
                archetype=ai_archetype,
                archetype_used=ai_archetype_used,
            ),
        ],
    )


class TestNoviceReturnsValidMoves:
    """Novice always returns legal (card in hand, cell empty) placements."""

    def test_returns_placement_intent(self) -> None:
        state = _ai_game_state()
        lookup = {f"c{i}": make_card(f"c{i}") for i in range(1, 6)}
        intent = choose_move(state, 1, AIDifficulty.EASY, lookup, Random(1))
        assert isinstance(intent, PlacementIntent)
        assert intent.player_index == 1
        assert intent.card_key in state.players[1].hand
        assert 0 <= intent.cell_index <= 8

    def test_only_places_in_empty_cells(self) -> None:
        board: list[BoardCell | None] = [
            BoardCell(card_key="x1", owner=0),
            BoardCell(card_key="x2", owner=1),
        ] + [None] * 7
        state = _ai_game_state(board=board, ai_hand=["c1"])
        lookup = {"c1": make_card("c1"), "x1": make_card("x1"), "x2": make_card("x2")}
        for seed in range(20):
            intent = choose_move(state, 1, AIDifficulty.EASY, lookup, Random(seed))
            assert intent.cell_index >= 2  # cells 0,1 occupied

    def test_raises_on_empty_hand(self) -> None:
        state = _ai_game_state(ai_hand=[])
        with pytest.raises(ValueError, match="no legal moves"):
            choose_move(state, 1, AIDifficulty.EASY, {}, Random(1))


class TestNovicePrefersCaptures:
    """Novice should prefer placements that capture opponent cards most of the time."""

    def test_prefers_capture_over_no_capture(self) -> None:
        """With a strong card adjacent to a weak opponent card, novice usually captures."""
        # Board: opponent card at cell 0 with weak sides (n=1,e=1,s=1,w=1)
        # AI has a strong card (n=9,e=9,s=9,w=9)
        # Cell 1 is adjacent to cell 0 (our W beats their E)
        # Other empty cells (2-8) have no adjacent opponents
        board: list[BoardCell | None] = [BoardCell(card_key="weak", owner=0)] + [None] * 8
        state = _ai_game_state(board=board, ai_hand=["strong"])
        lookup = {
            "weak": make_card("weak", n=1, e=1, s=1, w=1),
            "strong": make_card("strong", n=9, e=9, s=9, w=9),
        }

        # Run many times; novice should pick cell 1 or 3 (adjacent to 0) more often
        capture_cells = {1, 3}  # cells adjacent to 0
        capture_count = 0
        trials = 100
        for seed in range(trials):
            intent = choose_move(state, 1, AIDifficulty.EASY, lookup, Random(seed))
            if intent.cell_index in capture_cells:
                capture_count += 1

        # Should capture most of the time (>60% given +1 score bonus for capture)
        assert capture_count > 60, f"Expected >60 captures, got {capture_count}/{trials}"

    def test_multiple_captures_scored_higher(self) -> None:
        """A cell adjacent to 2 capturable opponent cards scores higher than 1."""
        # Cell 4 (center) is adjacent to cells 1,3,5,7
        # Place opponent cards at cells 1 and 3 (weak)
        board: list[BoardCell | None] = [None] * 9
        board[1] = BoardCell(card_key="w1", owner=0)
        board[3] = BoardCell(card_key="w2", owner=0)
        state = _ai_game_state(board=board, ai_hand=["strong"])
        lookup = {
            "w1": make_card("w1", n=1, e=1, s=1, w=1),
            "w2": make_card("w2", n=1, e=1, s=1, w=1),
            "strong": make_card("strong", n=9, e=9, s=9, w=9),
        }
        # Cell 4 scores +2 (captures from N and W); cell 8 scores 0 (no opponent neighbors)
        score_4 = _score_placement(state, 1, lookup["strong"], 4, lookup)
        score_8 = _score_placement(state, 1, lookup["strong"], 8, lookup)
        assert score_4 > score_8
        assert score_4 == 2.0
        assert score_8 == 0.0


class TestNoviceNoise:
    """Novice sometimes makes suboptimal choices due to random noise."""

    def test_sometimes_picks_non_capture(self) -> None:
        """With noise, novice occasionally picks a cell with no captures."""
        board: list[BoardCell | None] = [BoardCell(card_key="weak", owner=0)] + [None] * 8
        state = _ai_game_state(board=board, ai_hand=["strong"])
        lookup = {
            "weak": make_card("weak", n=1, e=1, s=1, w=1),
            "strong": make_card("strong", n=9, e=9, s=9, w=9),
        }

        non_capture_count = 0
        capture_cells = {1, 3}
        trials = 100
        for seed in range(trials):
            intent = choose_move(state, 1, AIDifficulty.EASY, lookup, Random(seed))
            if intent.cell_index not in capture_cells:
                non_capture_count += 1

        # Should sometimes miss the capture (noise up to 1.5 can override +1 score)
        assert non_capture_count > 0, "Novice should sometimes make suboptimal choices"


class TestNoviceElementalAwareness:
    """Novice gets +1 for elemental match."""

    def test_elemental_match_boosts_score(self) -> None:
        board_elements = ["shadow"] * 9
        state = _ai_game_state(board_elements=board_elements, ai_hand=["c1"])
        shadow_card = make_card("c1")  # default element is "shadow"
        score = _score_placement(state, 1, shadow_card, 0, {"c1": shadow_card})
        assert score == 1.0  # +1 for elemental match, no adjacent opponents

    def test_no_elemental_bonus_without_match(self) -> None:
        board_elements = ["blood"] * 9
        state = _ai_game_state(board_elements=board_elements, ai_hand=["c1"])
        shadow_card = make_card("c1")  # element is "shadow"
        score = _score_placement(state, 1, shadow_card, 0, {"c1": shadow_card})
        assert score == 0.0


class TestNoviceArchetypeUsage:
    """Novice archetype usage is inconsistent — sometimes used, sometimes not."""

    def test_archetype_sometimes_used(self) -> None:
        """Over many seeds, archetype should be used in some games but not all."""
        used_count = 0
        trials = 100
        for seed in range(trials):
            state = _ai_game_state(
                ai_hand=["c1", "c2", "c3", "c4", "c5"],
                ai_archetype=Archetype.SKULKER,
                seed=seed,
            )
            lookup = {f"c{i}": make_card(f"c{i}") for i in range(1, 6)}
            intent = choose_move(state, 1, AIDifficulty.EASY, lookup, Random(seed))
            if intent.use_archetype:
                used_count += 1

        assert 0 < used_count < trials, (
            f"Expected some but not all archetypes used, got {used_count}/{trials}"
        )

    def test_no_archetype_when_already_used(self) -> None:
        state = _ai_game_state(
            ai_hand=["c1", "c2", "c3", "c4", "c5"],
            ai_archetype=Archetype.SKULKER,
            ai_archetype_used=True,
        )
        lookup = {f"c{i}": make_card(f"c{i}") for i in range(1, 6)}
        for seed in range(20):
            intent = choose_move(state, 1, AIDifficulty.EASY, lookup, Random(seed))
            assert not intent.use_archetype

    def test_no_archetype_after_second_placement(self) -> None:
        """Novice only activates on 1st or 2nd placement (hand size 5 → 3+ placed)."""
        state = _ai_game_state(
            ai_hand=["c1", "c2"],  # 3 cards placed (5-2), past the 2nd placement
            ai_archetype=Archetype.MARTIAL,
        )
        lookup = {f"c{i}": make_card(f"c{i}") for i in range(1, 3)}
        for seed in range(20):
            intent = choose_move(state, 1, AIDifficulty.EASY, lookup, Random(seed))
            assert not intent.use_archetype

    def test_skip_flag_deterministic(self) -> None:
        """The 20% skip flag is deterministic for a given seed."""
        state = _ai_game_state(seed=42)
        result1 = _novice_should_skip_archetype(state, 1)
        result2 = _novice_should_skip_archetype(state, 1)
        assert result1 == result2

    @pytest.mark.parametrize("archetype", list(Archetype))
    def test_all_archetypes_produce_valid_intent(self, archetype: Archetype) -> None:
        """Each archetype type produces a valid PlacementIntent."""
        # For intimidate, place an opponent card adjacent to possible placements
        board: list[BoardCell | None] = [BoardCell(card_key="opp", owner=0)] + [None] * 8
        # Find a seed that doesn't skip archetype and does activate
        for seed in range(200):
            state = _ai_game_state(
                board=board,
                ai_hand=["c1", "c2", "c3", "c4", "c5"],
                ai_archetype=archetype,
                seed=seed,
            )
            lookup = {
                "opp": make_card("opp", n=1, e=1, s=1, w=1),
                **{f"c{i}": make_card(f"c{i}") for i in range(1, 6)},
            }
            intent = choose_move(state, 1, AIDifficulty.EASY, lookup, Random(seed))
            assert isinstance(intent, PlacementIntent)
            assert intent.card_key in state.players[1].hand
            if intent.use_archetype:
                break
        # Just verify no exception was raised for any archetype type


class TestChooseMoveDispatch:
    """choose_move dispatches to correct strategy by difficulty."""

    def test_easy_uses_novice(self) -> None:
        state = _ai_game_state()
        lookup = {f"c{i}": make_card(f"c{i}") for i in range(1, 6)}
        # Should not raise; uses novice path
        intent = choose_move(state, 1, AIDifficulty.EASY, lookup, Random(1))
        assert isinstance(intent, PlacementIntent)

    @pytest.mark.parametrize(
        "difficulty", [AIDifficulty.MEDIUM, AIDifficulty.HARD, AIDifficulty.NIGHTMARE]
    )
    def test_other_difficulties_use_random_fallback(self, difficulty: AIDifficulty) -> None:
        state = _ai_game_state()
        lookup = {f"c{i}": make_card(f"c{i}") for i in range(1, 6)}
        intent = choose_move(state, 1, difficulty, lookup, Random(1))
        assert isinstance(intent, PlacementIntent)
