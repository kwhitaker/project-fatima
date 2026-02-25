# Tech Decisions (MVP)

This file captures agreed technology decisions for the Project Fatima card game MVP.

## Stack

- Backend: FastAPI + Uvicorn.
- Backend data/auth/realtime: Supabase (Postgres, Auth, Realtime).
- Auth between client and API: Supabase access token (JWT) in `Authorization: Bearer <token>`.
  - Note: we may later swap to a cookie/session flow, but JWT is MVP.

## Game Model

- 2 players per game.
- Async game (players can take turns at different times).
- Real-time updates pushed to both players.

## Real-Time Updates

- Use Supabase Realtime subscriptions (not custom FastAPI websockets for MVP).
- Clients subscribe to inserts on `game_events` filtered by `game_id`.
- On event receipt, client may:
  - Re-fetch `GET /games/{game_id}` for the latest snapshot (MVP-simple), and/or
  - Later: apply events locally for smoother UI.

## Persistence Strategy (Scalable + Python-friendly)

- Source of truth: append-only `game_events` table (event log).
- Cached read model: `games.current_state` JSONB snapshot for fast reads.
- Reducer: a pure Python "rules engine" that applies a move/event to produce the next state.
  - This is the primary unit-test target.

Concurrency:

- Use per-game `seq` for ordering events and/or `state_version` for optimistic locking.
- Moves are processed transactionally: insert event + update snapshot in one transaction.

## Data Model (Tables)

Minimum tables:

- `profiles`: maps `auth.users` -> app profile fields.
- `games`: metadata + players + status + `current_state` snapshot + `state_version`.
- `game_events`: append-only, ordered by `(game_id, seq)`, drives realtime.

Optional (soon):

- `game_players`: seats, archetype selection, power-used flag.

## Security / RLS

- Clients can read only games/events for games they are in.
- Clients do not write `games`/`game_events` directly.
- FastAPI writes using Supabase service role key.

## Cards Storage (DB-tracked)

Cards live in the database (not import-only).

Recommended `cards` table is hybrid:

- Canonical columns for gameplay/indexing/constraints:
  - `card_key` (unique), `character_key`, `tier`, `rarity`, `is_named`, `n/e/s/w`, `set`, `tags`
- JSONB for extensibility:
  - `definition jsonb` (store original import payload / extra fields)

Rationale:

- Columns make constraints + indexing simple (e.g., side values 1-10, tier 1-3, rarity 1-100).
- JSONB lets us extend card structure later without schema churn.

Card source file for generation/import:

- `cards.jsonl` (JSON Lines) + documented in `CARDS_SPEC.md`.

## Decks (MVP)

- Deck size: 10 cards.
- Deck-building/inventory UI is out of scope for MVP.
- At game start, server randomly builds both players' decks from the card pool.
- Fairness constraint: decks should be "even" (avoid one deck rolling the other).
  - Approach: enforce rarity-slot caps + named uniqueness + copy limits, and match decks by a
    derived deck power/cost within a small tolerance.
- Store an RNG seed for deck generation in the game record/event log for replay/debuggability.

## Archetypes

- Player chooses archetype at game time (create/join).
- Archetype grants a once-per-game power per `GAME_RULES_OVERVIEW.md`.

## API-First Testing (Before UI)

- Use FastAPI Swagger UI: `/docs`.
- Use `curl`/`httpie` with Supabase JWT bearer tokens.
- Automated tests:
  - Unit tests: pure rules engine.
  - Integration tests: FastAPI endpoints (mock DB layer first; Supabase local can be added later).
