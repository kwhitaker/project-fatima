# project-fatima

Turn-based game (WIP) built for my D&D crew. This is primarily a learning exercise to brush up on Python.

## Tooling

We use [mise](https://mise.jdx.dev) to manage runtime/tool versions for consistent local development.

- Install mise: https://mise.jdx.dev/installing-mise.html
- After cloning, enable mise for your shell and install pinned tools (if configured): `mise install`

## Ralph (autonomous agent loop)

This repo includes a Ralph-style autonomous loop runner under `ralph/` that iterates through one user story at a time.

Prereqs:
- `jq`
- `claude` (Claude Code) installed and authenticated

Run (from repo root):

```bash
chmod +x ralph/ralph.sh
./ralph/ralph.sh 10
```

Notes:
- Active backlog lives in `ralph/prd.json`; progress is appended to `ralph/progress.txt`.
- Prior API MVP backlog is archived in `ralph/prd.json.api-mvp`.
- Each iteration should complete exactly ONE story, run the repo checks documented in `AGENTS.md`, then commit.

## Tech Stack

Backend:
- FastAPI
- Uvicorn

Data + realtime/communication:
- Supabase

Frontend:
- React + Vite (in `web/`)

## Deploy

- Railway: see `docs/railway_deploy.md`
