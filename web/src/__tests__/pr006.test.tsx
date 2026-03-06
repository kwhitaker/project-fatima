/**
 * US-PR-006: Frontend archetype copy and power descriptions updated
 * Tests archetype copy changes and Devout Ward cell selection UI.
 */
import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { ARCHETYPE_COPY } from "@/routes/game-room/archetypesCopy";
import { BoardGrid } from "@/routes/game-room/BoardGrid";
import { ActionPanel } from "@/routes/game-room/ActionPanel";
import { GameRoomWrapper, DEFAULT_GAME_ROOM_CTX, makePlayer } from "./helpers";

// Mock motion/react
vi.mock("motion/react", () => {
  const React = require("react");
  return {
    motion: new Proxy(
      {},
      {
        get: (_target: unknown, prop: string) =>
          React.forwardRef((props: Record<string, unknown>, ref: unknown) =>
            React.createElement(prop, { ...props, ref }),
          ),
      },
    ),
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  };
});

// Mock sounds
vi.mock("@/lib/sounds", () => ({
  playPlace: vi.fn(),
  playCapture: vi.fn(),
  playCombo: vi.fn(),
  playPlus: vi.fn(),
  playElemental: vi.fn(),
  playTurnStart: vi.fn(),
  isMuted: () => false,
  toggleMute: vi.fn(),
  initAudio: vi.fn(),
}));

describe("US-PR-006: Archetype copy and UI updates", () => {
  describe("Archetype copy text", () => {
    it("Caster power title is 'Guaranteed Omen'", () => {
      expect(ARCHETYPE_COPY.caster.powerTitle).toBe("Guaranteed Omen");
    });

    it("Caster power text mentions +2", () => {
      expect(ARCHETYPE_COPY.caster.powerText).toContain("+2");
    });

    it("Devout power title is 'Ward'", () => {
      expect(ARCHETYPE_COPY.devout.powerTitle).toBe("Ward");
    });

    it("Devout power text mentions capture protection", () => {
      expect(ARCHETYPE_COPY.devout.powerText).toContain("cannot be captured");
    });

    it("Intimidate power text mentions -3 debuff", () => {
      expect(ARCHETYPE_COPY.intimidate.powerText).toContain("reduced by 3");
    });

    it("no stale references in any archetype copy", () => {
      const allText = Object.values(ARCHETYPE_COPY)
        .map((c) => `${c.powerTitle} ${c.powerText}`)
        .join(" ");
      expect(allText).not.toContain("Reroll");
      expect(allText).not.toContain("Negate Fog");
      expect(allText).not.toContain("weakest side");
    });
  });

  describe("BoardGrid — warded cell visual indicator", () => {
    it("renders shield icon on warded cell", () => {
      const board = [
        { card_key: "c1", owner: 0 as const },
        { card_key: "c2", owner: 1 as const },
        null, null, null, null, null, null, null,
      ];
      render(
        <BoardGrid
          board={board}
          myIndex={0}
          wardedCell={0}
        />,
      );
      expect(screen.getByLabelText("warded")).toBeInTheDocument();
    });

    it("applies sky ring to warded cell", () => {
      const board = [
        { card_key: "c1", owner: 0 as const },
        null, null, null, null, null, null, null, null,
      ];
      render(
        <BoardGrid
          board={board}
          myIndex={0}
          wardedCell={0}
        />,
      );
      const cell = screen.getByTitle("c1");
      expect(cell.className).toContain("ring-sky-400");
    });

    it("does not render shield when wardedCell is null", () => {
      const board = [
        { card_key: "c1", owner: 0 as const },
        null, null, null, null, null, null, null, null,
      ];
      render(
        <BoardGrid
          board={board}
          myIndex={0}
          wardedCell={null}
        />,
      );
      expect(screen.queryByLabelText("warded")).not.toBeInTheDocument();
    });
  });

  describe("BoardGrid — Devout Ward target selection", () => {
    it("highlights own cards as ward targets when devoutWardPendingCell is set", () => {
      const board = [
        { card_key: "c1", owner: 0 as const },
        { card_key: "c2", owner: 1 as const },
        null, null, null, null, null, null, null,
      ];
      render(
        <BoardGrid
          board={board}
          myIndex={0}
          devoutWardPendingCell={4}
          onCellClick={() => {}}
        />,
      );
      // Own card should be clickable as ward target
      expect(screen.getByLabelText("ward target cell 0")).toBeInTheDocument();
      // Opponent card should NOT be a ward target
      expect(screen.queryByLabelText("ward target cell 1")).not.toBeInTheDocument();
    });
  });

  describe("ActionPanel — Devout Ward pending state", () => {
    it("shows ward step text when devout ward is pending", () => {
      render(
        <GameRoomWrapper
          ctx={{
            ...DEFAULT_GAME_ROOM_CTX,
            selectedCard: "c1",
            usePower: true,
            devoutWardPendingCell: 4,
          }}
        >
          <ActionPanel
            isMyTurn={true}
            myPlayer={makePlayer("user-123", "test@example.com", {
              archetype: "devout",
              archetype_used: false,
            })}
          />
        </GameRoomWrapper>,
      );
      expect(screen.getByText(/Click one of your cards.*to ward/)).toBeInTheDocument();
    });

    it("shows 'Placing at cell' info when devout ward is pending", () => {
      render(
        <GameRoomWrapper
          ctx={{
            ...DEFAULT_GAME_ROOM_CTX,
            selectedCard: "c1",
            usePower: true,
            devoutWardPendingCell: 3,
          }}
        >
          <ActionPanel
            isMyTurn={true}
            myPlayer={makePlayer("user-123", "test@example.com", {
              archetype: "devout",
              archetype_used: false,
            })}
          />
        </GameRoomWrapper>,
      );
      expect(screen.getByText(/Placing at cell 3/)).toBeInTheDocument();
    });
  });
});
