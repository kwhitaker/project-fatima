/**
 * Tests for US-GM-011: open games in list + newest-first ordering.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, beforeEach, describe, it, expect } from "vitest";
import App from "../App";
import type { GameState, PlayerState } from "@/lib/api";

// --- Supabase mock -----------------------------------------------------------
const { mockGetSession, mockOnAuthStateChange, mockSignOut } = vi.hoisted(
  () => ({
    mockGetSession: vi.fn(),
    mockOnAuthStateChange: vi.fn(),
    mockSignOut: vi.fn(),
  })
);

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: mockGetSession,
      onAuthStateChange: mockOnAuthStateChange,
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
      resetPasswordForEmail: vi.fn(),
      updateUser: vi.fn(),
      signOut: mockSignOut,
    },
    channel: vi.fn().mockReturnValue({
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn(),
    }),
    removeChannel: vi.fn().mockResolvedValue(undefined),
  },
}));

// --- API mock ----------------------------------------------------------------
const { mockListGames } = vi.hoisted(() => ({
  mockListGames: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  listGames: mockListGames,
  createGame: vi.fn(),
  getGame: vi.fn(),
  joinGame: vi.fn(),
  leaveGame: vi.fn(),
  placeCard: vi.fn(),
  selectArchetype: vi.fn(),
  getCardDefinitions: vi.fn().mockResolvedValue(new Map()),
}));

const MOCK_SESSION = {
  user: { id: "user-123", email: "test@example.com" },
  access_token: "fake-token",
};

function makeGame(overrides: Partial<GameState> = {}): GameState {
  return {
    game_id: "abc-123",
    status: "waiting",
    players: [],
    board: Array(9).fill(null),
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 0,
    round_number: 1,
    result: null,
    board_elements: null,
    created_at: "2026-03-03T00:00:00+00:00",
    ...overrides,
  };
}

function makePlayer(id: string, email?: string): PlayerState {
  return {
    player_id: id,
    email: email ?? `${id}@example.com`,
    archetype: null,
    hand: [],
    archetype_used: false,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGetSession.mockResolvedValue({ data: { session: MOCK_SESSION } });
  mockOnAuthStateChange.mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  });
  mockListGames.mockResolvedValue([]);
});

function renderGames() {
  return render(
    <MemoryRouter initialEntries={["/games"]}>
      <App />
    </MemoryRouter>
  );
}

// --- Open game rendering -----------------------------------------------------

describe("open games in list", () => {
  it("shows 'Open' badge for games user is not a participant of", async () => {
    mockListGames.mockResolvedValue([
      makeGame({
        game_id: "open-game-1",
        status: "waiting",
        players: [makePlayer("other-user", "host@example.com")],
      }),
    ]);
    renderGames();
    await waitFor(() => {
      expect(screen.getByText("Open")).toBeInTheDocument();
    });
  });

  it("shows host email for open games", async () => {
    mockListGames.mockResolvedValue([
      makeGame({
        game_id: "open-game-1",
        status: "waiting",
        players: [makePlayer("other-user", "host@example.com")],
      }),
    ]);
    renderGames();
    await waitFor(() => {
      expect(screen.getByText("host@example.com")).toBeInTheDocument();
    });
  });

  it("shows 'Waiting...' when open game host has no email", async () => {
    mockListGames.mockResolvedValue([
      makeGame({
        game_id: "open-game-1",
        status: "waiting",
        players: [{ player_id: "other-user", archetype: null, hand: [], archetype_used: false }],
      }),
    ]);
    renderGames();
    await waitFor(() => {
      expect(screen.getByText("Waiting...")).toBeInTheDocument();
    });
  });

  it("shows 'Waiting' status for own waiting game (not 'Open')", async () => {
    mockListGames.mockResolvedValue([
      makeGame({
        game_id: "my-game",
        status: "waiting",
        players: [makePlayer("user-123", "test@example.com")],
      }),
    ]);
    renderGames();
    await waitFor(() => {
      expect(screen.getByText("Waiting")).toBeInTheDocument();
      expect(screen.queryByText("Open")).not.toBeInTheDocument();
    });
  });
});

// --- Ordering ----------------------------------------------------------------

describe("list ordering", () => {
  it("renders games in the order returned by the API (sorted server-side)", async () => {
    mockListGames.mockResolvedValue([
      makeGame({
        game_id: "game-wai",
        status: "waiting",
        players: [makePlayer("user-123")],
        created_at: "2026-03-03T02:00:00+00:00",
      }),
      makeGame({
        game_id: "game-cmp",
        status: "complete",
        players: [makePlayer("user-123"), makePlayer("bob")],
        result: { winner: 0, is_draw: false },
        created_at: "2026-03-03T01:00:00+00:00",
      }),
    ]);
    renderGames();
    await waitFor(() => {
      expect(screen.getByText("game-wai")).toBeInTheDocument();
      expect(screen.getByText("game-cmp")).toBeInTheDocument();
    });
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0].textContent).toContain("game-wai");
    expect(items[1].textContent).toContain("game-cmp");
  });
});
