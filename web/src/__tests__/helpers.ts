/**
 * Shared test helpers for frontend tests.
 *
 * Exports data factories and constants. Due to vitest hoisting constraints,
 * each test file must still define its own `vi.hoisted()` + `vi.mock()` blocks.
 * This file deduplicates the data and factory functions, not the mock wiring.
 */
import type { GameState, PlayerState, BoardCell } from "@/lib/api";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const MOCK_SESSION = {
  user: { id: "user-123", email: "test@example.com" },
  access_token: "fake-token",
};

export const EMPTY_BOARD: (BoardCell | null)[] = Array(9).fill(null);

// ---------------------------------------------------------------------------
// Factories
// ---------------------------------------------------------------------------

export function makeGame(overrides: Partial<GameState> = {}): GameState {
  return {
    game_id: "abc-123",
    status: "waiting",
    players: [],
    board: Array(9).fill(null),
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 0,
    round_number: 1,
    result: null,
    board_elements: null,
    created_at: "2026-03-03T00:00:00+00:00",
    ...overrides,
  };
}

export function makePlayer(id: string, email?: string): PlayerState {
  return {
    player_id: id,
    email: email ?? `${id}@example.com`,
    archetype: null,
    hand: [],
    archetype_used: false,
  };
}
