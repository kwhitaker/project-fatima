# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Turn-based 3x3 card-capture game (Triple Triad–inspired, Curse of Strahd–flavored) built with FastAPI + Supabase.

See `AGENTS.md` for the authoritative command reference; update it when you add commands.

## Commands

Authoritative commands live in `AGENTS.md`.

```bash
# Install / bootstrap
uv sync --extra dev

# Dev server
uv run uvicorn app.main:app --reload

# Lint / format
uv run ruff check .
uv run ruff format .

# Typecheck
uv run pyright

# Tests
uv run pytest
```

## Architecture

### Layered structure (target)

```
app/
  main.py            # FastAPI app factory
  routers/           # HTTP endpoints (thin: validate input → call service)
  services/          # Orchestration (create game, submit move, etc.)
  store/             # Storage boundary: GameStore / CardStore interfaces
    memory.py        # In-memory impl for tests
    supabase.py      # Real Supabase impl
  rules/             # Pure Python rules engine (no I/O, no DB)
    reducer.py       # apply_intent(state, intent, rng) → next state
    captures.py      # Capture resolution logic
    archetypes.py    # Once-per-game archetype powers
    deck.py          # Deck generation + validation
    cards.py         # cards.jsonl loader + validator
    ai.py            # AI strategy engine (novice, greedy, expectimax)
    mcts.py          # MCTS strategy (Nightmare difficulty)
    ai_comments.py   # AI in-character commentary system
tests/
cards.jsonl          # Card definitions (JSON Lines, one card per line)
```

### Rules engine (the core invariant)

The reducer is a **pure function**: `apply_intent(state, intent, rng) → GameState`. It is the single source of game truth — no game logic should live in routers or services. All randomness flows through the explicit `rng` argument (seeded, never `random.*` globally).

### Persistence: event log + snapshot

- `game_events` table is the append-only source of truth.
- `games.current_state` (JSONB) is a cached snapshot for fast reads.
- Moves are atomic: insert event + update snapshot in one transaction.
- `state_version` provides optimistic locking; conflicts → 409.
- `seq` per `game_id` orders events.

### Auth

Supabase JWT in `Authorization: Bearer <token>`. FastAPI uses service role key for writes. RLS prevents clients from writing `games`/`game_events` directly.

### Realtime

Clients subscribe to Supabase Realtime inserts on `game_events` filtered by `game_id`, then refetch `GET /games/{game_id}` (MVP-simple strategy).

## Key Domain Concepts

- **Board**: 3×3 grid, one card per cell.
- **Card sides**: N/E/S/W integer values (1–10). Higher touching side wins a capture. Every card must have at least one side ≤ 3 (weak-side rule — ensures filler cards remain threatening on at least one edge).
- **Mists (1d6)**: Roll per placement. 1=Fog (−2 all comparisons), 6=Omen (+2), 2–5=no effect. Modifier is ephemeral — printed stats never change.
- **Plus rule**: When placing a card, if 2+ adjacent opponent cards each share the same sum (placed card's attacking side + neighbor's facing side), all matching neighbors are captured immediately — even if the placed card's side is lower. Uses raw printed values only; Mists modifier and Elemental bonus do NOT apply to Plus sums. Plus-captured cards enter the standard BFS combo chain.
- **Elemental system**: Each card has one of five elements: `blood`, `holy`, `arcane`, `shadow`, `nature`. Each board cell also has an element (9 elements, generated deterministically from the game seed at match start). Placing a card on a matching-element cell grants +1 to all its side comparisons for that placement's initial battles. Combo chains and Plus rule both use raw printed values (no elemental bonus).
- **Archetypes**: Once-per-game power. Martial (rotate card CW/CCW), Skulker (+3 one side), Caster (reroll Mists), Devout (negate Fog), Intimidate (debuff adjacent opponent card's facing side to its weakest).
- **Sudden Death**: Tie at board-full → same `game_id`, `round_number++`, each player gets back owned board cards + cards in hand. Cap: 3 Sudden Death rounds, then draw. With hand-in-score, ties are naturally reachable (5-5) and Sudden Death is a real game mechanic.
- **Deal & Draft**: Each player is dealt 7 cards (`DEAL_SIZE`), picks 5 to keep (`HAND_SIZE`). The draft phase (`DRAFTING` status) occurs between joining and the active match. The first player places all 5 cards; the second player places 4, keeping 1 in hand.
- **Scoring (hand-in-score)**: Final score = cells owned on board + cards remaining in hand. Total points = 10. First player can score 0–9, second player can score 1–10 (always has 1 card in hand).
- **Deal validation**: Named character uniqueness by `character_key`; rarity slots (ultra≤1, very_rare≤2, rare≤3); copy limits by rarity bucket.
- **Single Player**: Play against AI opponents at four difficulty levels, each themed as a Curse of Strahd character:
  - **Easy / Ireena Kolyana**: Semi-random placement with basic capture instincts and noisy scoring. Archetype use is enthusiastic but clumsy (50% chance on early turns, 20% chance to forget entirely).
  - **Medium / Rahadin**: One-ply greedy evaluation — simulates every legal move via `apply_intent`, picks the one that maximizes owned cells. Evaluates archetype variants per move.
  - **Hard / Strahd von Zarovich**: Expectimax search with opponent hand inference. Samples ~25 possible opponent hands, searches full depth when ≤4 empty cells, depth 4 otherwise.
  - **Nightmare / The Dark Powers**: MCTS with 2000+ playouts, UCB1 selection, lightweight `SimBoard` for fast rollouts. Concealment layer sandbagging early game. Gated by `asyncio.Semaphore(2)` to limit server load.
  - AI turns are triggered via `BackgroundTasks` after human moves. AI moves use the same `apply_intent` path — no special game logic.
  - AI commentary: in-character comments triggered by captures, Plus/Elemental events, archetype use, and game endings. Attached to `last_move.ai_comment`.

## Card Data

`cards.jsonl` is JSON Lines (one card per line). Key fields: `card_key` (unique), `character_key`, `tier` (1–3), `rarity` (1–100), `is_named`, `sides.{n,e,s,w}`, `set`. Budget/cap rules are in `CARDS_SPEC.md`.

## Ralph (Autonomous Loop)

```bash
./ralph/ralph.sh 10   # run up to 10 story iterations
```

- Active backlog: `ralph/prd.json` (ordered user stories, `passes` field tracks completion).
- Archived MVP backlog (API-first): `ralph/archive/2026-03-01-mvp/prd.json`.
- Progress log: `ralph/progress.txt` (append-only).
- Each iteration: implement ONE story → run checks → commit `feat: [US-XXX] - Title` → mark `passes: true`.
- Commit only when `pytest` passes; never mark `passes: true` without passing tests.
- Ralph targets the branch specified by PRD `branchName`.

## Conventions

- Pydantic models at API boundary; keep them out of the rules engine core.
- Type-hint all public functions; use `X | None` over `Optional[X]`.
- `snake_case` modules/functions/variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants.
- Catch narrow exceptions; translate domain errors to `HTTPException` at the router.
- Store seed in game state; derive per-move RNG from it (enables deterministic replay).
- **No dead code**: when replacing a component/module, delete the old file and all references in the same commit.
- **Dev Playground**: when adding new UI states, overlays, or visual interactions, add a matching scenario to `web/src/routes/DevPlayground.tsx`.
- **Shared test fixtures**: backend helpers in `tests/conftest.py`, frontend helpers in `web/src/__tests__/helpers.ts`. Never duplicate across test files.
- **Test behavior, not source**: frontend tests must render and assert on DOM, not read `.tsx` files with `fs.readFileSync`. See `AGENTS.md` for details.
