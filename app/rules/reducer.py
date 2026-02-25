"""Pure rules engine reducer.

apply_intent(state, intent, card_lookup) -> GameState

All game logic flows through here. Mists randomness (US-004) and full turn
validation (US-005) are added in subsequent stories.
"""

from dataclasses import dataclass
from random import Random

from app.models.cards import CardDefinition
from app.models.game import BoardCell, GameState
from app.rules.captures import resolve_captures


@dataclass
class PlacementIntent:
    player_index: int
    card_key: str
    cell_index: int


def apply_intent(
    state: GameState,
    intent: PlacementIntent,
    card_lookup: dict[str, CardDefinition],
    rng: Random | None = None,
) -> GameState:
    """Apply a placement and return the next GameState.

    US-003 scope: placement + capture resolution, no Mists, no turn validation.
    rng is accepted for API stability but unused until US-004.
    """
    placed_card = card_lookup[intent.card_key]
    placed_owner = intent.player_index

    new_board: list[BoardCell | None] = list(state.board)
    new_board[intent.cell_index] = BoardCell(card_key=intent.card_key, owner=placed_owner)

    new_board = resolve_captures(
        new_board,
        intent.cell_index,
        placed_card,
        placed_owner,
        card_lookup,
        mists_modifier=0,
    )

    return state.model_copy(update={"board": new_board, "state_version": state.state_version + 1})
