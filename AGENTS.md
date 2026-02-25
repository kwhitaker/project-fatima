# Agent Guide (project-fatima)

This file is for coding agents working in this repo.

## AI Instructions

- Be concise and direct in your communication.
- Do not write useless/redundant comments for easily understood functions, variables, etc.
- Reserve comments for obtuse code, exceptions, gotchas, and non-obvious tradeoffs.
- When writing comments, prefer concision over grammatical correctness.
- Functions and variables should be self-documenting.
- When you present a plan and still need more info to proceed safely, end with 2-5 leading questions.

## Repo Status (what exists today)

- Only `README.md` and `.gitignore` are present.
- No Python package/app layout, no `pyproject.toml`, and no test/lint tooling configs were found.
- No Cursor rules were found in `.cursor/rules/` or `.cursorrules`.
- No Copilot instructions were found in `.github/copilot-instructions.md`.

If you add any of the above, update this doc with the canonical commands.

## Tooling: mise

We intend to use `mise` for tool/runtime version management.

- Install: https://mise.jdx.dev/installing-mise.html
- After cloning (once `.mise.toml` / tools are defined): `mise install`
- Activate in shell: follow mise docs for your shell (`mise activate` is commonly used).

Tip for agents: prefer `mise x -- <cmd>` when you need a specific tool version.

## Build / Lint / Test Commands

Because the repo currently lacks config, the commands below are the expected defaults for a
FastAPI + pytest Python project. Adjust them once the actual toolchain is committed.

### Install / bootstrap (choose the one that matches the repo once added)

- If using uv: `uv sync` (or `uv pip install -r requirements.txt`)
- If using pip: `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
- If using poetry: `poetry install`

### Run the app (FastAPI/Uvicorn)

- Dev server (typical): `uvicorn app.main:app --reload`
- Alternate module path: `uvicorn <package>.main:app --reload`

### Lint / format (recommended defaults)

- Lint (ruff): `ruff check .`
- Format (ruff): `ruff format .`
- Autofix (ruff): `ruff check . --fix`

### Typecheck (pick one once configured)

- mypy: `mypy .`
- pyright: `pyright`

### Tests (pytest)

- All tests: `pytest`
- Quiet: `pytest -q`
- Stop on first failure: `pytest -x`
- Fail fast with max failures: `pytest --maxfail=1`
- Show stdout/stderr: `pytest -s`

Run a single test (most important):

- Single file: `pytest tests/test_something.py`
- Single test function: `pytest tests/test_something.py::test_happy_path`
- Single test class method: `pytest tests/test_api.py::TestAuth::test_login`
- By name substring: `pytest -k "login and not slow"`
- By marker: `pytest -m "unit"`

If you need coverage (once configured):

- `pytest --cov --cov-report=term-missing`

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
  - Use Pydantic models for request/response bodies.
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
