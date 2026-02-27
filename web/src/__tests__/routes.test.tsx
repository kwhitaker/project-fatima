import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi, beforeEach, describe, it, expect } from "vitest";
import App from "../App";
import type { BoardCell, GameState, PlayerState } from "@/lib/api";

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
const { mockListGames, mockCreateGame, mockGetGame, mockJoinGame, mockLeaveGame } = vi.hoisted(() => ({
  mockListGames: vi.fn(),
  mockCreateGame: vi.fn(),
  mockGetGame: vi.fn(),
  mockJoinGame: vi.fn(),
  mockLeaveGame: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  listGames: mockListGames,
  createGame: mockCreateGame,
  getGame: mockGetGame,
  joinGame: mockJoinGame,
  leaveGame: mockLeaveGame,
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

const EMPTY_BOARD: (BoardCell | null)[] = Array(9).fill(null);

function makeGame(overrides: Partial<GameState> = {}): GameState {
  return {
    game_id: "abc-123",
    status: "waiting",
    players: [],
    board: EMPTY_BOARD,
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 0,
    round_number: 1,
    result: null,
    ...overrides,
  };
}

const DEFAULT_GAME = makeGame();

beforeEach(() => {
  vi.clearAllMocks();
  // Default: unauthenticated, empty game list
  setupAuth(false);
  mockListGames.mockResolvedValue([]);
  mockCreateGame.mockResolvedValue(makeGame({ game_id: "new-game-id" }));
  mockGetGame.mockResolvedValue(DEFAULT_GAME);
  mockJoinGame.mockResolvedValue(DEFAULT_GAME);
  mockLeaveGame.mockResolvedValue(null);
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
      makeGame({ game_id: "game-aaa", status: "waiting" }),
      makeGame({ game_id: "game-bbb", status: "active", state_version: 3 }),
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
      makeGame({ game_id: "game-ccc" }),
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
  const waitingGame = makeGame({
    game_id: "game-xyz",
    status: "waiting",
    players: [makePlayer("other-user")],
  });

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
    const updatedGame = makeGame({
      game_id: "game-xyz",
      status: "waiting",
      players: [makePlayer("other-user"), makePlayer("user-123")],
    });
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

// --- Game room active state (US-UI-006) --------------------------------------

describe("game room active state", () => {
  const activeGame = makeGame({
    game_id: "game-active",
    status: "active",
    state_version: 5,
    current_player_index: 0,
    players: [
      { player_id: "user-123", archetype: "martial", hand: ["card-a", "card-b"], archetype_used: false },
      { player_id: "other-user", archetype: "devout", hand: ["card-c", "card-d"], archetype_used: true },
    ],
    board: [
      { card_key: "card-x", owner: 0 },
      null, null, null, null, null, null, null, null,
    ],
  });

  it("renders the 3x3 board (9 cells) when ACTIVE", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(activeGame);
    renderAt("/g/game-active");
    await waitFor(() => {
      expect(screen.getByLabelText(/game board/i)).toBeInTheDocument();
    });
    const board = screen.getByLabelText(/game board/i);
    expect(board.children).toHaveLength(9);
  });

  it("shows the caller's hand as selectable card buttons", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(activeGame);
    renderAt("/g/game-active");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "card-a" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "card-b" })).toBeInTheDocument();
    });
  });

  it("shows the opponent's hand as a card count", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(activeGame);
    renderAt("/g/game-active");
    await waitFor(() => {
      expect(screen.getByText(/2 cards/i)).toBeInTheDocument();
    });
  });

  it("shows 'Your turn' when current_player_index matches caller's index", async () => {
    setupAuth(true); // user-123 is player index 0
    mockGetGame.mockResolvedValue(activeGame); // current_player_index: 0
    renderAt("/g/game-active");
    await waitFor(() => {
      expect(screen.getByText(/your turn/i)).toBeInTheDocument();
    });
  });

  it("shows 'Opponent's turn' when it is not the caller's turn", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makeGame({
      ...activeGame,
      current_player_index: 1,
    }));
    renderAt("/g/game-active");
    await waitFor(() => {
      expect(screen.getByText(/opponent.?s turn/i)).toBeInTheDocument();
    });
  });

  it("shows both archetype states", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(activeGame);
    renderAt("/g/game-active");
    await waitFor(() => {
      expect(screen.getByText(/martial/i)).toBeInTheDocument();
      expect(screen.getByText(/devout/i)).toBeInTheDocument();
    });
  });

  it("shows current score for each player", async () => {
    setupAuth(true);
    // Board has 1 cell owned by player 0 (user-123)
    mockGetGame.mockResolvedValue(activeGame);
    renderAt("/g/game-active");
    await waitFor(() => {
      // Score section should be visible
      expect(screen.getByText(/score/i)).toBeInTheDocument();
    });
  });

  it("Leave button calls leaveGame and navigates to /games", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(activeGame);
    mockLeaveGame.mockResolvedValue(null);
    const user = userEvent.setup();
    renderAt("/g/game-active");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /leave/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /leave/i }));
    await waitFor(() => {
      expect(mockLeaveGame).toHaveBeenCalledWith("game-active", 5);
      expect(screen.getByRole("heading", { name: /my games/i })).toBeInTheDocument();
    });
  });
});

// --- Game room complete state (US-UI-006) ------------------------------------

describe("game room complete state", () => {
  it("shows 'You win!' banner when caller wins", async () => {
    setupAuth(true); // user-123 is player index 0
    mockGetGame.mockResolvedValue(makeGame({
      game_id: "game-done",
      status: "complete",
      state_version: 9,
      players: [
        { player_id: "user-123", archetype: null, hand: [], archetype_used: false },
        { player_id: "other-user", archetype: null, hand: [], archetype_used: false },
      ],
      result: { winner: 0, is_draw: false },
    }));
    renderAt("/g/game-done");
    await waitFor(() => {
      expect(screen.getByText(/you win/i)).toBeInTheDocument();
    });
  });

  it("shows 'You lose!' banner when opponent wins", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makeGame({
      game_id: "game-done",
      status: "complete",
      state_version: 9,
      players: [
        { player_id: "user-123", archetype: null, hand: [], archetype_used: false },
        { player_id: "other-user", archetype: null, hand: [], archetype_used: false },
      ],
      result: { winner: 1, is_draw: false },
    }));
    renderAt("/g/game-done");
    await waitFor(() => {
      expect(screen.getByText(/you lose/i)).toBeInTheDocument();
    });
  });

  it("shows 'Draw!' banner on draw", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makeGame({
      game_id: "game-done",
      status: "complete",
      state_version: 9,
      players: [
        { player_id: "user-123", archetype: null, hand: [], archetype_used: false },
        { player_id: "other-user", archetype: null, hand: [], archetype_used: false },
      ],
      result: { winner: null, is_draw: true },
    }));
    renderAt("/g/game-done");
    await waitFor(() => {
      expect(screen.getByText(/draw/i)).toBeInTheDocument();
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
