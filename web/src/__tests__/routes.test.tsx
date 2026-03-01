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
  mockSignInWithPassword,
  mockSignUp,
  mockResetPasswordForEmail,
  mockUpdateUser,
  mockSignOut,
} = vi.hoisted(() => ({
  mockGetSession: vi.fn(),
  mockOnAuthStateChange: vi.fn(),
  mockSignInWithPassword: vi.fn(),
  mockSignUp: vi.fn(),
  mockResetPasswordForEmail: vi.fn(),
  mockUpdateUser: vi.fn(),
  mockSignOut: vi.fn(),
}));

// --- Realtime mock -----------------------------------------------------------
const { mockChannel, mockRemoveChannel, realtimeCbs } = vi.hoisted(() => {
  const realtimeCbs = {
    insertHandler: null as ((() => void) | null),
    statusHandler: null as (((status: string) => void) | null),
  };

  // channelObj supports .on(...).subscribe(...) chaining
  type ChannelObj = { on: ReturnType<typeof vi.fn>; subscribe: ReturnType<typeof vi.fn> };
  const channelObj = {} as ChannelObj;
  channelObj.on = vi.fn().mockImplementation(
    (_event: unknown, _filter: unknown, handler: () => void) => {
      realtimeCbs.insertHandler = handler;
      return channelObj;
    }
  );
  channelObj.subscribe = vi.fn().mockImplementation((handler: (s: string) => void) => {
    realtimeCbs.statusHandler = handler;
    return channelObj;
  });

  return {
    mockChannel: vi.fn().mockReturnValue(channelObj),
    mockRemoveChannel: vi.fn().mockResolvedValue(undefined),
    realtimeCbs,
  };
});

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: mockGetSession,
      onAuthStateChange: mockOnAuthStateChange,
      signInWithPassword: mockSignInWithPassword,
      signUp: mockSignUp,
      resetPasswordForEmail: mockResetPasswordForEmail,
      updateUser: mockUpdateUser,
      signOut: mockSignOut,
    },
    channel: mockChannel,
    removeChannel: mockRemoveChannel,
  },
}));

// --- API mock ----------------------------------------------------------------
const { mockListGames, mockCreateGame, mockGetGame, mockJoinGame, mockLeaveGame, mockPlaceCard, mockSelectArchetype } = vi.hoisted(() => ({
  mockListGames: vi.fn(),
  mockCreateGame: vi.fn(),
  mockGetGame: vi.fn(),
  mockJoinGame: vi.fn(),
  mockLeaveGame: vi.fn(),
  mockPlaceCard: vi.fn(),
  mockSelectArchetype: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  listGames: mockListGames,
  createGame: mockCreateGame,
  getGame: mockGetGame,
  joinGame: mockJoinGame,
  leaveGame: mockLeaveGame,
  placeCard: mockPlaceCard,
  selectArchetype: mockSelectArchetype,
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
  // Reset realtime callbacks so tests don't share state
  realtimeCbs.insertHandler = null;
  realtimeCbs.statusHandler = null;
  // Default: unauthenticated, empty game list
  setupAuth(false);
  mockListGames.mockResolvedValue([]);
  mockCreateGame.mockResolvedValue(makeGame({ game_id: "new-game-id" }));
  mockGetGame.mockResolvedValue(DEFAULT_GAME);
  mockJoinGame.mockResolvedValue(DEFAULT_GAME);
  mockLeaveGame.mockResolvedValue(null);
  mockSelectArchetype.mockResolvedValue(makeGame({ game_id: "abc-123" }));
  // Auth form defaults
  mockSignInWithPassword.mockResolvedValue({ error: null });
  mockSignUp.mockResolvedValue({ error: null });
  mockResetPasswordForEmail.mockResolvedValue({ error: null });
  mockUpdateUser.mockResolvedValue({ error: null });
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

// --- Login form — sign-in (password) -----------------------------------------

describe("login form — sign-in", () => {
  it("renders email and password fields by default", async () => {
    renderAt("/login");
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/you@example.com/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/password/i)).toBeInTheDocument();
    });
  });

  it("calls signInWithPassword with entered credentials", async () => {
    const user = userEvent.setup();
    renderAt("/login");
    await user.type(screen.getByPlaceholderText(/you@example.com/i), "test@example.com");
    await user.type(screen.getByPlaceholderText(/password/i), "secret123");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));
    await waitFor(() => {
      expect(mockSignInWithPassword).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "secret123",
      });
    });
  });

  it("shows error message on sign-in failure", async () => {
    mockSignInWithPassword.mockResolvedValue({ error: { message: "Invalid credentials" } });
    const user = userEvent.setup();
    renderAt("/login");
    await user.type(screen.getByPlaceholderText(/you@example.com/i), "bad@example.com");
    await user.type(screen.getByPlaceholderText(/password/i), "wrong");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });

  it("shows Create an account and Forgot password links", async () => {
    renderAt("/login");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /create an account/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /forgot password/i })).toBeInTheDocument();
    });
  });
});

// --- Login form — sign-up mode -----------------------------------------------

describe("login form — sign-up mode", () => {
  it("switches to sign-up form when Create an account is clicked", async () => {
    const user = userEvent.setup();
    renderAt("/login");
    await waitFor(() => screen.getByRole("button", { name: /create an account/i }));
    await user.click(screen.getByRole("button", { name: /create an account/i }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /create account/i })).toBeInTheDocument();
    });
  });

  it("sign-up form has email and password fields", async () => {
    const user = userEvent.setup();
    renderAt("/login");
    await waitFor(() => screen.getByRole("button", { name: /create an account/i }));
    await user.click(screen.getByRole("button", { name: /create an account/i }));
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/you@example.com/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/password/i)).toBeInTheDocument();
    });
  });

  it("calls signUp with entered credentials and shows confirmation", async () => {
    const user = userEvent.setup();
    renderAt("/login");
    await waitFor(() => screen.getByRole("button", { name: /create an account/i }));
    await user.click(screen.getByRole("button", { name: /create an account/i }));
    await user.type(screen.getByPlaceholderText(/you@example.com/i), "new@example.com");
    await user.type(screen.getByPlaceholderText(/password/i), "newpass123");
    await user.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(mockSignUp).toHaveBeenCalledWith({ email: "new@example.com", password: "newpass123" });
      expect(screen.getByText(/check your email/i)).toBeInTheDocument();
    });
  });

  it("shows error message on sign-up failure", async () => {
    mockSignUp.mockResolvedValue({ error: { message: "Email already in use" } });
    const user = userEvent.setup();
    renderAt("/login");
    await waitFor(() => screen.getByRole("button", { name: /create an account/i }));
    await user.click(screen.getByRole("button", { name: /create an account/i }));
    await user.type(screen.getByPlaceholderText(/you@example.com/i), "dup@example.com");
    await user.type(screen.getByPlaceholderText(/password/i), "pass");
    await user.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText(/email already in use/i)).toBeInTheDocument();
    });
  });

  it("Back to sign in returns to sign-in form", async () => {
    const user = userEvent.setup();
    renderAt("/login");
    await waitFor(() => screen.getByRole("button", { name: /create an account/i }));
    await user.click(screen.getByRole("button", { name: /create an account/i }));
    await waitFor(() => screen.getByRole("button", { name: /back to sign in/i }));
    await user.click(screen.getByRole("button", { name: /back to sign in/i }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /^sign in$/i })).toBeInTheDocument();
    });
  });
});

// --- Login form — forgot password mode ---------------------------------------

describe("login form — forgot password mode", () => {
  it("switches to forgot-password form when Forgot password is clicked", async () => {
    const user = userEvent.setup();
    renderAt("/login");
    await waitFor(() => screen.getByRole("button", { name: /forgot password/i }));
    await user.click(screen.getByRole("button", { name: /forgot password/i }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /reset password/i })).toBeInTheDocument();
    });
  });

  it("forgot-password form has only an email field (no password)", async () => {
    const user = userEvent.setup();
    renderAt("/login");
    await waitFor(() => screen.getByRole("button", { name: /forgot password/i }));
    await user.click(screen.getByRole("button", { name: /forgot password/i }));
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/you@example.com/i)).toBeInTheDocument();
      expect(screen.queryByPlaceholderText(/password/i)).not.toBeInTheDocument();
    });
  });

  it("calls resetPasswordForEmail and shows confirmation", async () => {
    const user = userEvent.setup();
    renderAt("/login");
    await waitFor(() => screen.getByRole("button", { name: /forgot password/i }));
    await user.click(screen.getByRole("button", { name: /forgot password/i }));
    await user.type(screen.getByPlaceholderText(/you@example.com/i), "me@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));
    await waitFor(() => {
      expect(mockResetPasswordForEmail).toHaveBeenCalledWith(
        "me@example.com",
        expect.objectContaining({ redirectTo: expect.stringContaining("/reset-password") })
      );
      expect(screen.getByText(/check your email/i)).toBeInTheDocument();
    });
  });

  it("shows error message when reset email fails", async () => {
    mockResetPasswordForEmail.mockResolvedValue({ error: { message: "User not found" } });
    const user = userEvent.setup();
    renderAt("/login");
    await waitFor(() => screen.getByRole("button", { name: /forgot password/i }));
    await user.click(screen.getByRole("button", { name: /forgot password/i }));
    await user.type(screen.getByPlaceholderText(/you@example.com/i), "nobody@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));
    await waitFor(() => {
      expect(screen.getByText(/user not found/i)).toBeInTheDocument();
    });
  });

  it("Back to sign in returns to sign-in form", async () => {
    const user = userEvent.setup();
    renderAt("/login");
    await waitFor(() => screen.getByRole("button", { name: /forgot password/i }));
    await user.click(screen.getByRole("button", { name: /forgot password/i }));
    await waitFor(() => screen.getByRole("button", { name: /back to sign in/i }));
    await user.click(screen.getByRole("button", { name: /back to sign in/i }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /^sign in$/i })).toBeInTheDocument();
    });
  });
});

// --- Reset password page (/reset-password) -----------------------------------

describe("reset password page", () => {
  function setupPasswordRecovery() {
    // Make onAuthStateChange immediately fire PASSWORD_RECOVERY for all subscribers.
    mockOnAuthStateChange.mockImplementation((cb: (event: string, session: null) => void) => {
      cb("PASSWORD_RECOVERY", null);
      return { data: { subscription: { unsubscribe: vi.fn() } } };
    });
  }

  it("shows verifying state before PASSWORD_RECOVERY event", async () => {
    // onAuthStateChange never fires — component stays in verifying state
    renderAt("/reset-password");
    await waitFor(() => {
      expect(screen.getByText(/verifying reset link/i)).toBeInTheDocument();
    });
  });

  it("shows set-password form after PASSWORD_RECOVERY event", async () => {
    setupPasswordRecovery();
    renderAt("/reset-password");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /set new password/i })).toBeInTheDocument();
      expect(screen.getAllByPlaceholderText(/password/i).length).toBeGreaterThanOrEqual(2);
    });
  });

  it("shows error when passwords do not match", async () => {
    setupPasswordRecovery();
    const user = userEvent.setup();
    renderAt("/reset-password");
    await waitFor(() => screen.getByRole("heading", { name: /set new password/i }));
    const [newPass, confirmPass] = screen.getAllByPlaceholderText(/password/i);
    await user.type(newPass, "hunter2");
    await user.type(confirmPass, "different");
    await user.click(screen.getByRole("button", { name: /set password/i }));
    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
    });
    expect(mockUpdateUser).not.toHaveBeenCalled();
  });

  it("calls updateUser with new password on valid submit", async () => {
    setupPasswordRecovery();
    const user = userEvent.setup();
    renderAt("/reset-password");
    await waitFor(() => screen.getByRole("heading", { name: /set new password/i }));
    const [newPass, confirmPass] = screen.getAllByPlaceholderText(/password/i);
    await user.type(newPass, "newSecret99");
    await user.type(confirmPass, "newSecret99");
    await user.click(screen.getByRole("button", { name: /set password/i }));
    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledWith({ password: "newSecret99" });
    });
  });

  it("shows success message after password is updated", async () => {
    setupPasswordRecovery();
    const user = userEvent.setup();
    renderAt("/reset-password");
    await waitFor(() => screen.getByRole("heading", { name: /set new password/i }));
    const [newPass, confirmPass] = screen.getAllByPlaceholderText(/password/i);
    await user.type(newPass, "newSecret99");
    await user.type(confirmPass, "newSecret99");
    await user.click(screen.getByRole("button", { name: /set password/i }));
    await waitFor(() => {
      expect(screen.getByText(/password updated/i)).toBeInTheDocument();
    });
  });

  it("shows error message when updateUser fails", async () => {
    setupPasswordRecovery();
    mockUpdateUser.mockResolvedValue({ error: { message: "Password too short" } });
    const user = userEvent.setup();
    renderAt("/reset-password");
    await waitFor(() => screen.getByRole("heading", { name: /set new password/i }));
    const [newPass, confirmPass] = screen.getAllByPlaceholderText(/password/i);
    await user.type(newPass, "x");
    await user.type(confirmPass, "x");
    await user.click(screen.getByRole("button", { name: /set password/i }));
    await waitFor(() => {
      expect(screen.getByText(/password too short/i)).toBeInTheDocument();
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

// --- Game room move submission (US-UI-007) ------------------------------------

describe("game room move submission (US-UI-007)", () => {
  const moveGame = makeGame({
    game_id: "game-move",
    status: "active",
    state_version: 5,
    current_player_index: 0,
    players: [
      { player_id: "user-123", archetype: "martial" as const, hand: ["card-a", "card-b"], archetype_used: false },
      { player_id: "other-user", archetype: "devout" as const, hand: ["card-c"], archetype_used: false },
    ],
    board: EMPTY_BOARD,
  });

  it("card buttons are disabled when it is not the caller's turn", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue({ ...moveGame, current_player_index: 1 });
    renderAt("/g/game-move");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "card-a" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "card-b" })).toBeDisabled();
    });
  });

  it("empty cells become clickable buttons after selecting a card on caller's turn", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(moveGame);
    const user = userEvent.setup();
    renderAt("/g/game-move");
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    // Before selection: no cell buttons
    expect(screen.queryByRole("button", { name: /cell 0/i })).not.toBeInTheDocument();
    // Select card-a
    await user.click(screen.getByRole("button", { name: "card-a" }));
    // Now cell 0 should be a clickable button
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /cell 0/i })).toBeInTheDocument();
    });
  });

  it("clicking an empty cell with a selected card calls placeCard", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(moveGame);
    mockPlaceCard.mockResolvedValue({ ...moveGame, current_player_index: 1 });
    const user = userEvent.setup();
    renderAt("/g/game-move");
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));
    await waitFor(() => {
      expect(mockPlaceCard).toHaveBeenCalledWith(
        "game-move",
        "card-a",
        0,
        5,
        expect.any(String)
      );
    });
  });

  it("updates the game snapshot after a successful move", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(moveGame);
    const updatedBoard: (BoardCell | null)[] = [...EMPTY_BOARD];
    updatedBoard[0] = { card_key: "card-a", owner: 0 };
    const updatedGame: GameState = { ...moveGame, board: updatedBoard, current_player_index: 1 };
    mockPlaceCard.mockResolvedValue(updatedGame);
    const user = userEvent.setup();
    renderAt("/g/game-move");
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));
    await waitFor(() => {
      expect(screen.getByText(/opponent.?s turn/i)).toBeInTheDocument();
    });
  });

  it("shows move error on 409 conflict and refetches game", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(moveGame);
    mockPlaceCard.mockRejectedValue(
      Object.assign(new Error("State version conflict"), { status: 409 })
    );
    const user = userEvent.setup();
    renderAt("/g/game-move");
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));
    await waitFor(() => {
      expect(screen.getByText(/state version conflict/i)).toBeInTheDocument();
    });
    // mount call + refetch on error = 2 calls
    expect(mockGetGame).toHaveBeenCalledTimes(2);
  });

  it("shows move error on 422 invalid move and refetches game", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(moveGame);
    mockPlaceCard.mockRejectedValue(
      Object.assign(new Error("Cell is already occupied"), { status: 422 })
    );
    const user = userEvent.setup();
    renderAt("/g/game-move");
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));
    await waitFor(() => {
      expect(screen.getByText(/cell is already occupied/i)).toBeInTheDocument();
    });
    expect(mockGetGame).toHaveBeenCalledTimes(2);
  });
});

// --- Archetype selection UX (US-UI-008) --------------------------------------

describe("archetype selection UX (US-UI-008)", () => {
  const noArchGame = makeGame({
    game_id: "game-arch",
    status: "active",
    state_version: 2,
    current_player_index: 0,
    players: [
      { player_id: "user-123", archetype: null, hand: ["card-a"], archetype_used: false },
      { player_id: "other-user", archetype: null, hand: ["card-c"], archetype_used: false },
    ],
    board: EMPTY_BOARD,
  });

  it("shows archetype selector when caller has no archetype", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(noArchGame);
    renderAt("/g/game-arch");
    await waitFor(() => {
      expect(screen.getByText(/choose your archetype/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /martial/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /skulker/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /caster/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /devout/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /presence/i })).toBeInTheDocument();
    });
  });

  it("selecting an archetype calls selectArchetype and updates the game", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(noArchGame);
    const updatedGame = makeGame({
      ...noArchGame,
      players: [
        { player_id: "user-123", archetype: "martial", hand: ["card-a"], archetype_used: false },
        { player_id: "other-user", archetype: null, hand: ["card-c"], archetype_used: false },
      ],
    });
    mockSelectArchetype.mockResolvedValue(updatedGame);
    const user = userEvent.setup();
    renderAt("/g/game-arch");
    await waitFor(() => screen.getByRole("button", { name: /martial/i }));
    await user.click(screen.getByRole("button", { name: /martial/i }));
    await waitFor(() => {
      expect(mockSelectArchetype).toHaveBeenCalledWith("game-arch", "martial");
      // Selector gone after archetype chosen
      expect(screen.queryByText(/choose your archetype/i)).not.toBeInTheDocument();
    });
  });

  it("does not show archetype selector when caller already has an archetype", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makeGame({
      ...noArchGame,
      players: [
        { player_id: "user-123", archetype: "devout", hand: ["card-a"], archetype_used: false },
        { player_id: "other-user", archetype: null, hand: ["card-c"], archetype_used: false },
      ],
    }));
    renderAt("/g/game-arch");
    await waitFor(() => {
      expect(screen.getByText(/your turn/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/choose your archetype/i)).not.toBeInTheDocument();
  });

  it("shows archetype power as Available when not yet used", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makeGame({
      ...noArchGame,
      players: [
        { player_id: "user-123", archetype: "caster", hand: ["card-a"], archetype_used: false },
        { player_id: "other-user", archetype: null, hand: ["card-c"], archetype_used: false },
      ],
    }));
    renderAt("/g/game-arch");
    await waitFor(() => {
      expect(screen.getByText(/caster/i)).toBeInTheDocument();
      expect(screen.getByText(/available/i)).toBeInTheDocument();
    });
  });

  it("shows archetype power as Used when already used", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makeGame({
      ...noArchGame,
      players: [
        { player_id: "user-123", archetype: "skulker", hand: ["card-a"], archetype_used: true },
        { player_id: "other-user", archetype: null, hand: ["card-c"], archetype_used: false },
      ],
    }));
    renderAt("/g/game-arch");
    await waitFor(() => {
      expect(screen.getByText(/skulker/i)).toBeInTheDocument();
      expect(screen.getAllByText(/used/i).length).toBeGreaterThan(0);
    });
  });
});

// --- Archetype power UX (US-UI-009) ------------------------------------------

describe("archetype power UX (US-UI-009)", () => {
  const makePowerGame = (archetype: PlayerState["archetype"], archetypeUsed = false) =>
    makeGame({
      game_id: "game-power",
      status: "active",
      state_version: 5,
      current_player_index: 0,
      players: [
        { player_id: "user-123", archetype, hand: ["card-a"], archetype_used: archetypeUsed },
        { player_id: "other-user", archetype: "caster" as const, hand: ["card-c"], archetype_used: false },
      ],
      board: EMPTY_BOARD,
    });

  it("shows Use Power toggle when caller has unused archetype on their turn", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makePowerGame("martial"));
    renderAt("/g/game-power");
    await waitFor(() => {
      expect(screen.getByRole("checkbox", { name: /use power/i })).toBeInTheDocument();
    });
  });

  it("does not show Use Power toggle when archetype is already used", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makePowerGame("martial", true));
    renderAt("/g/game-power");
    await waitFor(() => {
      expect(screen.getByText(/your turn/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole("checkbox", { name: /use power/i })).not.toBeInTheDocument();
  });

  it("skulker: shows side selector (n/e/s/w) after Use Power is toggled", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makePowerGame("skulker"));
    const user = userEvent.setup();
    renderAt("/g/game-power");
    await waitFor(() => screen.getByRole("checkbox", { name: /use power/i }));
    await user.click(screen.getByRole("checkbox", { name: /use power/i }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^n$/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /^e$/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /^s$/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /^w$/i })).toBeInTheDocument();
    });
  });

  it("presence: shows direction selector (n/e/s/w) after Use Power is toggled", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makePowerGame("presence"));
    const user = userEvent.setup();
    renderAt("/g/game-power");
    await waitFor(() => screen.getByRole("checkbox", { name: /use power/i }));
    await user.click(screen.getByRole("checkbox", { name: /use power/i }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^n$/i })).toBeInTheDocument();
    });
  });

  it("submits move with use_archetype=true and no extra params for martial", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makePowerGame("martial"));
    mockPlaceCard.mockResolvedValue(makePowerGame("martial"));
    const user = userEvent.setup();
    renderAt("/g/game-power");
    await waitFor(() => screen.getByRole("checkbox", { name: /use power/i }));
    await user.click(screen.getByRole("checkbox", { name: /use power/i }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));
    await waitFor(() => {
      expect(mockPlaceCard).toHaveBeenCalledWith(
        "game-power", "card-a", 0, 5, expect.any(String),
        { useArchetype: true, skulkerBoostSide: undefined, presenceBoostDirection: undefined }
      );
    });
  });

  it("submits move with skulker_boost_side when skulker power used with side selected", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(makePowerGame("skulker"));
    mockPlaceCard.mockResolvedValue(makePowerGame("skulker"));
    const user = userEvent.setup();
    renderAt("/g/game-power");
    await waitFor(() => screen.getByRole("checkbox", { name: /use power/i }));
    await user.click(screen.getByRole("checkbox", { name: /use power/i }));
    await waitFor(() => screen.getByRole("button", { name: /^n$/i }));
    await user.click(screen.getByRole("button", { name: /^n$/i }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));
    await waitFor(() => {
      expect(mockPlaceCard).toHaveBeenCalledWith(
        "game-power", "card-a", 0, 5, expect.any(String),
        { useArchetype: true, skulkerBoostSide: "n", presenceBoostDirection: undefined }
      );
    });
  });
});

// --- Realtime subscription (US-UI-010) ---------------------------------------

describe("realtime subscription (US-UI-010)", () => {
  const rtGame = makeGame({
    game_id: "game-rt",
    status: "active",
    state_version: 3,
    players: [
      { player_id: "user-123", archetype: null, hand: ["card-a"], archetype_used: false },
      { player_id: "other-user", archetype: null, hand: ["card-b"], archetype_used: false },
    ],
    board: EMPTY_BOARD,
    current_player_index: 0,
  });

  it("subscribes to Supabase Realtime channel on mount", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(rtGame);
    renderAt("/g/game-rt");

    await waitFor(() => {
      expect(mockChannel).toHaveBeenCalledWith("game:game-rt");
    });
  });

  it("refetches game snapshot when INSERT event fires", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(rtGame);
    renderAt("/g/game-rt");

    await waitFor(() => {
      expect(realtimeCbs.insertHandler).not.toBeNull();
    });

    // initial load = 1 call; simulate INSERT event
    realtimeCbs.insertHandler!();

    await waitFor(() => {
      expect(mockGetGame).toHaveBeenCalledTimes(2);
    });
  });

  it("removes the channel on unmount", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(rtGame);
    const { unmount } = renderAt("/g/game-rt");

    await waitFor(() => {
      expect(mockChannel).toHaveBeenCalled();
    });

    unmount();

    expect(mockRemoveChannel).toHaveBeenCalled();
  });

  it("starts fallback polling interval when channel status is CLOSED", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(rtGame);
    renderAt("/g/game-rt");

    await waitFor(() => {
      expect(realtimeCbs.statusHandler).not.toBeNull();
    });

    vi.useFakeTimers();
    try {
      realtimeCbs.statusHandler!("CLOSED");
      // Advance 30 seconds — fallback interval should fire
      vi.advanceTimersByTime(30_000);
      // getGame was called once on mount; now at least once more via interval
      expect(mockGetGame.mock.calls.length).toBeGreaterThanOrEqual(2);
    } finally {
      vi.useRealTimers();
    }
  });
});

// --- Effects: Mists + Captures + End-game banner (US-UI-011) -----------------

describe("effects (US-UI-011)", () => {
  const effectsGame = makeGame({
    game_id: "game-fx",
    status: "active",
    state_version: 4,
    current_player_index: 0,
    players: [
      { player_id: "user-123", archetype: "martial" as const, hand: ["card-a"], archetype_used: false },
      { player_id: "other-user", archetype: "devout" as const, hand: ["card-c", "card-d"], archetype_used: false },
    ],
    board: [
      { card_key: "card-x", owner: 1 } as BoardCell,
      { card_key: "card-y", owner: 1 } as BoardCell,
      null, null, null, null, null, null, null,
    ],
  });

  it("shows Fog mists banner when last_move has mists_effect fog", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue({ ...effectsGame, last_move: { mists_roll: 1, mists_effect: "fog" } });
    renderAt("/g/game-fx");
    await waitFor(() => {
      expect(screen.getByLabelText(/mists feedback/i)).toBeInTheDocument();
      expect(screen.getByText(/fog/i)).toBeInTheDocument();
    });
  });

  it("shows Omen mists banner when last_move has mists_effect omen", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue({ ...effectsGame, last_move: { mists_roll: 6, mists_effect: "omen" } });
    renderAt("/g/game-fx");
    await waitFor(() => {
      expect(screen.getByLabelText(/mists feedback/i)).toBeInTheDocument();
      expect(screen.getByText(/omen/i)).toBeInTheDocument();
    });
  });

  it("shows the mists roll number in the banner", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue({ ...effectsGame, last_move: { mists_roll: 4, mists_effect: "none" } });
    renderAt("/g/game-fx");
    await waitFor(() => {
      expect(screen.getByLabelText(/mists feedback/i)).toBeInTheDocument();
      // Roll number 4 should appear in the Mists banner text
      expect(screen.getByText(/roll.*4/i)).toBeInTheDocument();
    });
  });

  it("does not show mists banner when last_move is null", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue({ ...effectsGame, last_move: null });
    renderAt("/g/game-fx");
    await waitFor(() => {
      expect(screen.getByText(/your turn/i)).toBeInTheDocument();
    });
    expect(screen.queryByLabelText(/mists feedback/i)).not.toBeInTheDocument();
  });

  it("shows combo indicator when 2+ cells are captured in one move", async () => {
    setupAuth(true);
    mockGetGame.mockResolvedValue(effectsGame);

    // After placing card-a at cell 2, cells 0+1 flip to caller
    const capturedBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 0 },
      { card_key: "card-y", owner: 0 },
      { card_key: "card-a", owner: 0 },
      null, null, null, null, null, null,
    ];
    mockPlaceCard.mockResolvedValue({ ...effectsGame, board: capturedBoard, current_player_index: 1 });

    const user = userEvent.setup();
    renderAt("/g/game-fx");
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 2/i }));
    await user.click(screen.getByRole("button", { name: /cell 2/i }));

    await waitFor(() => {
      expect(screen.getByText(/combo/i)).toBeInTheDocument();
    });
  });

  it("does not show combo indicator for a single capture", async () => {
    setupAuth(true);
    // Initial board: only cell 0 owned by opponent
    const singleCaptureGame = makeGame({
      ...effectsGame,
      board: [
        { card_key: "card-x", owner: 1 } as BoardCell,
        null, null, null, null, null, null, null, null,
      ],
    });
    mockGetGame.mockResolvedValue(singleCaptureGame);

    const singleCaptureBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 0 },  // captured
      { card_key: "card-a", owner: 0 },  // placed
      null, null, null, null, null, null, null,
    ];
    mockPlaceCard.mockResolvedValue({ ...singleCaptureGame, board: singleCaptureBoard, current_player_index: 1 });

    const user = userEvent.setup();
    renderAt("/g/game-fx");
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 1/i }));
    await user.click(screen.getByRole("button", { name: /cell 1/i }));

    await waitFor(() => {
      // After move, board updated — verify no combo text
      expect(screen.getByText(/opponent.?s turn/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/combo/i)).not.toBeInTheDocument();
  });
});

// --- shadcn Button component -------------------------------------------------

describe("Button component", () => {
  it("renders shadcn Button on login page", async () => {
    renderAt("/login");
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /^sign in$/i })
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
