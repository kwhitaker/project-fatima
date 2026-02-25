# Agent Guide (project-fatima)

This file is for coding agents working in this repo.

## AI Instructions
- Be concise and direct in your communication.
- Do not write useless/redundant comments for easily understood functions, variables, etc.
- Reserve comments for obtuse code, exceptions, gotchas, and non-obvious tradeoffs.
- When writing comments, prefer concision over grammatical correctness.
- When you present a plan and still need more info to proceed safely, end with 2-5 leading questions.

## Repo Status (what exists today)

- This repo is currently mostly planning + game design docs and data.
- Key docs/data: `TECH_DECISIONS.md`, `MVP_PLAN_OVERVIEW.md`, `GAME_RULES_OVERVIEW.md`, `CARDS_SPEC.md`, `cards.jsonl`.
- Agent loop tooling exists in `ralph/` (see `ralph/README.md` and `ralph/CLAUDE.md`).
- No Python package/app layout yet (no `pyproject.toml`, no `app/`, no `tests/`).
- No Cursor rules found in `.cursor/rules/` or `.cursorrules`.
- No Copilot instructions found in `.github/copilot-instructions.md`.

If you add any of the above, update this doc with the canonical commands.

## Tooling: mise
We intend to use `mise` for tool/runtime version management.
- Install: https://mise.jdx.dev/installing-mise.html
- After cloning (once `.mise.toml` / tools are defined): `mise install`
- Activate in shell: follow mise docs for your shell (`mise activate` is commonly used).
- Tip: prefer `mise x -- <cmd>` when you need a specific tool version.

## Ralph (autonomous loop)
This repo includes a Claude Code loop runner under `ralph/`.
- Run: `./ralph/ralph.sh 10`
- Prereqs: `jq`, and `claude` (Claude Code) installed/authenticated.
- Each iteration should: do ONE story, run checks from this file, commit, update `ralph/prd.json`, append to `ralph/progress.txt`.

## Build / Lint / Test Commands
There is no runnable app or test suite yet. The commands below are the intended defaults for the upcoming FastAPI + pytest backend; update this section once the scaffold lands.

### Install / bootstrap (choose the one that matches the repo once added)
- If using uv (recommended): `uv sync` (or `uv pip install -r requirements.txt`)
- If using pip: `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
- If using poetry: `poetry install`

### Run the app (FastAPI/Uvicorn)
- Dev server (typical): `uvicorn app.main:app --reload`
- Alternate module path: `uvicorn <package>.main:app --reload`
- Factory function (if used): `uvicorn app.main:create_app --factory --reload`

### Lint / format (recommended defaults)
- Lint (ruff): `ruff check .`
- Format (ruff): `ruff format .`
- Autofix (ruff): `ruff check . --fix`
- If/when pre-commit is configured: `pre-commit run -a`

### Typecheck (pick one once configured)

- pyright: `pyright`

### Tests (pytest)

- All tests: `pytest` (or `pytest -q`)
- Stop on first failure: `pytest -x` (or `pytest --maxfail=1`)
- Show stdout/stderr: `pytest -s`

Run a single test (most important):
- Single file: `pytest tests/test_something.py`
- Single test function: `pytest tests/test_something.py::test_happy_path`
- Single test class method: `pytest tests/test_api.py::TestAuth::test_login`
- By name substring: `pytest -k "login and not slow"`
- By marker: `pytest -m "unit"`

Debugging collection/import issues: `pytest -q --maxfail=1 --disable-warnings`

## Code Style Guidelines (Python)

### Formatting

- Prefer automated formatting (ruff/black-style). Do not hand-format large blocks.
- Keep lines reasonably short (88-100 chars typical); follow the formatter if configured.
- Prefer one logical change per commit/PR.

### Imports

- Group imports: standard library, third-party, then local.
- Sort imports automatically (ruff/isort behavior).
- Avoid wildcard imports (`from x import *`).
- Import modules (not objects) when it clarifies ownership (e.g., `import datetime as dt`).

### Types and annotations

- Add type hints for all new public functions/methods.
- Use precise container types: `list[str]`, `dict[str, int]`, etc.
- Prefer `| None` over `Optional[...]` on Python 3.10+.
- Avoid `Any` unless bridging an untyped dependency; localize it.
- If/when using Pydantic/FastAPI:
  - Use Pydantic models at the API boundary (request/response + settings), not deep in the rules engine.
  - Keep API schemas stable; version or migrate deliberately.

### Naming

- Modules/files: `snake_case.py`.
- Functions/variables: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Tests: `test_*.py` files; `test_*` functions.

### Project structure (recommended)

If you introduce code, keep boundaries clear:

- `app/` (or `src/<package>/`) for application code
- `tests/` for pytest tests
- Separate layers: API (FastAPI routers), services, data access, domain models

Rules engine guidance (MVP):

- Keep the reducer pure: `next_state = apply_intent(state, intent, rng)`.
- Make state JSON-serializable (event log + snapshot storage).
- Derive randomness from an explicit seed; do not call global `random.*` inside core logic.

### Error handling

- Do not swallow exceptions with bare `except:`.
- Catch narrow exception types and add context.
- Prefer raising explicit domain exceptions and translating them at the API boundary.
- For FastAPI endpoints:
  - Use `HTTPException` for client-facing errors with correct status codes.
  - Validate inputs with Pydantic; avoid manual validation scattered around.
- Log errors with context; do not log secrets.

### Logging

- Use structured, consistent messages (include identifiers, not entire payloads).
- Avoid logging PII/secrets; `.env` is ignored by git for a reason.

### Testing style

- Use pytest fixtures for shared setup; keep fixtures small and composable.
- Prefer unit tests for pure logic; integration tests for API/db boundaries.
- Use Arrange/Act/Assert; keep tests deterministic.
- Name tests for behavior, not implementation.

### Performance / correctness

- Prefer clarity first; optimize only with evidence.
- Avoid global mutable state.
- Be deliberate about async vs sync; do not block the event loop in async code.

## Agent Workflow Notes

- Before large changes: search for existing conventions and match them.
- Keep diffs minimal; avoid drive-by refactors.
- Do not add new tooling/config files unless the task calls for it.
- Never commit secrets; `.env` and virtualenvs are ignored.

If Cursor/Copilot rules are added later:

- Mirror the key constraints here so non-editor agents see them too.
