# Spectator Mode — Implementation Plan

## Overview

Allow any authenticated user to watch an in-progress (or completed) game in real time without participating. Spectators see the board, captures, Mists effects, and scores — but never see either player's hand or deal.

---

## Changes

### 1. Backend: relax GET /games/{id} access control

**File:** `app/routers/games.py`

Remove the 403 block that restricts `GET /games/{id}` to participants only. Instead:

- Any authenticated user can GET any game in `ACTIVE` or `COMPLETE` status.
- `WAITING` and `DRAFTING` games remain participant-only (no point spectating a draft).

### 2. Backend: redact private state for non-participants

**File:** `app/routers/games.py` (response shaping)

When the caller is not a participant, strip from the response:

- `players[*].deal` → always `[]`
- `players[*].hand` → replace with count only (e.g. `hand_count: int`) or empty list

Two options for implementation:

- **Option A (projection in router):** After loading `GameState`, zero out `deal`/`hand` before returning. Simple, no new model needed — just mutate the copy.
- **Option B (response model):** Define a `SpectatorGameState` Pydantic model that omits `deal`/`hand`. More type-safe but heavier.

Recommend **Option A** — keep it simple, add a helper like `redact_for_spectator(state: GameState) -> GameState`.

### 3. Backend: public game listing

**File:** `app/routers/games.py`

Add `GET /games/active` (or extend `GET /games` with a `?status=active` filter) that returns a list of in-progress games any authenticated user can browse. Return minimal info: `game_id`, player emails, round number, status, created_at.

### 4. Supabase RLS migration

**File:** `supabase/migrations/NNN_spectator_rls.sql`

Add SELECT policies so spectators' Realtime subscriptions work:

```sql
-- Any authenticated user can read ACTIVE or COMPLETE games
CREATE POLICY "games_select_active_public"
    ON public.games FOR SELECT
    USING (auth.uid() IS NOT NULL AND status IN ('active', 'complete'));

-- Any authenticated user can read events for active/complete games
CREATE POLICY "game_events_select_active_public"
    ON public.game_events FOR SELECT
    USING (
        auth.uid() IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM public.games g
            WHERE g.id = game_id
              AND g.status IN ('active', 'complete')
        )
    );
```

### 5. Frontend: spectator mode in GameRoom

**File:** `web/src/pages/GameRoom.tsx` (and child components)

When `myIndex === -1` and game is `ACTIVE` or `COMPLETE`:

- Show a "Spectating" banner/badge at the top.
- Render the board normally (all placed cards are public info).
- Hide `HandPanel` entirely (spectators have no hand).
- Disable all interactive controls (card placement, archetype activation).
- Show both players' names/emails and the score.
- Realtime subscription works identically — spectator refetches on each `game_events` insert.

### 6. Frontend: spectate discovery

**File:** `web/src/pages/Lobby.tsx` (or new component)

Add a "Watch a Game" section that calls the new `/games/active` endpoint and lists ongoing matches with a "Spectate" button linking to `/games/{id}`.

---

## What does NOT change

- **Reducer** — pure function, no awareness of spectators.
- **Game creation/joining flow** — spectators never join.
- **Store layer** — no new tables or columns.
- **Drafting phase** — not spectatable (boring + would leak hand info).

---

## Test plan

- Backend: test that non-participant GET returns 200 for ACTIVE games with redacted hands.
- Backend: test that non-participant GET returns 403 for WAITING/DRAFTING games.
- Backend: test that `redact_for_spectator` strips `deal` and `hand`.
- Backend: test `GET /games/active` returns only ACTIVE games.
- Frontend: test that spectator mode renders board without hand panel or action buttons.
