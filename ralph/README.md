# Ralph (Autonomous Loop)

This directory contains a Ralph-style autonomous agent loop (Claude Code) that iterates through
one user story at a time until the PRD is complete.

Ralph works because each iteration is a fresh Claude session with clean context. Memory persists
via git history, `ralph/progress.txt`, and `ralph/prd.json`.

## Prereqs

- Claude Code installed and authenticated.
- `jq` installed (used by `ralph/ralph.sh`).

## Files

- `ralph/prd.json`: the active PRD backlog (stories with `passes: false/true`).
- `ralph/archive/2026-03-01-mvp/prd.json`: archived MVP backlog (API-first).
- `ralph/progress.txt`: append-only learnings / breadcrumbs between iterations.
- `ralph/CLAUDE.md`: instructions fed into Claude each iteration.
- `ralph/ralph.sh`: the loop runner.

## Run

From repo root:

```bash
chmod +x ralph/ralph.sh
./ralph/ralph.sh 10
```

Notes:
- Each iteration should complete exactly ONE story, run checks, commit, update `ralph/prd.json`,
  and append to `ralph/progress.txt`.
- Stories should be small enough to finish in one context window.
