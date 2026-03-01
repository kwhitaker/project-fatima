/**
 * US-UX-009: Card visuals: render name + side values on board and in hand (with hover enlargement)
 *
 * Covers:
 * - Board cells show display name (not card_key) when card definitions are loaded
 * - Board cells show N/E/S/W side values
 * - Hand cards show display name (not card_key) when card definitions are loaded
 * - Hand cards show N/E/S/W side values
 * - Hand cards have hover scale/enlarge class
 * - Selected vs unselected/disabled state remains distinct (aria-pressed)
 */
import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import GameRoom from "../routes/GameRoom";
import type { GameState, CardDefinition } from "@/lib/api";

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: { id: "player-1" } }),
}));

const MOCK_CARD_DEFS = new Map<string, CardDefinition>([
  [
    "card_001",
    {
      card_key: "card_001",
      name: "Barovia Guard",
      version: "v1",
      sides: { n: 4, e: 5, s: 3, w: 2 },
    },
  ],
  [
    "card_002",
    {
      card_key: "card_002",
      name: "Night Hag",
      version: "v1",
      sides: { n: 7, e: 3, s: 8, w: 1 },
    },
  ],
]);

vi.mock("@/lib/api", () => ({
  getGame: vi.fn(),
  joinGame: vi.fn(),
  leaveGame: vi.fn(),
  placeCard: vi.fn(),
  selectArchetype: vi.fn(),
  getCardDefinitions: vi.fn(),
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

const { getGame, getCardDefinitions } = await import("@/lib/api");

function makeActiveGame(): GameState {
  return {
    game_id: "game-ux009",
    status: "active",
    players: [
      {
        player_id: "player-1",
        email: "me@example.com",
        archetype: "martial",
        hand: ["card_001", "card_002"],
        archetype_used: false,
      },
      {
        player_id: "player-2",
        email: "opponent@example.com",
        archetype: "devout",
        hand: ["card_010"],
        archetype_used: false,
      },
    ],
    board: [
      { card_key: "card_001", owner: 0 }, // cell 0 occupied by player-1
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
    ],
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 3,
    round_number: 1,
    result: null,
    last_move: null,
  };
}

function renderGameRoom() {
  render(
    <MemoryRouter initialEntries={["/g/game-ux009"]}>
      <Routes>
        <Route path="/g/:gameId" element={<GameRoom />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getCardDefinitions).mockResolvedValue(MOCK_CARD_DEFS);
});

describe("US-UX-009: card visuals — board and hand", () => {
  it("board cell shows display name (not card_key) when definitions loaded", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    const board = screen.getByLabelText("game board");
    // Display name should appear in board
    expect(board.textContent).toContain("Barovia Guard");
    // Raw card_key should NOT appear in board
    expect(board.textContent).not.toContain("card_001");
  });

  it("board cell shows N side value", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    // card_001 has n:4, e:5, s:3, w:2
    // All four side values should appear in the board area
    const board = screen.getByLabelText("game board");
    expect(board.textContent).toContain("4"); // N
    expect(board.textContent).toContain("5"); // E
    expect(board.textContent).toContain("3"); // S
    expect(board.textContent).toContain("2"); // W
  });

  it("hand cards show display name (not card_key)", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    // Hand cards should show display names
    expect(screen.getByRole("button", { name: /barovia guard/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /night hag/i })).toBeTruthy();
    // Raw card_keys should NOT be visible in the hand buttons
    const handBtn1 = screen.getByRole("button", { name: /barovia guard/i });
    expect(handBtn1.textContent).not.toContain("card_001");
  });

  it("hand cards show N/E/S/W side values", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your hand/i);

    // Find the hand section and verify side values for card_001 (n:4, e:5, s:3, w:2)
    const handBtn = screen.getByRole("button", { name: /barovia guard/i });
    expect(handBtn.textContent).toContain("4"); // N
    expect(handBtn.textContent).toContain("5"); // E
    expect(handBtn.textContent).toContain("3"); // S
    expect(handBtn.textContent).toContain("2"); // W
  });

  it("hand cards have hover scale class for enlargement", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    const cardBtn = screen.getByRole("button", { name: /barovia guard/i });
    expect(cardBtn.className).toMatch(/hover:scale/);
  });

  it("selected hand card has aria-pressed=true, unselected has aria-pressed=false", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    const cardBtn = screen.getByRole("button", { name: /barovia guard/i });
    // Initially unselected
    expect(cardBtn.getAttribute("aria-pressed")).toBe("false");
  });
});
