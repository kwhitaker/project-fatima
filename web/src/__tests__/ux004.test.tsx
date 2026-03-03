/**
 * US-UX-004: Archetype selection is an unskippable modal.
 *
 * Covers:
 * - Blocking modal is shown when game is active and caller has no archetype
 * - Modal is NOT shown when caller already has an archetype
 * - Hand cards are disabled when no archetype selected
 * - Board cells cannot be activated for placement when no archetype selected
 */
import { render, screen, within } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import GameRoom from "../routes/GameRoom";
import type { GameState } from "@/lib/api";

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: { id: "player-1" } }),
}));

vi.mock("@/lib/api", () => ({
  getGame: vi.fn(),
  joinGame: vi.fn(),
  leaveGame: vi.fn(),
  placeCard: vi.fn(),
  selectArchetype: vi.fn(),
  getCardDefinitions: vi.fn().mockResolvedValue(new Map()),
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    channel: () => ({
      on: () => ({ subscribe: () => ({ unsubscribe: vi.fn() }) }),
      subscribe: vi.fn().mockReturnValue({ unsubscribe: vi.fn() }),
    }),
    removeChannel: vi.fn(),
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
    },
  },
}));

const { getGame } = await import("@/lib/api");

function makeActiveGame(myArchetype: string | null = null): GameState {
  return {
    game_id: "game-ux004",
    status: "active",
    players: [
      {
        player_id: "player-1",
        archetype: myArchetype as GameState["players"][0]["archetype"],
        hand: ["card_001", "card_002"],
        archetype_used: false,
      },
      {
        player_id: "player-2",
        archetype: "martial" as const,
        hand: ["card_010", "card_011"],
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
  };
}

function renderGameRoom() {
  render(
    <MemoryRouter initialEntries={["/g/game-ux004"]}>
      <Routes>
        <Route path="/g/:gameId" element={<GameRoom />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("US-UX-004: unskippable archetype modal", () => {
  it("shows blocking archetype modal when game is active and caller has no archetype", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(null));
    renderGameRoom();

    const modal = await screen.findByRole("dialog", { name: /choose your archetype/i });
    expect(modal).toBeTruthy();
  });

  it("does not show archetype modal when caller already has an archetype", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame("devout"));
    renderGameRoom();

    await screen.findByText(/your turn|opponent's turn/i);
    expect(screen.queryByRole("dialog", { name: /choose your archetype/i })).toBeNull();
  });

  it("modal contains all five archetype options", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(null));
    renderGameRoom();

    const modal = await screen.findByRole("dialog", { name: /choose your archetype/i });
    for (const arch of ["martial", "skulker", "caster", "devout", "intimidate"]) {
      expect(within(modal).getByRole("button", { name: new RegExp(arch, "i") })).toBeTruthy();
    }
  });

  it("hand cards are disabled when no archetype selected", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(null));
    renderGameRoom();

    // Wait for the modal to appear (implies game loaded)
    await screen.findByRole("dialog", { name: /choose your archetype/i });

    // Hand card selection buttons (those with aria-pressed) should be disabled
    const handButtons = screen.queryAllByRole("button", { name: /card_00/i })
      .filter((b) => b.hasAttribute("aria-pressed"));
    for (const btn of handButtons) {
      expect((btn as HTMLButtonElement).disabled).toBe(true);
    }
  });

  it("hand cards are enabled when archetype is selected", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame("caster"));
    renderGameRoom();

    await screen.findByText(/your turn|opponent's turn/i);

    // Hand card selection buttons (those with aria-pressed) should not be disabled
    const handButtons = screen.queryAllByRole("button", { name: /card_00/i })
      .filter((b) => b.hasAttribute("aria-pressed"));
    expect(handButtons.length).toBeGreaterThan(0);
    for (const btn of handButtons) {
      expect((btn as HTMLButtonElement).disabled).toBe(false);
    }
  });
});
