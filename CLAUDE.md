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
- **Card sides**: N/E/S/W integer values (1–10). Higher touching side wins a capture.
- **Mists (1d6)**: Roll per placement. 1=Fog (−1 all comparisons), 6=Omen (+1), 2–5=no effect. Modifier is ephemeral — printed stats never change.
- **Archetypes**: Once-per-game power. Martial (rotate card), Skulker (+2 one side), Caster (reroll Mists), Devout (negate Fog), Presence (+1 one comparison).
- **Sudden Death**: Tie at board-full → same `game_id`, `round_number++`, each player's deck = the 9 cards they owned. Cap: 3 Sudden Death rounds, then draw.
- **Deck (10 cards)**: Named character uniqueness by `character_key`; rarity slots (ultra≤1, very_rare≤2, rare≤3); copy limits by rarity bucket.

## Card Data

`cards.jsonl` is JSON Lines (one card per line). Key fields: `card_key` (unique), `character_key`, `tier` (1–3), `rarity` (1–100), `is_named`, `sides.{n,e,s,w}`, `set`. Budget/cap rules are in `CARDS_SPEC.md`.

## Ralph (Autonomous Loop)

```bash
./ralph/ralph.sh 10   # run up to 10 story iterations
```

- Active backlog: `ralph/prd.json` (ordered user stories, `passes` field tracks completion).
- Archived API MVP backlog: `ralph/prd.json.api-mvp`.
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
