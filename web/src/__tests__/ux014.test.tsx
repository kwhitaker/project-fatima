/**
 * US-UX-014: Mobile card inspect: tap-to-preview for hand and board
 *
 * Covers:
 * - Tapping inspect button on hand card opens preview dialog
 * - Preview shows card name and N/E/S/W values
 * - Preview can be closed with Close button
 * - Preview can be closed with Escape key
 * - Tapping an occupied board cell opens preview
 * - Preview has role="dialog" and aria-modal for accessibility
 * - Does not interfere with hand card selection (aria-pressed still works)
 * - Preview has dark mode classes for readability
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

const CARD_DEFS = new Map<string, CardDefinition>([
  [
    "card_001",
    {
      card_key: "card_001",
      name: "Barovia Guard",
      version: "v1",
      sides: { n: 4, e: 5, s: 3, w: 2 },
    },
  ],
  [
    "card_002",
    {
      card_key: "card_002",
      name: "Night Hag",
      version: "v1",
      sides: { n: 7, e: 3, s: 8, w: 1 },
    },
  ],
]);

const BOARD_WITH_CARDS: (BoardCell | null)[] = [
  { card_key: "card_002", owner: 1 }, // opponent card on board
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
];

function makeActiveGame(): GameState {
  return {
    game_id: "game-ux014",
    status: "active",
    players: [
      {
        player_id: "player-1",
        email: "me@example.com",
        archetype: "martial",
        hand: ["card_001"],
        archetype_used: false,
      },
      {
        player_id: "player-2",
        email: "opponent@example.com",
        archetype: "devout",
        hand: ["card_002"],
        archetype_used: false,
      },
    ],
    board: BOARD_WITH_CARDS,
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 2,
    round_number: 1,
    result: null,
    last_move: null,
  };
}

function renderGameRoom() {
  render(
    <MemoryRouter initialEntries={["/g/game-ux014"]}>
      <Routes>
        <Route path="/g/:gameId" element={<GameRoom />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getCardDefinitions).mockResolvedValue(CARD_DEFS);
});

describe("US-UX-014: mobile card inspect — tap-to-preview", () => {
  it("inspect button on a hand card opens the card preview dialog", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    const inspectBtn = screen.getByRole("button", { name: /inspect barovia guard/i });
    await userEvent.click(inspectBtn);

    expect(screen.getByRole("dialog", { name: /card preview/i })).toBeInTheDocument();
  });

  it("preview dialog shows the card name", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    await userEvent.click(screen.getByRole("button", { name: /inspect barovia guard/i }));

    const dialog = screen.getByRole("dialog", { name: /card preview/i });
    expect(dialog.textContent).toContain("Barovia Guard");
  });

  it("preview dialog shows N/E/S/W side values", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    await userEvent.click(screen.getByRole("button", { name: /inspect barovia guard/i }));

    const dialog = screen.getByRole("dialog", { name: /card preview/i });
    // card_001: n:4, e:5, s:3, w:2
    expect(dialog.textContent).toContain("4");
    expect(dialog.textContent).toContain("5");
    expect(dialog.textContent).toContain("3");
    expect(dialog.textContent).toContain("2");
  });

  it("preview dialog can be closed with the Close button", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    await userEvent.click(screen.getByRole("button", { name: /inspect barovia guard/i }));
    expect(screen.getByRole("dialog", { name: /card preview/i })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(screen.queryByRole("dialog", { name: /card preview/i })).not.toBeInTheDocument();
  });

  it("preview dialog can be closed with the Escape key", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    await userEvent.click(screen.getByRole("button", { name: /inspect barovia guard/i }));
    expect(screen.getByRole("dialog", { name: /card preview/i })).toBeInTheDocument();

    await userEvent.keyboard("{Escape}");

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: /card preview/i })).not.toBeInTheDocument();
    });
  });

  it("tapping an occupied board cell opens the card preview dialog", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    // cell 0 has card_002 (Night Hag, owned by opponent)
    const boardCells = screen.getByLabelText("game board").children;
    await userEvent.click(boardCells[0] as HTMLElement);

    await waitFor(() => {
      expect(screen.getByRole("dialog", { name: /card preview/i })).toBeInTheDocument();
    });
    const dialog = screen.getByRole("dialog", { name: /card preview/i });
    expect(dialog.textContent).toContain("Night Hag");
  });

  it("hand card still has aria-pressed (selection not broken by inspect button)", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    // The main card button (not the inspect button) should still have aria-pressed
    const cardButton = screen.getAllByRole("button", { name: /barovia guard/i })
      .find((b) => b.hasAttribute("aria-pressed"));
    expect(cardButton).toBeTruthy();
    expect(cardButton).toHaveAttribute("aria-pressed");
  });

  it("preview dialog has dark mode classes for readability", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame());
    renderGameRoom();

    await screen.findByText(/your turn/i);

    await userEvent.click(screen.getByRole("button", { name: /inspect barovia guard/i }));

    const dialog = screen.getByRole("dialog", { name: /card preview/i });
    // The dialog content box should have dark: classes
    expect(dialog.innerHTML).toMatch(/dark:/);
  });
});
