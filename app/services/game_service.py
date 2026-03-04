"""Game orchestration: create, join, archetype selection, and move submission."""

import uuid
from datetime import UTC, datetime
from random import Random

from app.models.game import Archetype, GameResult, GameState, GameStatus, PlayerState
from app.rules.deck import generate_matched_decks
from app.rules.errors import ArchetypeNotSelectedError
from app.rules.reducer import PlacementIntent, apply_intent
from app.store import CardStore, ConflictError, GameStore


class ActiveGameExistsError(Exception):
    """Raised when a player tries to create/join but already has a non-complete game."""

    def __init__(self, existing_game_id: str) -> None:
        self.existing_game_id = existing_game_id
        super().__init__(
            f"You already have a non-complete game ({existing_game_id}). "
            "Finish or forfeit it before starting a new one."
        )


def _check_no_active_game(game_store: GameStore, player_id: str) -> None:
    """Raise ActiveGameExistsError if player has any non-complete game."""
    games = game_store.list_games_for_player(player_id)
    for g in games:
        if g.status != GameStatus.COMPLETE:
            raise ActiveGameExistsError(g.game_id)


def create_game(
    game_store: GameStore,
    card_store: CardStore,
    player_id: str,
    seed: int | None = None,
    email: str | None = None,
) -> GameState:
    """Create a new game and auto-join the caller as player 1."""
    _check_no_active_game(game_store, player_id)
    game_id = str(uuid.uuid4())
    if seed is None:
        seed = Random().randint(0, 2**31 - 1)
    initial_state = GameState(
        game_id=game_id,
        seed=seed,
        status=GameStatus.WAITING,
        players=[PlayerState(player_id=player_id, email=email)],
        created_at=datetime.now(UTC).isoformat(),
    )
    game_store.create_game(game_id, initial_state)
    return initial_state


def join_game(
    game_store: GameStore,
    card_store: CardStore,
    game_id: str,
    player_id: str,
    email: str | None = None,
) -> GameState:
    _check_no_active_game(game_store, player_id)
    state = game_store.get_game(game_id)
    if state is None:
        raise KeyError(f"Game {game_id!r} not found")
    if state.status != GameStatus.WAITING:
        raise ValueError("Game is not in WAITING state")
    if any(p.player_id == player_id for p in state.players):
        raise ValueError(f"Player {player_id!r} already joined")
    if len(state.players) >= 2:
        raise ValueError("Game already has 2 players")

    new_players = list(state.players) + [PlayerState(player_id=player_id, email=email)]

    extra_updates: dict[str, object] = {}
    if len(new_players) == 2:
        cards = card_store.list_cards()
        deck_a, deck_b = generate_matched_decks(cards, seed=state.seed)
        new_players[0] = new_players[0].model_copy(update={"hand": [c.card_key for c in deck_a]})
        new_players[1] = new_players[1].model_copy(update={"hand": [c.card_key for c in deck_b]})
        new_status = GameStatus.ACTIVE
        # Pick starting player deterministically from seed
        starting = Random(state.seed).randint(0, 1)
        extra_updates["starting_player_index"] = starting
        extra_updates["current_player_index"] = starting
        # Generate board elements deterministically from seed (one per cell)
        extra_updates["board_elements"] = Random(state.seed).choices(
            ["blood", "holy", "arcane", "shadow", "nature"], k=9
        )
    else:
        new_status = state.status

    new_state = state.model_copy(
        update={
            "players": new_players,
            "status": new_status,
            "state_version": state.state_version + 1,
            **extra_updates,
        }
    )
    game_store.append_event(
        game_id=game_id,
        event_type="player_joined",
        payload={"player_id": player_id},
        expected_version=state.state_version,
        new_state=new_state,
    )
    return new_state


def select_archetype(
    game_store: GameStore, game_id: str, player_id: str, archetype: Archetype
) -> GameState:
    state = game_store.get_game(game_id)
    if state is None:
        raise KeyError(f"Game {game_id!r} not found")
    player_index = next((i for i, p in enumerate(state.players) if p.player_id == player_id), None)
    if player_index is None:
        raise PermissionError(f"Player {player_id!r} is not in this game")
    player = state.players[player_index]
    if player.archetype is not None:
        raise ValueError(f"Player {player_id!r} has already selected an archetype")

    new_players = list(state.players)
    new_players[player_index] = player.model_copy(update={"archetype": archetype})
    new_state = state.model_copy(
        update={
            "players": new_players,
            "state_version": state.state_version + 1,
        }
    )
    game_store.append_event(
        game_id=game_id,
        event_type="archetype_selected",
        payload={"player_id": player_id, "archetype": archetype.value},
        expected_version=state.state_version,
        new_state=new_state,
    )
    return new_state


def leave_game(
    game_store: GameStore,
    game_id: str,
    player_id: str,
    state_version: int,
    idempotency_key: str | None = None,
) -> GameState | None:
    """Leave a game.

    ACTIVE + 2 players → forfeit: append game_forfeited event, other player wins.
    WAITING + 1 player → delete the game lobby.
    Returns the new GameState for forfeits, or None when the game was deleted.
    """
    state = game_store.get_game(game_id)
    if state is None:
        raise KeyError(f"Game {game_id!r} not found")

    player_index = next((i for i, p in enumerate(state.players) if p.player_id == player_id), None)
    if player_index is None:
        raise PermissionError(f"Player {player_id!r} is not in this game")

    if state.status == GameStatus.ACTIVE:
        other_index = 1 - player_index
        new_result = GameResult(
            winner=other_index,
            is_draw=False,
            completion_reason="forfeit",
            forfeit_by_index=player_index,
        )
        new_state = state.model_copy(
            update={
                "status": GameStatus.COMPLETE,
                "result": new_result,
                "state_version": state.state_version + 1,
            }
        )
        game_store.append_event(
            game_id=game_id,
            event_type="game_forfeited",
            payload={
                "forfeit_by": player_id,
                "winner": state.players[other_index].player_id,
            },
            expected_version=state_version,
            new_state=new_state,
            idempotency_key=idempotency_key,
        )
        return new_state
    elif state.status == GameStatus.WAITING and len(state.players) == 1:
        game_store.delete_game(game_id, expected_version=state_version)
        return None
    else:
        raise ValueError(
            f"Cannot leave game {game_id!r}: "
            f"status={state.status.value!r}, players={len(state.players)}"
        )


def submit_move(
    game_store: GameStore,
    card_store: CardStore,
    game_id: str,
    player_id: str,
    card_key: str,
    cell_index: int,
    expected_version: int,
    use_archetype: bool = False,
    skulker_boost_side: str | None = None,
    intimidate_target_cell: int | None = None,
    martial_rotation_direction: str | None = None,
    idempotency_key: str | None = None,
) -> GameState:
    state = game_store.get_game(game_id)
    if state is None:
        raise KeyError(f"Game {game_id!r} not found")
    player_index = next((i for i, p in enumerate(state.players) if p.player_id == player_id), None)
    if player_index is None:
        raise PermissionError(f"Player {player_id!r} is not in this game")
    if state.state_version != expected_version:
        raise ConflictError(
            f"Version conflict for game {game_id!r}: "
            f"expected {expected_version}, got {state.state_version}"
        )

    player = state.players[player_index]
    if player.archetype is None:
        raise ArchetypeNotSelectedError(
            "You must select an archetype before placing cards. "
            "Use POST /games/{game_id}/archetype to select one."
        )

    card_lookup = {c.card_key: c for c in card_store.list_cards()}
    # Derive per-move RNG from seed + current state_version for deterministic replay
    rng = Random(state.seed + state.state_version)

    intent = PlacementIntent(
        player_index=player_index,
        card_key=card_key,
        cell_index=cell_index,
        use_archetype=use_archetype,
        skulker_boost_side=skulker_boost_side,
        intimidate_target_cell=intimidate_target_cell,
        martial_rotation_direction=martial_rotation_direction,
    )
    new_state = apply_intent(state, intent, card_lookup, rng)

    game_store.append_event(
        game_id=game_id,
        event_type="card_placed",
        payload={"player_id": player_id, "card_key": card_key, "cell_index": cell_index},
        expected_version=expected_version,
        new_state=new_state,
        idempotency_key=idempotency_key,
    )
    return new_state
