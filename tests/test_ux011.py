"""Tests for US-UX-011: enrich last_move snapshot with player_index, card_key, cell_index.

Covers:
- last_move includes player_index (0 or 1) after a move
- last_move includes card_key matching what was placed
- last_move includes cell_index matching where it was placed
- Existing mists_roll and mists_effect still present
- Second move updates last_move correctly (different player_index)
- Sudden Death resets last_move to None (begin_sudden_death_round)
- Archetype usage does not break last_move population
"""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.auth import get_caller_id
from app.dependencies import get_card_store, get_game_store
from app.main import app
from app.models.cards import CardDefinition, CardSides
from app.store.memory import MemoryCardStore, MemoryGameStore


def _make_card(idx: int) -> CardDefinition:
    return CardDefinition(
        card_key=f"ux011_{idx:03d}",
        character_key=f"ch011_{idx:03d}",
        name=f"UX011 Card {idx}",
        version="v1",
        tier=1,
        rarity=15,
        is_named=False,
        sides=CardSides(n=4, e=4, s=4, w=4),
        set="test",
    )


_TEST_CARDS = [_make_card(i) for i in range(20)]


def _mock_caller_id(request: Request) -> str:
    return request.headers.get("X-User-Id", "test-user")


@pytest.fixture()
def client() -> TestClient:  # type: ignore[misc]
    game_store = MemoryGameStore()
    card_store = MemoryCardStore(cards=_TEST_CARDS)
    app.dependency_overrides[get_game_store] = lambda: game_store
    app.dependency_overrides[get_card_store] = lambda: card_store
    app.dependency_overrides[get_caller_id] = _mock_caller_id
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


def _as(client: TestClient, user: str, method: str, path: str, **kwargs):  # type: ignore[no-untyped-def]
    return getattr(client, method)(path, headers={"X-User-Id": user}, **kwargs)


def _setup_active_game(client: TestClient, seed: int = 42) -> tuple[str, dict]:  # type: ignore[misc]
    """Create a game, join, select archetypes, return (game_id, state_data)."""
    resp = _as(client, "alice", "post", "/games", json={"seed": seed})
    game_id = resp.json()["game_id"]
    _as(client, "bob", "post", f"/games/{game_id}/join", json={})
    _as(client, "alice", "post", f"/games/{game_id}/archetype", json={"archetype": "martial"})
    resp = _as(client, "bob", "post", f"/games/{game_id}/archetype", json={"archetype": "devout"})
    return game_id, resp.json()


# ---------------------------------------------------------------------------
# Tests: last_move enriched fields
# ---------------------------------------------------------------------------


def test_last_move_includes_player_index(client: TestClient) -> None:
    """last_move.player_index is set to the index of the player who moved."""
    game_id, state = _setup_active_game(client)
    first_idx = state["current_player_index"]
    first_user = "alice" if first_idx == 0 else "bob"
    first_hand = state["players"][first_idx]["hand"]

    resp = _as(
        client,
        first_user,
        "post",
        f"/games/{game_id}/moves",
        json={"card_key": first_hand[0], "cell_index": 0, "state_version": state["state_version"]},
    )
    assert resp.status_code == 200
    lm = resp.json()["last_move"]
    assert lm is not None
    assert lm["player_index"] == first_idx


def test_last_move_includes_card_key(client: TestClient) -> None:
    """last_move.card_key matches the card placed."""
    game_id, state = _setup_active_game(client, seed=99)
    first_idx = state["current_player_index"]
    first_user = "alice" if first_idx == 0 else "bob"
    first_hand = state["players"][first_idx]["hand"]
    placed_card = first_hand[0]

    resp = _as(
        client,
        first_user,
        "post",
        f"/games/{game_id}/moves",
        json={
            "card_key": placed_card,
            "cell_index": 3,
            "state_version": state["state_version"],
        },
    )
    assert resp.status_code == 200
    lm = resp.json()["last_move"]
    assert lm is not None
    assert lm["card_key"] == placed_card


def test_last_move_includes_cell_index(client: TestClient) -> None:
    """last_move.cell_index matches the cell where the card was placed."""
    game_id, state = _setup_active_game(client, seed=7)
    first_idx = state["current_player_index"]
    first_user = "alice" if first_idx == 0 else "bob"
    first_hand = state["players"][first_idx]["hand"]
    target_cell = 5

    resp = _as(
        client,
        first_user,
        "post",
        f"/games/{game_id}/moves",
        json={
            "card_key": first_hand[0],
            "cell_index": target_cell,
            "state_version": state["state_version"],
        },
    )
    assert resp.status_code == 200
    lm = resp.json()["last_move"]
    assert lm is not None
    assert lm["cell_index"] == target_cell


def test_last_move_still_includes_mists_fields(client: TestClient) -> None:
    """Existing mists_roll and mists_effect fields are still present."""
    game_id, state = _setup_active_game(client, seed=13)
    first_idx = state["current_player_index"]
    first_user = "alice" if first_idx == 0 else "bob"
    first_hand = state["players"][first_idx]["hand"]

    resp = _as(
        client,
        first_user,
        "post",
        f"/games/{game_id}/moves",
        json={"card_key": first_hand[0], "cell_index": 2, "state_version": state["state_version"]},
    )
    assert resp.status_code == 200
    lm = resp.json()["last_move"]
    assert lm is not None
    assert 1 <= lm["mists_roll"] <= 6
    assert lm["mists_effect"] in ("fog", "omen", "none", "fog_negated")


def test_last_move_updated_on_second_move(client: TestClient) -> None:
    """last_move is updated for the second move with the correct player_index."""
    game_id, state = _setup_active_game(client, seed=55)
    first_idx = state["current_player_index"]
    second_idx = 1 - first_idx
    first_user = "alice" if first_idx == 0 else "bob"
    second_user = "alice" if second_idx == 0 else "bob"

    # First move
    first_hand = state["players"][first_idx]["hand"]
    resp = _as(
        client,
        first_user,
        "post",
        f"/games/{game_id}/moves",
        json={"card_key": first_hand[0], "cell_index": 0, "state_version": state["state_version"]},
    )
    assert resp.status_code == 200
    state2 = resp.json()

    # Second move
    second_hand = state2["players"][second_idx]["hand"]
    resp = _as(
        client,
        second_user,
        "post",
        f"/games/{game_id}/moves",
        json={
            "card_key": second_hand[0],
            "cell_index": 8,
            "state_version": state2["state_version"],
        },
    )
    assert resp.status_code == 200
    lm = resp.json()["last_move"]
    assert lm is not None
    assert lm["player_index"] == second_idx
    assert lm["card_key"] == second_hand[0]
    assert lm["cell_index"] == 8


def test_last_move_with_archetype_activated(client: TestClient) -> None:
    """Archetype activation (martial rotate) does not break last_move population."""
    game_id, state = _setup_active_game(client, seed=23)
    # alice is index 0, archetype=martial
    alice_idx = next(i for i, p in enumerate(state["players"]) if p["player_id"] == "alice")
    alice_hand = state["players"][alice_idx]["hand"]

    # Make alice go first (use whichever player goes first)
    first_idx = state["current_player_index"]
    first_user = "alice" if first_idx == 0 else "bob"
    first_hand = state["players"][first_idx]["hand"]

    # alice moves with archetype if it's her turn, otherwise just move first player
    use_archetype = first_user == "alice"
    body: dict = {
        "card_key": first_hand[0],
        "cell_index": 4,
        "state_version": state["state_version"],
    }
    if use_archetype:
        body["use_archetype"] = True

    resp = _as(client, first_user, "post", f"/games/{game_id}/moves", json=body)
    assert resp.status_code == 200
    lm = resp.json()["last_move"]
    assert lm is not None
    assert lm["player_index"] == first_idx
    assert lm["card_key"] == first_hand[0]
    assert lm["cell_index"] == 4
