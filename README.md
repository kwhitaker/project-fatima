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

### Disclaimer

I am well aware of all of the various issues with using generative AI in the development process. The purpose of this experiment/app was two-fold:

1. Build a fun app for my D&D group to use in our [Curse of Strahd](https://en.wikipedia.org/wiki/Curse_of_Strahd) campaign
2. See what could be accomplished using an AI-driven workflow, leaning on tools like [Claude AI](https://claude.ai/), [OpenCode](https://opencode.ai/), and [Ralph](https://github.com/snarktank/ralph?tab=readme-ov-file#ralph)

I have a lot of mixed feelings about gen-AI in software development. I think it can cause real problems when used by someone without development experience, who vibe-codes a complex app and then dumps it on their eng team (or puts it directly on production). The next few years are going to look a lot like the lead-up to [Y2K](https://en.wikipedia.org/wiki/Year_2000_problem); lots of very good engineers making lots of money fixing the problems vibe-coding has introduced.

I also know that these models take an enormous amount of power and water to train, and that a lot of CEOs are practically slavering at the thought of replacing their high-paid engineers with brainless statistical prediction software. All of that sucks real bad.

And finally, I _also_ know that gen-AI is likely going to take the bottom, and especially the middle, right out of the engineering market. This entire project is an example of something that a more junior engineer would normally handle. That's certainly how I approached it. If gen-AI is capable of (mostly) producing this level of code in 2026, getting started as a software engineer is going to be much, much harder.

But other people have already said that better than me.

So, enough of me trying to ward off any "[bean-soup theory](https://suzie81speaks.com/2026/01/06/the-bean-soup-theory/)".

### Approach

After learning about the [Ralph](https://github.com/snarktank/ralph?tab=readme-ov-file#ralph) autonomous workflow, and experimenting with OpenCode and Claude, I thought this small-ish project would be a great test bed.

- It uses well-documented tools and frameworks that LLMs have lots of training data on (Python and TypeScript)
- It has complexity (the game logic + Supabase stack + auth)
- It needed some basic art direction
- It was something "real" that I could put in the hands of a small group of people to check out

My plan was to take on the role of a Product Manager/Senior Engineer, and treat Ralph like a more junior dev. I decided to use OpenCode to craft PRD stories, and then the Claude CLI to execute the Ralph process. I started on the `Pro` tier of Claude, and bought $20 USD worth of credits on OpenCode [Zen](https://opencode.ai/docs/zen/) to start with. By the time I was done, I'd burned through about $40 USD of Zen credits, and upgraded to the `Max` tier of Claude, just because I was running into limits and wanted to get things done for my D&D group.

### The Good

- The process of generating the PRDs was pretty easy and straightforward. I had OpenCode (using GPT 5.2) read some articles about Ralph, generate the scripts, and we did a back-and-forth to create the MVP stories for the initial API. That entire process took less than 30 minutes, and the Ralph process itself probably took 2 hours to run. Python is not my strongest language, but the initial results were pretty good, all things considered. The same can be said for the React code. No initial complaints.
- Look, it's just a fact that AI agents "type" faster than you. Even when it took an hour to run through a Ralph session, it was producing code at an exponentially faster rate than I could have.
- Following on: I was able to build this project in 12 hours of total time, from start to finish. If I had manually done everything, it would have easily been 3x that.
- As skeptical as I am, it does feel very cool to kick off a set of tasks, go do my real job, and come back to find a whole new set of features done.
- It really is fantastic for understanding a large API surface area. It could instantly answer any questions I had about the tools I was using.
- The resulting app looks and feels pretty good, IMO. The back-and-forth process of dialing in animations, art direction, etc. felt like any kickoff session I've been a part of.
- The AI was surprisingly good at suggesting areas for improvement, when properly asked.

### The Bad

- You'll notice I used a lot of words like "directed," "asked," and "guided." That's because this system requires a fair amount of hand-holding. More than I would expect, honestly, from a system that was trained on every OSS project ever written. You will spend a fair amount of time dialing it in, and this was for a Python/React project. I imagine it would be worse with a project using more esoteric or less-used software or frameworks.
- It _loves_ to repeat itself, especially when writing tests.
- Speaking of tests, while it was pretty good at generating useful tests for the Ralph process, it also generated a fair amount of bad tests.
- It really loves big, chonky files. I had to do a specific set of iterations just to get it to break up some big Python files and React components. This is partially my fault for not telling it how I wanted it to code upfront, but again, Python and React are probably the languages the AI knows the most about. I feel like I shouldn't _have_ to tell it to use best practices.
- Sometimes it would go through an iteration and things would not work on the other side. This was usually because of some new env var or something similar that it forgot to properly document.
- It is _terrible_ at cleaning up dead code, unused imports, etc. Again, you will need to spend time dialing it in, or steal someone else's `CLAUDE.md`/`AGENTS.md`/Cursor rules.
- There is something about Tailwind colors that Claude really struggles with. For most of this project, my Tailwind colors weren't coming through, because the AI was mixing Tailwind v3 and Tailwind v4 configs. This isn't the first project I've seen this on, either. It was very weird and frustrating to deal with.
- You absolutely NEED solid red/green testing for the autonomous part of this process to work, and you need to know what good tests look like. This is not a workflow for projects that have poor automated tests.

### Conclusion

So, would I use this flow again? It depends. On a personal project like this, where I'm building a toy to get in front of my D&D group? Absolutely. For a sensitive production app that needs to be bulletproof and secure? Probably not. While it certainly saves you a tremendous amount of time on basic stuff (build me a login, build me a REST endpoint), it falls down in unexpected ways that will really bite you. Like I said before, I think a lot of engineers are going to make a lot of money cleaning up vibe-coded apps.

### A Note on Ethics

Much has been said about the ethics of gen-AI, especially when it comes to image gen. There's a case to be made against code gen for similar reasons, but I think they are two very different problems. Image gen is built on the creativity of millions of people, and while it nominally aspires to democratize art (whatever that means), what it's really doing is taking money out of the pockets of artists (or writers, or musicians) who more-or-less created it. The purpose of image gen is to replace people. I know code gen is doing some of the same things, but it is fundamentally incapable (so far) of doing so. Right now, it's more of a tool for handing the boring stuff we've all done a million times. Every day we read stories of people who vibe-coded what they thought was a killer app, only to have their PII leaked to the whole internet. To me, code gen is like Rosie the Robot; she's here to do my laundry so I can build interesting things. Image gen is like a Terminator for human creativity.

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
