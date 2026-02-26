"""FastAPI router: game lifecycle endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.dependencies import get_card_store, get_game_store
from app.models.game import Archetype, GameState
from app.rules.errors import InvalidMoveError
from app.services import game_service
from app.store import CardStore, ConflictError, DuplicateEventError, GameStore

router = APIRouter(prefix="/games", tags=["games"])

GameStoreDep = Annotated[GameStore, Depends(get_game_store)]
CardStoreDep = Annotated[CardStore, Depends(get_card_store)]


class CreateGameRequest(BaseModel):
    seed: int | None = None


class JoinGameRequest(BaseModel):
    player_id: str


class SelectArchetypeRequest(BaseModel):
    player_id: str
    archetype: Archetype


class LeaveGameRequest(BaseModel):
    player_id: str
    state_version: int
    idempotency_key: str | None = None


class MoveRequest(BaseModel):
    player_id: str
    card_key: str
    cell_index: int
    state_version: int
    use_archetype: bool = False
    skulker_boost_side: str | None = None
    presence_boost_direction: str | None = None
    idempotency_key: str | None = None


@router.post("", response_model=GameState, status_code=201)
def create_game(
    body: CreateGameRequest,
    game_store: GameStoreDep,
    card_store: CardStoreDep,
) -> GameState:
    return game_service.create_game(game_store, card_store, body.seed)


@router.post("/{game_id}/join", response_model=GameState)
def join_game(
    game_id: str,
    body: JoinGameRequest,
    game_store: GameStoreDep,
    card_store: CardStoreDep,
) -> GameState:
    try:
        return game_service.join_game(game_store, card_store, game_id, body.player_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{game_id}/archetype", response_model=GameState)
def select_archetype(
    game_id: str,
    body: SelectArchetypeRequest,
    game_store: GameStoreDep,
) -> GameState:
    try:
        return game_service.select_archetype(game_store, game_id, body.player_id, body.archetype)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{game_id}", response_model=GameState)
def get_game(game_id: str, game_store: GameStoreDep) -> GameState:
    state = game_store.get_game(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id!r} not found")
    return state


@router.post("/{game_id}/moves", response_model=GameState)
def submit_move(
    game_id: str,
    body: MoveRequest,
    game_store: GameStoreDep,
    card_store: CardStoreDep,
) -> GameState:
    # Idempotency check must happen before version/auth validation so that
    # retries with a stale state_version are still recognised as duplicates.
    if body.idempotency_key is not None and game_store.has_idempotency_key(
        game_id, body.idempotency_key
    ):
        state = game_store.get_game(game_id)
        if state is None:
            raise HTTPException(status_code=404, detail=f"Game {game_id!r} not found")
        return state

    try:
        return game_service.submit_move(
            game_store,
            card_store,
            game_id,
            body.player_id,
            body.card_key,
            body.cell_index,
            body.state_version,
            body.use_archetype,
            body.skulker_boost_side,
            body.presence_boost_direction,
            body.idempotency_key,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidMoveError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DuplicateEventError:
        # Belt-and-suspenders: store also raises DuplicateEventError; return current state.
        state = game_store.get_game(game_id)
        if state is None:
            raise HTTPException(status_code=404, detail=f"Game {game_id!r} not found")
        return state


@router.post("/{game_id}/leave", response_model=GameState)
def leave_game(
    game_id: str,
    body: LeaveGameRequest,
    game_store: GameStoreDep,
) -> GameState | Response:
    # Idempotency check for ACTIVE forfeits (same semantics as moves).
    if body.idempotency_key is not None and game_store.has_idempotency_key(
        game_id, body.idempotency_key
    ):
        state = game_store.get_game(game_id)
        if state is None:
            raise HTTPException(status_code=404, detail=f"Game {game_id!r} not found")
        return state

    try:
        result = game_service.leave_game(
            game_store,
            game_id,
            body.player_id,
            body.state_version,
            body.idempotency_key,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DuplicateEventError:
        state = game_store.get_game(game_id)
        if state is None:
            raise HTTPException(status_code=404, detail=f"Game {game_id!r} not found")
        return state

    if result is None:
        # Game was deleted (WAITING lobby with a single player)
        return Response(status_code=204)
    return result
