/**
 * US-GM-015 — Guided action flow: select card -> optional power -> place
 *
 * Tests verify the action panel shows step text, selected card summary with
 * cancel, power controls, and direction-required gating.
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import App from "@/App";
import type { BoardCell, GameState } from "@/lib/api";

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

const { mockGetGame, mockGetCardDefinitions, mockListGames } = vi.hoisted(
  () => ({
    mockGetGame: vi.fn(),
    mockGetCardDefinitions: vi.fn(),
    mockListGames: vi.fn(),
  })
);

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

function makeGame(overrides: Partial<GameState> = {}): GameState {
  return {
    game_id: "gm015",
    status: "active",
    players: [
      {
        player_id: "user-123",
        archetype: "skulker",
        hand: ["card-a", "card-b"],
        archetype_used: false,
      },
      {
        player_id: "opp-456",
        archetype: "devout",
        hand: ["card-d", "card-e"],
        archetype_used: false,
      },
    ],
    board: Array(9).fill(null) as (BoardCell | null)[],
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 1,
    round_number: 1,
    result: null,
    ...overrides,
  };
}

function makeCardDefs() {
  return new Map([
    [
      "card-a",
      {
        card_key: "card-a",
        name: "Zombie Guard",
        sides: { n: 5, e: 3, s: 2, w: 4 },
        tier: 1,
        rarity: 50,
        element: "blood",
      },
    ],
    [
      "card-b",
      {
        card_key: "card-b",
        name: "Skeleton Archer",
        sides: { n: 3, e: 6, s: 1, w: 5 },
        tier: 1,
        rarity: 40,
        element: "shadow",
      },
    ],
  ]);
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
  mockGetCardDefinitions.mockResolvedValue(makeCardDefs());
});

// --- Tests -------------------------------------------------------------------

describe("US-GM-015 — Guided action flow", () => {
  it("shows 'Select a card' step when it is my turn and no card selected", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm015");
    await waitFor(() => {
      expect(screen.getByLabelText("action panel")).toBeInTheDocument();
    });
    expect(screen.getByText("Your turn")).toBeInTheDocument();
    expect(screen.getByTestId("action-step")).toHaveTextContent("Select a card");
  });

  it("shows 'Opponent's turn' when it is not my turn", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame({ current_player_index: 1 }));
    renderAt("/g/gm015");
    await waitFor(() => {
      expect(screen.getByLabelText("action panel")).toBeInTheDocument();
    });
    expect(screen.getByText("Opponent's turn")).toBeInTheDocument();
    // No step text shown on opponent's turn
    expect(screen.queryByTestId("action-step")).not.toBeInTheDocument();
  });

  it("shows selected card summary with Cancel button after selecting a card", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm015");
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /zombie guard/i, pressed: false })).toBeInTheDocument();
    });
    // Select card
    await user.click(screen.getByRole("button", { name: /zombie guard/i, pressed: false }));
    // Action panel should show selected card name
    const panel = screen.getByLabelText("action panel");
    const summary = within(panel).getByLabelText("selected card summary");
    expect(summary).toHaveTextContent("Zombie Guard");
    // Cancel button present
    expect(within(panel).getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  it("Cancel deselects the card", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm015");
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /zombie guard/i, pressed: false })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /zombie guard/i, pressed: false }));
    const panel = screen.getByLabelText("action panel");
    await user.click(within(panel).getByRole("button", { name: /cancel/i }));
    // Should go back to "Select a card"
    expect(screen.getByTestId("action-step")).toHaveTextContent("Select a card");
    // No selected card summary
    expect(screen.queryByLabelText("selected card summary")).not.toBeInTheDocument();
  });

  it("shows direction required step for skulker when power is on but no direction selected", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm015");
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /zombie guard/i, pressed: false })).toBeInTheDocument();
    });
    // Select card
    await user.click(screen.getByRole("button", { name: /zombie guard/i, pressed: false }));
    // Toggle power on
    await user.click(screen.getByLabelText("Use Power"));
    // Should show direction required step
    expect(screen.getByTestId("action-step")).toHaveTextContent(
      "Choose a direction for your power"
    );
    // Direction buttons visible
    const panel = screen.getByLabelText("action panel");
    expect(within(panel).getByRole("button", { name: "n" })).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: "s" })).toBeInTheDocument();
  });

  it("shows 'Choose a cell' after selecting direction for skulker power", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame());
    renderAt("/g/gm015");
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /zombie guard/i, pressed: false })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /zombie guard/i, pressed: false }));
    await user.click(screen.getByLabelText("Use Power"));
    const panel = screen.getByLabelText("action panel");
    await user.click(within(panel).getByRole("button", { name: "n" }));
    expect(screen.getByTestId("action-step")).toHaveTextContent("Choose a cell");
  });

  it("hand cards are disabled when it is opponent's turn", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(makeGame({ current_player_index: 1 }));
    renderAt("/g/gm015");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /zombie guard/i, pressed: false })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /zombie guard/i, pressed: false })).toBeDisabled();
    expect(screen.getByRole("button", { name: /skeleton archer/i, pressed: false })).toBeDisabled();
  });

  it("power controls are hidden when archetype is already used", async () => {
    setupAuth();
    mockGetGame.mockResolvedValue(
      makeGame({
        players: [
          {
            player_id: "user-123",
            archetype: "skulker",
            hand: ["card-a"],
            archetype_used: true,
          },
          {
            player_id: "opp-456",
            archetype: "devout",
            hand: ["card-d"],
            archetype_used: false,
          },
        ],
      })
    );
    renderAt("/g/gm015");
    await waitFor(() => {
      expect(screen.getByLabelText("action panel")).toBeInTheDocument();
    });
    expect(screen.queryByLabelText("Use Power")).not.toBeInTheDocument();
  });
});
