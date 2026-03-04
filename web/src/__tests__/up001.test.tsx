import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, beforeEach, describe, it, expect } from "vitest";
import App from "../App";
import { MOCK_SESSION, makeGame, makePlayer } from "./helpers";

// --- Supabase mock -----------------------------------------------------------
const {
  mockGetSession,
  mockOnAuthStateChange,
  mockSignInWithPassword,
  mockSignUp,
  mockResetPasswordForEmail,
  mockUpdateUser,
  mockSignOut,
} = vi.hoisted(() => ({
  mockGetSession: vi.fn(),
  mockOnAuthStateChange: vi.fn(),
  mockSignInWithPassword: vi.fn(),
  mockSignUp: vi.fn(),
  mockResetPasswordForEmail: vi.fn(),
  mockUpdateUser: vi.fn(),
  mockSignOut: vi.fn(),
}));

// --- Realtime mock -----------------------------------------------------------
const { mockChannel, mockRemoveChannel, realtimeCbs } = vi.hoisted(() => {
  const realtimeCbs = {
    insertHandler: null as (() => void) | null,
    statusHandler: null as ((status: string) => void) | null,
  };
  type ChannelObj = { on: ReturnType<typeof vi.fn>; subscribe: ReturnType<typeof vi.fn> };
  const channelObj = {} as ChannelObj;
  channelObj.on = vi.fn().mockImplementation(
    (_event: unknown, _filter: unknown, handler: () => void) => {
      realtimeCbs.insertHandler = handler;
      return channelObj;
    },
  );
  channelObj.subscribe = vi.fn().mockImplementation((handler: (s: string) => void) => {
    realtimeCbs.statusHandler = handler;
    return channelObj;
  });
  return { mockChannel: vi.fn().mockReturnValue(channelObj), mockRemoveChannel: vi.fn().mockResolvedValue(undefined), realtimeCbs };
});

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: mockGetSession,
      onAuthStateChange: mockOnAuthStateChange,
      signInWithPassword: mockSignInWithPassword,
      signUp: mockSignUp,
      resetPasswordForEmail: mockResetPasswordForEmail,
      updateUser: mockUpdateUser,
      signOut: mockSignOut,
    },
    channel: mockChannel,
    removeChannel: mockRemoveChannel,
  },
}));

// --- API mock ----------------------------------------------------------------
const { mockGetGame, mockGetCardDefinitions } = vi.hoisted(() => ({
  mockGetGame: vi.fn(),
  mockGetCardDefinitions: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  listGames: vi.fn().mockResolvedValue([]),
  createGame: vi.fn(),
  getGame: mockGetGame,
  joinGame: vi.fn(),
  leaveGame: vi.fn(),
  placeCard: vi.fn(),
  selectArchetype: vi.fn(),
  getCardDefinitions: mockGetCardDefinitions,
}));

function setupAuth() {
  mockGetSession.mockResolvedValue({ data: { session: MOCK_SESSION } });
  mockOnAuthStateChange.mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  realtimeCbs.insertHandler = null;
  realtimeCbs.statusHandler = null;
  setupAuth();
  mockGetCardDefinitions.mockResolvedValue(new Map());
});

describe("US-UP-001: Compact game room header", () => {
  it("renders title with compact text size (not text-2xl)", async () => {
    const game = makeGame({
      status: "waiting",
      players: [makePlayer("user-123", "test@example.com")],
    });
    mockGetGame.mockResolvedValue(game);
    render(
      <MemoryRouter initialEntries={["/g/abc-123"]}>
        <App />
      </MemoryRouter>,
    );
    const heading = await screen.findByRole("heading", { name: /waiting for opponent/i });
    expect(heading.className).not.toMatch(/text-2xl/);
    expect(heading.className).toMatch(/text-base/);
  });

  it("renders Back to Games link with text-xs styling", async () => {
    const game = makeGame({
      status: "waiting",
      players: [makePlayer("user-123", "test@example.com")],
    });
    mockGetGame.mockResolvedValue(game);
    render(
      <MemoryRouter initialEntries={["/g/abc-123"]}>
        <App />
      </MemoryRouter>,
    );
    const link = await screen.findByRole("link", { name: /back to games/i });
    expect(link.className).toMatch(/text-xs/);
  });

  it("renders Refresh button with text-xs styling", async () => {
    const game = makeGame({
      status: "waiting",
      players: [makePlayer("user-123", "test@example.com")],
    });
    mockGetGame.mockResolvedValue(game);
    render(
      <MemoryRouter initialEntries={["/g/abc-123"]}>
        <App />
      </MemoryRouter>,
    );
    const btn = await screen.findByRole("button", { name: /refresh game/i });
    expect(btn.className).toMatch(/text-xs/);
  });

  it("renders realtime status badge with compact styling", async () => {
    const game = makeGame({
      status: "waiting",
      players: [makePlayer("user-123", "test@example.com")],
    });
    mockGetGame.mockResolvedValue(game);
    render(
      <MemoryRouter initialEntries={["/g/abc-123"]}>
        <App />
      </MemoryRouter>,
    );
    const badge = await screen.findByLabelText("realtime status");
    // Badge should use smaller padding and text
    expect(badge.className).toMatch(/text-\[10px\]|text-\[11px\]/);
  });
});
