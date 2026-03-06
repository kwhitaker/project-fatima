# Yugi-Strahd

A turn-based 3x3 card-capture game inspired by Triple Triad, set in the world of Curse of Strahd. Players draft decks of gothic horror characters and battle on a 3x3 grid, capturing opponent cards by comparing side values. Features include Mists modifiers, the Plus rule, elemental affinities, and character archetypes with unique once-per-game powers.

## Why "Project Fatima?"

Fatima is the name of the character in our campaign who was obsessed with the unique CCG in Barovia. The player who created Fatima started it as a gag, and it grew into an actual plot point.

## Table of Contents

- [Why "Project Fatima?"](#why-project-fatima)
- [Notes on an AI-Driven Workflow](#notes-on-an-ai-driven-workflow)
- [Prerequisites](#prerequisites)
- [Backend Setup](#backend-setup)
- [Seed Data](#seed-data)
- [Frontend Setup](#frontend-setup)
- [Running Tests](#running-tests)
- [Lint \& Typecheck](#lint--typecheck)
- [Tooling (mise)](#tooling-mise)
- [Deploy](#deploy)
- [Ralph (Autonomous Agent Loop)](#ralph-autonomous-agent-loop)
- [Further Reading](#further-reading)

## Notes on an AI-Driven Workflow

Just here to run the repo? Jump to [Prerequisites](#prerequisites).

### What This Is (and Isn't)

I'm aware of the (many) issues with using generative AI in software development. This project was a small experiment with two goals:

1. Build a fun app for my D&D group to use in our [Curse of Strahd](https://en.wikipedia.org/wiki/Curse_of_Strahd) campaign
2. See what could be accomplished with an AI-driven workflow using tools like [Claude AI](https://claude.ai/), [OpenCode](https://opencode.ai/), and [Ralph](https://github.com/snarktank/ralph?tab=readme-ov-file#ralph)

I have mixed feelings about gen-AI in software development. Used irresponsibly, it can create real problems: someone with limited engineering experience can vibe-code a complex app and dump it on an eng team (or ship it to production). The next few years may look like the lead-up to [Y2K](https://en.wikipedia.org/wiki/Year_2000_problem): lots of good engineers getting paid to unwind avoidable messes.

I also don't love the externalities (power/water costs, and the obvious incentive some leaders have to treat "code gen" as a headcount reduction plan). And I'm especially uneasy about what this does to entry-level and mid-level engineering work. This entire project is the kind of thing a more junior engineer might normally build. If gen-AI can produce this much in 2026, getting started as a software engineer is going to be much, much harder.

I'm not going to litigate all of that here. This is just what I tried, what worked, and what didn't.

### Approach

After learning about the [Ralph](https://github.com/snarktank/ralph?tab=readme-ov-file#ralph) autonomous workflow and experimenting with OpenCode and Claude, I thought this project was a good test bed:

- It uses well-documented tools and frameworks that LLMs have lots of training data on (Python and TypeScript)
- It has real complexity (game logic + Supabase stack + auth)
- It needed some basic art direction
- It was something "real" I could put in the hands of a small group of people

I treated this like a PM/Senior Engineer directing a more junior dev:

- OpenCode: craft stories / PRD-ish prompts
- Claude CLI: execute the Ralph loop

Costs (very rough): ~$40 USD in [Zen](https://opencode.ai/docs/zen/) credits plus a Claude `Max` subscription.

### The Good

- Generating the initial stories/spec with OpenCode was quick; the first backend + frontend iterations landed surprisingly close.
- It's just a fact that AI agents "type" faster than you. Even with long iteration cycles, the throughput is real.
- End-to-end build time was about 12 hours of my time; manually, it would've easily been 3x.
- As skeptical as I am, it does feel very cool to kick off a set of tasks, go do my real job, and come back to find a whole new set of features done.
- It's fantastic for understanding a large API surface area. It could instantly answer any questions I had about the tools I was using.
- The back-and-forth on animations/art direction felt like any kickoff session I've been a part of.
- When prompted well, the AI was decent at suggesting areas for improvement.

### The Bad

- You'll notice I used a lot of words like "directed," "asked," and "guided". That's because this workflow requires a fair amount of hand-holding.
- The Ralph script does not provide great feedback (at least the one I used). Initially it just wrote basic text to the terminal, and you had no idea if it was doing anything unless you watched git. I tried having Claude tweak the feedback to be more useful, but that introduced a new bug where it would show terminal feedback for the first one or two iterations and then never update again (the work was still getting done, though). I still haven't solved that bug. TL;DR: run a few small iterations first so you can dial in your preferred feedback.
- It loves to repeat itself (tests are the worst offender).
- It produces a meaningful amount of bad tests alongside good ones; you need to know what "good" looks like.
- It gravitates toward big, chonky files; I had to explicitly push it to split modules/components.
- It sometimes finishes an iteration "successfully" but the result doesn't work due to missing env vars or incomplete docs.
- It's terrible at cleaning up dead code and unused imports unless you force the issue (rules files help a lot).
- Tailwind config/version mismatches were a recurring pain (mixing v3 and v4 conventions).
- Red/green automation is non-negotiable for the autonomous loop. This is not a good workflow for projects with weak tests.

### What I'd Do Differently Next Time

- Start with strict repo rules (agent instructions, lint/format/typecheck gates) before building features.
- Add cleanup as a first-class story: unused imports, dead code, file sizes, module boundaries.
- Force smaller PR-sized iterations (more steps, fewer changes per step) rather than letting the agent sprawl.
- Treat env var + setup docs as required deliverables for every story, not "nice to have".

### Conclusion

Would I use this again? It depends.

For personal projects like this (a toy for my D&D group): yes, absolutely.

For a sensitive production system that needs to be bulletproof and secure: probably not. It saves a ton of time on the boring-but-standard stuff ("build me a login," "build me an endpoint"), but it fails in unexpected ways that can really bite you. I still think a lot of engineers are going to make a lot of money cleaning up vibe-coded apps.

### A Note on Ethics

A lot has been said about the ethics of gen-AI, especially image generation. There are real issues with code gen too, but I think the shape of the harm is different.

Image gen is built on the creativity of millions of people, and in practice it often functions as labor replacement for artists (and writers and musicians). Code gen is also used for labor replacement, but (so far) it's much better as leverage: a tool for grinding through the boring work we've all done a million times.

That said: every day there are new stories of people vibe-coding "a killer app" and leaking PII to the whole internet. If you use this workflow, you still own the outcome.

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

More Supabase setup details: [`docs/SUPABASE_DEV_SETUP.md`](docs/SUPABASE_DEV_SETUP.md).

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

- Install mise: <https://mise.jdx.dev/installing-mise.html>
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

- Railway: see [`docs/RAILWAY_DEPLOY.md`](docs/RAILWAY_DEPLOY.md)

## Ralph (Autonomous Agent Loop)

This repo includes an autonomous coding agent loop under `ralph/` that iterates through user stories one at a time.

```bash
./ralph/ralph.sh 10
```

See [`AGENTS.md`](AGENTS.md) for agent-specific workflow notes and the full command reference.

## Further Reading

- [docs/GAME_RULES_OVERVIEW.md](docs/GAME_RULES_OVERVIEW.md) — Full game rules (Mists, Plus, Elemental, Archetypes, Sudden Death)
- [docs/CARDS_SPEC.md](docs/CARDS_SPEC.md) — Card data format, budget rules, and balance constraints
- [docs/TECH_DECISIONS.md](docs/TECH_DECISIONS.md) — Architecture decisions and tradeoffs
- [docs/MVP_PLAN_OVERVIEW.md](docs/MVP_PLAN_OVERVIEW.md) — MVP scope and implementation plan
- [docs/SUPABASE_DEV_SETUP.md](docs/SUPABASE_DEV_SETUP.md) — Supabase setup (seeding + manual testing)
- [docs/REALTIME.md](docs/REALTIME.md) — Realtime subscription contract (game_events -> refetch snapshot)
- [docs/RAILWAY_DEPLOY.md](docs/RAILWAY_DEPLOY.md) — Railway deploy notes
- [docs/PRD_LIST.md](docs/PRD_LIST.md) — Archived PRD story index
