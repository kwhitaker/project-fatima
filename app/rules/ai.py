"""AI move selection.

choose_move(state, ai_index, difficulty, card_lookup, rng) -> PlacementIntent

Dispatches to per-difficulty strategy functions. Currently implements:
- easy (Novice/Ireena): semi-random with capture-aware scoring
- medium (Greedy/Rahadin): one-ply simulation, picks move maximizing owned cells
- hard/nightmare: placeholder (random legal move)
"""

from random import Random

from app.models.cards import CardDefinition
from app.models.game import AIDifficulty, Archetype, GameState
from app.rules.board import ADJACENCY
from app.rules.reducer import PlacementIntent, apply_intent


def choose_move(
    state: GameState,
    ai_index: int,
    difficulty: AIDifficulty,
    card_lookup: dict[str, CardDefinition],
    rng: Random,
) -> PlacementIntent:
    """Pick a move for the AI player, dispatching by difficulty."""
    if difficulty == AIDifficulty.EASY:
        return _novice_move(state, ai_index, card_lookup, rng)
    if difficulty == AIDifficulty.MEDIUM:
        return _greedy_move(state, ai_index, card_lookup, rng)
    return _random_move(state, ai_index, rng)


def _random_move(
    state: GameState,
    ai_index: int,
    rng: Random,
) -> PlacementIntent:
    """Fallback: random legal (card, cell) pair."""
    player = state.players[ai_index]
    empty_cells = [i for i, cell in enumerate(state.board) if cell is None]
    hand = player.hand

    if not hand or not empty_cells:
        raise ValueError("AI has no legal moves (empty hand or full board)")

    card_key = rng.choice(hand)
    cell_index = rng.choice(empty_cells)
    return PlacementIntent(player_index=ai_index, card_key=card_key, cell_index=cell_index)


def _count_owned(board: list, owner: int) -> int:
    """Count cells owned by the given player."""
    return sum(1 for cell in board if cell is not None and cell.owner == owner)


def _simulate_move(
    state: GameState,
    intent: PlacementIntent,
    card_lookup: dict[str, CardDefinition],
    rng: Random,
) -> int:
    """Simulate a move and return the number of cells owned by the intent's player."""
    # Use a separate RNG for simulation so we don't consume from the main RNG
    sim_rng = Random(rng.randint(0, 2**31))
    result = apply_intent(state, intent, card_lookup, sim_rng)
    return _count_owned(result.board, intent.player_index)


def _greedy_archetype_variants(
    state: GameState,
    ai_index: int,
    card_key: str,
    cell_index: int,
) -> list[dict[str, object]]:
    """Generate archetype parameter variants for greedy evaluation.

    Returns a list of archetype param dicts to try (empty list if no archetype available).
    """
    player = state.players[ai_index]
    if player.archetype_used or player.archetype is None:
        return []

    archetype = player.archetype
    variants: list[dict[str, object]] = []

    if archetype == Archetype.SKULKER:
        for side in ("n", "e", "s", "w"):
            variants.append({"use_archetype": True, "skulker_boost_side": side})
    elif archetype == Archetype.MARTIAL:
        for direction in ("cw", "ccw"):
            variants.append({"use_archetype": True, "martial_rotation_direction": direction})
    elif archetype == Archetype.INTIMIDATE:
        for neighbor_index, _, _ in ADJACENCY[cell_index]:
            cell = state.board[neighbor_index]
            if cell is not None and cell.owner != ai_index:
                variants.append({"use_archetype": True, "intimidate_target_cell": neighbor_index})
    elif archetype in (Archetype.CASTER, Archetype.DEVOUT):
        variants.append({"use_archetype": True})

    return variants


def _greedy_move(
    state: GameState,
    ai_index: int,
    card_lookup: dict[str, CardDefinition],
    rng: Random,
) -> PlacementIntent:
    """Greedy (Rahadin): one-ply evaluation, picks move maximizing owned cells.

    For each legal (card, cell) pair, simulates via apply_intent and counts
    cells owned by AI. Also evaluates archetype variants. Picks the best
    overall; breaks ties randomly.
    """
    player = state.players[ai_index]
    empty_cells = [i for i, cell in enumerate(state.board) if cell is None]
    hand = player.hand

    if not hand or not empty_cells:
        raise ValueError("AI has no legal moves (empty hand or full board)")

    # Evaluate all (card, cell, archetype_variant) combos
    best_score = -1
    best_moves: list[PlacementIntent] = []

    for card_key in hand:
        for cell_index in empty_cells:
            # Base move (no archetype)
            base_intent = PlacementIntent(
                player_index=ai_index, card_key=card_key, cell_index=cell_index
            )
            score = _simulate_move(state, base_intent, card_lookup, rng)
            if score > best_score:
                best_score = score
                best_moves = [base_intent]
            elif score == best_score:
                best_moves.append(base_intent)

            # Archetype variants
            for arch_params in _greedy_archetype_variants(state, ai_index, card_key, cell_index):
                arch_intent = PlacementIntent(
                    player_index=ai_index,
                    card_key=card_key,
                    cell_index=cell_index,
                    **arch_params,  # type: ignore[arg-type]
                )
                arch_score = _simulate_move(state, arch_intent, card_lookup, rng)
                if arch_score > best_score:
                    best_score = arch_score
                    best_moves = [arch_intent]
                elif arch_score == best_score:
                    best_moves.append(arch_intent)

    return rng.choice(best_moves)


def _score_placement(
    state: GameState,
    ai_index: int,
    card: CardDefinition,
    cell_index: int,
    card_lookup: dict[str, CardDefinition],
) -> float:
    """Score a (card, cell) pair for the novice strategy.

    +1 per adjacent opponent card where our attacking side > their facing side.
    +1 for elemental match with the cell.
    No noise here — caller adds noise.
    """
    score = 0.0
    for neighbor_index, attacking_side, defending_side in ADJACENCY[cell_index]:
        neighbor_cell = state.board[neighbor_index]
        if neighbor_cell is None or neighbor_cell.owner == ai_index:
            continue
        our_value = getattr(card.sides, attacking_side)
        their_value = getattr(card_lookup[neighbor_cell.card_key].sides, defending_side)
        if our_value > their_value:
            score += 1.0

    if state.board_elements is not None and state.board_elements[cell_index] == card.element:
        score += 1.0

    return score


def _novice_should_skip_archetype(state: GameState, ai_index: int) -> bool:
    """20% chance the novice never uses their archetype (derived from seed)."""
    return Random(state.seed + 7777 + ai_index).random() < 0.2


def _novice_should_activate_archetype(
    state: GameState,
    ai_index: int,
    rng: Random,
) -> bool:
    """50% chance to activate on first or second placement, never after."""
    player = state.players[ai_index]
    if player.archetype_used:
        return False
    if player.archetype is None:
        return False
    if _novice_should_skip_archetype(state, ai_index):
        return False

    # Count placements so far: initial hand size - current hand size
    cards_placed = 5 - len(player.hand)
    if cards_placed >= 2:
        return False

    return rng.random() < 0.5


def _novice_archetype_params(
    state: GameState,
    ai_index: int,
    cell_index: int,
    rng: Random,
) -> dict[str, object]:
    """Generate random archetype parameters for novice usage."""
    player = state.players[ai_index]
    archetype = player.archetype

    if archetype == Archetype.SKULKER:
        return {"use_archetype": True, "skulker_boost_side": rng.choice(["n", "e", "s", "w"])}
    if archetype == Archetype.MARTIAL:
        return {"use_archetype": True, "martial_rotation_direction": rng.choice(["cw", "ccw"])}
    if archetype == Archetype.INTIMIDATE:
        # Pick a random adjacent opponent card
        targets = []
        for neighbor_index, _, _ in ADJACENCY[cell_index]:
            cell = state.board[neighbor_index]
            if cell is not None and cell.owner != ai_index:
                targets.append(neighbor_index)
        if targets:
            return {"use_archetype": True, "intimidate_target_cell": rng.choice(targets)}
        return {}
    if archetype in (Archetype.CASTER, Archetype.DEVOUT):
        return {"use_archetype": True}
    return {}


def _novice_move(
    state: GameState,
    ai_index: int,
    card_lookup: dict[str, CardDefinition],
    rng: Random,
) -> PlacementIntent:
    """Novice (Ireena): semi-random placement with capture-aware scoring.

    Scores each (card, cell) pair: base score + uniform noise [0, 1.5].
    Picks from top candidates via weighted random choice.
    """
    player = state.players[ai_index]
    empty_cells = [i for i, cell in enumerate(state.board) if cell is None]
    hand = player.hand

    if not hand or not empty_cells:
        raise ValueError("AI has no legal moves (empty hand or full board)")

    # Score all legal moves
    candidates: list[tuple[str, int, float]] = []
    for card_key in hand:
        card = card_lookup[card_key]
        for cell_index in empty_cells:
            base_score = _score_placement(state, ai_index, card, cell_index, card_lookup)
            noise = rng.uniform(0, 1.5)
            candidates.append((card_key, cell_index, base_score + noise))

    # Pick via weighted random from top candidates
    # Sort by score descending, take top ~30% (at least 3), then weighted choice
    candidates.sort(key=lambda x: x[2], reverse=True)
    top_count = max(3, len(candidates) // 3)
    top = candidates[:top_count]

    # Weighted choice: use scores as weights (shift to positive)
    min_score = min(s for _, _, s in top)
    weights = [s - min_score + 0.1 for _, _, s in top]
    chosen_idx = _weighted_choice(weights, rng)
    card_key, cell_index, _ = top[chosen_idx]

    # Archetype activation
    arch_params: dict[str, object] = {}
    if _novice_should_activate_archetype(state, ai_index, rng):
        arch_params = _novice_archetype_params(state, ai_index, cell_index, rng)

    return PlacementIntent(
        player_index=ai_index,
        card_key=card_key,
        cell_index=cell_index,
        **arch_params,  # type: ignore[arg-type]
    )


def _weighted_choice(weights: list[float], rng: Random) -> int:
    """Return an index chosen proportionally to weights."""
    total = sum(weights)
    r = rng.uniform(0, total)
    cumulative = 0.0
    for i, w in enumerate(weights):
        cumulative += w
        if r <= cumulative:
            return i
    return len(weights) - 1
