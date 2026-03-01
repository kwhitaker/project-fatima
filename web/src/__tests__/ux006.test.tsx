/**
 * US-UX-006: Leaving ACTIVE games requires confirmation (forfeit warning dialog)
 *
 * Covers:
 * - In ACTIVE game, clicking Leave opens a confirmation dialog with forfeit language
 * - Cancel closes the dialog without calling leaveGame
 * - Confirm calls leaveGame and navigates to /games
 * - WAITING game has no Leave button (no forfeit dialog needed)
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import GameRoom from "../routes/GameRoom";
import type { GameState } from "@/lib/api";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: { id: "player-1" } }),
}));

vi.mock("@/lib/api", () => ({
  getGame: vi.fn(),
  joinGame: vi.fn(),
  leaveGame: vi.fn().mockResolvedValue(undefined),
  placeCard: vi.fn(),
  selectArchetype: vi.fn(),
  getCardDefinitions: vi.fn().mockResolvedValue(new Map()),
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

const { getGame, leaveGame } = await import("@/lib/api");

function makeActiveGame(): GameState {
  return {
    game_id: "game-ux006",
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
        hand: ["card_010", "card_011"],
        archetype_used: false,
      },
    ],
    board: Array(9).fill(null) as null[],
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 2,
    round_number: 1,
    result: null,
    last_move: null,
  };
}

function makeWaitingGame(): GameState {
  return {
    game_id: "game-ux006",
    status: "waiting",
    players: [
      {
        player_id: "player-1",
        email: "me@example.com",
        archetype: null,
        hand: [],
        archetype_used: false,
      },
    ],
    board: Array(9).fill(null) as null[],
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
    <MemoryRouter initialEntries={["/g/game-ux006"]}>
      <Routes>
        <Route path="/g/:gameId" element={<GameRoom />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("US-UX-006: forfeit confirmation dialog", () => {
  it("clicking Leave in ACTIVE game shows a confirmation dialog", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/playing against/i);

    const leaveBtn = screen.getByRole("button", { name: /leave game/i });
    fireEvent.click(leaveBtn);

    expect(await screen.findByRole("dialog", { name: /forfeit/i })).toBeTruthy();
  });

  it("confirmation dialog contains forfeit warning language", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/playing against/i);
    fireEvent.click(screen.getByRole("button", { name: /leave game/i }));

    const dialog = await screen.findByRole("dialog", { name: /forfeit/i });
    expect(dialog.textContent).toMatch(/forfeit/i);
  });

  it("Cancel closes the dialog without calling leaveGame", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/playing against/i);
    fireEvent.click(screen.getByRole("button", { name: /leave game/i }));

    await screen.findByRole("dialog", { name: /forfeit/i });

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: /forfeit/i })).toBeNull();
    });
    expect(vi.mocked(leaveGame)).not.toHaveBeenCalled();
  });

  it("Confirm calls leaveGame and navigates to /games", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/playing against/i);
    fireEvent.click(screen.getByRole("button", { name: /leave game/i }));

    await screen.findByRole("dialog", { name: /forfeit/i });

    // Click the confirm/forfeit button inside the dialog
    const dialog = screen.getByRole("dialog", { name: /forfeit/i });
    const confirmBtn = dialog.querySelector("button[data-confirm]") ??
      screen.getByRole("button", { name: /forfeit.*leave|confirm.*forfeit|yes.*forfeit/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(vi.mocked(leaveGame)).toHaveBeenCalledWith("game-ux006", 2);
    });
    expect(mockNavigate).toHaveBeenCalledWith("/games");
  });

  it("WAITING game has no Leave Game button", async () => {
    vi.mocked(getGame).mockResolvedValue(makeWaitingGame());
    renderGameRoom();

    await screen.findByText(/waiting for opponent/i);
    expect(screen.queryByRole("button", { name: /leave game/i })).toBeNull();
  });
});
