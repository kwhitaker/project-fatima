import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi, beforeEach, describe, it, expect } from "vitest";
import App from "../App";
import type { GameState, PlayerState } from "@/lib/api";

// --- Supabase mock -----------------------------------------------------------
// vi.mock is hoisted to the top, so use vi.hoisted() for the shared fns.
const {
  mockGetSession,
  mockOnAuthStateChange,
  mockSignInWithOtp,
  mockSignOut,
} = vi.hoisted(() => ({
  mockGetSession: vi.fn(),
  mockOnAuthStateChange: vi.fn(),
  mockSignInWithOtp: vi.fn(),
  mockSignOut: vi.fn(),
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: mockGetSession,
      onAuthStateChange: mockOnAuthStateChange,
      signInWithOtp: mockSignInWithOtp,
      signOut: mockSignOut,
    },
  },
}));

// --- API mock ----------------------------------------------------------------
const { mockListGames, mockCreateGame, mockGetGame, mockJoinGame } = vi.hoisted(() => ({
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
}));

const MOCK_SESSION = {
  user: { id: "user-123", email: "test@example.com" },
  access_token: "fake-token",
};

function setupAuth(authenticated: boolean) {
  const session = authenticated ? MOCK_SESSION : null;
  mockGetSession.mockResolvedValue({ data: { session } });
  mockOnAuthStateChange.mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  });
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
}

const DEFAULT_GAME: GameState = {
  game_id: "abc-123",
  status: "waiting",
  players: [],
  state_version: 0,
  round_number: 1,
};

beforeEach(() => {
  vi.clearAllMocks();
  // Default: unauthenticated, empty game list
  setupAuth(false);
  mockListGames.mockResolvedValue([]);
  mockCreateGame.mockResolvedValue({
    game_id: "new-game-id",
    status: "waiting",
    players: [],
    state_version: 0,
    round_number: 1,
  });
  mockGetGame.mockResolvedValue(DEFAULT_GAME);
  mockJoinGame.mockResolvedValue(DEFAULT_GAME);
});

// --- Auth guards -------------------------------------------------------------

describe("auth guards", () => {
  it("unauthenticated /games redirects to /login", async () => {
    renderAt("/games");
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /sign in/i })
      ).toBeInTheDocument();
    });
  });

  it("unauthenticated /g/:gameId redirects to /login", async () => {
    renderAt("/g/abc-123");
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /sign in/i })
      ).toBeInTheDocument();
    });
  });

  it("authenticated /games shows My Games", async () => {
    setupAuth(true);
    renderAt("/games");
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /my games/i })
      ).toBeInTheDocument();
    });
  });

  it("authenticated /g/:gameId shows game room", async () => {
    setupAuth(true);
    renderAt("/g/abc-123");
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /game abc-123/i })
      ).toBeInTheDocument();
    });
  });
});

// --- Basic routes ------------------------------------------------------------

describe("routes", () => {
  it("renders login route", async () => {
    renderAt("/login");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    });
  });

  it("wildcard unauthenticated redirect goes to /login", async () => {
    renderAt("/");
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /sign in/i })
      ).toBeInTheDocument();
    });
  });
});

// --- Login form --------------------------------------------------------------

describe("login form", () => {
  it("sends magic link and shows confirmation message", async () => {
    mockSignInWithOtp.mockResolvedValue({ error: null });
    const user = userEvent.setup();
    renderAt("/login");

    await user.type(
      screen.getByPlaceholderText(/you@example.com/i),
      "test@example.com"
    );
    await user.click(screen.getByRole("button", { name: /send magic link/i }));

    await waitFor(() => {
      expect(screen.getByText(/check your email/i)).toBeInTheDocument();
    });
  });

  it("shows error message on magic link failure", async () => {
    mockSignInWithOtp.mockResolvedValue({
      error: { message: "Invalid email address" },
    });
    const user = userEvent.setup();
    renderAt("/login");

    await user.type(
      screen.getByPlaceholderText(/you@example.com/i),
      "bad@example.com"
    );
    await user.click(screen.getByRole("button", { name: /send magic link/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid email address/i)).toBeInTheDocument();
    });
  });
});

// --- Games page --------------------------------------------------------------

describe("games page", () => {
  it("shows a Log out button when authenticated", async () => {
    setupAuth(true);
    renderAt("/games");
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /log out/i })
      ).toBeInTheDocument();
    });
  });

  it("shows 'No games yet.' when the list is empty", async () => {
    setupAuth(true);
    mockListGames.mockResolvedValue([]);
    renderAt("/games");
    await waitFor(() => {
      expect(screen.getByText(/no games yet/i)).toBeInTheDocument();
    });
  });

  it("renders a game row for each game returned by the API", async () => {
    setupAuth(true);
    mockListGames.mockResolvedValue([
      { game_id: "game-aaa", status: "waiting", players: [], state_version: 0, round_number: 1 },
      { game_id: "game-bbb", status: "active", players: [], state_version: 3, round_number: 1 },
    ]);
    renderAt("/games");
    await waitFor(() => {
      expect(screen.getByText("game-aaa")).toBeInTheDocument();
      expect(screen.getByText("game-bbb")).toBeInTheDocument();
      expect(screen.getByText("Waiting")).toBeInTheDocument();
      expect(screen.getByText("Active")).toBeInTheDocument();
    });
  });

  it("clicking a game row navigates to /g/:gameId", async () => {
    setupAuth(true);
    mockListGames.mockResolvedValue([
      { game_id: "game-ccc", status: "waiting", players: [], state_version: 0, round_number: 1 },
    ]);
    const user = userEvent.setup();
    renderAt("/games");
    await waitFor(() => {
      expect(screen.getByText("game-ccc")).toBeInTheDocument();
    });
    await user.click(screen.getByText("game-ccc"));
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /game game-ccc/i })
      ).toBeInTheDocument();
    });
  });

  it("Create Game button calls createGame and navigates to /g/:gameId", async () => {
    setupAuth(true);
    const user = userEvent.setup();
    renderAt("/games");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /create game/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /create game/i }));
    await waitFor(() => {
      expect(mockCreateGame).toHaveBeenCalledOnce();
      expect(
        screen.getByRole("heading", { name: /game new-game-id/i })
      ).toBeInTheDocument();
    });
  });
});

// --- Game room lobby (US-UI-005) ---------------------------------------------

function makePlayer(id: string): PlayerState {
  return { player_id: id, archetype: null, hand: [], archetype_used: false };
}

describe("game room lobby", () => {
  const waitingGame: GameState = {
    game_id: "game-xyz",
    status: "waiting",
    players: [makePlayer("other-user")],
    state_version: 0,
    round_number: 1,
  };

  it("shows Join button when WAITING and caller is not a participant", async () => {
    setupAuth(true); // user id = "user-123"
    mockGetGame.mockResolvedValue(waitingGame);
    renderAt("/g/game-xyz");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /join game/i })).toBeInTheDocument();
    });
  });

  it("shows blocked message when WAITING, full, and caller is not a participant", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue({
      ...waitingGame,
      players: [makePlayer("other-user"), makePlayer("another-user")],
    });
    renderAt("/g/game-xyz");
    await waitFor(() => {
      expect(screen.getByText(/this game is full/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /join/i })).not.toBeInTheDocument();
  });

  it("does not show Join button when caller is already a participant", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue({
      ...waitingGame,
      players: [makePlayer("user-123")],
    });
    renderAt("/g/game-xyz");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /game game-xyz/i })).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /join/i })).not.toBeInTheDocument();
  });

  it("shows a Copy Link button for the invite link", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(waitingGame);
    renderAt("/g/game-xyz");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /copy link/i })).toBeInTheDocument();
    });
  });

  it("Join button calls joinGame and updates the UI", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(waitingGame);
    const updatedGame: GameState = {
      ...waitingGame,
      players: [makePlayer("other-user"), makePlayer("user-123")],
    };
    mockJoinGame.mockResolvedValue(updatedGame);
    const user = userEvent.setup();
    renderAt("/g/game-xyz");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /join game/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /join game/i }));
    await waitFor(() => {
      expect(mockJoinGame).toHaveBeenCalledWith("game-xyz");
      // Now a participant — no more Join button
      expect(screen.queryByRole("button", { name: /join game/i })).not.toBeInTheDocument();
    });
  });
});

// --- shadcn Button component -------------------------------------------------

describe("Button component", () => {
  it("renders shadcn Button on login page", async () => {
    renderAt("/login");
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /send magic link/i })
      ).toBeInTheDocument();
    });
  });

  it("renders shadcn Buttons on games page when authenticated", async () => {
    setupAuth(true);
    renderAt("/games");
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /create game/i })
      ).toBeInTheDocument();
    });
  });
});
