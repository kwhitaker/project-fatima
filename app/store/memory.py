"""In-memory implementations of GameStore and CardStore.

Used in tests and local development; no external dependencies.
"""

from app.models.cards import CardDefinition
from app.models.game import GameState
from app.store import ConflictError, GameEvent


class MemoryGameStore:
    """Append-only event log + snapshot cache, entirely in-process."""

    def __init__(self) -> None:
        self._states: dict[str, GameState] = {}
        self._events: dict[str, list[GameEvent]] = {}

    def create_game(self, game_id: str, initial_state: GameState) -> None:
        self._states[game_id] = initial_state
        self._events[game_id] = []

    def get_game(self, game_id: str) -> GameState | None:
        return self._states.get(game_id)

    def append_event(
        self,
        game_id: str,
        event_type: str,
        payload: dict,  # type: ignore[type-arg]
        expected_version: int,
        new_state: GameState,
    ) -> GameEvent:
        """Atomically insert event and update snapshot.

        Raises KeyError if game_id does not exist.
        Raises ConflictError if current state_version != expected_version.
        """
        current = self._states.get(game_id)
        if current is None:
            raise KeyError(f"Game {game_id!r} does not exist")
        if current.state_version != expected_version:
            raise ConflictError(
                f"Version conflict for game {game_id!r}: "
                f"expected {expected_version}, got {current.state_version}"
            )
        seq = len(self._events[game_id]) + 1
        event = GameEvent(game_id=game_id, seq=seq, event_type=event_type, payload=payload)
        self._events[game_id].append(event)
        self._states[game_id] = new_state
        return event

    def get_events(self, game_id: str) -> list[GameEvent]:
        return list(self._events.get(game_id, []))


class MemoryCardStore:
    """Simple card registry backed by a dict."""

    def __init__(self, cards: list[CardDefinition] | None = None) -> None:
        self._cards: dict[str, CardDefinition] = {}
        if cards:
            for card in cards:
                self._cards[card.card_key] = card

    def get_card(self, card_key: str) -> CardDefinition | None:
        return self._cards.get(card_key)

    def list_cards(self) -> list[CardDefinition]:
        return list(self._cards.values())
