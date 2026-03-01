import pytest
from pydantic import ValidationError

from app.models.cards import CardDefinition, CardSides
from app.models.game import Archetype, BoardCell, GameState, GameStatus, PlayerState

# --- CardSides ---


def test_card_sides_valid() -> None:
    sides = CardSides(n=1, e=5, s=10, w=3)
    assert sides.n == 1
    assert sides.w == 3


def test_card_sides_rejects_zero() -> None:
    with pytest.raises(ValidationError):
        CardSides(n=0, e=5, s=5, w=5)


def test_card_sides_rejects_eleven() -> None:
    with pytest.raises(ValidationError):
        CardSides(n=11, e=5, s=5, w=5)


# --- CardDefinition ---


def _valid_card_kwargs(**overrides: object) -> dict:
    defaults: dict = {
        "card_key": "strahd_iii",
        "character_key": "strahd_von_zarovich",
        "name": "Strahd von Zarovich",
        "version": "Strahd III",
        "tier": 3,
        "rarity": 100,
        "is_named": True,
        "sides": {"n": 10, "e": 9, "s": 7, "w": 6},
        "set": "barovia_200y_v1",
    }
    defaults.update(overrides)
    return defaults


def test_card_definition_valid() -> None:
    card = CardDefinition(**_valid_card_kwargs())
    assert card.card_key == "strahd_iii"
    assert card.sides.n == 10


def test_card_definition_optional_tags_default_empty() -> None:
    card = CardDefinition(**_valid_card_kwargs())
    assert card.tags == []


def test_card_definition_rejects_tier_zero() -> None:
    with pytest.raises(ValidationError):
        CardDefinition(**_valid_card_kwargs(tier=0))


def test_card_definition_rejects_tier_four() -> None:
    with pytest.raises(ValidationError):
        CardDefinition(**_valid_card_kwargs(tier=4))


def test_card_definition_rejects_rarity_zero() -> None:
    with pytest.raises(ValidationError):
        CardDefinition(**_valid_card_kwargs(rarity=0))


def test_card_definition_rejects_rarity_over_100() -> None:
    with pytest.raises(ValidationError):
        CardDefinition(**_valid_card_kwargs(rarity=101))


def test_card_definition_json_roundtrip() -> None:
    card = CardDefinition(**_valid_card_kwargs(tags=["boss", "ravenloft"]))
    data = card.model_dump()
    assert data["card_key"] == "strahd_iii"
    assert data["sides"]["n"] == 10
    assert data["tags"] == ["boss", "ravenloft"]
    card2 = CardDefinition.model_validate(data)
    assert card2 == card


def test_card_definition_missing_required_field() -> None:
    kwargs = _valid_card_kwargs()
    del kwargs["card_key"]
    with pytest.raises(ValidationError):
        CardDefinition(**kwargs)


# --- GameState ---


def test_game_state_default_board_nine_cells() -> None:
    state = GameState(game_id="g1", seed=42)
    assert len(state.board) == 9
    assert all(cell is None for cell in state.board)


def test_game_state_default_status_waiting() -> None:
    state = GameState(game_id="g1", seed=42)
    assert state.status == GameStatus.WAITING


def test_game_state_json_roundtrip() -> None:
    state = GameState(
        game_id="g1",
        seed=42,
        players=[PlayerState(player_id="p1"), PlayerState(player_id="p2")],
    )
    data = state.model_dump()
    assert data["game_id"] == "g1"
    assert data["status"] == "waiting"
    assert len(data["players"]) == 2
    state2 = GameState.model_validate(data)
    assert state2 == state


def test_game_state_drops_legacy_last_move_shape() -> None:
    state = GameState.model_validate(
        {
            "game_id": "g1",
            "seed": 1,
            "last_move": {"mists_roll": 1, "mists_effect": "fog"},
        }
    )
    assert state.last_move is None


def test_board_cell_valid() -> None:
    cell = BoardCell(card_key="zombie_i", owner=0)
    assert cell.owner == 0
    cell2 = BoardCell(card_key="zombie_i", owner=1)
    assert cell2.owner == 1


def test_board_cell_rejects_invalid_owner() -> None:
    with pytest.raises(ValidationError):
        BoardCell(card_key="zombie_i", owner=2)


def test_player_state_archetype_enum() -> None:
    p = PlayerState(player_id="p1", archetype=Archetype.MARTIAL)
    assert p.archetype == Archetype.MARTIAL
    assert not p.archetype_used


def test_game_state_board_with_placed_card() -> None:
    board: list[BoardCell | None] = [None] * 9
    board[4] = BoardCell(card_key="strahd_iii", owner=0)
    state = GameState(game_id="g1", seed=7, board=board)
    assert state.board[4] is not None
    assert state.board[4].card_key == "strahd_iii"
