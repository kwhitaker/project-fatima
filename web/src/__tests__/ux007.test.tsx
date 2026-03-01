/**
 * US-UX-007: Games list UX — opponent + truncated id + Win/Loss/Forfeit labels
 *
 * Covers:
 * - Each row shows opponent email (or "Waiting...") plus a truncated game id
 * - Rows show status and, for COMPLETE games, a result label: Win/Loss/Forfeit/Draw
 * - Full UUID is NOT displayed by default (only first 8 chars shown as primary id)
 * - Row interactions have clear hover/cursor feedback
 */
import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Games from "../routes/Games";
import type { GameState } from "@/lib/api";

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "player-1" },
    signOut: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  listGames: vi.fn(),
  createGame: vi.fn(),
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
    },
  },
}));

const { listGames } = await import("@/lib/api");

const GAME_ID = "aaaabbbb-cccc-dddd-eeee-ffff00001111";
const SHORT_ID = "aaaabbbb"; // first 8 chars

function makeGame(overrides: Partial<GameState> = {}): GameState {
  return {
    game_id: GAME_ID,
    status: "active",
    players: [
      {
        player_id: "player-1",
        email: "me@example.com",
        archetype: "martial",
        hand: [],
        archetype_used: false,
      },
      {
        player_id: "player-2",
        email: "opponent@example.com",
        archetype: "devout",
        hand: [],
        archetype_used: false,
      },
    ],
    board: Array(9).fill(null) as null[],
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 2,
    round_number: 1,
    result: null,
    last_move: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("US-UX-007: Games list row UX", () => {
  it("shows opponent email when game has two players", async () => {
    vi.mocked(listGames).mockResolvedValue([makeGame()]);
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>
    );
    expect(await screen.findByText("opponent@example.com")).toBeTruthy();
  });

  it("shows 'Waiting...' when only one player (no opponent yet)", async () => {
    vi.mocked(listGames).mockResolvedValue([
      makeGame({
        status: "waiting",
        players: [
          {
            player_id: "player-1",
            email: "me@example.com",
            archetype: null,
            hand: [],
            archetype_used: false,
          },
        ],
      }),
    ]);
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>
    );
    expect(await screen.findByText(/waiting\.\.\./i)).toBeTruthy();
  });

  it("shows truncated game id (8 chars) not the full UUID", async () => {
    vi.mocked(listGames).mockResolvedValue([makeGame()]);
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>
    );
    await screen.findByText("opponent@example.com");
    // Short ID should be present
    expect(screen.getByText(SHORT_ID)).toBeTruthy();
    // Full UUID should NOT appear as visible text
    expect(screen.queryByText(GAME_ID)).toBeNull();
  });

  it("shows 'Win' result label when current user won normally", async () => {
    vi.mocked(listGames).mockResolvedValue([
      makeGame({
        status: "complete",
        result: {
          winner: 0, // player-1 is index 0
          is_draw: false,
          completion_reason: "normal",
          forfeit_by_index: null,
        },
      }),
    ]);
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>
    );
    expect(await screen.findByText(/\bwin\b/i)).toBeTruthy();
  });

  it("shows 'Loss' result label when current user lost normally", async () => {
    vi.mocked(listGames).mockResolvedValue([
      makeGame({
        status: "complete",
        result: {
          winner: 1, // player-2 won, player-1 (me) lost
          is_draw: false,
          completion_reason: "normal",
          forfeit_by_index: null,
        },
      }),
    ]);
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>
    );
    expect(await screen.findByText(/\bloss\b/i)).toBeTruthy();
  });

  it("shows 'Draw' result label on draw", async () => {
    vi.mocked(listGames).mockResolvedValue([
      makeGame({
        status: "complete",
        result: {
          winner: null,
          is_draw: true,
          completion_reason: "normal",
          forfeit_by_index: null,
        },
      }),
    ]);
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>
    );
    expect(await screen.findByText(/\bdraw\b/i)).toBeTruthy();
  });

  it("shows 'Forfeit' when current user forfeited", async () => {
    vi.mocked(listGames).mockResolvedValue([
      makeGame({
        status: "complete",
        result: {
          winner: 1,
          is_draw: false,
          completion_reason: "forfeit",
          forfeit_by_index: 0, // I (player-1, index 0) forfeited
        },
      }),
    ]);
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>
    );
    expect(await screen.findByText(/\bforfeit\b/i)).toBeTruthy();
  });

  it("shows 'Win' when opponent forfeited", async () => {
    vi.mocked(listGames).mockResolvedValue([
      makeGame({
        status: "complete",
        result: {
          winner: 0,
          is_draw: false,
          completion_reason: "forfeit",
          forfeit_by_index: 1, // opponent (index 1) forfeited
        },
      }),
    ]);
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>
    );
    expect(await screen.findByText(/\bwin\b/i)).toBeTruthy();
  });

  it("game list row button has cursor-pointer for clear UX affordance", async () => {
    vi.mocked(listGames).mockResolvedValue([makeGame()]);
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>
    );
    await screen.findByText("opponent@example.com");
    const rows = document.querySelectorAll("button.cursor-pointer");
    expect(rows.length).toBeGreaterThan(0);
  });
});
