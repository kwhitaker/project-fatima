/**
 * US-UX-013: Realtime status indicator + manual refresh/resync
 *
 * Covers:
 * - Shows "Live" indicator when realtime is connected (SUBSCRIBED)
 * - Shows "Reconnecting" indicator when realtime is disconnected (CLOSED/CHANNEL_ERROR)
 * - Manual Refresh button is present in the game room
 * - Clicking Refresh refetches GET /games/:gameId
 * - Status indicator has dark mode classes for readability
 */
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import GameRoom from "../routes/GameRoom";
import type { GameState } from "@/lib/api";

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

// Module-level variable (starts with "mock" to bypass vi.mock hoisting restriction)
let mockSubscribeCallback: (status: string) => void = () => {};

vi.mock("@/lib/supabase", () => ({
  supabase: {
    channel: () => ({
      on: () => ({
        subscribe: (cb: (status: string) => void) => {
          mockSubscribeCallback = cb;
          return { unsubscribe: vi.fn() };
        },
      }),
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
    game_id: "game-ux013",
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
    <MemoryRouter initialEntries={["/g/game-ux013"]}>
      <Routes>
        <Route path="/g/:gameId" element={<GameRoom />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockSubscribeCallback = () => {};
  vi.mocked(getCardDefinitions).mockResolvedValue(new Map());
});

describe("US-UX-013: realtime status indicator + manual refresh", () => {
  it("shows 'Live' indicator when realtime is SUBSCRIBED", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await waitFor(() => screen.getByText(/your turn/i));

    act(() => { mockSubscribeCallback("SUBSCRIBED"); });

    await waitFor(() => {
      expect(screen.getByLabelText(/realtime status/i).textContent).toMatch(/live/i);
    });
  });

  it("shows 'Reconnecting' indicator when realtime status is CLOSED", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await waitFor(() => screen.getByText(/your turn/i));

    // First connect, then disconnect
    act(() => { mockSubscribeCallback("SUBSCRIBED"); });
    act(() => { mockSubscribeCallback("CLOSED"); });

    await waitFor(() => {
      expect(screen.getByLabelText(/realtime status/i).textContent).toMatch(/reconnecting/i);
    });
  });

  it("shows 'Reconnecting' indicator when realtime status is CHANNEL_ERROR", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await waitFor(() => screen.getByText(/your turn/i));

    act(() => { mockSubscribeCallback("CHANNEL_ERROR"); });

    await waitFor(() => {
      expect(screen.getByLabelText(/realtime status/i).textContent).toMatch(/reconnecting/i);
    });
  });

  it("manual Refresh button is present in the game room", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await waitFor(() => screen.getByText(/your turn/i));

    expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
  });

  it("clicking Refresh refetches the game state", async () => {
    const game = makeActiveGame();
    vi.mocked(getGame).mockResolvedValue(game);
    renderGameRoom();

    await waitFor(() => screen.getByText(/your turn/i));

    const callsBefore = vi.mocked(getGame).mock.calls.length;

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /refresh/i }));

    await waitFor(() => {
      expect(vi.mocked(getGame).mock.calls.length).toBeGreaterThan(callsBefore);
    });
    // The most recent call should be for game-ux013
    const lastCall = vi.mocked(getGame).mock.calls.at(-1);
    expect(lastCall?.[0]).toBe("game-ux013");
  });

  it("status indicator has dark mode classes for readability", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await waitFor(() => screen.getByText(/your turn/i));

    const indicator = screen.getByLabelText(/realtime status/i);
    expect(indicator.className).toMatch(/dark:/);
  });
});
