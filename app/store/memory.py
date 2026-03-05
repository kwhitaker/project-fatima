"""In-memory implementations of GameStore and CardStore.

Used in tests and local development; no external dependencies.
"""

from app.models.cards import CardDefinition
from app.models.game import GameState, GameStatus
from app.store import ConflictError, DuplicateEventError, GameEvent


class MemoryGameStore:
    """Append-only event log + snapshot cache, entirely in-process."""

    def __init__(self) -> None:
        self._states: dict[str, GameState] = {}
        self._events: dict[str, list[GameEvent]] = {}
        self._idempotency_keys: dict[str, set[str]] = {}

    def create_game(self, game_id: str, initial_state: GameState) -> None:
        self._states[game_id] = initial_state
        self._events[game_id] = []
        self._idempotency_keys[game_id] = set()

    def get_game(self, game_id: str) -> GameState | None:
        return self._states.get(game_id)

    def list_games_for_player(self, player_id: str) -> list[GameState]:
        return [
            state
            for state in self._states.values()
            if any(p.player_id == player_id for p in state.players)
        ]

    def list_open_games(self, exclude_player_id: str) -> list[GameState]:
        return [
            state
            for state in self._states.values()
            if state.status == GameStatus.WAITING
            and len(state.players) == 1
            and not any(p.player_id == exclude_player_id for p in state.players)
        ]

    def has_idempotency_key(self, game_id: str, idempotency_key: str) -> bool:
        return idempotency_key in self._idempotency_keys.get(game_id, set())

    def append_event(
        self,
        game_id: str,
        event_type: str,
        payload: dict,  # type: ignore[type-arg]
        expected_version: int,
        new_state: GameState,
        idempotency_key: str | None = None,
    ) -> GameEvent:
        """Atomically insert event and update snapshot.

        Raises KeyError if game_id does not exist.
        Raises ConflictError if current state_version != expected_version.
        Raises DuplicateEventError if idempotency_key was already used for this game.
        """
        current = self._states.get(game_id)
        if current is None:
            raise KeyError(f"Game {game_id!r} does not exist")
        if idempotency_key is not None and idempotency_key in self._idempotency_keys[game_id]:
            raise DuplicateEventError(
                f"Idempotency key {idempotency_key!r} already used for game {game_id!r}"
            )
        if current.state_version != expected_version:
            raise ConflictError(
                f"Version conflict for game {game_id!r}: "
                f"expected {expected_version}, got {current.state_version}"
            )
        seq = len(self._events[game_id]) + 1
        event = GameEvent(game_id=game_id, seq=seq, event_type=event_type, payload=payload)
        self._events[game_id].append(event)
        self._states[game_id] = new_state
        if idempotency_key is not None:
            self._idempotency_keys[game_id].add(idempotency_key)
        return event

    def delete_game(self, game_id: str, expected_version: int) -> None:
        """Delete a game and all its events (optimistic lock).

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
        del self._states[game_id]
        del self._events[game_id]
        self._idempotency_keys.pop(game_id, None)

    def update_state(self, game_id: str, new_state: GameState) -> None:
        if game_id not in self._states:
            raise KeyError(f"Game {game_id!r} does not exist")
        self._states[game_id] = new_state

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
