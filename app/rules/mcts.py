"""MCTS (The Dark Powers / nightmare) AI strategy.

Monte Carlo Tree Search with UCB1 selection, lightweight SimBoard for speed,
opponent hand inference, concealment layer, and concurrency limiting.
"""

import asyncio
import math
from random import Random

from app.models.cards import CardDefinition
from app.models.game import GameState
from app.rules.board import ADJACENCY
from app.rules.reducer import PlacementIntent

# ---------------------------------------------------------------------------
# Concurrency limiter: at most 2 concurrent Nightmare computations
# ---------------------------------------------------------------------------

_nightmare_semaphore = asyncio.Semaphore(2)


async def acquire_nightmare_semaphore() -> None:
    """Acquire the nightmare semaphore. Caller should use asyncio.wait_for for timeout."""
    await _nightmare_semaphore.acquire()


# ---------------------------------------------------------------------------
# SimBoard: lightweight simulation board (~5-10x faster than full apply_intent)
# ---------------------------------------------------------------------------

# Precomputed side values: (n, e, s, w) tuples indexed by card_key
_SIDE_INDEX = {"n": 0, "e": 1, "s": 2, "w": 3}


class SimBoard:
    """Lightweight simulation board operating on raw tuples for speed.

    Each cell is either None or (card_key, owner).
    Card sides are cached as (n, e, s, w) tuples.
    """

    __slots__ = ("cells", "sides_cache", "elements")

    def __init__(
        self,
        cells: list[tuple[str, int] | None],
        sides_cache: dict[str, tuple[int, int, int, int]],
        elements: list[str] | None = None,
    ) -> None:
        self.cells = cells
        self.sides_cache = sides_cache
        self.elements = elements

    @classmethod
    def from_game_state(
        cls,
        state: GameState,
        card_lookup: dict[str, CardDefinition],
    ) -> "SimBoard":
        cells: list[tuple[str, int] | None] = []
        for cell in state.board:
            if cell is None:
                cells.append(None)
            else:
                cells.append((cell.card_key, cell.owner))

        sides_cache: dict[str, tuple[int, int, int, int]] = {}
        for key, card in card_lookup.items():
            sides_cache[key] = (card.sides.n, card.sides.e, card.sides.s, card.sides.w)

        return cls(cells, sides_cache, state.board_elements)

    def copy(self) -> "SimBoard":
        return SimBoard(list(self.cells), self.sides_cache, self.elements)

    def empty_cells(self) -> list[int]:
        return [i for i, c in enumerate(self.cells) if c is None]

    def count_owned(self, owner: int) -> int:
        return sum(1 for c in self.cells if c is not None and c[1] == owner)

    def place(self, cell_index: int, card_key: str, owner: int, rng: Random) -> None:
        """Place a card and resolve captures (mists + BFS combo). Mutates in place."""
        self.cells[cell_index] = (card_key, owner)

        # Mists roll
        roll = rng.randint(1, 6)
        mists_mod = -2 if roll == 1 else (2 if roll == 6 else 0)

        total_mod = mists_mod

        placed_sides = self.sides_cache.get(card_key)
        if placed_sides is None:
            return

        # BFS capture queue: (source_cell, source_sides, modifier)
        queue: list[tuple[int, tuple[int, int, int, int], int]] = [
            (cell_index, placed_sides, total_mod)
        ]

        while queue:
            src_idx, src_sides, mod = queue.pop(0)
            for nb_idx, atk_side, def_side in ADJACENCY[src_idx]:
                nb = self.cells[nb_idx]
                if nb is None or nb[1] == owner:
                    continue
                nb_sides = self.sides_cache.get(nb[0])
                if nb_sides is None:
                    continue
                atk_val = src_sides[_SIDE_INDEX[atk_side]] + mod
                def_val = nb_sides[_SIDE_INDEX[def_side]]
                if atk_val > def_val:
                    self.cells[nb_idx] = (nb[0], owner)
                    # Combo: captured card uses printed stats, no modifier
                    queue.append((nb_idx, nb_sides, 0))


# ---------------------------------------------------------------------------
# MCTS node and search
# ---------------------------------------------------------------------------

_MCTS_ITERATIONS = 2000
_UCB1_C = 1.414  # exploration constant


class MCTSNode:
    __slots__ = ("move", "parent", "children", "visits", "wins", "untried_moves")

    def __init__(
        self,
        move: tuple[str, int] | None,  # (card_key, cell_index) or None for root
        parent: "MCTSNode | None",
        untried_moves: list[tuple[str, int]],
    ) -> None:
        self.move = move
        self.parent = parent
        self.children: list[MCTSNode] = []
        self.visits = 0
        self.wins = 0.0
        self.untried_moves = untried_moves

    def ucb1(self, parent_visits: int) -> float:
        if self.visits == 0:
            return float("inf")
        return (self.wins / self.visits) + _UCB1_C * math.sqrt(
            math.log(parent_visits) / self.visits
        )

    def best_child(self) -> "MCTSNode":
        return max(self.children, key=lambda c: c.ucb1(self.visits))

    def expand(self, move: tuple[str, int], child_moves: list[tuple[str, int]]) -> "MCTSNode":
        child = MCTSNode(move=move, parent=self, untried_moves=child_moves)
        self.untried_moves.remove(move)
        self.children.append(child)
        return child

    def backprop(self, result: float) -> None:
        node: MCTSNode | None = self
        while node is not None:
            node.visits += 1
            node.wins += result
            node = node.parent


def _get_legal_moves(hand: list[str], empty_cells: list[int]) -> list[tuple[str, int]]:
    return [(card, cell) for card in hand for cell in empty_cells]


def _card_strength(sides: tuple[int, int, int, int]) -> int:
    return sum(sides)


def _run_mcts(
    state: GameState,
    ai_index: int,
    card_lookup: dict[str, CardDefinition],
    rng: Random,
) -> PlacementIntent:
    """Run MCTS search and return the best move."""
    opp_index = 1 - ai_index
    ai_hand = list(state.players[ai_index].hand)

    # Infer opponent card pool (same as expectimax)
    known_keys: set[str] = set()
    for cell in state.board:
        if cell is not None:
            known_keys.add(cell.card_key)
    known_keys.update(ai_hand)
    opp_pool = [k for k in card_lookup if k not in known_keys]
    opp_hand_size = len(state.players[opp_index].hand)

    sim_board_template = SimBoard.from_game_state(state, card_lookup)
    empty = sim_board_template.empty_cells()
    root_moves = _get_legal_moves(ai_hand, empty)

    if len(root_moves) == 1:
        card_key, cell_index = root_moves[0]
        return PlacementIntent(player_index=ai_index, card_key=card_key, cell_index=cell_index)

    root = MCTSNode(move=None, parent=None, untried_moves=list(root_moves))

    for _ in range(_MCTS_ITERATIONS):
        board = sim_board_template.copy()
        node = root
        sim_ai_hand = list(ai_hand)
        # Sample a random opponent hand for this playout
        pool_size = min(opp_hand_size, len(opp_pool))
        sim_opp_hand = rng.sample(opp_pool, pool_size) if pool_size > 0 else []
        is_ai = True  # AI moves first (root is AI node)

        # --- Selection ---
        while not node.untried_moves and node.children:
            node = node.best_child()
            if node.move is not None:
                card_key, cell_index = node.move
                if is_ai:
                    board.place(cell_index, card_key, ai_index, Random(rng.randint(0, 2**31)))
                    if card_key in sim_ai_hand:
                        sim_ai_hand.remove(card_key)
                else:
                    board.place(cell_index, card_key, opp_index, Random(rng.randint(0, 2**31)))
                    if card_key in sim_opp_hand:
                        sim_opp_hand.remove(card_key)
                is_ai = not is_ai

        # --- Expansion ---
        if node.untried_moves:
            move = rng.choice(node.untried_moves)
            card_key, cell_index = move
            if is_ai:
                board.place(cell_index, card_key, ai_index, Random(rng.randint(0, 2**31)))
                if card_key in sim_ai_hand:
                    sim_ai_hand.remove(card_key)
            else:
                board.place(cell_index, card_key, opp_index, Random(rng.randint(0, 2**31)))
                if card_key in sim_opp_hand:
                    sim_opp_hand.remove(card_key)
            is_ai = not is_ai

            # Determine next legal moves
            next_empty = board.empty_cells()
            if is_ai:
                next_moves = _get_legal_moves(sim_ai_hand, next_empty)
            else:
                next_moves = _get_legal_moves(sim_opp_hand, next_empty)

            node = node.expand(move, next_moves)

        # --- Rollout (random to terminal) ---
        rollout_ai_hand = list(sim_ai_hand)
        rollout_opp_hand = list(sim_opp_hand)
        rollout_is_ai = is_ai

        while True:
            rollout_empty = board.empty_cells()
            if not rollout_empty:
                break
            if rollout_is_ai:
                if not rollout_ai_hand:
                    break
                card_key = rng.choice(rollout_ai_hand)
                cell_index = rng.choice(rollout_empty)
                board.place(cell_index, card_key, ai_index, Random(rng.randint(0, 2**31)))
                rollout_ai_hand.remove(card_key)
            else:
                if not rollout_opp_hand:
                    break
                card_key = rng.choice(rollout_opp_hand)
                cell_index = rng.choice(rollout_empty)
                board.place(cell_index, card_key, opp_index, Random(rng.randint(0, 2**31)))
                rollout_opp_hand.remove(card_key)
            rollout_is_ai = not rollout_is_ai

        # --- Evaluate ---
        ai_cells = board.count_owned(ai_index)
        opp_cells = board.count_owned(opp_index)
        # Include hand-in-score
        ai_score = ai_cells + len(rollout_ai_hand)
        opp_score = opp_cells + len(rollout_opp_hand)

        if ai_score > opp_score:
            result = 1.0
        elif ai_score < opp_score:
            result = 0.0
        else:
            result = 0.5

        # --- Backpropagation ---
        node.backprop(result)

    # --- Select best move with concealment layer ---
    return _select_with_concealment(root, ai_index, sim_board_template, state)


def _select_with_concealment(
    root: MCTSNode,
    ai_index: int,
    board: SimBoard,
    state: GameState,
) -> PlacementIntent:
    """Select the best move, applying concealment (sandbagging) in early game.

    When two moves have similar visit counts (within 10%), prefer the one
    that plays a mid-strength card over the strongest card.
    """
    if not root.children:
        # Fallback — shouldn't happen
        card_key, cell_index = root.untried_moves[0]
        return PlacementIntent(player_index=ai_index, card_key=card_key, cell_index=cell_index)

    # Sort by visits (most visited = best)
    children = sorted(root.children, key=lambda c: c.visits, reverse=True)
    best = children[0]
    best_visits = best.visits

    # Early game check: more than 4 empty cells
    empty_count = len(board.empty_cells())
    if empty_count <= 4:
        # Late game: no concealment, pick the most visited
        card_key, cell_index = best.move  # type: ignore[misc]
        return PlacementIntent(player_index=ai_index, card_key=card_key, cell_index=cell_index)

    # Concealment: among moves within 10% of best visits, prefer mid-strength
    threshold = best_visits * 0.9
    candidates = [c for c in children if c.visits >= threshold]

    if len(candidates) <= 1:
        card_key, cell_index = best.move  # type: ignore[misc]
        return PlacementIntent(player_index=ai_index, card_key=card_key, cell_index=cell_index)

    # Rank cards by total side strength
    card_strengths: dict[str, int] = {}
    for c in candidates:
        ck = c.move[0]  # type: ignore[index]
        if ck not in card_strengths:
            sides = board.sides_cache.get(ck)
            card_strengths[ck] = sum(sides) if sides else 0

    # Find the max strength among candidates
    max_strength = max(card_strengths.values()) if card_strengths else 0

    # Prefer candidates that are NOT the strongest card
    non_max = [c for c in candidates if card_strengths.get(c.move[0], 0) < max_strength]  # type: ignore[index]
    if non_max:
        chosen = max(non_max, key=lambda c: c.visits)
        card_key, cell_index = chosen.move  # type: ignore[misc]
    else:
        card_key, cell_index = best.move  # type: ignore[misc]

    return PlacementIntent(player_index=ai_index, card_key=card_key, cell_index=cell_index)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def mcts_move(
    state: GameState,
    ai_index: int,
    card_lookup: dict[str, CardDefinition],
    rng: Random,
) -> PlacementIntent:
    """MCTS (The Dark Powers): Monte Carlo tree search for nightmare difficulty.

    Runs 2000 simulated playouts, UCB1 selection, random rollouts.
    Concealment layer prefers mid-strength cards when visit counts are close.
    """
    player = state.players[ai_index]
    empty_cells = [i for i, cell in enumerate(state.board) if cell is None]

    if not player.hand or not empty_cells:
        raise ValueError("AI has no legal moves (empty hand or full board)")

    return _run_mcts(state, ai_index, card_lookup, rng)
