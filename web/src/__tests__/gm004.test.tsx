/**
 * US-GM-004: Plus rule — UI callout and capture feedback
 *
 * Covers:
 * - Plus! callout shown when plus_triggered=true
 * - No Plus! callout when plus_triggered=false or absent
 * - Plus! callout is cyan/teal, visually distinct from capture feedback
 * - Plus! and capture count can coexist
 * - Plus! callout has aria-live="polite" and aria-label="plus feedback"
 * - Plus! callout has dark mode classes
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import GameRoom from "../routes/GameRoom";
import type { BoardCell, GameState, LastMoveInfo } from "@/lib/api";

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

const { getGame, placeCard, getCardDefinitions } = await import("@/lib/api");

const EMPTY_BOARD: (BoardCell | null)[] = Array(9).fill(null);

function makeLastMove(extras: Partial<LastMoveInfo> = {}): LastMoveInfo {
  return {
    player_index: 0,
    card_key: "card-a",
    cell_index: 0,
    mists_roll: 3,
    mists_effect: "none",
    ...extras,
  };
}

function makeActiveGame(
  board: (BoardCell | null)[] = EMPTY_BOARD,
  currentPlayer = 0,
  lastMove: LastMoveInfo | null = null
): GameState {
  return {
    game_id: "game-gm004",
    status: "active",
    players: [
      {
        player_id: "player-1",
        email: "me@example.com",
        archetype: "martial",
        hand: ["card-a"],
        archetype_used: false,
      },
      {
        player_id: "player-2",
        email: "opponent@example.com",
        archetype: "devout",
        hand: ["card-x"],
        archetype_used: false,
      },
    ],
    board,
    current_player_index: currentPlayer,
    starting_player_index: 0,
    state_version: 3,
    round_number: 1,
    result: null,
    last_move: lastMove,
  };
}

function renderGameRoom() {
  render(
    <MemoryRouter initialEntries={["/g/game-gm004"]}>
      <Routes>
        <Route path="/g/:gameId" element={<GameRoom />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getCardDefinitions).mockResolvedValue(new Map());
});

describe("US-GM-004: Plus rule UI callout", () => {
  it("shows Plus! callout when plus_triggered=true", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(EMPTY_BOARD));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      null, null, null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(
      makeActiveGame(afterMoveBoard, 1, makeLastMove({ plus_triggered: true }))
    );

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/plus feedback/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/plus feedback/i).textContent).toMatch(/plus/i);
  });

  it("does not show Plus! callout when plus_triggered=false", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(EMPTY_BOARD));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      null, null, null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(
      makeActiveGame(afterMoveBoard, 1, makeLastMove({ plus_triggered: false }))
    );

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));

    await waitFor(() => {
      expect(screen.getByText(/opponent.?s turn/i)).toBeInTheDocument();
    });
    expect(screen.queryByLabelText(/plus feedback/i)).not.toBeInTheDocument();
  });

  it("does not show Plus! callout when plus_triggered is absent", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(EMPTY_BOARD));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      null, null, null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(
      // last_move without plus_triggered field (backward compat)
      makeActiveGame(afterMoveBoard, 1, makeLastMove())
    );

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));

    await waitFor(() => {
      expect(screen.getByText(/opponent.?s turn/i)).toBeInTheDocument();
    });
    expect(screen.queryByLabelText(/plus feedback/i)).not.toBeInTheDocument();
  });

  it("Plus! callout and capture count can coexist", async () => {
    const initialBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 1 },
      null, null, null, null, null, null, null, null,
    ];
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(initialBoard));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 0 }, // captured via Plus
      { card_key: "card-a", owner: 0 }, // placed
      null, null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(
      makeActiveGame(afterMoveBoard, 1, makeLastMove({ plus_triggered: true }))
    );

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 1/i }));
    await user.click(screen.getByRole("button", { name: /cell 1/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/plus feedback/i)).toBeInTheDocument();
    });
    // Capture feedback should also be visible
    expect(screen.getByLabelText(/capture feedback/i)).toBeInTheDocument();
  });

  it("Plus! callout has aria-live='polite' for accessibility", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(EMPTY_BOARD));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      null, null, null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(
      makeActiveGame(afterMoveBoard, 1, makeLastMove({ plus_triggered: true }))
    );

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/plus feedback/i)).toBeInTheDocument();
    });
    expect(
      screen.getByLabelText(/plus feedback/i).getAttribute("aria-live")
    ).toBe("polite");
  });

  it("Plus! callout has dark mode classes", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(EMPTY_BOARD));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      null, null, null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(
      makeActiveGame(afterMoveBoard, 1, makeLastMove({ plus_triggered: true }))
    );

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/plus feedback/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/plus feedback/i).className).toMatch(/dark:/);
  });
});
