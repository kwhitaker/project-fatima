# MVP Plan Overview

This document records the implementation phases for the Project Fatima MVP.

North stars:
- Rules engine is the source of truth (pure Python reducer + unit tests).
- API-first (integration tests before any UI).
- Persistence uses an append-only event log + cached snapshot.

Key MVP rule decisions:
- Implement all 5 archetype powers from `GAME_RULES_OVERVIEW.md`.
- Include Sudden Death.
- Sudden Death stays in the same `game_id` by incrementing `round_number`.
- Cap Sudden Death at 3 rounds; if still tied, result is a draw.
- Deck generation uses a weighted-sum heuristic (not simulation).

## Phase 0: Repo + App Skeleton

Deliverables:
- Python project layout for app code + tests.
- FastAPI app bootstrapped (includes `GET /health`).
- Test harness wired (pytest); formatting/linting wired (tooling TBD).

Exit criteria:
- `pytest` runs locally.
- `GET /health` returns 200.

## Phase 1: Core Rules Engine (Pure + Deterministic)

Deliverables:
- Canonical, JSON-serializable `GameState` snapshot.
- Intent models for moves/powers.
- Pure reducer `apply_intent(state, intent, rng)` (or equivalent) that:
  - validates move legality
  - resolves Mists randomness per placement
  - applies archetype power modifiers (once-per-game)
  - resolves captures vs orthogonal adjacent enemy cards (no combos)
  - advances turn and determines end-of-round/game result
- Sudden Death flow:
  - tie at board-full triggers a new round
  - increment `round_number` and `sudden_death_rounds_used`
  - rebuild each player's next-round deck from the 9 cards they ended owning
  - cap at 3 sudden-death rounds then draw

Exit criteria:
- Unit tests cover captures, Mists, each archetype power, and Sudden Death transitions.
- Deterministic replay with a fixed seed.

## Phase 2: Cards Validation + Import Pipeline

Deliverables:
- `cards.jsonl` loader + validator per `CARDS_SPEC.md`:
  - schema/type checks
  - `card_key` uniqueness
  - tier/rarity/side ranges
  - rarity bucket derivation
  - sum budget and side cap enforcement by (tier, bucket)
- Validation report format (line-numbered errors).

Exit criteria:
- Invalid inputs fail validation with actionable errors.
- Valid inputs produce a normalized in-memory card pool.

## Phase 3: Deck Rules + Server Deck Generation

Deliverables:
- Deck validator (even if MVP ships with prebuilt/random decks) enforcing:
  - size 10
  - named uniqueness by `character_key` when `is_named`
  - copy limits by `card_key` (lookup driven by rarity bucket)
  - rarity slots: ultra <= 1, very_rare <= 2, rare <= 3
- Seeded deck generator:
  - uses RNG seed stored in game state/event log
  - generates two legal decks
  - matches decks using a weighted-sum deck cost within a tolerance

Exit criteria:
- Generator is deterministic given a seed.
- Generated decks pass validation.
- Cost deltas stay within the configured tolerance in tests.

## Phase 4: FastAPI API (Mock-First Storage)

Deliverables:
- Storage interfaces (thin boundary): `GameStore`, `CardStore`.
- In-memory `GameStore` implementation for integration tests:
  - append-only events
  - `state_version` optimistic locking
  - per-game `seq` ordering
- Endpoints (minimal MVP):
  - `POST /games` create game
  - `POST /games/{game_id}/join`
  - `POST /games/{game_id}/archetype`
  - `GET /games/{game_id}` snapshot
  - `POST /games/{game_id}/moves` submit intent (transactional in real store)

Exit criteria:
- Integration tests cover the full flow using the in-memory store.
- The reducer remains the only implementation of game rules.

## Phase 5: Supabase Persistence + RLS

Deliverables:
- Tables per `TECH_DECISIONS.md`: `profiles`, `games`, `game_events` (+ optional `game_players`).
- Transactional move processing:
  - insert event + update snapshot in one transaction
  - `seq` allocation + `state_version` optimistic locking
- RLS:
  - players read only games/events they are in
  - clients do not write `games`/`game_events` directly
  - FastAPI writes with Supabase service role key

Exit criteria:
- Same API behavior backed by Supabase store.
- Conflicts return 409 and can be retried.

## Phase 6: Realtime Updates

Deliverables:
- Supabase Realtime subscription on `game_events` inserts filtered by `game_id`.
- Client strategy (MVP-simple): on event receipt, refetch `GET /games/{game_id}`.

Exit criteria:
- Two clients observe updates without polling.

## Phase 7: MVP Hardening

Deliverables:
- Idempotency for move submission (prevents duplicate writes on retries).
- Tight error taxonomy (403/404/409/422) and validation.
- Seed scripts to load cards into DB.

Exit criteria:
- Replays/debugging are possible from event log + seed.
- API is stable enough to build a UI against.
