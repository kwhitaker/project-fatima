from typing import Annotated, Literal

from pydantic import BaseModel, Field

SideValue = Annotated[int, Field(ge=1, le=10)]

VALID_ELEMENTS = ("blood", "holy", "arcane", "shadow", "nature")
ElementType = Literal["blood", "holy", "arcane", "shadow", "nature"]


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
    element: ElementType
