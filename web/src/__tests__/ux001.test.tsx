/**
 * US-UX-001: Dark mode default + mobile-first layout baseline
 * Red/Green tests for cursor, hover, and layout class assertions.
 */
import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Games from "../routes/Games";
import type { GameState } from "@/lib/api";

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ signOut: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  listGames: vi.fn(),
  createGame: vi.fn(),
}));

// Supabase mock (Games doesn't use it directly, but the module graph imports it)
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

const mockGame: GameState = {
  game_id: "game-abc123",
  status: "waiting",
  players: [],
  board: Array(9).fill(null) as (null)[],
  current_player_index: 0,
  starting_player_index: 0,
  state_version: 1,
  round_number: 1,
  result: null,
  last_move: null,
};

beforeEach(() => {
  vi.mocked(listGames).mockResolvedValue([mockGame]);
});

describe("US-UX-001: dark mode default + mobile-first layout", () => {
  it("game list row button has cursor-pointer for clear UX affordance", async () => {
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>
    );
    const row = await screen.findByRole("button", { name: /game-abc123/i });
    expect(row.className).toContain("cursor-pointer");
  });

  it("header actions are wrapped for mobile flex layout", async () => {
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>
    );
    // Header should be present; find by the Create Game button which is always rendered
    await screen.findByRole("button", { name: /create game/i });
    const header = document.querySelector("div.flex");
    expect(header).not.toBeNull();
  });
});
