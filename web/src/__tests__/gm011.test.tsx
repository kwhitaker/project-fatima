/**
 * Tests for US-GM-011: open games in list + newest-first ordering.
 * Updated for the reworked Games page with separate sections.
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, beforeEach, describe, it, expect } from "vitest";
import App from "../App";
import { MOCK_SESSION, makeGame, makePlayer } from "./helpers";

// --- Supabase mock -----------------------------------------------------------
const { mockGetSession, mockOnAuthStateChange, mockSignOut } = vi.hoisted(
  () => ({
    mockGetSession: vi.fn(),
    mockOnAuthStateChange: vi.fn(),
    mockSignOut: vi.fn(),
  }),
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
  createGameVsAi: vi.fn(),
  getGame: vi.fn(),
  joinGame: vi.fn(),
  leaveGame: vi.fn(),
  placeCard: vi.fn(),
  selectArchetype: vi.fn(),
  getCardDefinitions: vi.fn().mockResolvedValue(new Map()),
}));

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
    </MemoryRouter>,
  );
}

// --- Open game rendering -----------------------------------------------------

describe("open games in list", () => {
  it("shows 'Join' label for games user is not a participant of", async () => {
    mockListGames.mockResolvedValue([
      makeGame({
        game_id: "open-game-1",
        status: "waiting",
        players: [makePlayer("other-user", "host@example.com")],
      }),
    ]);
    renderGames();
    await waitFor(() => {
      expect(screen.getByText("Join")).toBeInTheDocument();
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

  it("shows 'Unknown' when open game host has no email", async () => {
    mockListGames.mockResolvedValue([
      makeGame({
        game_id: "open-game-1",
        status: "waiting",
        players: [
          {
            player_id: "other-user",
            archetype: null,
            hand: [],
            deal: [],
            archetype_used: false,
            player_type: "human",
          },
        ],
      }),
    ]);
    renderGames();
    await waitFor(() => {
      const openSection = screen.getByText("Open Games").closest("section")!;
      expect(within(openSection).getByText("Unknown")).toBeInTheDocument();
    });
  });

  it("shows 'Waiting' status for own waiting game (not in Open Games)", async () => {
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
      // Should not appear in open games section
      const openSection = screen.getByText("Open Games").closest("section")!;
      expect(
        within(openSection).getByText("No open games available."),
      ).toBeInTheDocument();
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
    const myGamesSection = screen.getByText("My Games").closest("section")!;
    const items = within(myGamesSection).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0].textContent).toContain("game-wai");
    expect(items[1].textContent).toContain("game-cmp");
  });
});
