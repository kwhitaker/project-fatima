/**
 * Smoke test: create → share link → join → play one move.
 *
 * Auth is bypassed by injecting a fake Supabase session into localStorage before
 * any page script runs.  All network calls (Supabase auth API + app API) are
 * intercepted with page.route() so no live backend is required.
 *
 * Supabase JS v2 storage key format:
 *   sb-${new URL(VITE_SUPABASE_URL).hostname.split('.')[0]}-auth-token
 * For https://yhrwetmhhrxeyiiijixb.supabase.co this is:
 *   sb-yhrwetmhhrxeyiiijixb-auth-token
 */
import { test, expect } from "@playwright/test";

const SUPABASE_KEY = "sb-yhrwetmhhrxeyiiijixb-auth-token";

const P1 = { id: "smoke-p1", email: "p1@smoke.test" };
const P2 = { id: "smoke-p2", email: "p2@smoke.test" };
const GAME_ID = "smoke-game-001";

function makeSession(user: { id: string; email: string }): string {
  return JSON.stringify({
    access_token: `tok-${user.id}`,
    refresh_token: `ref-${user.id}`,
    expires_at: Math.floor(Date.now() / 1000) + 86_400,
    token_type: "bearer",
    user: {
      id: user.id,
      email: user.email,
      aud: "authenticated",
      role: "authenticated",
      created_at: "2024-01-01T00:00:00.000Z",
    },
  });
}

const EMPTY_BOARD = Array(9).fill(null);
const P1_PLAYER = {
  player_id: P1.id,
  archetype: null,
  hand: ["card-a", "card-b"],
  archetype_used: false,
};
const P2_PLAYER = {
  player_id: P2.id,
  archetype: null,
  hand: ["card-c", "card-d"],
  archetype_used: false,
};

function waitingGame(players = [P1_PLAYER]) {
  return {
    game_id: GAME_ID,
    status: "waiting",
    players,
    board: EMPTY_BOARD,
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 1,
    round_number: 1,
    result: null,
    last_move: null,
  };
}

function activeGame(currentPlayerIndex = 0, stateVersion = 2) {
  return {
    ...waitingGame([P1_PLAYER, P2_PLAYER]),
    status: "active",
    current_player_index: currentPlayerIndex,
    state_version: stateVersion,
  };
}

function gameAfterMove() {
  const board = [...EMPTY_BOARD];
  board[0] = { card_key: "card-a", owner: 0 };
  return { ...activeGame(1, 3), board };
}

test("smoke: create → share link → join → play one move", async ({
  browser,
}) => {
  // Shared mutable game state — mutated in route handlers as the test progresses
  let currentGame: ReturnType<typeof waitingGame> = waitingGame();

  const p1Ctx = await browser.newContext();
  const p2Ctx = await browser.newContext();

  try {
    const p1 = await p1Ctx.newPage();
    const p2 = await p2Ctx.newPage();

    // Inject Supabase sessions before any page scripts run
    for (const [page, user] of [
      [p1, P1],
      [p2, P2],
    ] as const) {
      await page.addInitScript(
        ({ k, v }) => localStorage.setItem(k, v),
        { k: SUPABASE_KEY, v: makeSession(user) }
      );
    }

    // Mock Supabase auth REST endpoints as a safety net
    for (const page of [p1, p2]) {
      await page.route("**/auth/v1/**", (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: "{}",
        })
      );
    }

    // Helper to respond with JSON
    const json = (route: Parameters<Parameters<typeof p1.route>[1]>[0], body: object) =>
      route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });

    // P1 API routes
    await p1.route("**/api/**", (route) => {
      const path = new URL(route.request().url()).pathname;
      const method = route.request().method();

      if (path === "/api/games" && method === "POST") {
        currentGame = waitingGame();
        return json(route, currentGame);
      }
      if (path === "/api/games" && method === "GET") {
        return json(route, [currentGame]);
      }
      if (path === `/api/games/${GAME_ID}` && method === "GET") {
        return json(route, currentGame);
      }
      if (path === `/api/games/${GAME_ID}/moves` && method === "POST") {
        currentGame = gameAfterMove();
        return json(route, currentGame);
      }
      return json(route, currentGame);
    });

    // P2 API routes
    await p2.route("**/api/**", (route) => {
      const path = new URL(route.request().url()).pathname;
      const method = route.request().method();

      if (path === `/api/games/${GAME_ID}/join` && method === "POST") {
        currentGame = activeGame();
        return json(route, currentGame);
      }
      if (path === `/api/games/${GAME_ID}` && method === "GET") {
        return json(route, currentGame);
      }
      return json(route, [currentGame]);
    });

    // ── Step 1: P1 creates a game ──────────────────────────────────────────
    await p1.goto("/games");
    await p1.waitForSelector("h1:has-text(\"My Games\")");
    await p1.getByRole("button", { name: /create game/i }).click();
    await p1.waitForURL(`**/g/${GAME_ID}`);

    // P1 sees the invite link (waiting state)
    await expect(p1.getByRole("button", { name: /copy link/i })).toBeVisible();

    // ── Step 2: P2 navigates to the share link and joins ──────────────────
    await p2.goto(`/g/${GAME_ID}`);
    await p2.waitForSelector("button:has-text(\"Join Game\")");
    await p2.getByRole("button", { name: /join game/i }).click();
    // P1 goes first (index 0); P2 sees "Opponent's turn"
    await expect(p2.getByText("Opponent's turn")).toBeVisible();

    // ── Step 3: P1 reloads (simulates realtime sync) and plays a card ─────
    await p1.goto(`/g/${GAME_ID}`);
    await expect(p1.getByText("Your turn")).toBeVisible();

    // Select card-a from hand
    await p1.getByRole("button", { name: "card-a", exact: true }).click();

    // Cell 0 becomes clickable once a card is selected
    await expect(p1.getByRole("button", { name: "cell 0" })).toBeVisible();
    await p1.click('[aria-label="cell 0"]');

    // After the move it is P2's turn → P1 sees "Opponent's turn"
    await expect(p1.getByText("Opponent's turn")).toBeVisible();
  } finally {
    await p1Ctx.close();
    await p2Ctx.close();
  }
});
