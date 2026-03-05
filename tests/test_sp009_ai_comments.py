"""Tests for US-SP-009: AI commentary system — model and backend.

Covers:
- ai_comment field on LastMoveInfo
- Comment pools exist for all triggers and difficulties
- Comments generated for capture triggers
- Comments match correct character personality
- Comment chance is roughly 30-50% over many runs
- No comments in human-vs-human games
- Human move reactions work
- AI move commentary works
"""

from collections.abc import Sequence
from random import Random

import pytest

from app.models.game import (
    AIDifficulty,
    Archetype,
    BoardCell,
    GameState,
    GameStatus,
    LastMoveInfo,
    PlayerState,
)
from app.rules.ai_comments import (
    _COMMENT_POOLS,
    detect_ai_move_triggers,
    detect_human_move_triggers,
    evaluate_ai_comment,
)
from app.services.game_service import AI_PLAYER_ID, attach_human_move_reaction
from app.store.memory import MemoryGameStore


def _ai_game_state(
    board: Sequence[BoardCell | None] | None = None,
    ai_hand: list[str] | None = None,
    human_hand: list[str] | None = None,
    ai_archetype: Archetype | None = Archetype.MARTIAL,
    ai_archetype_used: bool = False,
    current_player_index: int = 1,
    seed: int = 42,
    difficulty: AIDifficulty = AIDifficulty.EASY,
    last_move: LastMoveInfo | None = None,
    status: GameStatus = GameStatus.ACTIVE,
) -> GameState:
    """Build a GameState for AI comment testing with AI as player index 1."""
    return GameState(
        game_id="test-ai",
        status=status,
        seed=seed,
        current_player_index=current_player_index,
        board=list(board) if board is not None else [None] * 9,
        last_move=last_move,
        players=[
            PlayerState(
                player_id="human-p",
                archetype=Archetype.SKULKER,
                hand=human_hand or ["h1", "h2", "h3"],
            ),
            PlayerState(
                player_id=AI_PLAYER_ID,
                player_type="ai",
                ai_difficulty=difficulty,
                archetype=ai_archetype,
                archetype_used=ai_archetype_used,
                hand=ai_hand or ["a1", "a2", "a3"],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# LastMoveInfo.ai_comment field
# ---------------------------------------------------------------------------


class TestLastMoveInfoAiComment:
    def test_ai_comment_defaults_to_none(self):
        lm = LastMoveInfo(
            player_index=0, card_key="c1", cell_index=0, mists_roll=3, mists_effect="none"
        )
        assert lm.ai_comment is None

    def test_ai_comment_can_be_set(self):
        lm = LastMoveInfo(
            player_index=0,
            card_key="c1",
            cell_index=0,
            mists_roll=3,
            mists_effect="none",
            ai_comment="You amuse me, mortal.",
        )
        assert lm.ai_comment == "You amuse me, mortal."

    def test_ai_comment_survives_serialization(self):
        lm = LastMoveInfo(
            player_index=0,
            card_key="c1",
            cell_index=0,
            mists_roll=3,
            mists_effect="none",
            ai_comment="Predictable.",
        )
        data = lm.model_dump()
        restored = LastMoveInfo.model_validate(data)
        assert restored.ai_comment == "Predictable."


# ---------------------------------------------------------------------------
# Comment pools coverage
# ---------------------------------------------------------------------------


TRIGGERS = [
    "ai_captured_cards",
    "ai_got_captured",
    "plus_triggered",
    "elemental_triggered",
    "archetype_used",
    "game_ending",
]


class TestCommentPools:
    @pytest.mark.parametrize("difficulty", list(AIDifficulty))
    def test_all_difficulties_have_pools(self, difficulty: AIDifficulty):
        assert difficulty in _COMMENT_POOLS

    @pytest.mark.parametrize("difficulty", list(AIDifficulty))
    @pytest.mark.parametrize("trigger", TRIGGERS)
    def test_all_triggers_have_comments(self, difficulty: AIDifficulty, trigger: str):
        pool = _COMMENT_POOLS[difficulty]
        assert trigger in pool
        assert len(pool[trigger]) >= 5  # at least 5 comments per trigger


# ---------------------------------------------------------------------------
# Trigger detection
# ---------------------------------------------------------------------------


class TestDetectAiMoveTriggers:
    def test_capture_detected(self):
        before = _ai_game_state(
            board=[
                BoardCell(card_key="h1", owner=0), None, None,
                None, None, None,
                None, None, None,
            ],
            last_move=None,
        )
        after = _ai_game_state(
            board=[
                BoardCell(card_key="h1", owner=1),  # captured!
                None, None,
                BoardCell(card_key="a1", owner=1),  # AI placed
                None, None,
                None, None, None,
            ],
            last_move=LastMoveInfo(
                player_index=1, card_key="a1", cell_index=3,
                mists_roll=3, mists_effect="none",
            ),
        )
        triggers = detect_ai_move_triggers(before, after, ai_index=1)
        assert "ai_captured_cards" in triggers

    def test_no_capture_no_trigger(self):
        before = _ai_game_state(board=[None] * 9)
        after = _ai_game_state(
            board=[
                BoardCell(card_key="a1", owner=1), None, None,
                None, None, None,
                None, None, None,
            ],
            last_move=LastMoveInfo(
                player_index=1, card_key="a1", cell_index=0,
                mists_roll=3, mists_effect="none",
            ),
        )
        triggers = detect_ai_move_triggers(before, after, ai_index=1)
        assert "ai_captured_cards" not in triggers

    def test_plus_triggered(self):
        before = _ai_game_state(board=[None] * 9)
        after = _ai_game_state(
            board=[BoardCell(card_key="a1", owner=1)] + [None] * 8,
            last_move=LastMoveInfo(
                player_index=1, card_key="a1", cell_index=0,
                mists_roll=3, mists_effect="none",
                plus_triggered=True,
            ),
        )
        triggers = detect_ai_move_triggers(before, after, ai_index=1)
        assert "plus_triggered" in triggers

    def test_elemental_triggered(self):
        before = _ai_game_state(board=[None] * 9)
        after = _ai_game_state(
            board=[BoardCell(card_key="a1", owner=1)] + [None] * 8,
            last_move=LastMoveInfo(
                player_index=1, card_key="a1", cell_index=0,
                mists_roll=3, mists_effect="none",
                elemental_triggered=True,
            ),
        )
        triggers = detect_ai_move_triggers(before, after, ai_index=1)
        assert "elemental_triggered" in triggers

    def test_archetype_used(self):
        before = _ai_game_state(ai_archetype_used=False)
        after = _ai_game_state(
            ai_archetype_used=True,
            board=[BoardCell(card_key="a1", owner=1)] + [None] * 8,
            last_move=LastMoveInfo(
                player_index=1, card_key="a1", cell_index=0,
                mists_roll=3, mists_effect="none",
            ),
        )
        triggers = detect_ai_move_triggers(before, after, ai_index=1)
        assert "archetype_used" in triggers

    def test_game_ending(self):
        # Board full after move
        full_board = [BoardCell(card_key=f"c{i}", owner=i % 2) for i in range(9)]
        before = _ai_game_state(
            board=full_board[:8] + [None],
        )
        after = _ai_game_state(
            board=full_board,
            last_move=LastMoveInfo(
                player_index=1, card_key="c8", cell_index=8,
                mists_roll=3, mists_effect="none",
            ),
        )
        triggers = detect_ai_move_triggers(before, after, ai_index=1)
        assert "game_ending" in triggers


class TestDetectHumanMoveTriggers:
    def test_ai_got_captured(self):
        before = _ai_game_state(
            board=[
                BoardCell(card_key="a1", owner=1), None, None,
                None, None, None,
                None, None, None,
            ],
        )
        after = _ai_game_state(
            board=[
                BoardCell(card_key="a1", owner=0),  # flipped to human
                None, None,
                BoardCell(card_key="h1", owner=0),  # human placed
                None, None,
                None, None, None,
            ],
            last_move=LastMoveInfo(
                player_index=0, card_key="h1", cell_index=3,
                mists_roll=3, mists_effect="none",
            ),
        )
        triggers = detect_human_move_triggers(before, after, ai_index=1)
        assert "ai_got_captured" in triggers

    def test_no_capture_no_reaction(self):
        before = _ai_game_state(board=[None] * 9)
        after = _ai_game_state(
            board=[
                BoardCell(card_key="h1", owner=0), None, None,
                None, None, None,
                None, None, None,
            ],
            last_move=LastMoveInfo(
                player_index=0, card_key="h1", cell_index=0,
                mists_roll=3, mists_effect="none",
            ),
        )
        triggers = detect_human_move_triggers(before, after, ai_index=1)
        assert "ai_got_captured" not in triggers


# ---------------------------------------------------------------------------
# evaluate_ai_comment
# ---------------------------------------------------------------------------


class TestEvaluateAiComment:
    def test_returns_none_for_human_player(self):
        state = _ai_game_state()
        # Pass ai_index=0 which is the human player
        result = evaluate_ai_comment(
            state, ai_index=0, triggers=["ai_captured_cards"], rng=Random(1),
        )
        assert result is None

    def test_returns_none_when_no_triggers(self):
        state = _ai_game_state()
        result = evaluate_ai_comment(state, ai_index=1, triggers=[], rng=Random(1))
        assert result is None

    @pytest.mark.parametrize("difficulty,character_pool", [
        (AIDifficulty.EASY, "Ireena"),
        (AIDifficulty.MEDIUM, "Rahadin"),
        (AIDifficulty.HARD, "Strahd"),
        (AIDifficulty.NIGHTMARE, "Dark Powers"),
    ])
    def test_comment_from_correct_character(self, difficulty: AIDifficulty, character_pool: str):
        """When a comment IS generated, it comes from the correct pool."""
        state = _ai_game_state(difficulty=difficulty)
        pool = _COMMENT_POOLS[difficulty]["ai_captured_cards"]
        # Try many seeds until we get a comment
        for seed in range(100):
            comment = evaluate_ai_comment(
                state, ai_index=1, triggers=["ai_captured_cards"], rng=Random(seed)
            )
            if comment is not None:
                assert comment in pool, f"Comment '{comment}' not in {character_pool} pool"
                return
        pytest.fail(f"No comment generated after 100 attempts for {character_pool}")

    def test_comment_chance_roughly_30_to_50_percent(self):
        """Over many runs, comments should fire ~30-50% of the time."""
        state = _ai_game_state()
        count = 0
        trials = 1000
        for seed in range(trials):
            comment = evaluate_ai_comment(
                state, ai_index=1, triggers=["ai_captured_cards"], rng=Random(seed)
            )
            if comment is not None:
                count += 1
        rate = count / trials
        # Allow generous margin: 15-65% (the randomness is from both threshold and roll)
        assert 0.15 < rate < 0.65, f"Comment rate {rate:.2%} outside expected range"


# ---------------------------------------------------------------------------
# No comments in human-vs-human games
# ---------------------------------------------------------------------------


class TestNoCommentsInHumanGames:
    def test_no_comment_for_human_vs_human(self):
        state = GameState(
            game_id="test-human",
            status=GameStatus.ACTIVE,
            seed=42,
            current_player_index=0,
            board=[None] * 9,
            players=[
                PlayerState(player_id="p0", archetype=Archetype.MARTIAL, hand=["c1"]),
                PlayerState(player_id="p1", archetype=Archetype.SKULKER, hand=["c2"]),
            ],
        )
        # All players are human (default player_type)
        for seed in range(50):
            comment = evaluate_ai_comment(
                state, ai_index=0, triggers=["ai_captured_cards"], rng=Random(seed)
            )
            assert comment is None


# ---------------------------------------------------------------------------
# Integration: attach_human_move_reaction
# ---------------------------------------------------------------------------


class TestAttachHumanMoveReaction:
    def test_reaction_attached_on_capture(self):
        store = MemoryGameStore()
        before = _ai_game_state(
            board=[
                BoardCell(card_key="a1", owner=1), None, None,
                None, None, None,
                None, None, None,
            ],
        )
        after = _ai_game_state(
            board=[
                BoardCell(card_key="a1", owner=0),  # flipped
                None, None,
                BoardCell(card_key="h1", owner=0),  # human placed
                None, None,
                None, None, None,
            ],
            last_move=LastMoveInfo(
                player_index=0, card_key="h1", cell_index=3,
                mists_roll=3, mists_effect="none",
            ),
        )
        store.create_game("test-ai", after)

        # Try many seeds until we get a reaction
        found_comment = False
        for seed in range(50):
            state_with_seed = after.model_copy(update={"seed": seed})
            store._states["test-ai"] = state_with_seed
            attach_human_move_reaction(before, state_with_seed, store)
            result = store.get_game("test-ai")
            assert result is not None
            if result.last_move is not None and result.last_move.ai_comment is not None:
                found_comment = True
                # Comment should be from Ireena (easy difficulty)
                pool = _COMMENT_POOLS[AIDifficulty.EASY]["ai_got_captured"]
                assert result.last_move.ai_comment in pool
                break

        assert found_comment, "Expected at least one comment across 50 seeds"

    def test_no_reaction_in_human_game(self):
        store = MemoryGameStore()
        state = GameState(
            game_id="test-human",
            status=GameStatus.ACTIVE,
            seed=42,
            current_player_index=0,
            board=[
                BoardCell(card_key="c1", owner=0), None, None,
                None, None, None,
                None, None, None,
            ],
            last_move=LastMoveInfo(
                player_index=0, card_key="c1", cell_index=0,
                mists_roll=3, mists_effect="none",
            ),
            players=[
                PlayerState(player_id="p0", archetype=Archetype.MARTIAL, hand=["c2"]),
                PlayerState(player_id="p1", archetype=Archetype.SKULKER, hand=["c3"]),
            ],
        )
        store.create_game("test-human", state)
        before = state.model_copy(update={"board": [None] * 9})
        attach_human_move_reaction(before, state, store)
        result = store.get_game("test-human")
        assert result is not None
        assert result.last_move is not None
        assert result.last_move.ai_comment is None
