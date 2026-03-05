"""Tests for US-SP-017: AI commentary win/loss canned responses.

Covers:
- game_won and game_lost comment pools exist for all difficulties
- AI comments on winning (game_won trigger, 100% chance)
- AI comments on losing (game_lost trigger, 100% chance)
- Draw uses game_ending (not game_won/game_lost)
- Correct character flavor per difficulty
- Both detect_ai_move_triggers and detect_human_move_triggers handle win/loss
"""

from random import Random

import pytest

from app.models.game import (
    AIDifficulty,
    Archetype,
    BoardCell,
    GameResult,
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
from app.services.game_service import AI_PLAYER_ID


def _game(
    ai_index: int = 1,
    difficulty: AIDifficulty = AIDifficulty.EASY,
    status: GameStatus = GameStatus.COMPLETE,
    result: GameResult | None = None,
    board: list[BoardCell | None] | None = None,
    last_move: LastMoveInfo | None = None,
) -> GameState:
    human = PlayerState(
        player_id="human-p",
        archetype=Archetype.SKULKER,
        hand=[],
    )
    ai = PlayerState(
        player_id=AI_PLAYER_ID,
        player_type="ai",
        ai_difficulty=difficulty,
        archetype=Archetype.MARTIAL,
        hand=["extra"],
    )
    players = [human, ai] if ai_index == 1 else [ai, human]
    full_board: list[BoardCell | None] = board or [
        BoardCell(card_key=f"c{i}", owner=i % 2) for i in range(9)
    ]
    return GameState(
        game_id="test-wl",
        status=status,
        seed=42,
        current_player_index=0,
        board=full_board,
        last_move=last_move or LastMoveInfo(
            player_index=ai_index, card_key="c8", cell_index=8,
            mists_roll=3, mists_effect="none",
        ),
        result=result,
        players=players,
    )


# ---------------------------------------------------------------------------
# Comment pool coverage
# ---------------------------------------------------------------------------


class TestWinLossPoolsExist:
    @pytest.mark.parametrize("difficulty", list(AIDifficulty))
    @pytest.mark.parametrize("trigger", ["game_won", "game_lost"])
    def test_pool_exists_with_5_entries(self, difficulty: AIDifficulty, trigger: str):
        pool = _COMMENT_POOLS[difficulty]
        assert trigger in pool
        assert len(pool[trigger]) >= 5


# ---------------------------------------------------------------------------
# Trigger detection: AI move
# ---------------------------------------------------------------------------


class TestAiMoveTriggers:
    def test_ai_win_triggers_game_won(self):
        before = _game(status=GameStatus.ACTIVE, result=None, board=[None] + [BoardCell(card_key=f"c{i}", owner=i % 2) for i in range(8)])
        after = _game(status=GameStatus.COMPLETE, result=GameResult(winner=1, is_draw=False))
        triggers = detect_ai_move_triggers(before, after, ai_index=1)
        assert "game_won" in triggers
        assert "game_ending" not in triggers

    def test_ai_loss_triggers_game_lost(self):
        before = _game(status=GameStatus.ACTIVE, result=None, board=[None] + [BoardCell(card_key=f"c{i}", owner=i % 2) for i in range(8)])
        after = _game(status=GameStatus.COMPLETE, result=GameResult(winner=0, is_draw=False))
        triggers = detect_ai_move_triggers(before, after, ai_index=1)
        assert "game_lost" in triggers
        assert "game_ending" not in triggers

    def test_draw_triggers_game_ending(self):
        before = _game(status=GameStatus.ACTIVE, result=None, board=[None] + [BoardCell(card_key=f"c{i}", owner=i % 2) for i in range(8)])
        after = _game(status=GameStatus.COMPLETE, result=GameResult(winner=None, is_draw=True))
        triggers = detect_ai_move_triggers(before, after, ai_index=1)
        assert "game_ending" in triggers
        assert "game_won" not in triggers
        assert "game_lost" not in triggers


# ---------------------------------------------------------------------------
# Trigger detection: human move
# ---------------------------------------------------------------------------


class TestHumanMoveTriggers:
    def test_human_wins_triggers_game_lost_for_ai(self):
        before = _game(status=GameStatus.ACTIVE, result=None, board=[None] + [BoardCell(card_key=f"c{i}", owner=i % 2) for i in range(8)])
        after = _game(
            status=GameStatus.COMPLETE,
            result=GameResult(winner=0, is_draw=False),
            last_move=LastMoveInfo(player_index=0, card_key="c0", cell_index=0, mists_roll=3, mists_effect="none"),
        )
        triggers = detect_human_move_triggers(before, after, ai_index=1)
        assert "game_lost" in triggers
        assert "game_ending" not in triggers

    def test_human_loses_triggers_game_won_for_ai(self):
        before = _game(status=GameStatus.ACTIVE, result=None, board=[None] + [BoardCell(card_key=f"c{i}", owner=i % 2) for i in range(8)])
        after = _game(
            status=GameStatus.COMPLETE,
            result=GameResult(winner=1, is_draw=False),
            last_move=LastMoveInfo(player_index=0, card_key="c0", cell_index=0, mists_roll=3, mists_effect="none"),
        )
        triggers = detect_human_move_triggers(before, after, ai_index=1)
        assert "game_won" in triggers


# ---------------------------------------------------------------------------
# evaluate_ai_comment: guaranteed triggers
# ---------------------------------------------------------------------------


class TestEvaluateWinLoss:
    def test_game_won_always_produces_comment(self):
        """game_won has 100% chance, should always produce a comment."""
        state = _game(difficulty=AIDifficulty.HARD)
        for seed in range(50):
            rng = Random(seed)
            comment = evaluate_ai_comment(state, ai_index=1, triggers=["game_won"], rng=rng)
            assert comment is not None
            assert comment in _COMMENT_POOLS[AIDifficulty.HARD]["game_won"]

    def test_game_lost_always_produces_comment(self):
        """game_lost has 100% chance, should always produce a comment."""
        state = _game(difficulty=AIDifficulty.EASY)
        for seed in range(50):
            rng = Random(seed)
            comment = evaluate_ai_comment(state, ai_index=1, triggers=["game_lost"], rng=rng)
            assert comment is not None
            assert comment in _COMMENT_POOLS[AIDifficulty.EASY]["game_lost"]

    @pytest.mark.parametrize(
        "difficulty,trigger,sample_fragment",
        [
            (AIDifficulty.EASY, "game_won", "won"),
            (AIDifficulty.EASY, "game_lost", "fun"),
            (AIDifficulty.MEDIUM, "game_won", "question"),
            (AIDifficulty.MEDIUM, "game_lost", "Noted"),
            (AIDifficulty.HARD, "game_won", "Kneel"),
            (AIDifficulty.HARD, "game_lost", "Enjoy"),
            (AIDifficulty.NIGHTMARE, "game_won", "meant"),
            (AIDifficulty.NIGHTMARE, "game_lost", "nothing"),
        ],
    )
    def test_correct_character_flavor(
        self, difficulty: AIDifficulty, trigger: str, sample_fragment: str
    ):
        """Each character's win/loss pool contains expected thematic words."""
        pool = _COMMENT_POOLS[difficulty][trigger]
        assert any(sample_fragment in line for line in pool)

    def test_no_comment_for_human_vs_human(self):
        """game_won/game_lost should not produce comments in human games."""
        state = GameState(
            game_id="pvp",
            status=GameStatus.COMPLETE,
            seed=42,
            current_player_index=0,
            board=[BoardCell(card_key=f"c{i}", owner=i % 2) for i in range(9)],
            players=[
                PlayerState(player_id="p1", archetype=Archetype.SKULKER, hand=[]),
                PlayerState(player_id="p2", archetype=Archetype.MARTIAL, hand=["x"]),
            ],
        )
        rng = Random(1)
        assert evaluate_ai_comment(state, ai_index=1, triggers=["game_won"], rng=rng) is None
