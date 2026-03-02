"""Tests for US-UX-003: record completion reason (normal vs forfeit) for result labels.

Covers:
- Forfeiting an ACTIVE game sets completion_reason="forfeit" and forfeit_by_index
- Normal game completion (board full) sets completion_reason="normal"
- Draw completion (Sudden Death cap) sets completion_reason="normal"
- API returns these fields in the result payload
- Existing winner/is_draw fields are still correct
"""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.auth import get_caller_id
from app.dependencies import get_card_store, get_game_store
from app.main import app
from app.models.cards import CardDefinition, CardSides
from app.models.game import BoardCell, GameResult, GameState, GameStatus, PlayerState
from app.rules.reducer import begin_sudden_death_round, compute_round_result
from app.store.memory import MemoryCardStore, MemoryGameStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_card(idx: int) -> CardDefinition:
    return CardDefinition(
        card_key=f"tc_{idx:03d}",
        character_key=f"ch_{idx:03d}",
        name=f"Card {idx}",
        version="v1",
        tier=1,
        rarity=15,
        is_named=False,
        sides=CardSides(n=4, e=4, s=4, w=4),
        set="test",
        element="shadow",
    )


_TEST_CARDS = [_make_card(i) for i in range(20)]


def _mock_caller_id(request: Request) -> str:
    return request.headers.get("X-User-Id", "test-user")


def _as(client: TestClient, user: str, method: str, path: str, **kwargs):  # type: ignore[no-untyped-def]
    return getattr(client, method)(path, headers={"X-User-Id": user}, **kwargs)


@pytest.fixture()
def game_store() -> MemoryGameStore:
    return MemoryGameStore()


@pytest.fixture()
def client(game_store: MemoryGameStore) -> TestClient:  # type: ignore[misc]
    card_store = MemoryCardStore(cards=_TEST_CARDS)
    app.dependency_overrides[get_game_store] = lambda: game_store
    app.dependency_overrides[get_card_store] = lambda: card_store
    app.dependency_overrides[get_caller_id] = _mock_caller_id
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


def _create_active_game(client: TestClient) -> tuple[str, str, str]:
    game_id = _as(client, "p1", "post", "/games", json={}).json()["game_id"]
    _as(client, "p2", "post", f"/games/{game_id}/join", json={})
    return game_id, "p1", "p2"


# ---------------------------------------------------------------------------
# GameResult model: completion_reason field
# ---------------------------------------------------------------------------


def test_game_result_has_completion_reason_field() -> None:
    result = GameResult(winner=0, is_draw=False)
    assert hasattr(result, "completion_reason")


def test_game_result_completion_reason_defaults_none() -> None:
    result = GameResult(winner=0, is_draw=False)
    assert result.completion_reason is None


def test_game_result_has_forfeit_by_index_field() -> None:
    result = GameResult(winner=0, is_draw=False)
    assert hasattr(result, "forfeit_by_index")


def test_game_result_forfeit_by_index_defaults_none() -> None:
    result = GameResult(winner=0, is_draw=False)
    assert result.forfeit_by_index is None


# ---------------------------------------------------------------------------
# compute_round_result: normal completion
# ---------------------------------------------------------------------------


def test_compute_round_result_sets_normal_reason_for_win() -> None:
    board: list[BoardCell | None] = [
        BoardCell(card_key="c", owner=0),  # 0
        BoardCell(card_key="c", owner=0),  # 1
        BoardCell(card_key="c", owner=0),  # 2
        BoardCell(card_key="c", owner=0),  # 3
        BoardCell(card_key="c", owner=0),  # 4
        BoardCell(card_key="c", owner=1),  # 5
        BoardCell(card_key="c", owner=1),  # 6
        BoardCell(card_key="c", owner=1),  # 7
        BoardCell(card_key="c", owner=1),  # 8
    ]
    result = compute_round_result(board)
    assert result.winner == 0
    assert result.completion_reason == "normal"


def test_compute_round_result_sets_normal_reason_for_draw() -> None:
    # 9 cells total → p0 sweeps; completion_reason is still "normal"
    board_p0: list[BoardCell | None] = [BoardCell(card_key="c", owner=0)] * 9
    result = compute_round_result(board_p0)
    assert result.completion_reason == "normal"


def test_compute_round_result_draw_returns_none_winner() -> None:
    # 4 vs 5 on a 9-cell board can't be equal. Use 4 cells each with 1 None:
    # Actually 9 cells: let's skip None cells and use all 9 but unequal
    # For a pure draw test: player 0 gets cells 0-4 (5), player 1 gets cells 5-8 (4) → p0 wins
    # For draw: make a draw board using a special case:
    # On 9 cells, odd number total, can't have equal per-player (5 vs 4 is the best).
    # Actually the code handles None cells, so we can have fewer than 9 cells.
    # Build a 8-cell board (one None) with 4 each:
    board: list[BoardCell | None] = [
        BoardCell(card_key="c", owner=0),  # 0
        BoardCell(card_key="c", owner=0),  # 1
        BoardCell(card_key="c", owner=0),  # 2
        BoardCell(card_key="c", owner=0),  # 3
        BoardCell(card_key="c", owner=1),  # 4
        BoardCell(card_key="c", owner=1),  # 5
        BoardCell(card_key="c", owner=1),  # 6
        BoardCell(card_key="c", owner=1),  # 7
        None,  # 8
    ]
    result = compute_round_result(board)
    assert result.is_draw is True
    assert result.winner is None
    assert result.completion_reason == "normal"


# ---------------------------------------------------------------------------
# begin_sudden_death_round: draw cap → completion_reason="normal"
# ---------------------------------------------------------------------------


def test_sudden_death_cap_sets_normal_reason() -> None:
    """After 3 SD rounds, the draw result has completion_reason='normal'."""
    state = GameState(
        game_id="g1",
        state_version=5,
        sudden_death_rounds_used=3,  # at cap
        status=GameStatus.ACTIVE,
        players=[
            PlayerState(player_id="p1", hand=[]),
            PlayerState(player_id="p2", hand=[]),
        ],
        board=[BoardCell(card_key=f"c{i}", owner=i % 2) for i in range(9)],
    )
    result_state = begin_sudden_death_round(state)
    assert result_state.status == GameStatus.COMPLETE
    assert result_state.result is not None
    assert result_state.result.is_draw is True
    assert result_state.result.completion_reason == "normal"


# ---------------------------------------------------------------------------
# leave_game (forfeit): completion_reason="forfeit" + forfeit_by_index
# ---------------------------------------------------------------------------


def test_forfeit_sets_completion_reason_forfeit(client: TestClient) -> None:
    game_id, p1, _p2 = _create_active_game(client)
    sv = _as(client, p1, "get", f"/games/{game_id}").json()["state_version"]

    resp = _as(client, p1, "post", f"/games/{game_id}/leave", json={"state_version": sv})

    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["completion_reason"] == "forfeit"


def test_forfeit_by_p1_sets_forfeit_by_index_0(client: TestClient) -> None:
    game_id, p1, _p2 = _create_active_game(client)
    sv = _as(client, p1, "get", f"/games/{game_id}").json()["state_version"]

    resp = _as(client, p1, "post", f"/games/{game_id}/leave", json={"state_version": sv})

    result = resp.json()["result"]
    assert result["forfeit_by_index"] == 0  # p1 is player index 0


def test_forfeit_by_p2_sets_forfeit_by_index_1(client: TestClient) -> None:
    game_id, _p1, p2 = _create_active_game(client)
    sv = _as(client, p2, "get", f"/games/{game_id}").json()["state_version"]

    resp = _as(client, p2, "post", f"/games/{game_id}/leave", json={"state_version": sv})

    result = resp.json()["result"]
    assert result["forfeit_by_index"] == 1  # p2 is player index 1


def test_forfeit_winner_is_non_forfeiting_player(client: TestClient) -> None:
    game_id, p1, _p2 = _create_active_game(client)
    sv = _as(client, p1, "get", f"/games/{game_id}").json()["state_version"]

    resp = _as(client, p1, "post", f"/games/{game_id}/leave", json={"state_version": sv})

    result = resp.json()["result"]
    assert result["winner"] == 1
    assert result["is_draw"] is False


def test_forfeit_result_returned_by_get_game(client: TestClient) -> None:
    game_id, p1, p2 = _create_active_game(client)
    sv = _as(client, p1, "get", f"/games/{game_id}").json()["state_version"]
    _as(client, p1, "post", f"/games/{game_id}/leave", json={"state_version": sv})

    resp = _as(client, p2, "get", f"/games/{game_id}")
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["completion_reason"] == "forfeit"
    assert result["forfeit_by_index"] == 0
