/**
 * US-GM-014 — Game room layout redesign: board + hand always visible
 *
 * Tests verify that the board and hand panel render simultaneously
 * in active games and that the old drawer toggle affordance is removed.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import App from "@/App";
import type { BoardCell, GameState } from "@/lib/api";

// --- Supabase mock (vi.hoisted so vi.mock can reference) ---------------------

const {
  mockGetSession,
  mockOnAuthStateChange,
} = vi.hoisted(() => ({
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

const MOCK_SESSION = {
  user: { id: "user-123", email: "test@example.com" },
  access_token: "tok",
};

function setupAuth() {
  mockGetSession.mockResolvedValue({ data: { session: MOCK_SESSION } });
  mockOnAuthStateChange.mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  });
}

const EMPTY_BOARD: (BoardCell | null)[] = Array(9).fill(null);

function makeGame(overrides: Partial<GameState> = {}): GameState {
  return {
    game_id: "gm014",
    status: "active",
    players: [
      { player_id: "user-123", archetype: "martial", hand: ["card-a", "card-b", "card-c"], archetype_used: false },
      { player_id: "opp-456", archetype: "devout", hand: ["card-d", "card-e"], archetype_used: false },
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

describe("US-GM-014 — board + hand always visible", () => {
  it("board and hand panel are both rendered in active game", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm014");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    // Hand panel should be visible simultaneously
    expect(screen.getByLabelText("hand panel")).toBeInTheDocument();
    // Hand cards visible
    expect(screen.getByRole("button", { name: "card-a" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "card-b" })).toBeInTheDocument();
  });

  it("no drawer toggle affordance exists", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm014");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    expect(screen.queryByLabelText("toggle hand drawer")).not.toBeInTheDocument();
  });

  it("hand panel shows 'Your hand' label and all cards", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm014");
    await waitFor(() => {
      expect(screen.getByLabelText("hand panel")).toBeInTheDocument();
    });
    expect(screen.getByText("Your hand")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "card-a" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "card-b" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "card-c" })).toBeInTheDocument();
  });

  it("hand panel is not inside a fixed-position element", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm014");
    await waitFor(() => {
      expect(screen.getByLabelText("hand panel")).toBeInTheDocument();
    });
    const handPanel = screen.getByLabelText("hand panel");
    // HandPanel is rendered in-flow, not inside a fixed-position wrapper
    expect(handPanel.closest(".fixed")).toBeNull();
  });

  it("secondary info region is present (sidebar or mobile toggle)", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm014");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    const sidebar = screen.queryByLabelText("game sidebar");
    const mobileToggle = screen.queryByLabelText("toggle secondary info");
    expect(sidebar ?? mobileToggle).toBeTruthy();
  });
});
