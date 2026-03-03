# Yugi-Strahd

A turn-based 3x3 card-capture game inspired by Triple Triad, set in the world of Curse of Strahd. Players draft decks of gothic horror characters and battle on a 3x3 grid, capturing opponent cards by comparing side values. Features include Mists modifiers, the Plus rule, elemental affinities, and character archetypes with unique once-per-game powers.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [bun](https://bun.sh/) (JavaScript runtime / package manager)
- A [Supabase](https://supabase.com/) project (for auth, database, and realtime)

## Backend Setup

```bash
# Install Python dependencies
uv sync --extra dev

# Configure environment
cp .env.example .env
# Fill in SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (see .env.example for details)

# Start the dev server
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

### Seed Data

Seed `cards.jsonl` into the Supabase `public.cards` table (requires `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` in your environment):

```bash
uv run python scripts/seed_cards.py cards.jsonl
```

More Supabase setup details: [`docs/supabase_dev_setup.md`](docs/supabase_dev_setup.md).

## Frontend Setup

```bash
cd web
bun install

# Create web/.env.local with your Supabase project credentials:
#   VITE_SUPABASE_URL=https://your-project.supabase.co
#   VITE_SUPABASE_ANON_KEY=your-anon-key

bun run dev
```

The frontend dev server proxies `/api/*` requests to the backend at `localhost:8000`.

## Running Tests

```bash
# Backend tests
uv run pytest

# Frontend tests
cd web && bun run test --run
```

## Lint & Typecheck

```bash
uv run ruff check .
uv run ruff format .
uv run pyright
```

## Tooling (mise)

We use [mise](https://mise.jdx.dev) to manage runtimes and provide unified dev tasks.

- Install mise: https://mise.jdx.dev/installing-mise.html
- After cloning: `mise install`

```bash
mise run dev          # Start backend + frontend concurrently
mise run dev:api      # Start FastAPI backend only
mise run dev:ui       # Start Vite frontend only
mise run test         # Run backend + frontend tests
mise run lint         # Lint Python code (ruff check)
mise run format       # Format Python code (ruff format)
```

These are convenience wrappers — the individual commands (documented above) still work without mise.

## Deploy

- Railway: see [`docs/railway_deploy.md`](docs/railway_deploy.md)

## Ralph (Autonomous Agent Loop)

This repo includes an autonomous coding agent loop under `ralph/` that iterates through user stories one at a time.

```bash
./ralph/ralph.sh 10
```

See [`AGENTS.md`](AGENTS.md) for agent-specific workflow notes and the full command reference.

## Further Reading

- [GAME_RULES_OVERVIEW.md](GAME_RULES_OVERVIEW.md) — Full game rules (Mists, Plus, Elemental, Archetypes, Sudden Death)
- [CARDS_SPEC.md](CARDS_SPEC.md) — Card data format, budget rules, and balance constraints
- [TECH_DECISIONS.md](TECH_DECISIONS.md) — Architecture decisions and tradeoffs
- [MVP_PLAN_OVERVIEW.md](MVP_PLAN_OVERVIEW.md) — MVP scope and implementation plan
- [docs/](docs/) — Additional docs (Supabase setup, realtime, deployment)
