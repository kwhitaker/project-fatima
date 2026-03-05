/**
 * US-SP-016: Frontend Sudden Death banner overlay
 */
import { render, screen, act, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { SuddenDeathBanner } from "@/routes/game-room/SuddenDeathBanner";

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

describe("US-SP-016: Sudden Death banner overlay", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders banner when round_number transitions from 1 to 2", () => {
    const { rerender } = render(<SuddenDeathBanner roundNumber={1} />);
    expect(screen.queryByLabelText("sudden death banner")).not.toBeInTheDocument();

    rerender(<SuddenDeathBanner roundNumber={2} />);
    expect(screen.getByLabelText("sudden death banner")).toBeInTheDocument();
    expect(screen.getByText("Sudden Death")).toBeInTheDocument();
    expect(screen.getByText("The souls are bound. Play on.")).toBeInTheDocument();
  });

  it.each([
    [2, "Sudden Death", "The souls are bound. Play on."],
    [3, "Sudden Death II", "The Mists refuse to release you."],
    [4, "Final Sudden Death", "Barovia trembles. This ends now."],
  ] as [number, string, string][])(
    "shows correct text for round %i",
    (round, heading, subtitle) => {
      const { rerender } = render(<SuddenDeathBanner roundNumber={1} />);
      rerender(<SuddenDeathBanner roundNumber={round} />);

      expect(screen.getByText(heading)).toBeInTheDocument();
      expect(screen.getByText(subtitle)).toBeInTheDocument();
    },
  );

  it("auto-dismisses after 3.5 seconds", () => {
    const { rerender } = render(<SuddenDeathBanner roundNumber={1} />);
    rerender(<SuddenDeathBanner roundNumber={2} />);
    expect(screen.getByLabelText("sudden death banner")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3500);
    });

    expect(screen.queryByLabelText("sudden death banner")).not.toBeInTheDocument();
  });

  it("dismisses on click", () => {
    const { rerender } = render(<SuddenDeathBanner roundNumber={1} />);
    rerender(<SuddenDeathBanner roundNumber={2} />);

    const banner = screen.getByLabelText("sudden death banner");
    fireEvent.click(banner);

    expect(screen.queryByLabelText("sudden death banner")).not.toBeInTheDocument();
  });

  it("does not render banner when round_number stays at 1", () => {
    const { rerender } = render(<SuddenDeathBanner roundNumber={1} />);
    rerender(<SuddenDeathBanner roundNumber={1} />);
    expect(screen.queryByLabelText("sudden death banner")).not.toBeInTheDocument();
  });

  it("shows new banner when transitioning from round 2 to 3", () => {
    const { rerender } = render(<SuddenDeathBanner roundNumber={1} />);
    rerender(<SuddenDeathBanner roundNumber={2} />);
    expect(screen.getByText("Sudden Death")).toBeInTheDocument();

    // Dismiss first banner
    act(() => {
      vi.advanceTimersByTime(3500);
    });

    rerender(<SuddenDeathBanner roundNumber={3} />);
    expect(screen.getByText("Sudden Death II")).toBeInTheDocument();
  });
});
