"""Game orchestration: create, join, archetype selection, and move submission."""

import uuid
from random import Random

from app.models.game import Archetype, GameState, GameStatus, PlayerState
from app.rules.deck import generate_matched_decks
from app.rules.reducer import PlacementIntent, apply_intent
from app.store import CardStore, ConflictError, GameStore


def create_game(game_store: GameStore, card_store: CardStore, seed: int | None = None) -> GameState:
    game_id = str(uuid.uuid4())
    if seed is None:
        seed = Random().randint(0, 2**31 - 1)
    state = GameState(game_id=game_id, seed=seed, status=GameStatus.WAITING)
    game_store.create_game(game_id, state)
    return state


def join_game(
    game_store: GameStore, card_store: CardStore, game_id: str, player_id: str
) -> GameState:
    state = game_store.get_game(game_id)
    if state is None:
        raise KeyError(f"Game {game_id!r} not found")
    if state.status != GameStatus.WAITING:
        raise ValueError("Game is not in WAITING state")
    if any(p.player_id == player_id for p in state.players):
        raise ValueError(f"Player {player_id!r} already joined")
    if len(state.players) >= 2:
        raise ValueError("Game already has 2 players")

    new_players = list(state.players) + [PlayerState(player_id=player_id)]

    if len(new_players) == 2:
        cards = card_store.list_cards()
        deck_a, deck_b = generate_matched_decks(cards, seed=state.seed)
        new_players[0] = new_players[0].model_copy(update={"hand": [c.card_key for c in deck_a]})
        new_players[1] = new_players[1].model_copy(update={"hand": [c.card_key for c in deck_b]})
        new_status = GameStatus.ACTIVE
    else:
        new_status = state.status

    new_state = state.model_copy(
        update={
            "players": new_players,
            "status": new_status,
            "state_version": state.state_version + 1,
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
    presence_boost_direction: str | None = None,
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

    card_lookup = {c.card_key: c for c in card_store.list_cards()}
    # Derive per-move RNG from seed + current state_version for deterministic replay
    rng = Random(state.seed + state.state_version)

    intent = PlacementIntent(
        player_index=player_index,
        card_key=card_key,
        cell_index=cell_index,
        use_archetype=use_archetype,
        skulker_boost_side=skulker_boost_side,
        presence_boost_direction=presence_boost_direction,
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
