"""FastAPI router: card definitions endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import get_caller_id
from app.dependencies import get_card_store
from app.models.cards import CardDefinition
from app.store import CardStore

router = APIRouter(prefix="/cards", tags=["cards"])

CardStoreDep = Annotated[CardStore, Depends(get_card_store)]
CallerIdDep = Annotated[str, Depends(get_caller_id)]


@router.get("", response_model=list[CardDefinition])
def list_cards(caller_id: CallerIdDep, card_store: CardStoreDep) -> list[CardDefinition]:
    return card_store.list_cards()
