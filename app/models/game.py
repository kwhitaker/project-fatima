from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class AIDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    NIGHTMARE = "nightmare"


class Archetype(str, Enum):
    MARTIAL = "martial"
    SKULKER = "skulker"
    CASTER = "caster"
    DEVOUT = "devout"
    INTIMIDATE = "intimidate"


class GameStatus(str, Enum):
    WAITING = "waiting"
    DRAFTING = "drafting"
    ACTIVE = "active"
    COMPLETE = "complete"


class BoardCell(BaseModel):
    card_key: str
    owner: Annotated[int, Field(ge=0, le=1)]


class PlayerState(BaseModel):
    player_id: str
    email: str | None = None
    player_type: Literal["human", "ai"] = "human"
    ai_difficulty: AIDifficulty | None = None
    archetype: Archetype | None = None
    deal: list[str] = []  # 7 dealt cards before draft selection; empty after draft
    hand: list[str] = []  # 5 selected cards (populated after draft)
    archetype_used: bool = False


class GameResult(BaseModel):
    winner: int | None  # player index (0 or 1), or None for draw
    is_draw: bool
    completion_reason: str | None = None  # "normal" | "forfeit"
    forfeit_by_index: int | None = None  # player index who forfeited (only when reason="forfeit")
    early_finish: bool = False  # True when game ended because outcome was mathematically decided


class LastMoveInfo(BaseModel):
    player_index: int  # 0 or 1
    card_key: str
    cell_index: int  # 0-8
    mists_roll: int  # 1-6 die result
    mists_effect: str  # "fog" | "omen" | "none"
    plus_triggered: bool = False  # True when the Plus rule fired this placement
    elemental_triggered: bool = False  # True when elemental bonus (+1) was applied
    ai_comment: str | None = None  # In-character AI comment (single-player only)
    archetype_used_name: str | None = None  # Archetype name when power was used this move
    skulker_boost_side: str | None = None  # Which side was boosted (n/e/s/w) for Skulker UI
    martial_rotation_direction: str | None = None  # Rotation direction (cw/ccw) for Martial UI
    intimidate_target_cell: int | None = None  # Cell targeted by Intimidate (for UI highlight)
    warded_cell: int | None = None  # Cell protected by Devout Ward (for UI highlight)


class GameState(BaseModel):
    game_id: str
    state_version: int = 0
    round_number: int = 1
    sudden_death_rounds_used: int = 0
    status: GameStatus = GameStatus.WAITING
    players: list[PlayerState] = []
    board: list[BoardCell | None] = Field(default_factory=lambda: [None] * 9)
    current_player_index: int = 0
    starting_player_index: int = 0  # set when game becomes ACTIVE; drives SD alternation
    result: GameResult | None = None
    seed: int = 0
    last_move: LastMoveInfo | None = None
    warded_cell: int | None = None  # Devout Ward; cleared after one opponent placement
    board_elements: list[str] | None = None  # one element per cell (0-8); None for old snapshots
    created_at: str | None = None  # ISO-8601 UTC timestamp; None for old snapshots

    @model_validator(mode="before")
    @classmethod
    def _drop_legacy_last_move(cls, data: object) -> object:
        """Drop legacy/partial last_move payloads.

        Older snapshots stored only mists fields in last_move. We keep the
        current LastMoveInfo schema strict; partial payloads are treated as if
        last_move was not present.
        """
        if not isinstance(data, dict):
            return data
        last_move = data.get("last_move")
        if not isinstance(last_move, dict):
            return data

        required = {"player_index", "card_key", "cell_index"}
        if not required.issubset(last_move.keys()):
            new_data = dict(data)
            new_data["last_move"] = None
            return new_data
        return data
