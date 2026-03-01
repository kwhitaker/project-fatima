"""Unit tests for SupabaseGameStore using mock Supabase client.

No real Supabase credentials are required: the client is injected directly.
"""

from unittest.mock import MagicMock

import pytest

from app.models.game import GameState, GameStatus
from app.store import ConflictError
from app.store.supabase_store import SupabaseGameStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_state(game_id: str = "g1", version: int = 0, seed: int = 42) -> GameState:
    return GameState(game_id=game_id, state_version=version, seed=seed)


@pytest.fixture
def mock_client():
    """Returns (client, games_table_mock, events_table_mock) with table routing."""
    client = MagicMock()
    games_table = MagicMock()
    events_table = MagicMock()

    def _table(name: str) -> MagicMock:
        return games_table if name == "games" else events_table

    client.table.side_effect = _table
    return client, games_table, events_table


# ---------------------------------------------------------------------------
# create_game
# ---------------------------------------------------------------------------


class TestCreateGame:
    def test_upserts_with_correct_fields(self, mock_client: tuple) -> None:
        client, games_table, _ = mock_client
        store = SupabaseGameStore(client=client)
        state = make_state()

        store.create_game("g1", state)

        games_table.upsert.assert_called_once()
        row = games_table.upsert.call_args[0][0]
        assert row["id"] == "g1"
        assert row["state_version"] == 0
        assert row["seed"] == 42
        assert row["status"] == GameStatus.WAITING.value
        assert "current_state" in row

    def test_execute_is_called(self, mock_client: tuple) -> None:
        client, games_table, _ = mock_client
        store = SupabaseGameStore(client=client)

        store.create_game("g1", make_state())

        games_table.upsert.return_value.execute.assert_called_once()


# ---------------------------------------------------------------------------
# get_game
# ---------------------------------------------------------------------------


class TestGetGame:
    def test_returns_game_state_when_found(self, mock_client: tuple) -> None:
        client, games_table, _ = mock_client
        state = make_state()
        state_dict = state.model_dump(mode="json")
        (
            games_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data
        ) = {"current_state": state_dict}

        store = SupabaseGameStore(client=client)
        result = store.get_game("g1")

        assert result is not None
        assert result.game_id == "g1"
        assert result.state_version == 0

    def test_returns_none_when_not_found(self, mock_client: tuple) -> None:
        client, games_table, _ = mock_client
        (
            games_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data
        ) = None

        store = SupabaseGameStore(client=client)
        assert store.get_game("missing") is None

    def test_select_selects_current_state(self, mock_client: tuple) -> None:
        client, games_table, _ = mock_client
        state_dict = make_state().model_dump(mode="json")
        (
            games_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data
        ) = {"current_state": state_dict}

        SupabaseGameStore(client=client).get_game("g1")

        games_table.select.assert_called_once_with("current_state")


# ---------------------------------------------------------------------------
# append_event — success path
# ---------------------------------------------------------------------------


class TestAppendEventSuccess:
    def _setup_success(
        self, games_table: MagicMock, events_table: MagicMock, existing_seq: int | None
    ) -> None:
        # Conditional update returns a row (success)
        (
            games_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data
        ) = [{"id": "g1"}]
        # Max seq query
        seq_data = [{"seq": existing_seq}] if existing_seq is not None else []
        (
            events_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data
        ) = seq_data

    def test_returns_event_with_seq_1_for_first_event(self, mock_client: tuple) -> None:
        client, games_table, events_table = mock_client
        self._setup_success(games_table, events_table, existing_seq=None)

        store = SupabaseGameStore(client=client)
        event = store.append_event("g1", "MOVE", {"pos": 4}, 0, make_state(version=1))

        assert event.seq == 1
        assert event.game_id == "g1"
        assert event.event_type == "MOVE"
        assert event.payload == {"pos": 4}

    def test_seq_increments_from_existing_max(self, mock_client: tuple) -> None:
        client, games_table, events_table = mock_client
        self._setup_success(games_table, events_table, existing_seq=3)

        store = SupabaseGameStore(client=client)
        event = store.append_event("g1", "MOVE", {}, 3, make_state(version=4))

        assert event.seq == 4

    def test_calls_update_with_new_state(self, mock_client: tuple) -> None:
        client, games_table, events_table = mock_client
        self._setup_success(games_table, events_table, existing_seq=None)

        new_state = make_state(version=1)
        SupabaseGameStore(client=client).append_event("g1", "MOVE", {}, 0, new_state)

        games_table.update.assert_called_once()
        update_data = games_table.update.call_args[0][0]
        assert update_data["state_version"] == 1

    def test_insert_is_called_with_correct_payload(self, mock_client: tuple) -> None:
        client, games_table, events_table = mock_client
        self._setup_success(games_table, events_table, existing_seq=None)

        store = SupabaseGameStore(client=client)
        store.append_event("g1", "MOVE", {"x": 7}, 0, make_state(version=1))

        events_table.insert.assert_called_once()
        insert_data = events_table.insert.call_args[0][0]
        assert insert_data["game_id"] == "g1"
        assert insert_data["seq"] == 1
        assert insert_data["event_type"] == "MOVE"
        assert insert_data["payload"] == {"x": 7}


# ---------------------------------------------------------------------------
# append_event — conflict / missing paths
# ---------------------------------------------------------------------------


class TestAppendEventConflict:
    def _setup_update_returns_empty(self, games_table: MagicMock) -> None:
        (
            games_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data
        ) = []

    def test_raises_conflict_error_when_version_mismatch(self, mock_client: tuple) -> None:
        client, games_table, _ = mock_client
        self._setup_update_returns_empty(games_table)
        # Game exists with a different version
        (
            games_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data
        ) = {"state_version": 5}

        store = SupabaseGameStore(client=client)
        with pytest.raises(ConflictError, match="Version conflict"):
            store.append_event(
                "g1", "MOVE", {}, expected_version=0, new_state=make_state(version=1)
            )

    def test_conflict_error_includes_version_info(self, mock_client: tuple) -> None:
        client, games_table, _ = mock_client
        self._setup_update_returns_empty(games_table)
        (
            games_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data
        ) = {"state_version": 9}

        store = SupabaseGameStore(client=client)
        with pytest.raises(ConflictError, match="expected 0, got 9"):
            store.append_event(
                "g1", "MOVE", {}, expected_version=0, new_state=make_state(version=1)
            )

    def test_raises_key_error_when_game_missing(self, mock_client: tuple) -> None:
        client, games_table, _ = mock_client
        self._setup_update_returns_empty(games_table)
        # Confirmation query returns None (game does not exist)
        (
            games_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data
        ) = None

        store = SupabaseGameStore(client=client)
        with pytest.raises(KeyError, match="does not exist"):
            store.append_event(
                "missing", "MOVE", {}, expected_version=0, new_state=make_state(version=1)
            )

    def test_no_insert_on_conflict(self, mock_client: tuple) -> None:
        client, games_table, events_table = mock_client
        self._setup_update_returns_empty(games_table)
        (
            games_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data
        ) = {"state_version": 3}

        store = SupabaseGameStore(client=client)
        with pytest.raises(ConflictError):
            store.append_event(
                "g1", "MOVE", {}, expected_version=0, new_state=make_state(version=1)
            )

        events_table.insert.assert_not_called()


# ---------------------------------------------------------------------------
# get_events
# ---------------------------------------------------------------------------


class TestGetEvents:
    def test_returns_ordered_events(self, mock_client: tuple) -> None:
        client, _, events_table = mock_client
        (
            events_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data
        ) = [
            {"seq": 1, "event_type": "CREATE", "payload": {}},
            {"seq": 2, "event_type": "MOVE", "payload": {"pos": 4}},
        ]

        store = SupabaseGameStore(client=client)
        events = store.get_events("g1")

        assert len(events) == 2
        assert events[0].seq == 1
        assert events[0].event_type == "CREATE"
        assert events[1].seq == 2
        assert events[1].payload == {"pos": 4}

    def test_returns_empty_list_when_no_events(self, mock_client: tuple) -> None:
        client, _, events_table = mock_client
        (
            events_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data
        ) = []

        store = SupabaseGameStore(client=client)
        assert store.get_events("g1") == []

    def test_events_have_correct_game_id(self, mock_client: tuple) -> None:
        client, _, events_table = mock_client
        (
            events_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data
        ) = [{"seq": 1, "event_type": "X", "payload": {}}]

        store = SupabaseGameStore(client=client)
        events = store.get_events("g42")
        assert events[0].game_id == "g42"


# ---------------------------------------------------------------------------
# maybe_single() returns None (supabase-py v2.10+ regression)
# ---------------------------------------------------------------------------
#
# In supabase-py >=2.10, when no rows match, maybe_single().execute() returns
# None directly rather than a response object with data=None.  Every call site
# that uses maybe_single() must guard against this.  These tests reproduce the
# AttributeError that occurred before the fix and verify it no longer crashes.


class TestMaybeSingleNullResponse:
    """Regression: execute() returns None, not a response with data=None."""

    def test_get_game_returns_none_without_crashing(self, mock_client: tuple) -> None:
        client, games_table, _ = mock_client
        (
            games_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value
        ) = None

        result = SupabaseGameStore(client=client).get_game("missing")
        assert result is None

    def test_has_idempotency_key_returns_false_without_crashing(
        self, mock_client: tuple
    ) -> None:
        client, _, events_table = mock_client
        (
            events_table.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value
        ) = None

        result = SupabaseGameStore(client=client).has_idempotency_key("g1", "idem-key")
        assert result is False

    def test_append_event_dup_check_proceeds_when_execute_returns_none(
        self, mock_client: tuple
    ) -> None:
        """None dup-check response means no existing key — append should succeed."""
        client, games_table, events_table = mock_client
        # Dup-check: execute() returns None (no matching row)
        (
            events_table.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value
        ) = None
        # Update succeeds
        (
            games_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data
        ) = [{"id": "g1"}]
        # Seq query returns empty (first event)
        (
            events_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data
        ) = []

        event = SupabaseGameStore(client=client).append_event(
            "g1", "MOVE", {}, 0, make_state(version=1), idempotency_key="fresh-key"
        )
        assert event.seq == 1

    def test_append_event_conflict_check_raises_key_error_when_execute_returns_none(
        self, mock_client: tuple
    ) -> None:
        """None conflict-check response means game is missing — should raise KeyError."""
        client, games_table, _ = mock_client
        # Update returns empty rows (game missing or version mismatch)
        (
            games_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data
        ) = []
        # Conflict check: execute() returns None (game truly missing)
        (
            games_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value
        ) = None

        with pytest.raises(KeyError, match="does not exist"):
            SupabaseGameStore(client=client).append_event(
                "missing", "MOVE", {}, 0, make_state(version=1)
            )

    def test_delete_game_conflict_check_raises_key_error_when_execute_returns_none(
        self, mock_client: tuple
    ) -> None:
        """None conflict-check response on delete means game is missing — KeyError."""
        client, games_table, _ = mock_client
        # Delete returns empty rows
        (
            games_table.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data
        ) = []
        # Conflict check: execute() returns None
        (
            games_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value
        ) = None

        with pytest.raises(KeyError, match="does not exist"):
            SupabaseGameStore(client=client).delete_game("missing", 0)


# ---------------------------------------------------------------------------
# Constructor / injection
# ---------------------------------------------------------------------------


class TestConstructor:
    def test_no_env_vars_needed_with_injected_client(self, mock_client: tuple) -> None:
        """Injecting a client bypasses SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY."""
        client, _, _ = mock_client
        store = SupabaseGameStore(client=client)
        assert store is not None

    def test_missing_env_var_raises_without_injected_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        with pytest.raises((KeyError, Exception)):
            SupabaseGameStore()
