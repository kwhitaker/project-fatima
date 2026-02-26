"""Storage boundary: GameStore and CardStore Protocol interfaces.

Implementations live in memory.py (in-memory, for tests) and supabase.py (production).
"""

from dataclasses import dataclass
from typing import Protocol

from app.models.cards import CardDefinition
from app.models.game import GameState


class ConflictError(Exception):
    """Raised when a state_version mismatch is detected (optimistic locking → 409)."""


@dataclass
class GameEvent:
    game_id: str
    seq: int  # 1-indexed, monotonically increasing per game
    event_type: str
    payload: dict  # type: ignore[type-arg]


class GameStore(Protocol):
    def create_game(self, game_id: str, initial_state: GameState) -> None: ...

    def get_game(self, game_id: str) -> GameState | None: ...

    def append_event(
        self,
        game_id: str,
        event_type: str,
        payload: dict,  # type: ignore[type-arg]
        expected_version: int,
        new_state: GameState,
    ) -> GameEvent:
        """Atomically insert an event and update the game snapshot.

        Raises ConflictError if current state_version != expected_version.
        Raises KeyError if game_id does not exist.
        """
        ...

    def get_events(self, game_id: str) -> list[GameEvent]: ...


class CardStore(Protocol):
    def get_card(self, card_key: str) -> CardDefinition | None: ...

    def list_cards(self) -> list[CardDefinition]: ...
