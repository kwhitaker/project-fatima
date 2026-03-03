# Agent Guide (project-fatima)

This file is for coding agents working in this repo.

## AI Instructions
- Be concise and direct in your communication.
- Do not write useless/redundant comments for easily understood functions, variables, etc.
- Reserve comments for obtuse code, exceptions, gotchas, and non-obvious tradeoffs.
- When writing comments, prefer concision over grammatical correctness.
- When you present a plan and still need more info to proceed safely, end with 2-5 leading questions.

## Quick Reference

Setup, dev commands, and test commands are in the root [README.md](README.md). Below are agent-specific notes only.

### Useful pytest flags
```bash
uv run pytest -x                          # stop on first failure
uv run pytest -k "capture and not slow"   # by name substring
```

### Ruff autofix
```bash
uv run ruff check . --fix
```

### Regenerate frontend types from backend OpenAPI schema
```bash
cd web && bun run typegen
```
Requires the backend importable (uses `uv run python` to dump the schema). Output: `web/src/lib/api-types.generated.ts`.

### Frontend E2E (Playwright)
```bash
# One-time browser install: cd web && bunx playwright install chromium
cd web && bun run test:e2e
```

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

### Testing — shared fixtures (backend)

- Common helpers (`_make_card`, `make_state`, `mock_rng`, `_mock_caller_id`, the
  `client` fixture with MemoryGameStore) live in `tests/conftest.py`.
- Import them — never copy-paste into individual test files.
- When adding a new helper used by 2+ test files, put it in `conftest.py`.

### Testing — shared fixtures (frontend)

- Common helpers (`makeGame`, `makeActiveGame`, `makePlayer`, Supabase channel mock,
  `renderGameRoom`, `MOCK_SESSION`, `MOCK_CARD_DEFS`) live in
  `web/src/__tests__/helpers.ts`.
- Import them — never copy-paste into individual test files.

### Testing — frontend test quality

- **Test behavior, not source strings.** Render components and assert on DOM output
  (text, roles, aria attributes, visibility). Never use `fs.readFileSync` to read
  `.tsx` source and assert on string/regex matches — these tests are brittle and test
  implementation, not behavior. Exception: static config files (package.json,
  index.html, index.css) are OK to read directly.
- **No duplicate test scenarios.** Before adding a test for an error case (404, 403,
  409, 422), search existing tests. One test per scenario is enough.
- **Parameterize repetitive tests.** Use `it.each` / `describe.each` when 3+ tests
  differ only by input values.

### Dead code policy

- When replacing a component, module, or hook, delete the old file and remove all
  references (imports, test assertions, comments) in the same commit.
- Never leave orphaned files "for reference" — git history preserves them.

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
