import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, beforeEach, describe, it, expect } from "vitest";
import { MemoryRouter } from "react-router-dom";
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

function makeActiveGame() {
  return makeGame({
    status: "active",
    players: [
      { ...makePlayer("user-123", "test@example.com"), archetype: "martial", hand: ["c2"] },
      { ...makePlayer("user-456", "opp@example.com"), archetype: "skulker", hand: ["c3"] },
    ],
    current_player_index: 0,
  });
}

describe("US-UP-003: Archetype tooltips", () => {
  it("shows archetype power tooltip content on hover", async () => {
    const game = makeActiveGame();
    mockGetGame.mockResolvedValue(game);
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/g/abc-123"]}>
        <App />
      </MemoryRouter>,
    );

    // Wait for the archetype name to appear
    const archetypeLabel = await screen.findByLabelText("You archetype");
    // Hover over the archetype name
    await user.hover(archetypeLabel);

    // Tooltip should be in DOM (even if visually hidden when not hovered, it's there via CSS)
    const tooltip = archetypeLabel.querySelector('[role="tooltip"]');
    expect(tooltip).toBeInTheDocument();
    expect(tooltip?.textContent).toContain("Spin your card");
  });

  it("does not show ArchetypePowerAside blocks in sidebar", async () => {
    const game = makeActiveGame();
    mockGetGame.mockResolvedValue(game);

    render(
      <MemoryRouter initialEntries={["/g/abc-123"]}>
        <App />
      </MemoryRouter>,
    );

    await screen.findByLabelText("You archetype");
    // The old always-visible power asides should not be present
    expect(screen.queryByLabelText("your archetype power")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("opponent archetype power")).not.toBeInTheDocument();
  });
});
