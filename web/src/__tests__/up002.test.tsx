import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { BoardCallouts } from "@/routes/game-room/BoardCallouts";

// Mock motion/react to render children without animation
vi.mock("motion/react", () => {
  const React = require("react");
  return {
    motion: new Proxy({}, {
      get: (_target: unknown, prop: string) =>
        React.forwardRef((props: Record<string, unknown>, ref: unknown) =>
          React.createElement(prop, { ...props, ref }),
        ),
    }),
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  };
});

describe("US-UP-002: Board-level event callouts", () => {
  it("renders fog mists callout when mists_effect is fog", () => {
    render(
      <BoardCallouts
        mistsEffect="fog"
        mistsRoll={1}
        captureCount={0}
        plusTriggered={false}
        elementalTriggered={false}
        elementKey={null}
        changeKey="0-card1"
      />,
    );
    expect(screen.getByLabelText("board mists callout")).toBeInTheDocument();
    expect(screen.getByText(/mists cloud your vision/i)).toBeInTheDocument();
  });

  it("renders omen mists callout when mists_effect is omen", () => {
    render(
      <BoardCallouts
        mistsEffect="omen"
        mistsRoll={6}
        captureCount={0}
        plusTriggered={false}
        elementalTriggered={false}
        elementKey={null}
        changeKey="0-card1"
      />,
    );
    expect(screen.getByText(/mists favor you/i)).toBeInTheDocument();
  });

  it("renders Plus! callout when plus triggered", () => {
    render(
      <BoardCallouts
        mistsEffect="none"
        mistsRoll={3}
        captureCount={0}
        plusTriggered={true}
        elementalTriggered={false}
        elementKey={null}
        changeKey="0-card1"
      />,
    );
    expect(screen.getByLabelText("board plus callout")).toBeInTheDocument();
    expect(screen.getByText("Plus!")).toBeInTheDocument();
  });

  it("renders elemental callout with element symbol", () => {
    render(
      <BoardCallouts
        mistsEffect="none"
        mistsRoll={3}
        captureCount={0}
        plusTriggered={false}
        elementalTriggered={true}
        elementKey="blood"
        changeKey="0-card1"
      />,
    );
    expect(screen.getByLabelText("board elemental callout")).toBeInTheDocument();
    expect(screen.getByText(/blood elemental/i)).toBeInTheDocument();
  });

  it("renders combo capture callout for 2+ captures", () => {
    render(
      <BoardCallouts
        mistsEffect="none"
        mistsRoll={3}
        captureCount={3}
        plusTriggered={false}
        elementalTriggered={false}
        elementKey={null}
        changeKey="0-card1"
      />,
    );
    expect(screen.getByLabelText("board capture callout")).toBeInTheDocument();
    expect(screen.getByText(/chain.*×3/i)).toBeInTheDocument();
  });

  it("does not render callouts when no events", () => {
    render(
      <BoardCallouts
        mistsEffect="none"
        mistsRoll={3}
        captureCount={0}
        plusTriggered={false}
        elementalTriggered={false}
        elementKey={null}
        changeKey="0-card1"
      />,
    );
    expect(screen.queryByLabelText("board mists callout")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("board plus callout")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("board elemental callout")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("board capture callout")).not.toBeInTheDocument();
  });
});
