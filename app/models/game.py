from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class Archetype(str, Enum):
    MARTIAL = "martial"
    SKULKER = "skulker"
    CASTER = "caster"
    DEVOUT = "devout"
    PRESENCE = "presence"


class GameStatus(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    COMPLETE = "complete"


class BoardCell(BaseModel):
    card_key: str
    owner: Annotated[int, Field(ge=0, le=1)]


class PlayerState(BaseModel):
    player_id: str
    archetype: Archetype | None = None
    hand: list[str] = []
    archetype_used: bool = False


class GameResult(BaseModel):
    winner: int | None  # player index (0 or 1), or None for draw
    is_draw: bool


class GameState(BaseModel):
    game_id: str
    state_version: int = 0
    round_number: int = 1
    sudden_death_rounds_used: int = 0
    status: GameStatus = GameStatus.WAITING
    players: list[PlayerState] = []
    board: list[BoardCell | None] = Field(default_factory=lambda: [None] * 9)
    current_player_index: int = 0
    result: GameResult | None = None
    seed: int = 0
