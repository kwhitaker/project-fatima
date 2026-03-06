"""AI move selection.

choose_move(state, ai_index, difficulty, card_lookup, rng) -> PlacementIntent

Dispatches to per-difficulty strategy functions:
- easy (Novice/Ireena): semi-random with capture-aware scoring
- medium (Greedy/Rahadin): one-ply simulation, picks move maximizing owned cells
- hard (Expectimax/Strahd): multi-ply expectimax with opponent hand inference
- nightmare (MCTS/The Dark Powers): Monte Carlo tree search with concealment
"""

from random import Random

from app.models.cards import CardDefinition
from app.models.game import AIDifficulty, Archetype, GameState, GameStatus
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
    if difficulty == AIDifficulty.HARD:
        return _expectimax_move(state, ai_index, card_lookup, rng)
    if difficulty == AIDifficulty.NIGHTMARE:
        from app.rules.mcts import mcts_move

        return mcts_move(state, ai_index, card_lookup, rng)
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
    elif archetype == Archetype.CASTER:
        variants.append({"use_archetype": True})
    elif archetype == Archetype.DEVOUT:
        for idx, cell in enumerate(state.board):
            if cell is not None and cell.owner == ai_index and idx != cell_index:
                variants.append({"use_archetype": True, "devout_ward_cell": idx})

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
    if archetype == Archetype.CASTER:
        return {"use_archetype": True}
    if archetype == Archetype.DEVOUT:
        friendly_cells = [
            idx for idx, cell in enumerate(state.board)
            if cell is not None and cell.owner == ai_index and idx != cell_index
        ]
        if friendly_cells:
            return {"use_archetype": True, "devout_ward_cell": rng.choice(friendly_cells)}
        return {}
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


# ---------------------------------------------------------------------------
# Expectimax (Strahd / hard) — multi-ply with opponent hand inference
# ---------------------------------------------------------------------------

_EXPECTIMAX_HAND_SAMPLES = 10  # number of sampled opponent hands
_EXPECTIMAX_MAX_DEPTH = 2  # max search depth when >4 empty cells (1 AI ply + 1 opp response)
_EXPECTIMAX_FULL_DEPTH_THRESHOLD = 4  # search to terminal when ≤ this many empties


def _infer_opponent_pool(
    state: GameState,
    ai_index: int,
    card_lookup: dict[str, CardDefinition],
) -> list[str]:
    """Return card keys that could be in the opponent's hand.

    Excludes cards visible on the board and cards in the AI's own hand.
    """
    known_keys: set[str] = set()
    for cell in state.board:
        if cell is not None:
            known_keys.add(cell.card_key)
    known_keys.update(state.players[ai_index].hand)
    return [k for k in card_lookup if k not in known_keys]


def _sample_opponent_hands(
    pool: list[str],
    hand_size: int,
    n_samples: int,
    rng: Random,
) -> list[list[str]]:
    """Sample n_samples random opponent hands of given size from pool."""
    if hand_size <= 0 or not pool:
        return [[]]
    hand_size = min(hand_size, len(pool))
    hands: list[list[str]] = []
    for _ in range(n_samples):
        hands.append(rng.sample(pool, hand_size))
    return hands


def _heuristic_eval(
    state: GameState, ai_index: int, card_lookup: dict[str, CardDefinition],
) -> float:
    """Heuristic board evaluation for expectimax cutoff.

    Score = cells owned by AI - cells owned by opponent
          + 0.1 * (sum of side strengths of AI's placed cards
                  - sum of side strengths of opponent's placed cards)
    """
    ai_cells = 0
    opp_cells = 0
    ai_strength = 0.0
    opp_strength = 0.0
    for cell in state.board:
        if cell is None:
            continue
        card = card_lookup.get(cell.card_key)
        sides_sum = (card.sides.n + card.sides.e + card.sides.s + card.sides.w) if card else 20
        if cell.owner == ai_index:
            ai_cells += 1
            ai_strength += sides_sum
        else:
            opp_cells += 1
            opp_strength += sides_sum
    return (ai_cells - opp_cells) + 0.1 * (ai_strength - opp_strength)


def _expectimax_search(
    state: GameState,
    ai_index: int,
    card_lookup: dict[str, CardDefinition],
    rng: Random,
    depth: int,
    is_ai_turn: bool,
    opponent_hands: list[list[str]] | None = None,
) -> float:
    """Recursive expectimax evaluation.

    At AI nodes: maximize over all legal moves (including archetype variants).
    At opponent nodes: average over sampled hands, with opponent playing greedily.
    """
    empty_cells = [i for i, cell in enumerate(state.board) if cell is None]

    # Terminal or depth cutoff
    if not empty_cells or state.status != GameStatus.ACTIVE:
        if state.result is not None:
            if state.result.is_draw:
                return 0.0
            return 10.0 if state.result.winner == ai_index else -10.0
        return _heuristic_eval(state, ai_index, card_lookup)

    if depth <= 0:
        return _heuristic_eval(state, ai_index, card_lookup)

    if is_ai_turn:
        # Maximize over AI's legal moves
        best = float("-inf")
        player = state.players[ai_index]
        for card_key in player.hand:
            for cell_index in empty_cells:
                # Base move
                base_intent = PlacementIntent(
                    player_index=ai_index, card_key=card_key, cell_index=cell_index
                )
                sim_rng = Random(rng.randint(0, 2**31))
                next_state = apply_intent(state, base_intent, card_lookup, sim_rng)
                val = _expectimax_search(
                    next_state, ai_index, card_lookup, rng, depth - 1,
                    is_ai_turn=False, opponent_hands=opponent_hands,
                )
                if val > best:
                    best = val

                # Archetype variants
                arch_variants = _greedy_archetype_variants(
                    state, ai_index, card_key, cell_index,
                )
                for arch_params in arch_variants:
                    arch_intent = PlacementIntent(
                        player_index=ai_index,
                        card_key=card_key,
                        cell_index=cell_index,
                        **arch_params,  # type: ignore[arg-type]
                    )
                    sim_rng = Random(rng.randint(0, 2**31))
                    try:
                        next_state = apply_intent(state, arch_intent, card_lookup, sim_rng)
                    except Exception:
                        continue
                    val = _expectimax_search(
                        next_state, ai_index, card_lookup, rng, depth - 1,
                        is_ai_turn=False, opponent_hands=opponent_hands,
                    )
                    if val > best:
                        best = val

        return best if best > float("-inf") else 0.0
    else:
        # Opponent node: average over sampled hands, opponent plays greedily
        if not opponent_hands:
            return _heuristic_eval(state, ai_index, card_lookup)

        opp_index = 1 - ai_index
        total = 0.0
        valid_samples = 0
        for opp_hand in opponent_hands:
            # Filter to cards actually in lookup (safety)
            usable = [k for k in opp_hand if k in card_lookup and k not in
                       {c.card_key for c in state.board if c is not None}]
            if not usable:
                total += _heuristic_eval(state, ai_index, card_lookup)
                valid_samples += 1
                continue

            # Inject sampled hand into state so apply_intent validation passes
            opp_player = state.players[opp_index]
            patched_players = list(state.players)
            patched_players[opp_index] = opp_player.model_copy(update={"hand": usable})
            patched_state = state.model_copy(update={"players": patched_players})

            # Opponent plays greedily: pick the move that maximizes opponent cells
            best_opp_score = -1
            best_opp_state = patched_state
            for card_key in usable:
                for cell_index in empty_cells:
                    intent = PlacementIntent(
                        player_index=opp_index, card_key=card_key, cell_index=cell_index
                    )
                    sim_rng = Random(rng.randint(0, 2**31))
                    try:
                        next_state = apply_intent(patched_state, intent, card_lookup, sim_rng)
                    except Exception:
                        continue
                    opp_cells = _count_owned(next_state.board, opp_index)
                    if opp_cells > best_opp_score:
                        best_opp_score = opp_cells
                        best_opp_state = next_state

            val = _expectimax_search(
                best_opp_state, ai_index, card_lookup, rng, depth - 1,
                is_ai_turn=True, opponent_hands=opponent_hands,
            )
            total += val
            valid_samples += 1

        return total / valid_samples if valid_samples > 0 else 0.0


def _expectimax_move(
    state: GameState,
    ai_index: int,
    card_lookup: dict[str, CardDefinition],
    rng: Random,
) -> PlacementIntent:
    """Expectimax (Strahd): multi-ply search with opponent hand inference.

    Infers possible opponent hands, then runs expectimax tree search.
    Full depth for ≤4 empty cells; limited depth otherwise.
    """
    player = state.players[ai_index]
    empty_cells = [i for i, cell in enumerate(state.board) if cell is None]
    hand = player.hand

    if not hand or not empty_cells:
        raise ValueError("AI has no legal moves (empty hand or full board)")

    opp_index = 1 - ai_index
    opp_hand_size = len(state.players[opp_index].hand)

    # Infer opponent hand possibilities
    pool = _infer_opponent_pool(state, ai_index, card_lookup)
    n_samples = min(_EXPECTIMAX_HAND_SAMPLES, max(1, len(pool)))
    opponent_hands = _sample_opponent_hands(pool, opp_hand_size, n_samples, rng)

    # Determine search depth
    n_empty = len(empty_cells)
    if n_empty <= _EXPECTIMAX_FULL_DEPTH_THRESHOLD:
        depth = n_empty  # full depth (each move = 1 depth level)
    else:
        depth = _EXPECTIMAX_MAX_DEPTH

    # Evaluate all AI moves at the root
    best_score = float("-inf")
    best_moves: list[PlacementIntent] = []

    for card_key in hand:
        for cell_index in empty_cells:
            # Base move
            base_intent = PlacementIntent(
                player_index=ai_index, card_key=card_key, cell_index=cell_index
            )
            sim_rng = Random(rng.randint(0, 2**31))
            next_state = apply_intent(state, base_intent, card_lookup, sim_rng)
            val = _expectimax_search(
                next_state, ai_index, card_lookup, rng, depth - 1,
                is_ai_turn=False, opponent_hands=opponent_hands,
            )
            if val > best_score:
                best_score = val
                best_moves = [base_intent]
            elif val == best_score:
                best_moves.append(base_intent)

            # Archetype variants
            for arch_params in _greedy_archetype_variants(state, ai_index, card_key, cell_index):
                arch_intent = PlacementIntent(
                    player_index=ai_index,
                    card_key=card_key,
                    cell_index=cell_index,
                    **arch_params,  # type: ignore[arg-type]
                )
                sim_rng = Random(rng.randint(0, 2**31))
                try:
                    next_state = apply_intent(state, arch_intent, card_lookup, sim_rng)
                except Exception:
                    continue
                val = _expectimax_search(
                    next_state, ai_index, card_lookup, rng, depth - 1,
                    is_ai_turn=False, opponent_hands=opponent_hands,
                )
                if val > best_score:
                    best_score = val
                    best_moves = [arch_intent]
                elif val == best_score:
                    best_moves.append(arch_intent)

    return rng.choice(best_moves)
