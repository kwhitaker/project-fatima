"""Tests for US-SP-001: AI difficulty enum and PlayerState model changes."""

import pytest
from pydantic import ValidationError

from app.models.game import AIDifficulty, GameState, GameStatus, PlayerState
from app.services.game_service import AI_DISPLAY_NAMES, AI_PLAYER_ID


class TestAIDifficultyEnum:
    @pytest.mark.parametrize(
        "value",
        ["easy", "medium", "hard", "nightmare"],
    )
    def test_valid_values(self, value: str) -> None:
        assert AIDifficulty(value).value == value

    def test_invalid_value_rejected(self) -> None:
        with pytest.raises(ValueError):
            AIDifficulty("impossible")


class TestPlayerStateAIFields:
    def test_defaults_to_human(self) -> None:
        p = PlayerState(player_id="p1")
        assert p.player_type == "human"
        assert p.ai_difficulty is None

    def test_ai_player(self) -> None:
        p = PlayerState(
            player_id=AI_PLAYER_ID,
            player_type="ai",
            ai_difficulty=AIDifficulty.HARD,
        )
        assert p.player_type == "ai"
        assert p.ai_difficulty == AIDifficulty.HARD

    def test_invalid_player_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PlayerState(player_id="p1", player_type="bot")  # type: ignore[arg-type]

    def test_serialization_roundtrip(self) -> None:
        p = PlayerState(
            player_id=AI_PLAYER_ID,
            player_type="ai",
            ai_difficulty=AIDifficulty.EASY,
        )
        data = p.model_dump()
        assert data["player_type"] == "ai"
        assert data["ai_difficulty"] == "easy"
        p2 = PlayerState.model_validate(data)
        assert p2 == p


class TestGameStateBackwardCompat:
    def test_old_snapshot_without_ai_fields(self) -> None:
        """Old snapshots without player_type/ai_difficulty still deserialize."""
        raw = {
            "game_id": "g1",
            "seed": 42,
            "players": [
                {"player_id": "p1"},
                {"player_id": "p2"},
            ],
        }
        state = GameState.model_validate(raw)
        assert state.players[0].player_type == "human"
        assert state.players[0].ai_difficulty is None
        assert state.players[1].player_type == "human"

    def test_game_state_with_ai_player_roundtrip(self) -> None:
        state = GameState(
            game_id="g1",
            seed=42,
            status=GameStatus.ACTIVE,
            players=[
                PlayerState(player_id="human1"),
                PlayerState(
                    player_id=AI_PLAYER_ID,
                    player_type="ai",
                    ai_difficulty=AIDifficulty.NIGHTMARE,
                ),
            ],
        )
        data = state.model_dump()
        state2 = GameState.model_validate(data)
        assert state2.players[1].player_type == "ai"
        assert state2.players[1].ai_difficulty == AIDifficulty.NIGHTMARE


class TestAIConstants:
    def test_ai_player_id_is_valid_uuid(self) -> None:
        import uuid

        uuid.UUID(AI_PLAYER_ID)  # raises if invalid

    def test_display_names_cover_all_difficulties(self) -> None:
        for diff in AIDifficulty:
            assert diff in AI_DISPLAY_NAMES
            assert isinstance(AI_DISPLAY_NAMES[diff], str)

    @pytest.mark.parametrize(
        "difficulty,expected_name",
        [
            (AIDifficulty.EASY, "Ireena Kolyana"),
            (AIDifficulty.MEDIUM, "Rahadin"),
            (AIDifficulty.HARD, "Strahd von Zarovich"),
            (AIDifficulty.NIGHTMARE, "The Dark Powers"),
        ],
    )
    def test_display_name_values(self, difficulty: AIDifficulty, expected_name: str) -> None:
        assert AI_DISPLAY_NAMES[difficulty] == expected_name
