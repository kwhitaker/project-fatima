/**
 * US-GM-007: Elemental system — UI: board cell elements and match highlighting
 *
 * Covers:
 * - Element label renders on empty cell
 * - Element label renders on occupied cell
 * - Selected card highlights matching cells (emerald ring)
 * - No highlight when no card selected (selectedCardElement=null)
 * - Non-matching cells are not highlighted
 * - Elemental! callout shown when elemental_triggered=true
 * - No callout when elemental_triggered=false
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import GameRoom from "../routes/GameRoom";
import { BoardGrid } from "../routes/game-room/BoardGrid";
import type { BoardCell, GameState, LastMoveInfo } from "@/lib/api";

// ---------------------------------------------------------------------------
// Mocks for GameRoom tests
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const EMPTY_BOARD: (BoardCell | null)[] = Array(9).fill(null);

// Mixed elements: cells 0,5=blood; 1,6=holy; 2,7=arcane; 3,8=shadow; 4=nature
const MIXED_ELEMENTS = ["blood", "holy", "arcane", "shadow", "nature", "blood", "holy", "arcane", "shadow"];

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
  lastMove: LastMoveInfo | null = null,
  boardElements: string[] | null = null
): GameState {
  return {
    game_id: "game-gm007",
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
    board_elements: boardElements,
  };
}

function renderGameRoom() {
  render(
    <MemoryRouter initialEntries={["/g/game-gm007"]}>
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

// ---------------------------------------------------------------------------
// Direct BoardGrid tests: element labels
// ---------------------------------------------------------------------------

describe("US-GM-007: BoardGrid — element labels", () => {
  it("renders element label on each empty cell when boardElements provided", () => {
    const allBlood = Array(9).fill("blood");
    render(
      <BoardGrid board={EMPTY_BOARD} myIndex={0} boardElements={allBlood} />
    );
    // All 9 cells should display a blood element badge
    const labels = screen.getAllByLabelText("element blood");
    expect(labels).toHaveLength(9);
  });

  it("renders element label on an occupied cell", () => {
    const board: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      ...Array(8).fill(null),
    ];
    const elements = ["blood", ...Array(8).fill("holy")];
    render(<BoardGrid board={board} myIndex={0} boardElements={elements} />);

    expect(screen.getByLabelText("element blood")).toBeInTheDocument();
    expect(screen.getAllByLabelText("element holy")).toHaveLength(8);
  });

  it("renders no element badge when boardElements is null", () => {
    render(<BoardGrid board={EMPTY_BOARD} myIndex={0} boardElements={null} />);
    // No element labels should be present
    expect(screen.queryByLabelText(/^element /)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Direct BoardGrid tests: element match highlighting
// ---------------------------------------------------------------------------

describe("US-GM-007: BoardGrid — element match highlighting", () => {
  it("highlights matching cells with emerald ring when selectedCardElement is set", () => {
    render(
      <BoardGrid
        board={EMPTY_BOARD}
        myIndex={0}
        canPlace={true}
        onCellClick={vi.fn()}
        boardElements={MIXED_ELEMENTS}
        selectedCardElement="blood"
      />
    );
    // Cells 0 and 5 are "blood" → should have emerald ring
    const cell0 = screen.getByRole("button", { name: "cell 0" });
    const cell5 = screen.getByRole("button", { name: "cell 5" });
    // Cell 1 is "holy" → should NOT have emerald ring
    const cell1 = screen.getByRole("button", { name: "cell 1" });

    expect(cell0.className).toMatch(/ring-emerald/);
    expect(cell5.className).toMatch(/ring-emerald/);
    expect(cell1.className).not.toMatch(/ring-emerald/);
  });

  it("does not highlight any cell when selectedCardElement is null", () => {
    render(
      <BoardGrid
        board={EMPTY_BOARD}
        myIndex={0}
        canPlace={true}
        onCellClick={vi.fn()}
        boardElements={Array(9).fill("blood")}
        selectedCardElement={null}
      />
    );
    for (let i = 0; i < 9; i++) {
      const cell = screen.getByRole("button", { name: `cell ${i}` });
      expect(cell.className).not.toMatch(/ring-emerald/);
    }
  });

  it("does not highlight non-matching cells", () => {
    render(
      <BoardGrid
        board={EMPTY_BOARD}
        myIndex={0}
        canPlace={true}
        onCellClick={vi.fn()}
        boardElements={MIXED_ELEMENTS}
        selectedCardElement="nature"
      />
    );
    // Only cell 4 is "nature"
    const cell4 = screen.getByRole("button", { name: "cell 4" });
    const cell0 = screen.getByRole("button", { name: "cell 0" }); // blood
    const cell1 = screen.getByRole("button", { name: "cell 1" }); // holy

    expect(cell4.className).toMatch(/ring-emerald/);
    expect(cell0.className).not.toMatch(/ring-emerald/);
    expect(cell1.className).not.toMatch(/ring-emerald/);
  });
});

// ---------------------------------------------------------------------------
// Direct BoardGrid tests: cell element tooltip (US-GM-010)
// ---------------------------------------------------------------------------

describe("US-GM-010: BoardGrid — cell element tooltip", () => {
  it("empty cell has title with element when boardElements provided", () => {
    render(
      <BoardGrid board={EMPTY_BOARD} myIndex={0} boardElements={MIXED_ELEMENTS} />
    );
    // Cell 0 is "blood" → title should be "Element: Blood"
    const cells = screen.getAllByTitle(/^Element:/);
    expect(cells).toHaveLength(9);
    expect(cells[0]).toHaveAttribute("title", "Element: Blood");
    expect(cells[1]).toHaveAttribute("title", "Element: Holy");
  });

  it("occupied cell title includes both card info and element", () => {
    const board: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      ...Array(8).fill(null),
    ];
    const elements = ["blood", ...Array(8).fill("holy")];
    render(
      <BoardGrid
        board={board}
        myIndex={0}
        boardElements={elements}
        onCellInspect={vi.fn()}
        cardDefs={new Map([["card-a", { card_key: "card-a", name: "Zombie", tier: 1, sides: { n: 3, e: 2, s: 1, w: 4 }, element: "blood" } as any]])}
      />
    );

    // Occupied cell 0 should have card title + element
    const occupiedCell = screen.getByRole("button", { name: "inspect Zombie" });
    expect(occupiedCell).toHaveAttribute("title", "Zombie (Tier 1) — Element: Blood");
  });

  it("empty non-clickable cell still shows element tooltip", () => {
    render(
      <BoardGrid board={EMPTY_BOARD} myIndex={0} boardElements={["arcane", ...Array(8).fill("shadow")]} />
    );
    // canPlace is false (default), no onCellClick → cells are divs, not buttons
    const arcaneCell = screen.getByTitle("Element: Arcane");
    expect(arcaneCell).toBeInTheDocument();
  });

  it("no title attribute when boardElements is null", () => {
    render(
      <BoardGrid board={EMPTY_BOARD} myIndex={0} boardElements={null} />
    );
    expect(screen.queryByTitle(/^Element:/)).not.toBeInTheDocument();
  });

  it("clickable empty cell shows element tooltip", () => {
    render(
      <BoardGrid
        board={EMPTY_BOARD}
        myIndex={0}
        canPlace={true}
        onCellClick={vi.fn()}
        boardElements={["nature", ...Array(8).fill("blood")]}
      />
    );
    const cell0 = screen.getByRole("button", { name: "cell 0" });
    expect(cell0).toHaveAttribute("title", "Element: Nature");
  });
});

// ---------------------------------------------------------------------------
// GameRoom tests: Elemental! callout
// ---------------------------------------------------------------------------

describe("US-GM-007: Elemental! callout", () => {
  it("shows Elemental! callout with element name when elemental_triggered=true", async () => {
    vi.mocked(getGame).mockResolvedValue(
      makeActiveGame(EMPTY_BOARD, 0, null, MIXED_ELEMENTS)
    );

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      ...Array(8).fill(null),
    ];
    vi.mocked(placeCard).mockResolvedValue(
      makeActiveGame(
        afterMoveBoard,
        1,
        makeLastMove({ elemental_triggered: true, cell_index: 0 }),
        MIXED_ELEMENTS
      )
    );

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/elemental feedback/i)).toBeInTheDocument();
    });
    // cell_index 0 is "blood" → callout should say "Blood Elemental!"
    expect(screen.getByLabelText(/elemental feedback/i).textContent).toMatch(/blood elemental/i);
  });

  it("does not show Elemental! callout when elemental_triggered=false", async () => {
    vi.mocked(getGame).mockResolvedValue(
      makeActiveGame(EMPTY_BOARD, 0, null, MIXED_ELEMENTS)
    );

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      ...Array(8).fill(null),
    ];
    vi.mocked(placeCard).mockResolvedValue(
      makeActiveGame(
        afterMoveBoard,
        1,
        makeLastMove({ elemental_triggered: false }),
        MIXED_ELEMENTS
      )
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
    expect(screen.queryByLabelText(/elemental feedback/i)).not.toBeInTheDocument();
  });

  it("Elemental! callout has aria-live='polite' for accessibility", async () => {
    vi.mocked(getGame).mockResolvedValue(
      makeActiveGame(EMPTY_BOARD, 0, null, MIXED_ELEMENTS)
    );

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      ...Array(8).fill(null),
    ];
    vi.mocked(placeCard).mockResolvedValue(
      makeActiveGame(
        afterMoveBoard,
        1,
        makeLastMove({ elemental_triggered: true, cell_index: 0 }),
        MIXED_ELEMENTS
      )
    );

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/elemental feedback/i)).toBeInTheDocument();
    });
    expect(
      screen.getByLabelText(/elemental feedback/i).getAttribute("aria-live")
    ).toBe("polite");
  });

  it("Elemental! callout has dark mode classes", async () => {
    vi.mocked(getGame).mockResolvedValue(
      makeActiveGame(EMPTY_BOARD, 0, null, MIXED_ELEMENTS)
    );

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      ...Array(8).fill(null),
    ];
    vi.mocked(placeCard).mockResolvedValue(
      makeActiveGame(
        afterMoveBoard,
        1,
        makeLastMove({ elemental_triggered: true, cell_index: 0 }),
        MIXED_ELEMENTS
      )
    );

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/elemental feedback/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/elemental feedback/i).className).toMatch(/dark:/);
  });

  it("Elemental! and Plus! callouts can coexist", async () => {
    vi.mocked(getGame).mockResolvedValue(
      makeActiveGame(EMPTY_BOARD, 0, null, MIXED_ELEMENTS)
    );

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      ...Array(8).fill(null),
    ];
    vi.mocked(placeCard).mockResolvedValue(
      makeActiveGame(
        afterMoveBoard,
        1,
        makeLastMove({ elemental_triggered: true, plus_triggered: true, cell_index: 0 }),
        MIXED_ELEMENTS
      )
    );

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/elemental feedback/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/plus feedback/i)).toBeInTheDocument();
  });

  it("shows fallback 'Elemental!' when board_elements is null but triggered", async () => {
    vi.mocked(getGame).mockResolvedValue(makeActiveGame(EMPTY_BOARD, 0, null, null));

    const afterMoveBoard: (BoardCell | null)[] = [
      { card_key: "card-a", owner: 0 },
      ...Array(8).fill(null),
    ];
    vi.mocked(placeCard).mockResolvedValue(
      makeActiveGame(afterMoveBoard, 1, makeLastMove({ elemental_triggered: true }), null)
    );

    const user = userEvent.setup();
    renderGameRoom();
    await waitFor(() => screen.getByRole("button", { name: "card-a" }));
    await user.click(screen.getByRole("button", { name: "card-a" }));
    await waitFor(() => screen.getByRole("button", { name: /cell 0/i }));
    await user.click(screen.getByRole("button", { name: /cell 0/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/elemental feedback/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/elemental feedback/i).textContent).toBe("Elemental!");
  });
});
