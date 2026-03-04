# PRD List

Archived PRD stories from `ralph/archive/`, ordered by archive folder date (best-effort).

Some early MVP setup work appears in `ralph/mvp` git history before the first archived PRD folders; those rows are included as inferred items and marked `INF-*`.

| PRD | Story ID | Title | What Changed |
| --- | --- | --- | --- |
| 2026-02-25-mvp-bootstrap (inferred) | INF-001 | Repo bootstrap | initialize repo with `.gitignore` and `README.md` |
| 2026-02-25-mvp-bootstrap (inferred) | INF-002 | MVP scope docs + seed data | add `CARDS_SPEC.md`, `GAME_RULES_OVERVIEW.md`, `TECH_DECISIONS.md`, `cards.jsonl`, and `AGENTS.md` |
| 2026-02-25-mvp-bootstrap (inferred) | INF-003 | Ralph workflow bootstrap | add `ralph/prd.json`, `ralph/progress.txt`, `ralph/ralph.sh`, and `MVP_PLAN_OVERVIEW.md` |
| 2026-02-25-mvp-bootstrap (inferred) | INF-004 | Agent runbook | add top-level `CLAUDE.md` with repo instructions |
| 2026-02-26-ui-mvp | US-UI-001 | Scaffold web frontend (React/Vite/TS + Tailwind + shadcn/ui) | a working frontend scaffold in web/ |
| 2026-02-26-ui-mvp | US-UI-002 | Supabase auth UI (magic link) + session restore | to log in via Supabase magic link |
| 2026-02-26-ui-mvp | US-UI-003 | API adjustments for UI MVP (JWT identity, create auto-join, list games, mists feedback) | the API to be auth-scoped and UI-friendly |
| 2026-02-26-ui-mvp | US-UI-004 | Games list screen (/games) backed by GET /games | to see my games |
| 2026-02-26-ui-mvp | US-UI-005 | Join-by-link lobby flow (waiting state) | to join a game from a shared link and see a lobby until the match starts |
| 2026-02-26-ui-mvp | US-UI-006 | Game room core rendering (snapshot-first) | to see the board, hands, and turn state |
| 2026-02-26-ui-mvp | US-UI-007 | Place a card (no archetype power UX yet) | to place a card on my turn and see the updated snapshot |
| 2026-02-26-ui-mvp | US-UI-008 | Archetype selection UX | to select my archetype once |
| 2026-02-26-ui-mvp | US-UI-009 | Use archetype power on a move (power-specific params) | to activate my once-per-game archetype power when placing a card |
| 2026-02-26-ui-mvp | US-UI-010 | Realtime subscription: refetch snapshot on game_events insert | to see opponent moves without polling |
| 2026-02-26-ui-mvp | US-UI-011 | Make captures/combos/wins + Mists feel good (lightweight effects) | satisfying feedback for captures, combos, and Mists |
| 2026-02-26-ui-mvp | US-UI-012 | UI MVP tests: component sanity + Playwright smoke | a minimal test suite |
| 2026-03-01-game-mechanics-depth | US-GM-001 | Weak-side card rule: every card must have at least one side <= 3 | every card -- including ultra/very-rare -- to have at least one exploitable low side |
| 2026-03-01-game-mechanics-depth | US-GM-002 | Mists intensity buff: change modifier from +/-1 to +/-2 | the Mists of Barovia roll to feel impactful and risky |
| 2026-03-01-game-mechanics-depth | US-GM-003 | Plus rule -- backend: side-sum matching capture mechanic | a Plus capture rule |
| 2026-03-01-game-mechanics-depth | US-GM-004 | Plus rule -- UI: callout and capture feedback | clear visual feedback when the Plus rule fires |
| 2026-03-01-game-mechanics-depth | US-GM-005 | Elemental system -- card data and model | each card to carry an element |
| 2026-03-01-game-mechanics-depth | US-GM-006 | Elemental system -- game state, rules engine, and API | the board to have elemental cells |
| 2026-03-01-game-mechanics-depth | US-GM-007 | Elemental system -- UI: board cell elements and match highlighting | to see the element of each board cell and get a visual cue when my selected card matche... |
| 2026-03-01-game-mechanics-depth | US-GM-008 | Game rules documentation refresh | all four new mechanics documented accurately |
| 2026-03-01-mvp | US-001 | Establish Python project scaffold with tests | a runnable FastAPI skeleton and a working test runner |
| 2026-03-01-mvp | US-002 | Define canonical game state + card models | JSON-serializable state/models |
| 2026-03-01-mvp | US-003 | Implement capture resolution for a placement | when I place a card, adjacent enemy cards flip if my touching side is higher |
| 2026-03-01-mvp | US-004 | Add Mists randomness modifier | each placement rolls 1d6 and applies -1/+1 to comparisons for that placement only |
| 2026-03-01-mvp | US-005 | Add turn flow and move validation | the reducer to enforce turns, hands, and board placement rules |
| 2026-03-01-mvp | US-006 | Implement archetype power: Martial rotation | I can rotate the placed card once before comparisons, once per game |
| 2026-03-01-mvp | US-007 | Implement archetype power: Skulker side boost | I can add +2 to one chosen side for this placement only, once per game |
| 2026-03-01-mvp | US-008 | Implement archetype power: Caster reroll | I can reroll the Mists die for my placement, once per game |
| 2026-03-01-mvp | US-009 | Implement archetype power: Devout fog negation | I treat Fog (1) as no effect for my placement, once per game |
| 2026-03-01-mvp | US-010 | Implement archetype power: Presence single-comparison boost | I can force one adjacent comparison to be re-evaluated with +1 for me, once per game |
| 2026-03-01-mvp | US-011 | Implement end-of-round scoring | when the board is full the game determines the winner by controlled card count |
| 2026-03-01-mvp | US-012 | Implement Sudden Death rounds with cap | if the game is tied at board-full, it starts Sudden Death using the 9 cards each player... |
| 2026-03-01-mvp | US-013 | Add cards.jsonl validator: schema + key uniqueness | to validate cards.jsonl inputs before importing |
| 2026-03-01-mvp | US-014 | Add cards.jsonl validator: rarity buckets + budget/cap enforcement | to enforce per-tier rarity budgets |
| 2026-03-01-mvp | US-015 | Implement deck validator: named uniqueness + rarity slots | deck validation hooks to enforce anti-stacking rules |
| 2026-03-01-mvp | US-016 | Implement deck validator: copy limits by rarity bucket | to limit duplicates by exact card version to prevent stacked decks |
| 2026-03-01-mvp | US-017 | Implement weighted deck cost + fairness matching | server-generated decks should be roughly even strength |
| 2026-03-01-mvp | US-018 | Implement seeded deck generation producing two matched legal decks | game creation to generate decks from the card pool reproducibly |
| 2026-03-01-mvp | US-019 | Define GameStore/CardStore interfaces + in-memory GameStore | a thin storage boundary |
| 2026-03-01-mvp | US-020 | Implement FastAPI endpoints with in-memory store | API-first iteration on the full match flow |
| 2026-03-01-mvp | US-021 | Add Supabase SQL schema files for games + game_events | the database schema captured in-repo for Supabase |
| 2026-03-01-mvp | US-022 | Implement Supabase-backed GameStore append_event + snapshot update | the real store to insert an event and update snapshot transactionally |
| 2026-03-01-mvp | US-023 | Add idempotency keys for move submission | resubmitting a move should not create duplicate events |
| 2026-03-01-mvp | US-024 | Add cards seeding script for Supabase | to load cards.jsonl into the cards table with validation |
| 2026-03-01-mvp | US-025 | Add Supabase SQL schema files for cards table | the cards table schema captured in-repo to match CARDS_SPEC.md and TECH_DECISIONS.md |
| 2026-03-01-mvp | US-028 | Allow players to leave games (forfeit active, delete waiting) | to be able to leave a game. If the game is active, leaving forfeits and the other playe... |
| 2026-03-01-mvp | US-029 | Implement chain/combo capture resolution | captures can trigger additional captures (combos) for extra excitement and strategy |
| 2026-03-01-mvp | US-026 | Standardize API error responses and status codes | consistent errors (403/404/409/422) |
| 2026-03-01-mvp | US-027 | Document realtime event subscription contract | clear guidance on subscribing to game_events and refetching snapshots |
| 2026-03-01-ui-mvp | US-UI-001 | Scaffold web frontend (React/Vite/TS + Tailwind + shadcn/ui) | a working frontend scaffold in web/ |
| 2026-03-01-ui-mvp | US-UI-002 | Supabase auth UI (magic link) + session restore | to log in via Supabase magic link |
| 2026-03-01-ui-mvp | US-UI-003 | API adjustments for UI MVP (JWT identity, create auto-join, list games, mists feedback) | the API to be auth-scoped and UI-friendly |
| 2026-03-01-ui-mvp | US-UI-004 | Games list screen (/games) backed by GET /games | to see my games |
| 2026-03-01-ui-mvp | US-UI-005 | Join-by-link lobby flow (waiting state) | to join a game from a shared link and see a lobby until the match starts |
| 2026-03-01-ui-mvp | US-UI-006 | Game room core rendering (snapshot-first) | to see the board, hands, and turn state |
| 2026-03-01-ui-mvp | US-UI-007 | Place a card (no archetype power UX yet) | to place a card on my turn and see the updated snapshot |
| 2026-03-01-ui-mvp | US-UI-008 | Archetype selection UX | to select my archetype once |
| 2026-03-01-ui-mvp | US-UI-009 | Use archetype power on a move (power-specific params) | to activate my once-per-game archetype power when placing a card |
| 2026-03-01-ui-mvp | US-UI-010 | Realtime subscription: refetch snapshot on game_events insert | to see opponent moves without polling |
| 2026-03-01-ui-mvp | US-UI-011 | Make captures/combos/wins + Mists feel good (lightweight effects) | satisfying feedback for captures, combos, and Mists |
| 2026-03-01-ui-mvp | US-UI-012 | UI MVP tests: component sanity + Playwright smoke | a minimal test suite |
| 2026-03-03-archetype-power-revamp | US-PR-001 | Caster reroll: best of two rolls | the reroll power to use the better of two Mists rolls instead of blindly discarding the... |
| 2026-03-03-archetype-power-revamp | US-PR-002 | Devout conditional consume: only spent on Fog | my fog-negation power to only be consumed when Fog actually rolls -- |
| 2026-03-03-archetype-power-revamp | US-PR-003 | Skulker boost +2 -> +3 | my side boost increased from +2 to +3 -- |
| 2026-03-03-archetype-power-revamp | US-PR-004 | Martial rotation direction choice (CW/CCW) | to choose clockwise or counter-clockwise rotation when activating my power -- |
| 2026-03-03-code-health-1 | US-CH-001 | Extract shared backend test fixtures into conftest.py | common test helpers (_make_card, _mock_caller_id, client fixture, make_state, mock_rng)... |
| 2026-03-03-code-health-1 | US-CH-002 | Extract shared frontend test fixtures into helpers.ts | common frontend test setup (Supabase mock, API mock, MOCK_SESSION, setupAuth, makeGame,... |
| 2026-03-03-code-health-1 | US-CH-003 | Deduplicate backend test scenarios across test_api / test_auth_api / test_error_responses | each error scenario (404, 403, 409, 422) tested exactly once -- not duplicated across t... |
| 2026-03-03-code-health-1 | US-CH-004 | Extract archetype dispatch from apply_intent reducer | the archetype dispatch logic extracted from the 189-line apply_intent function into a d... |
| 2026-03-03-code-health-1 | US-CH-005 | Extract adjacency helper into shared board module | the board adjacency lookup to live in a shared module (app/rules/board.py) instead of b... |
| 2026-03-03-code-health-1 | US-CH-006 | Extract ModalShell shared dialog wrapper component | a shared <ModalShell> component that handles the backdrop overlay, content container, e... |
| 2026-03-03-code-health-1 | US-CH-007 | Reduce ActiveGameView prop count via useGameRoom context | game room state and callbacks to flow through a React context (useGameRoom) instead of... |
| 2026-03-03-code-health-1 | US-CH-008 | Convert source-string tests to behavioral tests | the UXP test files to test rendered behavior (what users see in the DOM) instead of rea... |
| 2026-03-03-code-health-1-legacy | US-CH-001 | Extract shared backend test fixtures into conftest.py | common test helpers (_make_card, _mock_caller_id, client fixture, make_state, mock_rng)... |
| 2026-03-03-code-health-1-legacy | US-CH-002 | Extract shared frontend test fixtures into helpers.ts | common frontend test setup (Supabase mock, API mock, MOCK_SESSION, setupAuth, makeGame,... |
| 2026-03-03-code-health-1-legacy | US-CH-003 | Deduplicate backend test scenarios across test_api / test_auth_api / test_error_responses | each error scenario (404, 403, 409, 422) tested exactly once -- not duplicated across t... |
| 2026-03-03-code-health-1-legacy | US-CH-004 | Extract archetype dispatch from apply_intent reducer | the archetype dispatch logic extracted from the 189-line apply_intent function into a d... |
| 2026-03-03-code-health-1-legacy | US-CH-005 | Extract adjacency helper into shared board module | the board adjacency lookup to live in a shared module (app/rules/board.py) instead of b... |
| 2026-03-03-code-health-1-legacy | US-CH-006 | Extract ModalShell shared dialog wrapper component | a shared <ModalShell> component that handles the backdrop overlay, content container, e... |
| 2026-03-03-code-health-1-legacy | US-CH-007 | Reduce ActiveGameView prop count via useGameRoom context | game room state and callbacks to flow through a React context (useGameRoom) instead of... |
| 2026-03-03-code-health-1-legacy | US-CH-008 | Convert source-string tests to behavioral tests | the UXP test files to test rendered behavior (what users see in the DOM) instead of rea... |
| 2026-03-03-game-mechanics-depth | US-GM-001 | Weak-side card rule: every card must have at least one side <= 3 | every card -- including ultra/very-rare -- to have at least one exploitable low side |
| 2026-03-03-game-mechanics-depth | US-GM-002 | Mists intensity buff: change modifier from +/-1 to +/-2 | the Mists of Barovia roll to feel impactful and risky |
| 2026-03-03-game-mechanics-depth | US-GM-003 | Plus rule -- backend: side-sum matching capture mechanic | a Plus capture rule |
| 2026-03-03-game-mechanics-depth | US-GM-004 | Plus rule -- UI: callout and capture feedback | clear visual feedback when the Plus rule fires |
| 2026-03-03-game-mechanics-depth | US-GM-005 | Elemental system -- card data and model | each card to carry an element |
| 2026-03-03-game-mechanics-depth | US-GM-006 | Elemental system -- game state, rules engine, and API | the board to have elemental cells |
| 2026-03-03-game-mechanics-depth | US-GM-007 | Elemental system -- UI: board cell elements and match highlighting | to see the element of each board cell and get a visual cue when my selected card matche... |
| 2026-03-03-game-mechanics-depth | US-GM-008 | Game rules documentation + Rules dialog refresh | all four new mechanics documented accurately |
| 2026-03-03-game-mechanics-depth | US-GM-009 | Card elements shown in hand drawer + preview | to see a card's element in the hand drawer and in the card preview |
| 2026-03-03-game-mechanics-depth | US-GM-010 | Board cell hover tooltip shows cell element | hovering a board cell to show that cell's element |
| 2026-03-03-game-mechanics-depth | US-GM-011 | Games list shows open games and sorts newest-first | the Games list to show open (joinable) games without needing an invite link, and to be... |
| 2026-03-03-game-mechanics-depth | US-GM-012 | Use anchors for route navigation | navigation-only UI controls to be anchors/links |
| 2026-03-03-game-mechanics-depth | US-GM-013 | Limit users to one non-complete game at a time | the app to prevent me from having multiple in-progress games at once |
| 2026-03-03-game-mechanics-depth | US-GM-014 | Game room layout redesign (board + hand always visible) | the board and my hand visible at the same time |
| 2026-03-03-game-mechanics-depth | US-GM-015 | Guided action flow (select card -> optional power -> place) | a clear, guided flow during my turn |
| 2026-03-03-game-mechanics-depth | US-GM-016 | Secondary sidebar (desktop) + bottom drawer (mobile) | secondary info/actions (rules, leave/forfeit, archetypes, last move) visible but clearl... |
| 2026-03-04-ui-polish | US-UP-001 | Shrink game room header chrome | the game room header (title, Refresh, Back to Games) to be smaller and less dominant -- |
| 2026-03-04-ui-polish | US-UP-002 | Board-level event feedback callouts | brief animated callouts to appear near the board when events happen (Mists roll, captur... |
| 2026-03-04-ui-polish | US-UP-003 | Declutter sidebar: archetype powers as tooltips | the sidebar to be less information-dense -- archetype power descriptions should be avai... |
| 2026-03-04-ui-polish | US-UP-004 | Prominent power activation toggle | the archetype power activation to be a large, visually distinct button instead of a sub... |
| 2026-03-04-ui-polish | US-UP-005 | Archetype selection confirm button | a confirm step when selecting my archetype -- |
