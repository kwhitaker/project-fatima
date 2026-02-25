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
6. If checks pass, commit ALL changes with message:
   - `feat: [Story ID] - [Story Title]`
7. Update `ralph/prd.json`: set `passes: true` for the completed story.
8. Append to `ralph/progress.txt` using the format below.

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

Stop condition:
- If all stories have `passes: true`, output:
  <promise>COMPLETE</promise>
