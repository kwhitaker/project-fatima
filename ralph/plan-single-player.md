# Single Player (AI Opponent) — Implementation Plan

## Overview

Allow a player to start a game against an AI opponent at one of four difficulty levels, themed as Curse of Strahd characters. The AI takes its turns automatically on the server; from the frontend's perspective, AI moves arrive via Realtime exactly like a human opponent's moves.

---

## Difficulty Levels

| Difficulty | Character | Strategy |
|---|---|---|
| **Easy** | Ireena Kolyana | Novice — picks placements semi-randomly with basic instincts. Uses archetype powers, but not well (sometimes wastes them, sometimes forgets). Plays like someone who just learned the rules. |
| **Medium** | Rahadin | Greedy — evaluates every legal placement, picks the one that captures the most cards this turn. Breaks ties randomly. Uses archetype opportunistically (Skulker boost on weakest matchup, Martial rotate to maximize captures). |
| **Hard** | Strahd von Zarovich | Expectimax with opponent hand inference — reasons about what the opponent is likely holding based on played cards and deal constraints, then maximizes expected score across possible hidden hands. Uses archetypes optimally. Plays to win despite imperfect information. |
| **Nightmare** | The Dark Powers | MCTS with information warfare — runs thousands of playouts, adaptively models the opponent, and plays for information advantage. Conceals its own strategy while probing the opponent's hand. Every move serves two purposes: board position and knowledge. |

---

## How the AI works

### Important: imperfect information

This is **not** a perfect-information game. Each player can only see their own hand — the opponent's specific cards are hidden (only the count is visible). The AI has the same constraint: it knows its own hand, sees all played cards on the board, but does not know the opponent's hand. This fundamentally shapes the strategy at each difficulty level.

### The core loop

The reducer is already a pure function: `apply_intent(state, intent, card_lookup, rng) → GameState`. The AI simply:

1. Enumerates all legal moves (each card in hand × each empty cell = at most 5×9 = 45 options, shrinking every turn).
2. Picks one according to its strategy (novice / greedy / expectimax / MCTS).
3. Constructs a `PlacementIntent` and passes it through the same `apply_intent` the human path uses.

No special game logic. No cheating. The AI plays by the exact same rules and has the same information a human player would.

### Novice (Ireena)

Ireena plays like someone who just learned the rules — she has basic instincts but makes plenty of mistakes.

**Placement strategy — "strong side out" with noise:**

```
for each (card, cell) in legal_moves:
    score = 0
    # She vaguely tries to place strong sides facing opponents
    for each adjacent opponent card:
        if my_attacking_side > their_facing_side: score += 1
    # She likes matching elements (someone told her it's good)
    if card.element == board_elements[cell]: score += 1
    # But she doesn't think very hard — add random noise
    score += random.uniform(0, 1.5)
pick = weighted_random_choice(candidates, by=score)
```

She doesn't think about *defense* — she doesn't consider which of her sides are exposed to future captures. She doesn't think about Plus rule setups. She sometimes places a strong card in a corner for no reason.

**Archetype usage — enthusiastic but clumsy:**

- She *does* use her archetype, but often suboptimally.
- **50% chance she uses it on her first or second turn** regardless of board state (too eager).
- When she uses Skulker, she boosts a random side rather than the one facing an opponent.
- When she uses Martial, she picks a random rotation direction.
- When she uses Intimidate, she targets a random adjacent opponent card rather than the most threatening one.
- When she uses Caster/Devout, she uses it on a non-Fog/non-Omen turn (wasted).
- 20% chance she forgets to use it entirely (reaches the endgame with `archetype_used = False`).

**Draft strategy:** Picks 5 of 7 cards randomly (doesn't min-max her deal).

### Greedy (Rahadin)

```
for each (card, cell) in legal_moves:
    next_state = apply_intent(state, PlacementIntent(card, cell), ...)
    score = count_cells_owned_by(next_state, ai_index)
best = max(candidates, key=score)  # ties broken randomly
```

Evaluates one move ahead. Considers archetype options (Skulker boost on weakest matchup, Martial rotation) by also testing `use_archetype=True` variants, picking the best overall. Doesn't think about what the opponent will do next — pure immediate greed. Doesn't reason about the opponent's hidden hand at all.

**Draft strategy:** Picks 5 of 7 cards with the highest total side values.

### Expectimax (Strahd)

Since Strahd doesn't know the opponent's hand, pure minimax is not possible. Instead, Strahd uses **expectimax with opponent hand inference** — he reasons about what the opponent *probably* holds, then maximizes his expected score.

**Opponent hand inference:**

```
known_cards = cards_on_board + strahd_hand
remaining_pool = all_cards_in_game - known_cards
# The opponent's hand is some subset of remaining_pool
# Weight candidates by deal generation constraints (rarity, character uniqueness)
possible_opponent_hands = sample_likely_hands(remaining_pool, count=N)
```

As the game progresses and the opponent plays cards, the pool shrinks and Strahd's picture of the opponent's hand sharpens. By the opponent's last card, Strahd knows exactly what it is.

**Expectimax search:**

```
def expectimax(state, depth, is_ai_turn, opponent_hand_samples):
    if terminal(state) or depth == 0:
        return evaluate(state)  # ai_score - opponent_score

    if is_ai_turn:
        # Strahd knows his own hand — maximize over his moves
        best = -inf
        for move in legal_moves(state, ai_index):
            next_state = apply_intent(state, move, ...)
            val = expectimax(next_state, depth-1, False, opponent_hand_samples)
            best = max(best, val)
        return best
    else:
        # Opponent's turn — average over sampled possible hands
        total = 0
        for sample_hand in opponent_hand_samples:
            # Assume opponent plays greedily with this hand
            opponent_move = best_greedy_move(state, sample_hand)
            next_state = apply_intent(state, opponent_move, ...)
            total += expectimax(next_state, depth-1, True, opponent_hand_samples)
        return total / len(opponent_hand_samples)
```

Key design choices:

- **Sample count (N):** ~20–50 sampled opponent hands balances accuracy vs. speed. The card pool is small enough that sampling covers the space well.
- **Opponent model:** Strahd assumes the opponent plays greedily (like Rahadin). This is a reasonable middle ground — it won't be exploited by truly random play, and it approximates competent human play.
- **Search depth:** Full depth when ≤4 empty cells remain (perfect endgame play). Earlier turns use depth 3–4 with a heuristic evaluation (cell ownership + positional strength).
- **Archetype usage:** Strahd evaluates both use/don't-use at every node, picking the path with higher expected value.

**Why this works:** The 3×3 board keeps the search space small even with sampling. 50 opponent hand samples × ~30 moves per node × depth 4 is well within sub-second computation. Late game (few cards left, opponent hand nearly known) converges toward perfect play.

**Draft strategy:** Evaluates hand compositions for side coverage and elemental matchups, picks the 5 that maximize defensive and offensive flexibility.

### MCTS + Information Warfare (The Dark Powers)

The Dark Powers represent the unseen forces that manipulate fate in Barovia. They don't just play well — they play *inscrutably*. Where Strahd optimizes board position, the Dark Powers optimize across two dimensions simultaneously: **board position** and **information advantage**.

**Core engine — Monte Carlo Tree Search (MCTS):**

Unlike Strahd's expectimax (fixed depth, sampled hands), the Dark Powers use MCTS which naturally handles imperfect information by running thousands of simulated playouts:

```
def mcts_choose_move(state, ai_index, card_lookup, rng, simulations=5000):
    root = MCTSNode(state)

    for _ in range(simulations):
        # 1. Sample a possible opponent hand for this playout
        opponent_hand = sample_opponent_hand(state, ai_index, card_lookup)

        # 2. SELECT: walk the tree using UCB1 (exploration/exploitation)
        node = select(root)

        # 3. EXPAND: add a child for an untried move
        child = expand(node)

        # 4. SIMULATE: random playout to terminal state
        #    (using sampled opponent hand for opponent moves)
        result = simulate(child.state, opponent_hand, card_lookup, rng)

        # 5. BACKPROPAGATE: update win statistics up the tree
        backpropagate(child, result)

    # Pick the move with the most visits (robust choice)
    return root.most_visited_child().move
```

2,000–3,000 simulations balances strength vs. compute on base-tier hosting (see Performance section below).

**Why MCTS beats expectimax here:**

- **No depth limit.** Every playout runs to game completion — no heuristic evaluation needed.
- **Natural imperfect-information handling.** Each playout samples a fresh opponent hand, so the tree statistics automatically integrate over the uncertainty.
- **Exploration.** UCB1 balances trying new moves vs. exploiting known-good ones — Strahd's expectimax can miss non-obvious moves that pay off later.
- **Scales with compute.** More simulations = better play. Can be tuned per-move based on game phase (spend more time on critical early placements).

**Information warfare layer — what makes the Dark Powers unique:**

On top of raw MCTS strength, the Dark Powers apply three information-theoretic principles that Strahd ignores:

**1. Concealment (minimize information leakage):**

When two moves have similar MCTS visit counts (i.e., similar expected value), prefer the one that reveals less about the hand:

```
def information_cost(move, ai_hand):
    # Playing your strongest card early tells the opponent your hand is weaker
    # Playing a card with distinctive side values narrows what you might hold
    card = card_lookup[move.card_key]
    total_strength = sum(card.sides.values())
    hand_avg = mean(sum(card_lookup[k].sides.values()) for k in ai_hand)
    # Penalty for playing cards far above hand average early
    reveal_penalty = max(0, total_strength - hand_avg) * (empty_cells / 9)
    return reveal_penalty
```

In practice: the Dark Powers sandbag early, playing mid-strength cards first. They save their strongest cards for the late game when the opponent can't adapt. This feels *wrong* to play against — the opponent keeps waiting for the Dark Powers to show their strength, and by the time they do, it's too late.

**2. Probing (maximize information gained):**

Prefer placements that create board states where the opponent's response is informative:

```
def information_value(move, state, opponent_hand_distribution):
    next_state = apply_intent(state, move, ...)
    # How many distinct "good responses" does the opponent have?
    # If placing here leaves a weak side exposed, and the opponent
    # captures it, we know they have a strong card on that side.
    # If they DON'T capture, we can eliminate those cards.
    response_entropy = estimate_response_entropy(next_state, opponent_hand_distribution)
    # Lower entropy = more informative (opponent's response tells us more)
    return -response_entropy
```

The Dark Powers sometimes make moves that look slightly suboptimal on the board but are *diagnostically valuable* — they reveal what the opponent is holding. This feeds back into better hand inference for subsequent turns.

**3. Denial (minimize opponent's best-case variance):**

Instead of just maximizing expected score, the Dark Powers also minimize the *spread* of outcomes:

```
def denial_score(move, mcts_node):
    # Among all simulated playouts through this move,
    # how often does the opponent achieve a high score?
    opponent_scores = [playout.opponent_score for playout in mcts_node.playouts]
    # Penalize moves where the opponent occasionally scores very well
    # (even if our average is good)
    return -percentile(opponent_scores, 90)  # minimize opponent's upside
```

This makes the Dark Powers feel *suffocating*. Against Strahd, you might lose on average but occasionally pull off a big win. Against the Dark Powers, your ceiling is capped — they systematically deny your best outcomes.

**Adaptive opponent modeling:**

The Dark Powers update their beliefs about the opponent during the game:

- **Card inference:** Track which cards the opponent has played and update the remaining pool. But also track what the opponent *didn't* do — if they had a chance to capture with a strong south-side card and didn't, reduce the probability they hold one.
- **Style detection:** Is the opponent playing aggressively (capturing when possible) or defensively (protecting sides)? Weight the MCTS simulation opponent model accordingly — don't assume greedy play if the opponent is clearly thinking ahead.
- **Archetype timing:** If the opponent hasn't used their archetype by turn 3, increase weight on "they're setting up a combo" — play to disrupt likely setups.

**Archetype usage:**

The Dark Powers use archetypes with precision informed by their MCTS simulations. They evaluate archetype use within the tree — the simulation naturally discovers the optimal timing because it plays out to completion. The concealment layer also applies: if using an archetype now would reveal too much about the strategy, delay it.

**Draft strategy:** MCTS-informed — simulate 50+ random games for each possible 5-of-7 hand composition (21 combos × 50 games = ~1,050 playouts), pick the hand that wins the most simulations across a range of opponent hands. This is ~200–400ms — acceptable since it only happens once at game start.

**Thinking time:** 1–3s per move (longer than other difficulties). This is real compute, not artificial delay — the MCTS simulations are the thinking. Scales with game phase: slower early (bigger tree), faster late (fewer options).

### Mists handling

All four difficulties use the same Mists rolls from the seeded RNG — the AI doesn't know what it will roll before placing. For Caster (Mists reroll archetype), the greedy/expectimax/MCTS strategies evaluate whether using it improves the position, but the roll is still random. The AI has no information advantage.

---

## Changes

### 1. New module: `app/rules/ai.py`

The AI strategy engine. Pure functions, no I/O.

```python
def choose_move(
    state: GameState,
    ai_index: int,
    difficulty: AIDifficulty,
    card_lookup: dict[str, CardDefinition],
    rng: Random,
) -> PlacementIntent:
    ...
```

Contains `_novice_move`, `_greedy_move`, `_expectimax_move`, `_mcts_move` as internal strategies. The MCTS engine (`_mcts_move`) is the most complex — consider a separate `app/rules/mcts.py` module if it grows beyond ~200 lines.

### 2. Model changes

**File:** `app/models/game.py`

- Add `player_type: Literal["human", "ai"] = "human"` to `PlayerState`.
- Add `ai_difficulty: AIDifficulty | None = None` to `PlayerState` (only set for AI players).

**File:** `app/models/game.py` (or new `app/models/ai.py`)

```python
class AIDifficulty(str, Enum):
    EASY = "easy"           # Ireena
    MEDIUM = "medium"       # Rahadin
    HARD = "hard"           # Strahd
    NIGHTMARE = "nightmare" # The Dark Powers
```

### 3. AI identity

**File:** `app/services/game_service.py`

- Define `AI_PLAYER_ID = "00000000-0000-0000-0000-000000000001"` (a reserved UUID that is never a real Supabase user).
- AI player email: display name based on difficulty (`"Ireena Kolyana"`, `"Rahadin"`, `"Strahd von Zarovich"`, `"The Dark Powers"`).
- Exempt `AI_PLAYER_ID` from `_check_no_active_game` (the AI can be in many games at once).

### 4. New service: create game vs AI

**File:** `app/services/game_service.py`

`create_game_vs_ai(caller_id, caller_email, difficulty, card_store, game_store) → GameState`

This does everything in one call:
1. Create game with human as player 0.
2. Add AI as player 1 with `player_type="ai"` and the chosen difficulty.
3. Generate deals for both players (same `generate_matched_deals`).
4. Auto-draft for AI: random 5 for Ireena, highest-total-sides for Rahadin, strategic composition for Strahd, MCTS-simulated draft for Dark Powers.
5. Auto-select archetype for AI (random for Ireena, strategic pick for Rahadin/Strahd/Dark Powers).
6. Game enters `DRAFTING` status — human still needs to draft and pick archetype.
7. Once human drafts → game goes `ACTIVE` → if AI goes first, immediately trigger AI move.

### 5. AI move trigger (background task)

**File:** `app/services/game_service.py` (in `submit_move` and `submit_draft`)

After any state transition that results in it being the AI's turn:

```python
if new_state.status == GameStatus.ACTIVE:
    next_player = new_state.players[new_state.current_player_index]
    if next_player.player_type == "ai":
        background_tasks.add_task(execute_ai_turn, game_id, game_store, card_store)
```

`execute_ai_turn` loads the current state, calls `choose_move`, then calls `submit_move` internally. This chains naturally — if there are consecutive AI turns (shouldn't happen in 1v1, but defensive), it handles them.

Add a small delay scaled by difficulty before the AI move so it feels like "thinking" rather than instant: Ireena 0.3–0.8s (quick, impulsive), Rahadin 0.5–1.0s (deliberate), Strahd 0.8–1.5s (calculating), Dark Powers 1.5–2.5s (ominous).

### 6. New endpoint

**File:** `app/routers/games.py`

```
POST /games/vs-ai
Body: { "difficulty": "easy" | "medium" | "hard" | "nightmare" }
Response: GameState (in DRAFTING status, ready for human to draft)
```

### 7. Frontend: AI game creation

**File:** `web/src/pages/Lobby.tsx` (or wherever game creation lives)

Add a "Play vs AI" section with four buttons/cards:

- **Ireena Kolyana** (Easy) — "A sheltered noble still learning the game."
- **Rahadin** (Medium) — "Strahd's chamberlain plays with cold precision."
- **Strahd von Zarovich** (Hard) — "The lord of Barovia does not lose."
- **The Dark Powers** (Nightmare) — "Ancient forces that see through every stratagem." (visually distinct — darker styling, maybe a subtle animation to signal this is the "real" challenge)

Clicking one calls `POST /games/vs-ai` with the chosen difficulty, then navigates to the game room.

### 8. Frontend: AI opponent display

**Files:** `web/src/pages/GameRoom.tsx`, `ActiveGameView.tsx`

- Show the AI character name instead of email (e.g., "Playing against Strahd von Zarovich").
- Optionally show a thematic avatar/icon per AI character.
- During the AI's turn, show a "thinking..." indicator. Flavor per character: Ireena "Ireena is thinking...", Rahadin "Rahadin calculates...", Strahd "Strahd contemplates...", Dark Powers "The Dark Powers stir..."
- Everything else works as-is — AI moves arrive via Realtime subscription.

---

## What does NOT change

- **Reducer (`apply_intent`)** — the AI submits intents through the exact same pure function. Zero changes.
- **Capture logic, Mists, Plus rule, Elementals** — all unchanged. AI plays by the same rules.
- **RLS** — AI never authenticates client-side; backend uses service role key.
- **Realtime** — AI moves are stored as normal `game_events`; human client picks them up identically.

---

## Performance & Infrastructure

This app runs on base-tier hosting (single uvicorn worker, shared vCPU, 256–512MB RAM). The AI difficulties have very different compute profiles.

### Cost per move

| Difficulty | `apply_intent` calls | Wall time | Memory |
|---|---|---|---|
| Ireena | 1 | <1ms | Negligible |
| Rahadin | ~45 (one ply) | ~5–10ms | Negligible |
| Strahd | ~5,000–10,000 (expectimax) | ~0.5–2s | ~10–20MB (tree) |
| Dark Powers | ~15,000–27,000 (MCTS) | ~1–3s | ~20–50MB (tree) |

### Critical optimization: lightweight simulation board

The biggest cost inside MCTS isn't game logic — it's Pydantic `model_copy()` with validation on every simulated move. For the simulation engine, **bypass Pydantic entirely**:

```python
# Instead of full GameState + apply_intent for each simulated move:
SimBoard = list[tuple[str, int] | None]  # (card_key, owner) × 9 cells

def sim_placement(board: SimBoard, card: CardSides, cell: int, owner: int, ...) -> SimBoard:
    # Operates on raw tuples — no Pydantic, no validation
    # ~5–10μs per call vs. ~50–200μs for full apply_intent
    ...
```

This alone should give a 5–10x speedup for MCTS playouts, bringing Dark Powers compute to **~0.5–1.5s per move** — comparable to Strahd.

The real `apply_intent` is only called once, for the final chosen move, to produce the canonical `GameState` for storage.

### Concurrency limiter for Nightmare games

A single Dark Powers move uses ~0.5–1.5s of CPU and ~20–50MB of transient memory. On a single-worker base-tier instance, concurrent Nightmare games would stack up and degrade the server for everyone — human-vs-human games, other AI games, even basic API calls.

**Implementation: a semaphore-based concurrency gate.**

**File:** `app/services/ai_limiter.py`

```python
import asyncio
from fastapi import HTTPException

# Max concurrent Nightmare games computing a move at once.
# On base-tier (1 worker, shared vCPU, 256–512MB):
#   - 2 concurrent = ~1–3s per move, ~40–100MB transient
#   - 3 concurrent = risk of timeouts + memory pressure
MAX_CONCURRENT_NIGHTMARE = 2

_nightmare_semaphore = asyncio.Semaphore(MAX_CONCURRENT_NIGHTMARE)

async def acquire_nightmare_slot() -> bool:
    """Try to acquire a Nightmare compute slot. Non-blocking."""
    return _nightmare_semaphore._value > 0  # check before blocking

async def run_nightmare_move(coro):
    """Run a Nightmare AI move within the concurrency limit."""
    if _nightmare_semaphore._value == 0:
        # All slots full — queue with a timeout rather than reject
        try:
            await asyncio.wait_for(_nightmare_semaphore.acquire(), timeout=10.0)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=503,
                detail="The Dark Powers are occupied. Try again in a moment."
            )
    else:
        await _nightmare_semaphore.acquire()
    try:
        return await coro
    finally:
        _nightmare_semaphore.release()
```

**Behavior:**

- Up to `MAX_CONCURRENT_NIGHTMARE` (default: 2) Nightmare moves can compute simultaneously.
- Additional requests queue for up to 10 seconds, then get a themed 503: *"The Dark Powers are occupied."*
- Ireena/Rahadin/Strahd are **not limited** — their compute is negligible to modest.
- The semaphore is per-process (resets on restart), which is fine for a single-worker deployment.
- `MAX_CONCURRENT_NIGHTMARE` is a constant, easily tuned. If the app moves to beefier hosting, bump it up.

**Where it hooks in:**

In `execute_ai_turn` (the background task that runs AI moves):

```python
async def execute_ai_turn(game_id, game_store, card_store):
    state = game_store.get_game(game_id)
    ai_player = state.players[state.current_player_index]

    if ai_player.ai_difficulty == AIDifficulty.NIGHTMARE:
        move = await run_nightmare_move(
            asyncio.get_event_loop().run_in_executor(
                None, _compute_dark_powers_move, state, card_store
            )
        )
    else:
        move = _compute_ai_move(state, ai_player.ai_difficulty, card_store)

    submit_move_internal(game_id, move, game_store, card_store)
```

**Frontend handling of 503:**

If the `POST /games/vs-ai` with `difficulty=nightmare` or a mid-game move gets a 503, show: *"The Dark Powers are occupied with another mortal. Please wait..."* and auto-retry after a few seconds.

### run_in_executor for all AI moves

Even Strahd's 0.5–2s expectimax can block the event loop. All AI move computation should be offloaded:

```python
await asyncio.get_event_loop().run_in_executor(None, compute_fn, ...)
```

This ensures the FastAPI worker stays responsive to other requests (game GETs, human moves, health checks) while AI churns.

---

## Test plan

### Ireena (novice)
- `test_novice_returns_valid_move` — returns a legal (card_in_hand, empty_cell) pair.
- `test_novice_prefers_strong_side_matchups` — given an obvious capture vs. a clearly worse placement, Ireena picks the capture *most* of the time (but not always — noise allows mistakes).
- `test_novice_archetype_usage` — over many runs, Ireena uses her archetype most of the time but occasionally forgets; when she uses it, it's not always optimal (e.g., Skulker boosts a random side).
- `test_novice_draft_is_random` — selected 5 cards are not consistently the highest-value ones.

### Rahadin (greedy)
- `test_greedy_prefers_captures` — given a board where one placement captures and another doesn't, greedy picks the capture.
- `test_greedy_archetype_maximizes_captures` — when using archetype would flip an extra capture, Rahadin uses it.
- `test_greedy_draft_picks_highest_value` — selected 5 cards have the highest total side values from the deal.

### Strahd (expectimax)
- `test_expectimax_finds_winning_endgame` — set up a near-endgame (2–3 cards left) where only one move wins; verify Strahd finds it.
- `test_expectimax_avoids_exposed_sides` — Strahd avoids placements that leave weak sides exposed to likely opponent captures.
- `test_expectimax_narrows_opponent_hand` — as opponent plays cards, Strahd's inferred opponent pool shrinks correctly.
- `test_expectimax_archetype_timing` — Strahd saves archetype for high-impact moments rather than using it early.

### Dark Powers (MCTS)
- `test_mcts_returns_valid_move` — returns a legal placement within the time budget.
- `test_mcts_beats_greedy_statistically` — over 50+ simulated games, Dark Powers wins significantly more often than Rahadin against the same greedy opponent.
- `test_mcts_concealment` — in early game (≥5 empty cells), Dark Powers avoids playing its strongest card first (measured over many runs — strongest card played turn 1 less than 20% of the time).
- `test_mcts_probing` — when a diagnostic placement (weak exposed side) and a safe placement have similar board value, Dark Powers prefers the diagnostic one.
- `test_mcts_opponent_inference_updates` — after observing opponent plays, the inferred opponent hand pool shrinks and excludes played cards.
- `test_mcts_draft_outperforms_random` — MCTS-drafted hand wins more simulated games than a randomly drafted hand from the same deal.

### Integration
- `test_create_game_vs_ai` — creates game with AI player, correct difficulty, auto-drafted hand.
- `test_ai_turn_triggers_after_human_move` — submit a human move where the next turn is AI; verify the AI move event appears.
- `test_ai_exempt_from_active_game_check` — AI UUID can be in multiple concurrent games.
- `test_ai_respects_same_information` — AI only uses information available to a human player (own hand + board state + played cards).

### Performance & concurrency
- `test_sim_board_matches_apply_intent` — lightweight simulation board produces the same captures as the full `apply_intent` for a suite of test positions.
- `test_nightmare_semaphore_limits_concurrency` — with `MAX_CONCURRENT_NIGHTMARE=2`, a third concurrent Nightmare move queues and eventually times out with 503.
- `test_nightmare_503_message` — 503 response body contains the themed error message.
- `test_non_nightmare_bypasses_limiter` — Ireena/Rahadin/Strahd moves are never blocked by the semaphore.

### Frontend
- Test that difficulty selector renders four AI characters with flavor text.
- Test that AI opponent name displays correctly in game room.
- Test that Dark Powers card has distinct visual treatment.
