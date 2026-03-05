"""AI move selection.

choose_move(state, ai_index, difficulty, card_lookup, rng) -> PlacementIntent

For US-SP-004 we implement a simple random-legal-move strategy. Later stories
(US-SP-005 through US-SP-008) will add per-difficulty strategies.
"""

from random import Random

from app.models.cards import CardDefinition
from app.models.game import AIDifficulty, GameState
from app.rules.reducer import PlacementIntent


def choose_move(
    state: GameState,
    ai_index: int,
    difficulty: AIDifficulty,
    card_lookup: dict[str, CardDefinition],
    rng: Random,
) -> PlacementIntent:
    """Pick a move for the AI player.

    Currently returns a random legal (card, cell) pair. Per-difficulty
    strategies will be added in subsequent stories.
    """
    player = state.players[ai_index]
    empty_cells = [i for i, cell in enumerate(state.board) if cell is None]
    hand = player.hand

    if not hand or not empty_cells:
        raise ValueError("AI has no legal moves (empty hand or full board)")

    card_key = rng.choice(hand)
    cell_index = rng.choice(empty_cells)

    return PlacementIntent(
        player_index=ai_index,
        card_key=card_key,
        cell_index=cell_index,
    )
