/**
 * US-GM-016 — Secondary sidebar (desktop) + bottom drawer (mobile)
 *
 * Tests verify the secondary region renders correct content
 * and that the mobile drawer opens/closes correctly.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import App from "@/App";
import type { BoardCell, GameState } from "@/lib/api";
import { MOCK_SESSION } from "./helpers";

// --- Supabase mock -----------------------------------------------------------

const { mockGetSession, mockOnAuthStateChange } = vi.hoisted(() => ({
  mockGetSession: vi.fn(),
  mockOnAuthStateChange: vi.fn(),
}));

const { mockChannel, mockRemoveChannel } = vi.hoisted(() => ({
  mockChannel: vi.fn().mockReturnValue({
    on: vi.fn().mockReturnValue({
      subscribe: vi.fn().mockReturnValue({ unsubscribe: vi.fn() }),
    }),
  }),
  mockRemoveChannel: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: mockGetSession,
      onAuthStateChange: mockOnAuthStateChange,
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
      resetPasswordForEmail: vi.fn(),
      updateUser: vi.fn(),
      signOut: vi.fn(),
    },
    channel: mockChannel,
    removeChannel: mockRemoveChannel,
  },
}));

// --- API mock ----------------------------------------------------------------

const { mockGetGame, mockGetCardDefinitions, mockListGames } = vi.hoisted(() => ({
  mockGetGame: vi.fn(),
  mockGetCardDefinitions: vi.fn(),
  mockListGames: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  listGames: mockListGames,
  createGame: vi.fn(),
  getGame: mockGetGame,
  getCardDefinitions: mockGetCardDefinitions,
  joinGame: vi.fn(),
  leaveGame: vi.fn(),
  placeCard: vi.fn(),
  selectArchetype: vi.fn(),
}));

// --- Helpers -----------------------------------------------------------------

function setupAuth() {
  mockGetSession.mockResolvedValue({ data: { session: MOCK_SESSION } });
  mockOnAuthStateChange.mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  });
}

function makeGame(overrides: Partial<GameState> = {}): GameState {
  return {
    game_id: "gm016",
    status: "active",
    players: [
      { player_id: "user-123", archetype: "martial", hand: ["c1", "c2"], archetype_used: false },
      { player_id: "opp-456", archetype: "devout", hand: ["c3", "c4"], archetype_used: false },
    ],
    board: [
      { card_key: "card-x", owner: 0 },
      null, null, null, null, null, null, null, null,
    ],
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 3,
    round_number: 1,
    result: null,
    ...overrides,
  };
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockListGames.mockResolvedValue([]);
  mockGetCardDefinitions.mockResolvedValue(new Map());
});

// --- Tests -------------------------------------------------------------------

describe("US-GM-016 — secondary sidebar content", () => {
  it("sidebar contains Rules entrypoint", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm016");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    // Rules button should exist inside the secondary info region
    const secondaryRegions = screen.getAllByLabelText("secondary info");
    const hasRulesButton = secondaryRegions.some(
      (region) => region.querySelector("button")?.textContent?.includes("Rules")
    );
    expect(hasRulesButton).toBe(true);
  });

  it("sidebar contains Leave Game button", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm016");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    const secondaryRegions = screen.getAllByLabelText("secondary info");
    const hasLeaveButton = secondaryRegions.some((region) =>
      Array.from(region.querySelectorAll("button")).some((btn) =>
        btn.textContent?.includes("Leave Game")
      )
    );
    expect(hasLeaveButton).toBe(true);
  });

  it("sidebar contains archetype info for both players", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm016");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    // Should show both archetypes somewhere
    expect(screen.getAllByText(/martial/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/devout/i).length).toBeGreaterThanOrEqual(1);
  });

  it("sidebar contains recent events area (last move callout)", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame({
      last_move: {
        card_key: "card-x",
        cell_index: 0,
        player_index: 0,
        mists_roll: 3,
        mists_effect: "none",
        captures: [],
      },
    }));
    renderAt("/g/gm016");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    expect(screen.getAllByLabelText("last move callout").length).toBeGreaterThanOrEqual(1);
  });

  it("desktop sidebar has independent scrolling", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm016");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    const sidebar = screen.getByLabelText("game sidebar");
    expect(sidebar.className).toMatch(/overflow-y-auto/);
  });
});

describe("US-GM-016 — mobile drawer open/close", () => {
  it("mobile drawer toggle exists", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm016");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText("toggle secondary info")).toBeInTheDocument();
  });

  it("mobile drawer opens when toggle is clicked", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm016");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    const toggle = screen.getByLabelText("toggle secondary info");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
  });

  it("mobile drawer closes on second toggle click", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm016");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    const toggle = screen.getByLabelText("toggle secondary info");
    await userEvent.click(toggle); // open
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await userEvent.click(toggle); // close
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });
});
