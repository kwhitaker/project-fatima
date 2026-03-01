/**
 * US-UX-012: Last move highlight + text callout in game room
 *
 * Covers:
 * - Callout shows "Opponent played <Name>" when last_move.player_index is opponent
 * - Callout shows "You played <Name>" when last_move.player_index is the viewer (my index)
 * - No callout when last_move is null
 * - Last placed cell has a data-last-move attribute for highlight
 * - Callout uses display name from card definitions (not raw card_key)
 * - Callout has dark mode classes for readability
 */
import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import GameRoom from "../routes/GameRoom";
import type { BoardCell, CardDefinition, GameState } from "@/lib/api";

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: { id: "player-1" } }),
}));

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

const MOCK_CARD_DEFS = new Map<string, CardDefinition>([
  [
    "card_shadow",
    {
      card_key: "card_shadow",
      name: "Shadow Wraith",
      version: "v1",
      sides: { n: 5, e: 3, s: 7, w: 2 },
    },
  ],
  [
    "card_knight",
    {
      card_key: "card_knight",
      name: "Dark Knight",
      version: "v1",
      sides: { n: 8, e: 4, s: 2, w: 6 },
    },
  ],
]);

const BOARD_WITH_MOVE: (BoardCell | null)[] = [
  { card_key: "card_shadow", owner: 1 }, // opponent placed at cell 0
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
];

function makeGameWithLastMove(playerIndex: 0 | 1, cardKey: string, cellIndex: number): GameState {
  return {
    game_id: "game-ux012",
    status: "active",
    players: [
      {
        player_id: "player-1",
        email: "me@example.com",
        archetype: "martial",
        hand: ["card_knight"],
        archetype_used: false,
      },
      {
        player_id: "player-2",
        email: "opponent@example.com",
        archetype: "devout",
        hand: [],
        archetype_used: false,
      },
    ],
    board: BOARD_WITH_MOVE,
    current_player_index: playerIndex === 0 ? 1 : 0, // next player's turn
    starting_player_index: 0,
    state_version: 2,
    round_number: 1,
    result: null,
    last_move: {
      player_index: playerIndex,
      card_key: cardKey,
      cell_index: cellIndex,
      mists_roll: 3,
      mists_effect: "none",
    },
  };
}

function makeGameNoLastMove(): GameState {
  return {
    game_id: "game-ux012",
    status: "active",
    players: [
      {
        player_id: "player-1",
        email: "me@example.com",
        archetype: "martial",
        hand: ["card_knight"],
        archetype_used: false,
      },
      {
        player_id: "player-2",
        email: "opponent@example.com",
        archetype: "devout",
        hand: [],
        archetype_used: false,
      },
    ],
    board: Array(9).fill(null) as (BoardCell | null)[],
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 1,
    round_number: 1,
    result: null,
    last_move: null,
  };
}

function renderGameRoom() {
  render(
    <MemoryRouter initialEntries={["/g/game-ux012"]}>
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

describe("US-UX-012: last move highlight + callout", () => {
  it("shows 'Opponent played' callout when last_move.player_index is opponent (1)", async () => {
    vi.mocked(getGame).mockResolvedValue(makeGameWithLastMove(1, "card_shadow", 0));
    renderGameRoom();

    await waitFor(() => {
      expect(screen.getByLabelText(/last move callout/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/last move callout/i).textContent).toMatch(/opponent played/i);
  });

  it("shows 'You played' callout when last_move.player_index is the viewer (0)", async () => {
    vi.mocked(getGame).mockResolvedValue(makeGameWithLastMove(0, "card_knight", 3));
    renderGameRoom();

    await waitFor(() => {
      expect(screen.getByLabelText(/last move callout/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/last move callout/i).textContent).toMatch(/you played/i);
  });

  it("shows no callout when last_move is null", async () => {
    vi.mocked(getGame).mockResolvedValue(makeGameNoLastMove());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    expect(screen.queryByLabelText(/last move callout/i)).not.toBeInTheDocument();
  });

  it("callout uses display name from card definitions (not raw card_key)", async () => {
    vi.mocked(getGame).mockResolvedValue(makeGameWithLastMove(1, "card_shadow", 0));
    renderGameRoom();

    await waitFor(() => {
      expect(screen.getByLabelText(/last move callout/i)).toBeInTheDocument();
    });
    const callout = screen.getByLabelText(/last move callout/i);
    // Should use "Shadow Wraith" from definitions, not "card_shadow"
    expect(callout.textContent).toMatch(/Shadow Wraith/i);
    expect(callout.textContent).not.toContain("card_shadow");
  });

  it("last placed cell has data-last-move attribute for highlight", async () => {
    // Opponent placed at cell 0
    vi.mocked(getGame).mockResolvedValue(makeGameWithLastMove(1, "card_shadow", 0));
    renderGameRoom();

    await waitFor(() => {
      expect(screen.getByLabelText(/last move callout/i)).toBeInTheDocument();
    });

    const board = screen.getByLabelText("game board");
    const cells = board.querySelectorAll("[data-last-move]");
    expect(cells.length).toBe(1);
    // The cell at index 0 should be highlighted
    const boardCells = board.children;
    expect(boardCells[0].getAttribute("data-last-move")).toBe("true");
  });

  it("callout has dark mode classes for readability", async () => {
    vi.mocked(getGame).mockResolvedValue(makeGameWithLastMove(1, "card_shadow", 0));
    renderGameRoom();

    await waitFor(() => {
      expect(screen.getByLabelText(/last move callout/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/last move callout/i).className).toMatch(/dark:/);
  });
});
