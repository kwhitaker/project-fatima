/**
 * US-UX-010: Capture feedback — clear indication of flips/combos after a move
 *
 * Covers:
 * - Single capture (1 card flips): shows per-move indicator (count, not "combo")
 * - Multi-capture / combo (2+ cards flip): shows "Combo!" indicator, distinct from single
 * - No captures (card placed, no flips): no capture indicator shown
 * - Capture indicator uses aria-live="polite" for accessibility
 * - Capture indicator has dark mode classes (readable in dark mode)
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import GameRoom from "../routes/GameRoom";
import type { BoardCell, GameState } from "@/lib/api";

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

function makeActiveGame(
  board: (BoardCell | null)[] = EMPTY_BOARD,
  currentPlayer = 0
): GameState {
  return {
    game_id: "game-ux010",
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
    last_move: null,
  };
}

function renderGameRoom() {
  render(
    <MemoryRouter initialEntries={["/g/game-ux010"]}>
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

describe("US-UX-010: capture feedback", () => {
  it("shows capture feedback indicator when exactly 1 card is captured", async () => {
    const initialBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 1 }, // opponent card at cell 0
      null, null, null, null, null, null, null, null,
    ];
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(initialBoard));

    // After move: cell 0 captured by player, cell 1 placed
    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 0 }, // captured!
      { card_key: "card-a", owner: 0 }, // placed
      null, null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(makeActiveGame(afterMoveBoard, 1));

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 1/i }));
    await user.click(screen.getByRole("button", { name: /cell 1/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/capture feedback/i)).toBeInTheDocument();
    });
    // Should mention 1 capture
    expect(screen.getByLabelText(/capture feedback/i).textContent).toMatch(/1/);
  });

  it("single capture does NOT show 'Combo' text", async () => {
    const initialBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 1 },
      null, null, null, null, null, null, null, null,
    ];
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(initialBoard));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 0 }, // captured
      { card_key: "card-a", owner: 0 }, // placed
      null, null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(makeActiveGame(afterMoveBoard, 1));

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 1/i }));
    await user.click(screen.getByRole("button", { name: /cell 1/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/capture feedback/i)).toBeInTheDocument();
    });
    // Single capture should NOT say "Combo"
    expect(screen.queryByText(/combo/i)).not.toBeInTheDocument();
  });

  it("shows Combo indicator when 2+ cards are captured (distinct from single)", async () => {
    const initialBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 1 }, // opponent cell 0
      { card_key: "card-y", owner: 1 }, // opponent cell 1
      null, null, null, null, null, null, null,
    ];
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(initialBoard));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 0 }, // captured
      { card_key: "card-y", owner: 0 }, // captured
      { card_key: "card-a", owner: 0 }, // placed
      null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(makeActiveGame(afterMoveBoard, 1));

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 2/i }));
    await user.click(screen.getByRole("button", { name: /cell 2/i }));

    await waitFor(() => {
      expect(screen.getByText(/combo/i)).toBeInTheDocument();
    });
  });

  it("does not show capture indicator when no cells change owner", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(EMPTY_BOARD));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 }, // placed — no captures
      null, null, null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(makeActiveGame(afterMoveBoard, 1));

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));

    await waitFor(() => {
      // Wait for move to complete (turn switches)
      expect(screen.getByText(/opponent.?s turn/i)).toBeInTheDocument();
    });
    expect(screen.queryByLabelText(/capture feedback/i)).not.toBeInTheDocument();
  });

  it("capture indicator has aria-live='polite' for accessibility", async () => {
    const initialBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 1 },
      null, null, null, null, null, null, null, null,
    ];
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(initialBoard));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 0 }, // captured
      { card_key: "card-a", owner: 0 }, // placed
      null, null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(makeActiveGame(afterMoveBoard, 1));

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 1/i }));
    await user.click(screen.getByRole("button", { name: /cell 1/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/capture feedback/i)).toBeInTheDocument();
    });
    expect(
      screen.getByLabelText(/capture feedback/i).getAttribute("aria-live")
    ).toBe("polite");
  });

  it("capture indicator has dark mode classes for readability", async () => {
    const initialBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 1 },
      null, null, null, null, null, null, null, null,
    ];
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(initialBoard));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-x", owner: 0 },
      { card_key: "card-a", owner: 0 },
      null, null, null, null, null, null, null,
    ];
    vi.mocked(placeCard).mockResolvedValue(makeActiveGame(afterMoveBoard, 1));

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 1/i }));
    await user.click(screen.getByRole("button", { name: /cell 1/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/capture feedback/i)).toBeInTheDocument();
    });
    // Should have dark: variant classes
    expect(screen.getByLabelText(/capture feedback/i).className).toMatch(/dark:/);
  });
});
