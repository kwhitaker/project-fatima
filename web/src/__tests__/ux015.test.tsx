/**
 * US-UX-015: Accessibility and interaction polish pass
 *
 * Covers:
 * - Board empty cells have focus-visible ring classes (keyboard navigable)
 * - Occupied board cells (inspect) have focus-visible ring classes
 * - Hand card selection buttons have focus-visible ring classes
 * - Hand card inspect icon buttons have focus-visible ring classes
 * - Game list buttons have focus-visible ring classes
 * - Login mode-switch buttons have focus-visible ring classes
 * - Login error text has dark mode variant (dark:text-red-400)
 * - All interactive GameRoom elements use <button> elements (keyboard operable)
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import GameRoom from "../routes/GameRoom";
import Games from "../routes/Games";
import Login from "../routes/Login";
import type { BoardCell, CardDefinition, GameState } from "@/lib/api";

// mockSignIn is prefixed with "mock" so vitest hoisting allows it in the factory below
const mockSignIn = vi.fn();

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "player-1" },
    session: null,
    signIn: mockSignIn,
    signUp: vi.fn(),
    resetPasswordForEmail: vi.fn(),
    signOut: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  getGame: vi.fn(),
  joinGame: vi.fn(),
  leaveGame: vi.fn(),
  placeCard: vi.fn(),
  selectArchetype: vi.fn(),
  getCardDefinitions: vi.fn(),
  listGames: vi.fn(),
  createGame: vi.fn(),
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

const { getGame, getCardDefinitions, listGames } = await import("@/lib/api");

// ── Fixtures ──────────────────────────────────────────────────────────────────

const CARD_DEFS = new Map<string, CardDefinition>([
  [
    "card_001",
    { card_key: "card_001", name: "Barovia Guard", version: "v1", sides: { n: 4, e: 5, s: 3, w: 2 } },
  ],
  [
    "card_002",
    { card_key: "card_002", name: "Night Hag", version: "v1", sides: { n: 7, e: 3, s: 8, w: 1 } },
  ],
]);

const BOARD_MIXED: (BoardCell | null)[] = [
  { card_key: "card_002", owner: 1 }, // occupied — opponent
  null, // empty
  null,
  null,
  null,
  null,
  null,
  null,
  null,
];

function makeActiveGame(): GameState {
  return {
    game_id: "game-ux015",
    status: "active",
    players: [
      { player_id: "player-1", email: "me@example.com", archetype: "martial", hand: ["card_001"], archetype_used: false },
      { player_id: "player-2", email: "opp@example.com", archetype: "devout", hand: ["card_002"], archetype_used: false },
    ],
    board: BOARD_MIXED,
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 2,
    round_number: 1,
    result: null,
    last_move: null,
  };
}

function makeGamesList(): GameState[] {
  return [
    {
      game_id: "aaaa-bbbb-cccc-dddd",
      status: "active",
      players: [
        { player_id: "player-1", email: "me@example.com", archetype: null, hand: [], archetype_used: false },
        { player_id: "player-2", email: "opp@example.com", archetype: null, hand: [], archetype_used: false },
      ],
      board: Array(9).fill(null),
      current_player_index: 0,
      starting_player_index: 0,
      state_version: 1,
      round_number: 1,
      result: null,
      last_move: null,
    },
  ];
}

function renderGameRoom() {
  render(
    <MemoryRouter initialEntries={["/g/game-ux015"]}>
      <Routes>
        <Route path="/g/:gameId" element={<GameRoom />} />
      </Routes>
    </MemoryRouter>
  );
}

function renderGames() {
  render(
    <MemoryRouter initialEntries={["/games"]}>
      <Routes>
        <Route path="/games" element={<Games />} />
      </Routes>
    </MemoryRouter>
  );
}

function renderLogin() {
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getCardDefinitions).mockResolvedValue(CARD_DEFS);
  // Default: signIn succeeds (no error)
  mockSignIn.mockResolvedValue({ error: null });
});

// ── GameRoom: board cell focus styles ─────────────────────────────────────────

describe("US-UX-015: GameRoom board cells have focus-visible styles", () => {
  it("empty board cell button has focus-visible:ring-2 class", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();
    await screen.findByText(/your turn/i);

    // Select a card first — empty cells only become <button> when canPlace is true
    const cardBtn = screen
      .getAllByRole("button", { name: /barovia guard/i })
      .find((b) => b.hasAttribute("aria-pressed"));
    await userEvent.click(cardBtn!);

    const cell1 = screen.getByRole("button", { name: /cell 1/i });
    expect(cell1.className).toContain("focus-visible:ring-2");
  });

  it("occupied board cell inspect button has focus-visible:ring-2 class", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();
    await screen.findByText(/your turn/i);

    // Board cell 0 is occupied by Night Hag — renders as an inspect button
    const inspectCell = screen.getByRole("button", { name: /inspect night hag/i });
    expect(inspectCell.className).toContain("focus-visible:ring-2");
  });
});

// ── GameRoom: hand card buttons focus styles ───────────────────────────────────

describe("US-UX-015: GameRoom hand card buttons have focus-visible styles", () => {
  it("hand card selection button has focus-visible:ring-2 class", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();
    await screen.findByText(/your turn/i);

    const cardBtn = screen
      .getAllByRole("button", { name: /barovia guard/i })
      .find((b) => b.hasAttribute("aria-pressed"));
    expect(cardBtn).toBeTruthy();
    expect(cardBtn!.className).toContain("focus-visible:ring-2");
  });

  it("hand card inspect icon button has focus-visible:ring-2 class", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();
    await screen.findByText(/your turn/i);

    const inspectBtn = screen.getByRole("button", { name: /inspect barovia guard/i });
    expect(inspectBtn.className).toContain("focus-visible:ring-2");
  });
});

// ── Games: game list button focus styles ──────────────────────────────────────

describe("US-UX-015: Games list button has focus-visible styles", () => {
  it("game list row button has focus-visible:ring-2 class", async () => {
    vi.mocked(listGames).mockResolvedValue(makeGamesList());
    renderGames();

    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });

    const rowLink = screen.getByRole("link", { name: /opp@example\.com/i });
    expect(rowLink.className).toContain("focus-visible:ring-2");
  });
});

// ── Login: mode-switch buttons focus styles ────────────────────────────────────

describe("US-UX-015: Login mode-switch buttons have focus-visible styles", () => {
  it("'Create an account' button has focus-visible:ring-2 class", () => {
    renderLogin();
    const btn = screen.getByRole("button", { name: /create an account/i });
    expect(btn.className).toContain("focus-visible:ring-2");
  });

  it("'Forgot password?' button has focus-visible:ring-2 class", () => {
    renderLogin();
    const btn = screen.getByRole("button", { name: /forgot password\?/i });
    expect(btn.className).toContain("focus-visible:ring-2");
  });

  it("'Back to sign in' button (in signup mode) has focus-visible:ring-2 class", async () => {
    renderLogin();
    await userEvent.click(screen.getByRole("button", { name: /create an account/i }));
    const backBtn = screen.getByRole("button", { name: /back to sign in/i });
    expect(backBtn.className).toContain("focus-visible:ring-2");
  });
});

// ── Login: dark mode contrast ─────────────────────────────────────────────────

describe("US-UX-015: Login text has dark mode contrast variants", () => {
  it("error text shows with dark:text-red-400 class after failed sign in", async () => {
    mockSignIn.mockResolvedValue({ error: new Error("Invalid credentials") });
    renderLogin();

    await userEvent.type(screen.getByPlaceholderText(/you@example\.com/i), "test@test.com");
    await userEvent.type(screen.getByPlaceholderText(/password/i), "wrongpass");
    await userEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    await waitFor(() => {
      const errEl = screen.getByText(/invalid credentials/i);
      expect(errEl.className).toContain("dark:text-red-400");
    });
  });
});

// ── All GameRoom interactives are <button> elements ───────────────────────────

describe("US-UX-015: GameRoom interactive elements are keyboard-operable <button> elements", () => {
  it("interactive board cells render as <button> elements", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();
    await screen.findByText(/your turn/i);

    // Select a card first so empty cells become <button> (canPlace requires selectedCard)
    const cardBtn = screen
      .getAllByRole("button", { name: /barovia guard/i })
      .find((b) => b.hasAttribute("aria-pressed"));
    await userEvent.click(cardBtn!);

    // Empty cell should be <button>
    const emptyCell = screen.getByRole("button", { name: /cell 1/i });
    expect(emptyCell.tagName).toBe("BUTTON");

    // Occupied cell inspect should be <button>
    const occupiedCell = screen.getByRole("button", { name: /inspect night hag/i });
    expect(occupiedCell.tagName).toBe("BUTTON");
  });
});
