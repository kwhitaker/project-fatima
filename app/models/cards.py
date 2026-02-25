from typing import Annotated

from pydantic import BaseModel, Field

SideValue = Annotated[int, Field(ge=1, le=10)]


class CardSides(BaseModel):
    n: SideValue
    e: SideValue
    s: SideValue
    w: SideValue


class CardDefinition(BaseModel):
    card_key: str
    character_key: str
    name: str
    version: str
    tier: Annotated[int, Field(ge=1, le=3)]
    rarity: Annotated[int, Field(ge=1, le=100)]
    is_named: bool
    sides: CardSides
    set: str
    tags: list[str] = []
