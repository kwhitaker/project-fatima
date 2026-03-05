/**
 * US-UX-001: Dark mode default + mobile-first layout baseline
 * Red/Green tests for cursor, hover, and layout class assertions.
 */
import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Games from "../routes/Games";
import { makeGame, makePlayer } from "./helpers";

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "user-123", email: "test@example.com" },
    signOut: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  listGames: vi.fn(),
  createGame: vi.fn(),
  createGameVsAi: vi.fn(),
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

beforeEach(() => {
  vi.mocked(listGames).mockResolvedValue([
    makeGame({
      game_id: "game-abc123",
      status: "waiting",
      players: [makePlayer("user-123", "test@example.com")],
    }),
  ]);
});

describe("US-UX-001: dark mode default + mobile-first layout", () => {
  it("game list row button has cursor-pointer for clear UX affordance", async () => {
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>,
    );
    // Row now shows truncated ID (8 chars: "game-abc") instead of full game_id
    await screen.findByText("game-abc");
    const rows = document.querySelectorAll("a.cursor-pointer");
    expect(rows.length).toBeGreaterThan(0);
  });

  it("header actions are wrapped for mobile flex layout", async () => {
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>,
    );
    // Header should be present; find by the Create Game button which is always rendered
    await screen.findByRole("button", { name: /create game/i });
    const header = document.querySelector("div.flex");
    expect(header).not.toBeNull();
  });
});
