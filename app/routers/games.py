"""FastAPI router: game lifecycle endpoints."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel

from app.auth import get_caller_email, get_caller_id
from app.dependencies import get_card_store, get_game_store
from app.models.game import AIDifficulty, Archetype, GameState, GameStatus
from app.rules.errors import InvalidMoveError
from app.services import game_service
from app.services.game_service import ActiveGameExistsError
from app.store import CardStore, ConflictError, DuplicateEventError, GameStore

router = APIRouter(prefix="/games", tags=["games"])

GameStoreDep = Annotated[GameStore, Depends(get_game_store)]
CardStoreDep = Annotated[CardStore, Depends(get_card_store)]
CallerIdDep = Annotated[str, Depends(get_caller_id)]
CallerEmailDep = Annotated[str | None, Depends(get_caller_email)]


class CreateGameRequest(BaseModel):
    seed: int | None = None


class CreateGameVsAiRequest(BaseModel):
    difficulty: AIDifficulty


class SelectArchetypeRequest(BaseModel):
    archetype: Archetype


class LeaveGameRequest(BaseModel):
    state_version: int
    idempotency_key: str | None = None


class DraftRequest(BaseModel):
    selected_cards: list[str]


class MoveRequest(BaseModel):
    card_key: str
    cell_index: int
    state_version: int
    use_archetype: bool = False
    skulker_boost_side: str | None = None
    intimidate_target_cell: int | None = None
    martial_rotation_direction: str | None = None
    idempotency_key: str | None = None


@router.get("", response_model=list[GameState])
def list_games(caller_id: CallerIdDep, game_store: GameStoreDep) -> list[GameState]:
    own = game_store.list_games_for_player(caller_id)
    open_games = game_store.list_open_games(caller_id)
    combined = own + open_games
    # Newest first, then non-complete before complete (stable sort)
    combined.sort(key=lambda g: g.created_at or "", reverse=True)
    combined.sort(key=lambda g: g.status == GameStatus.COMPLETE)
    return combined


@router.post("", response_model=GameState, status_code=201)
def create_game(
    body: CreateGameRequest,
    caller_id: CallerIdDep,
    caller_email: CallerEmailDep,
    game_store: GameStoreDep,
    card_store: CardStoreDep,
) -> GameState:
    try:
        return game_service.create_game(game_store, card_store, caller_id, body.seed, caller_email)
    except ActiveGameExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/vs-ai", response_model=GameState, status_code=201)
def create_game_vs_ai(
    body: CreateGameVsAiRequest,
    caller_id: CallerIdDep,
    caller_email: CallerEmailDep,
    game_store: GameStoreDep,
    card_store: CardStoreDep,
) -> GameState:
    try:
        return game_service.create_game_vs_ai(
            game_store, card_store, caller_id, caller_email, body.difficulty
        )
    except ActiveGameExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{game_id}/join", response_model=GameState)
def join_game(
    game_id: str,
    caller_id: CallerIdDep,
    caller_email: CallerEmailDep,
    game_store: GameStoreDep,
    card_store: CardStoreDep,
) -> GameState:
    try:
        return game_service.join_game(game_store, card_store, game_id, caller_id, caller_email)
    except ActiveGameExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{game_id}/draft", response_model=GameState)
def submit_draft(
    game_id: str,
    body: DraftRequest,
    caller_id: CallerIdDep,
    game_store: GameStoreDep,
    card_store: CardStoreDep,
    background_tasks: BackgroundTasks,
) -> GameState:
    try:
        state = game_service.submit_draft(game_store, game_id, caller_id, body.selected_cards)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if game_service.is_ai_turn(state):
        background_tasks.add_task(
            game_service.execute_ai_turn, state.game_id, game_store, card_store
        )
    return state


@router.post("/{game_id}/archetype", response_model=GameState)
def select_archetype(
    game_id: str,
    body: SelectArchetypeRequest,
    caller_id: CallerIdDep,
    game_store: GameStoreDep,
) -> GameState:
    try:
        return game_service.select_archetype(game_store, game_id, caller_id, body.archetype)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{game_id}", response_model=GameState)
def get_game(game_id: str, caller_id: CallerIdDep, game_store: GameStoreDep) -> GameState:
    state = game_store.get_game(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id!r} not found")
    # Spectator blocking: only participants can read ACTIVE/COMPLETE games
    if state.status != GameStatus.WAITING:
        if not any(p.player_id == caller_id for p in state.players):
            raise HTTPException(status_code=403, detail="Not a participant in this game")
    return state


@router.post("/{game_id}/moves", response_model=GameState)
def submit_move(
    game_id: str,
    body: MoveRequest,
    caller_id: CallerIdDep,
    game_store: GameStoreDep,
    card_store: CardStoreDep,
    background_tasks: BackgroundTasks,
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
        state = game_service.submit_move(
            game_store,
            card_store,
            game_id,
            caller_id,
            body.card_key,
            body.cell_index,
            body.state_version,
            body.use_archetype,
            body.skulker_boost_side,
            body.intimidate_target_cell,
            body.martial_rotation_direction,
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

    if game_service.is_ai_turn(state):
        background_tasks.add_task(
            game_service.execute_ai_turn, state.game_id, game_store, card_store
        )
    return state


@router.post("/{game_id}/leave", response_model=GameState)
def leave_game(
    game_id: str,
    body: LeaveGameRequest,
    caller_id: CallerIdDep,
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
            caller_id,
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
