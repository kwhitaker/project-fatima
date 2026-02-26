"""Supabase-backed GameStore implementation.

Reads SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from environment variables.
Uses the service role key which bypasses RLS for all server-side writes.
Inject a client instance directly (e.g., a MagicMock) to use without env vars.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from app.models.game import GameState
from app.store import ConflictError, DuplicateEventError, GameEvent

if TYPE_CHECKING:
    from supabase import Client


class SupabaseGameStore:
    """GameStore backed by Supabase REST API (PostgREST + service role key).

    Optimistic locking is implemented via a conditional UPDATE:
      UPDATE games SET ... WHERE id = ? AND state_version = expected_version
    If 0 rows are updated the caller either used a stale version (ConflictError)
    or the game does not exist (KeyError).
    """

    def __init__(self, client: Client | None = None) -> None:
        if client is None:
            from supabase import create_client

            url = os.environ["SUPABASE_URL"]
            key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
            client = create_client(url, key)
        self._client: Any = client

    # ------------------------------------------------------------------
    # GameStore interface
    # ------------------------------------------------------------------

    def create_game(self, game_id: str, initial_state: GameState) -> None:
        self._client.table("games").upsert(
            {
                "id": game_id,
                "current_state": initial_state.model_dump(mode="json"),
                "state_version": initial_state.state_version,
                "seed": initial_state.seed,
                "status": initial_state.status.value,
            }
        ).execute()

    def has_idempotency_key(self, game_id: str, idempotency_key: str) -> bool:
        response = (
            self._client.table("game_events")
            .select("seq")
            .eq("game_id", game_id)
            .eq("idempotency_key", idempotency_key)
            .maybe_single()
            .execute()
        )
        return response.data is not None

    def get_game(self, game_id: str) -> GameState | None:
        response = (
            self._client.table("games")
            .select("current_state")
            .eq("id", game_id)
            .maybe_single()
            .execute()
        )
        if response.data is None:
            return None
        return GameState.model_validate(response.data["current_state"])

    def append_event(
        self,
        game_id: str,
        event_type: str,
        payload: dict,  # type: ignore[type-arg]
        expected_version: int,
        new_state: GameState,
        idempotency_key: str | None = None,
    ) -> GameEvent:
        """Insert an event and update the snapshot atomically (optimistic lock).

        Raises ConflictError if current state_version != expected_version.
        Raises KeyError if game_id does not exist.
        Raises DuplicateEventError if idempotency_key was already used for this game.
        """
        if idempotency_key is not None:
            dup_response = (
                self._client.table("game_events")
                .select("seq")
                .eq("game_id", game_id)
                .eq("idempotency_key", idempotency_key)
                .maybe_single()
                .execute()
            )
            if dup_response.data is not None:
                raise DuplicateEventError(
                    f"Idempotency key {idempotency_key!r} already used for game {game_id!r}"
                )

        update_response = (
            self._client.table("games")
            .update(
                {
                    "current_state": new_state.model_dump(mode="json"),
                    "state_version": new_state.state_version,
                    "status": new_state.status.value,
                }
            )
            .eq("id", game_id)
            .eq("state_version", expected_version)
            .execute()
        )

        if not update_response.data:
            # Distinguish missing game from version conflict
            check = (
                self._client.table("games")
                .select("state_version")
                .eq("id", game_id)
                .maybe_single()
                .execute()
            )
            if check.data is None:
                raise KeyError(f"Game {game_id!r} does not exist")
            raise ConflictError(
                f"Version conflict for game {game_id!r}: "
                f"expected {expected_version}, got {check.data['state_version']}"
            )

        # Determine the next seq from existing events
        seq_response = (
            self._client.table("game_events")
            .select("seq")
            .eq("game_id", game_id)
            .order("seq", desc=True)
            .limit(1)
            .execute()
        )
        seq = (seq_response.data[0]["seq"] + 1) if seq_response.data else 1

        event_row: dict[str, Any] = {
            "game_id": game_id,
            "seq": seq,
            "event_type": event_type,
            "payload": payload,
        }
        if idempotency_key is not None:
            event_row["idempotency_key"] = idempotency_key
        self._client.table("game_events").insert(event_row).execute()

        return GameEvent(game_id=game_id, seq=seq, event_type=event_type, payload=payload)

    def get_events(self, game_id: str) -> list[GameEvent]:
        response = (
            self._client.table("game_events")
            .select("seq, event_type, payload")
            .eq("game_id", game_id)
            .order("seq")
            .execute()
        )
        return [
            GameEvent(
                game_id=game_id,
                seq=row["seq"],
                event_type=row["event_type"],
                payload=row["payload"],
            )
            for row in (response.data or [])
        ]
