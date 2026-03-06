/**
 * Tests for US-GM-013: limit users to one non-complete game at a time.
 *
 * Covers:
 * - Error shown when createGame returns 409
 * - Error shown when joinGame returns 409
 * - Error text explains the user must finish/forfeit existing game
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { vi, beforeEach, describe, it, expect } from "vitest";
import App from "../App";
import Games from "@/routes/Games";
import GameRoom from "@/routes/GameRoom";
import { MOCK_SESSION, makeGame, makePlayer } from "./helpers";

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
const { mockListGames, mockCreateGame, mockGetGame, mockJoinGame } =
  vi.hoisted(() => ({
    mockListGames: vi.fn(),
    mockCreateGame: vi.fn(),
    mockGetGame: vi.fn(),
    mockJoinGame: vi.fn(),
  }));

vi.mock("@/lib/api", () => ({
  listGames: mockListGames,
  createGame: mockCreateGame,
  getGame: mockGetGame,
  joinGame: mockJoinGame,
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
  mockCreateGame.mockResolvedValue(makeGame({ game_id: "new-game" }));
  mockGetGame.mockResolvedValue(
    makeGame({
      game_id: "open-game",
      players: [makePlayer("other-user", "host@example.com")],
    })
  );
  mockJoinGame.mockResolvedValue(
    makeGame({
      game_id: "open-game",
      players: [makePlayer("other-user"), makePlayer("user-123")],
    })
  );
});

function renderGames() {
  return render(
    <MemoryRouter initialEntries={["/games"]}>
      <App />
    </MemoryRouter>
  );
}

function renderGameRoom(gameId: string = "open-game") {
  return render(
    <MemoryRouter initialEntries={[`/g/${gameId}`]}>
      <App />
    </MemoryRouter>
  );
}

// --- Create game 409 error ---------------------------------------------------

describe("create game blocked (409)", () => {
  it("shows error when createGame returns 409", async () => {
    const err = new Error(
      "You already have a non-complete game (existing-id). Finish or forfeit it before starting a new one."
    );
    Object.assign(err, { status: 409 });
    mockCreateGame.mockRejectedValue(err);

    const user = userEvent.setup();
    renderGames();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /challenge another player/i })
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /challenge another player/i }));

    await waitFor(() => {
      expect(screen.getByText(/non-complete game/i)).toBeInTheDocument();
    });
  });

  it("error text mentions finishing or forfeiting", async () => {
    const err = new Error(
      "You already have a non-complete game (existing-id). Finish or forfeit it before starting a new one."
    );
    Object.assign(err, { status: 409 });
    mockCreateGame.mockRejectedValue(err);

    const user = userEvent.setup();
    renderGames();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /challenge another player/i })
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /challenge another player/i }));

    await waitFor(() => {
      expect(screen.getByText(/forfeit/i)).toBeInTheDocument();
    });
  });
});

// --- Join game 409 error -----------------------------------------------------

describe("join game blocked (409)", () => {
  it("shows error when joinGame returns 409", async () => {
    const err = new Error(
      "You already have a non-complete game (existing-id). Finish or forfeit it before starting a new one."
    );
    Object.assign(err, { status: 409 });
    mockJoinGame.mockRejectedValue(err);

    // Render the game room for an open game the user is not in
    mockGetGame.mockResolvedValue(
      makeGame({
        game_id: "open-game",
        players: [makePlayer("other-user", "host@example.com")],
      })
    );

    const user = userEvent.setup();
    renderGameRoom("open-game");

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /join game/i })
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /join game/i }));

    await waitFor(() => {
      expect(screen.getByText(/non-complete game/i)).toBeInTheDocument();
    });
  });

  it("join error text mentions finishing or forfeiting", async () => {
    const err = new Error(
      "You already have a non-complete game (existing-id). Finish or forfeit it before starting a new one."
    );
    Object.assign(err, { status: 409 });
    mockJoinGame.mockRejectedValue(err);

    mockGetGame.mockResolvedValue(
      makeGame({
        game_id: "open-game",
        players: [makePlayer("other-user", "host@example.com")],
      })
    );

    const user = userEvent.setup();
    renderGameRoom("open-game");

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /join game/i })
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /join game/i }));

    await waitFor(() => {
      expect(screen.getByText(/forfeit/i)).toBeInTheDocument();
    });
  });
});
