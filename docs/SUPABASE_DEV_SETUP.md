# Supabase Dev Setup (Seeding + Local Testing)

This repo uses Supabase for:
- Auth (magic link)
- Realtime (subscribe to `game_events` INSERTs)
- Persistence (Postgres tables + JSON snapshot)

## 1) Create a Supabase project

Create a new Supabase project (dev).

Auth:
- Enable Email + Magic Link.
- Add redirect URLs for local dev (typically `http://localhost:5173`).

## 2) Apply database migrations

Run these SQL migrations in order (Supabase Dashboard -> SQL editor):

1. `supabase/migrations/001_initial_schema.sql`
2. `supabase/migrations/002_cards_schema.sql`
3. `supabase/migrations/003_idempotency_key_and_player_columns.sql`

Notes:
- These create `public.profiles`, `public.games`, `public.game_events`, and `public.cards`.
- RLS is enabled; clients can only read games/events they participate in.

## 3) Enable Realtime for game events

In Supabase, enable Realtime on the `public.game_events` table (so INSERTs broadcast).

Client contract reference:
- `docs/realtime.md`

## 4) Seed data

### 4.1 Seed cards into `public.cards`

This repo includes a seeder for `cards.jsonl`:

```bash
# From repo root (requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)
uv run python scripts/seed_cards.py cards.jsonl
```

Verify in Supabase SQL editor:

```sql
select count(*) from public.cards;
```

### 4.2 Ensure profiles exist for auth users (recommended)

`public.games.player1_id/player2_id` references `public.profiles(id)`. The simplest dev flow is to
auto-create a profile row when a user signs up/logs in.

Run this once in Supabase SQL editor:

```sql
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
as $$
begin
  insert into public.profiles (id, username)
  values (
    new.id,
    coalesce(split_part(new.email, '@', 1), 'player')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();
```

Verify after logging in once:

```sql
select * from public.profiles order by created_at desc;
```

## 5) Configure environment variables

### 5.1 Backend (FastAPI)

Create `.env` (or export env vars in your shell). Required:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (server-only; do not expose to the browser)
- `SUPABASE_JWT_SECRET` (server-only; used to verify Supabase access tokens)

`SUPABASE_JWT_SECRET` is required by `app/auth.py`.

Template:
- `.env.example` (note: you still must add `SUPABASE_JWT_SECRET`)

### 5.2 Frontend (Vite)

Create `web/.env.local`:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

Values come from Supabase Project Settings -> API.

## 6) Run the app locally

Backend:

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

Frontend:

```bash
cd web
bun install
bun dev
```

The Vite dev server proxies `/api/*` to FastAPI at `http://localhost:8000/*`.

## 7) Quick manual test flow

1. Open `http://localhost:5173/login`
2. Log in via magic link (email)
3. Go to `/games`, create a game
4. Copy invite link, open it in a second browser session (incognito), log in as a second email, join, play a move
5. Confirm realtime updates: the opponent view refetches on `game_events` inserts

## 8) Important note about persistence (current repo wiring)

FastAPI's dependency wiring defaults to in-memory stores:
- `app/dependencies.py` uses `MemoryGameStore()` and `MemoryCardStore()`

That means:
- If you don't change wiring, games will NOT be persisted to Supabase even if you seeded the DB.
- Joining a game requires a populated `CardStore` (deck generation happens when player 2 joins).

For true Supabase-backed manual testing, the backend needs:
- `GameStore`: `SupabaseGameStore` (already exists: `app/store/supabase_store.py`)
- `CardStore`: either
  - a Supabase-backed CardStore (not currently implemented), OR
  - an in-memory CardStore loaded from `cards.jsonl` at startup

If you create a game and see no rows in `public.games`, the backend is still using the in-memory store.

## 9) Troubleshooting

- 401 from API:
  - Ensure requests include `Authorization: Bearer <supabase access token>`
  - Ensure backend has `SUPABASE_JWT_SECRET` set
- Realtime not updating:
  - Ensure Realtime is enabled for `public.game_events`
  - Ensure you are authenticated before subscribing (RLS applies to realtime)
- Join fails / deck generation fails:
  - Ensure backend `CardStore` is populated (cards available via file-load or DB-backed store)
