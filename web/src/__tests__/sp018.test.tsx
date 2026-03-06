/**
 * US-SP-018: Frontend archetype power visual feedback on cards
 */
import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { BoardCallouts } from "@/routes/game-room/BoardCallouts";
import { BoardGrid } from "@/routes/game-room/BoardGrid";

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

describe("US-SP-018: Archetype power visual feedback", () => {
  describe("BoardCallouts — archetype callout", () => {
    it.each([
      ["martial", "Martial Spin!"],
      ["skulker", "Skulker +3!"],
      ["intimidate", "Intimidate!"],
      ["caster", "Caster!"],
      ["devout", "Devout!"],
    ])(
      "renders callout for %s archetype",
      (archName, expectedText) => {
        render(
          <BoardCallouts
            mistsEffect={null}
            captureCount={0}
            plusTriggered={false}
            elementalTriggered={false}
            elementKey={null}
            archetypeUsedName={archName}
            changeKey="0-c1"
          />,
        );
        const callout = screen.getByLabelText("board archetype callout");
        expect(callout).toBeInTheDocument();
        expect(callout.textContent).toBe(expectedText);
      },
    );

    it("does not render archetype callout when archetypeUsedName is null", () => {
      render(
        <BoardCallouts
          mistsEffect={null}
          captureCount={0}
          plusTriggered={false}
          elementalTriggered={false}
          elementKey={null}
          archetypeUsedName={null}
          changeKey="0-c1"
        />,
      );
      expect(
        screen.queryByLabelText("board archetype callout"),
      ).not.toBeInTheDocument();
    });
  });

  describe("BoardGrid — gold ring on archetype use", () => {
    it("applies amber ring to last-move cell when archetypeUsedName is set", () => {
      const board = [
        { card_key: "c1", owner: 0 },
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
      ];
      render(
        <BoardGrid
          board={board}
          myIndex={0}
          lastMoveCellIndex={0}
          archetypeUsedName="skulker"
        />,
      );
      // The cell at index 0 should have the amber ring class
      const cell = screen.getByTitle("c1");
      expect(cell.className).toContain("ring-amber-400");
      expect(cell.className).toContain("animate-pulse");
    });

    it.each(["cw", "ccw"] as const)(
      "sets data-martial-spin=%s on placed card when martial rotation is %s",
      (direction) => {
        const board = [
          { card_key: "c1", owner: 0 },
          null,
          null,
          null,
          null,
          null,
          null,
          null,
          null,
        ];
        const { container } = render(
          <BoardGrid
            board={board}
            myIndex={0}
            lastMoveCellIndex={0}
            placedCells={new Set([0])}
            archetypeUsedName="martial"
            martialRotationDirection={direction}
          />,
        );
        const spinEl = container.querySelector(`[data-martial-spin="${direction}"]`);
        expect(spinEl).toBeInTheDocument();
      },
    );

    it("does not set data-martial-spin when archetype is not martial", () => {
      const board = [
        { card_key: "c1", owner: 0 },
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
      ];
      const { container } = render(
        <BoardGrid
          board={board}
          myIndex={0}
          lastMoveCellIndex={0}
          placedCells={new Set([0])}
          archetypeUsedName="skulker"
        />,
      );
      const spinEl = container.querySelector("[data-martial-spin]");
      expect(spinEl).not.toBeInTheDocument();
    });

    it.each(["n", "e", "s", "w"] as const)(
      "sets data-skulker-glow=%s on placed card when skulker boost side is %s",
      (side) => {
        const board = [
          { card_key: "c1", owner: 0 },
          null,
          null,
          null,
          null,
          null,
          null,
          null,
          null,
        ];
        const { container } = render(
          <BoardGrid
            board={board}
            myIndex={0}
            lastMoveCellIndex={0}
            placedCells={new Set([0])}
            archetypeUsedName="skulker"
            skulkerBoostSide={side}
          />,
        );
        const glowEl = container.querySelector(`[data-skulker-glow="${side}"]`);
        expect(glowEl).toBeInTheDocument();
        const particleEl = container.querySelector(`[data-skulker-particle="${side}"]`);
        expect(particleEl).toBeInTheDocument();
        expect(particleEl?.textContent).toBe("+3");
      },
    );

    it("does not set data-skulker-glow when archetype is not skulker", () => {
      const board = [
        { card_key: "c1", owner: 0 },
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
      ];
      const { container } = render(
        <BoardGrid
          board={board}
          myIndex={0}
          lastMoveCellIndex={0}
          placedCells={new Set([0])}
          archetypeUsedName="martial"
          martialRotationDirection="cw"
        />,
      );
      const glowEl = container.querySelector("[data-skulker-glow]");
      expect(glowEl).not.toBeInTheDocument();
    });

    it("applies standard yellow ring when no archetype used", () => {
      const board = [
        { card_key: "c1", owner: 0 },
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
      ];
      render(
        <BoardGrid
          board={board}
          myIndex={0}
          lastMoveCellIndex={0}
          archetypeUsedName={null}
        />,
      );
      const cell = screen.getByTitle("c1");
      expect(cell.className).toContain("ring-yellow-400");
      expect(cell.className).not.toContain("ring-amber-400");
    });
  });
});
