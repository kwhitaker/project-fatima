/**
 * Shared test helpers for frontend tests.
 *
 * Exports data factories and constants. Due to vitest hoisting constraints,
 * each test file must still define its own `vi.hoisted()` + `vi.mock()` blocks.
 * This file deduplicates the data and factory functions, not the mock wiring.
 */
import { createElement, type ReactNode } from "react";
import type { GameState, PlayerState, BoardCell, Archetype, CardDefinition } from "@/lib/api";
import { GameRoomProvider } from "@/routes/game-room/GameRoomContext";

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

export function makePlayer(id: string, email?: string, overrides?: Partial<PlayerState>): PlayerState {
  return {
    player_id: id,
    email: email ?? `${id}@example.com`,
    archetype: null,
    deal: [],
    hand: [],
    archetype_used: false,
    player_type: "human",
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// GameRoomContext wrapper for tests
// ---------------------------------------------------------------------------

/** Default no-op context values for tests that render components using useGameRoom. */
export const DEFAULT_GAME_ROOM_CTX = {
  selectedCard: null as string | null,
  onSelectCard: (() => {}) as (cardKey: string | null) => void,
  selectedCardElement: null as string | null,
  movePending: false,
  usePower: false,
  onUsePowerChange: (() => {}) as (next: boolean) => void,
  powerSide: null as string | null,
  onPowerSideToggle: (() => {}) as (side: "n" | "e" | "s" | "w") => void,
  intimidatePendingCell: null as number | null,
  onCancelIntimidatePending: () => {},
  archetypePending: false,
  archetypeError: null as string | null,
  onSelectArchetype: (() => {}) as (archetype: Archetype) => void | Promise<void>,
  onPreviewCard: (() => {}) as (cardKey: string, def?: CardDefinition) => void,
  leaving: false,
  onOpenLeaveConfirm: () => {},
  showLeaveConfirm: false,
  onCloseLeaveConfirm: () => {},
  onConfirmLeave: () => {},
  onShowRules: () => {},
};

/** Wraps children in a GameRoomProvider with sensible defaults. Override individual values as needed. */
export function GameRoomWrapper({
  ctx,
  children,
}: {
  ctx?: Partial<typeof DEFAULT_GAME_ROOM_CTX>;
  children: ReactNode;
}) {
  return createElement(
    GameRoomProvider,
    { value: { ...DEFAULT_GAME_ROOM_CTX, ...ctx } },
    children,
  );
}
