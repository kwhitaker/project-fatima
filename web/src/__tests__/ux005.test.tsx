/**
 * US-UX-005: Game room header UX: opponent title + back link; remove Leave after completion
 *
 * Covers:
 * - Title shows "Playing against <email>" when game is ACTIVE and opponent has email
 * - Title shows "Waiting for opponent" when game is WAITING
 * - A non-forfeit "Back to Games" navigation link is always present
 * - COMPLETE games do NOT show a "Leave Game" button
 * - COMPLETE games DO have navigation back to /games
 */
import { render, screen } from "@testing-library/react";
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

const { getGame } = await import("@/lib/api");

function makeWaitingGame(): GameState {
  return {
    game_id: "game-ux005",
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

function makeActiveGame(): GameState {
  return {
    game_id: "game-ux005",
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

function makeCompleteGame(): GameState {
  return {
    game_id: "game-ux005",
    status: "complete",
    players: [
      {
        player_id: "player-1",
        email: "me@example.com",
        archetype: "martial",
        hand: [],
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
    board: Array(9).fill(null) as null[],
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 9,
    round_number: 1,
    result: { winner: 0, is_draw: false },
    last_move: null,
  };
}

function renderGameRoom() {
  render(
    <MemoryRouter initialEntries={["/g/game-ux005"]}>
      <Routes>
        <Route path="/g/:gameId" element={<GameRoom />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("US-UX-005: game room header UX", () => {
  it("title reads 'Waiting for opponent' when game is WAITING", async () => {
    vi.mocked(getGame).mockResolvedValue(makeWaitingGame());
    renderGameRoom();
    expect(await screen.findByText(/waiting for opponent/i)).toBeTruthy();
  });

  it("title reads 'Playing against <email>' when game is ACTIVE", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();
    expect(
      await screen.findByText(/playing against opponent@example\.com/i)
    ).toBeTruthy();
  });

  it("Back to Games link is present in WAITING state", async () => {
    vi.mocked(getGame).mockResolvedValue(makeWaitingGame());
    renderGameRoom();
    await screen.findByText(/waiting for opponent/i);
    expect(screen.getByRole("link", { name: /back to games/i })).toBeTruthy();
  });

  it("Back to Games link is present in ACTIVE state", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();
    await screen.findByText(/playing against/i);
    expect(screen.getByRole("link", { name: /back to games/i })).toBeTruthy();
  });

  it("Back to Games link is present in COMPLETE state", async () => {
    vi.mocked(getGame).mockResolvedValue(makeCompleteGame());
    renderGameRoom();
    await screen.findByText(/you win/i);
    expect(screen.getByRole("link", { name: /back to games/i })).toBeTruthy();
  });

  it("Leave Game button is NOT shown in COMPLETE state", async () => {
    vi.mocked(getGame).mockResolvedValue(makeCompleteGame());
    renderGameRoom();
    await screen.findByText(/you win/i);
    expect(screen.queryByRole("button", { name: /leave game/i })).toBeNull();
  });

  it("Leave Game button IS still shown in ACTIVE state (forfeit path)", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();
    await screen.findByText(/playing against/i);
    expect(screen.getByRole("button", { name: /leave game/i })).toBeTruthy();
  });
});
