# Ralph Agent Instructions (Project Fatima)

You are an autonomous coding agent working on this repository.

Your task per iteration:

1. Study `ralph/prd.json` and `ralph/progress.txt`.
2. Ensure you are on the branch specified by PRD `branchName`.
   - If you are not, create it from `main` and check it out.
3. Choose the HIGHEST priority user story where `passes: false`.
4. Implement that single story.
   - Red/Green required: write failing tests first (or add a failing integration test), then
     implement the minimum to make them pass.
5. Run the repo's quality checks.
   - Use commands documented in `AGENTS.md`.
   - If commands are missing because the repo is early, add the correct commands to `AGENTS.md`
     as part of the story (keep it brief and operational).
6. If checks pass, commit ALL changed files with message:
   - `feat: [Story ID] - [Story Title]`
7. Update `ralph/prd.json`: set `passes: true` for the completed story.
8. Append to `ralph/progress.txt` using the format below.
9. Commit the progress updates (`ralph/prd.json` and `ralph/progress.txt`) with message:
   - `Updates progress`
   - This MUST be a separate commit AFTER the feat commit. Do NOT skip this step.

Progress log format (append-only):

## YYYY-MM-DD HH:MM - [Story ID]
- What changed (1-3 bullets)
- Tests/validation run
- Files changed
- Learnings for future iterations (patterns/gotchas)
---

Important constraints:
- Do ONE story per iteration.
- Do not mark `passes: true` unless tests exist for the story and pass.
- Do not commit broken code.
- Don't assume something is missing; search before adding duplicates.

Code quality constraints (MUST follow):
- **No dead code.** If you replace a component or module, delete the old one and remove
  all references (imports, test assertions, comments). Never leave orphaned files.
- **Shared test fixtures.** Before writing a helper like `makeGame()`, `_make_card()`,
  or a mock factory, check `tests/conftest.py` (backend) or `web/src/__tests__/helpers.ts`
  (frontend) first. If one exists, import it. If not, add it there — never duplicate
  helpers across test files.
- **Test behavior, not source strings.** Frontend tests must render components and assert
  on DOM output. Never use `fs.readFileSync` to read `.tsx` source files and assert on
  string content — these tests break on any refactor and test implementation, not behavior.
  Exception: asserting on static config files (package.json, index.html, index.css) is OK.
- **No duplicate test scenarios.** Before writing a test for an error case (404, 403, 409,
  422), search existing test files to see if it's already covered. One test per scenario
  is sufficient.
- **Parameterize repetitive tests.** If you'd write 3+ near-identical tests varying only
  one input, use `@pytest.mark.parametrize` (backend) or `it.each` (frontend) instead.

Stop condition:
- If all stories have `passes: true`, output:
  <promise>COMPLETE</promise>
