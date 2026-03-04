import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect } from "vitest";
import { ActionPanel } from "@/routes/game-room/ActionPanel";
import { GameRoomWrapper, DEFAULT_GAME_ROOM_CTX } from "./helpers";

// Mock motion/react
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

describe("US-UP-004: Prominent power toggle", () => {
  it("renders power toggle button with pulse when power is available", () => {
    render(
      <GameRoomWrapper ctx={{ ...DEFAULT_GAME_ROOM_CTX, usePower: false }}>
        <ActionPanel
          isMyTurn={true}
          myPlayer={{
            player_id: "user-123",
            email: "test@example.com",
            archetype: "skulker",
            hand: [],
            archetype_used: false,
          }}
        />
      </GameRoomWrapper>,
    );

    const btn = screen.getByRole("button", { name: /use power/i });
    expect(btn).toBeInTheDocument();
    expect(btn.className).toMatch(/animate-pulse/);
    expect(btn.getAttribute("aria-pressed")).toBe("false");
  });

  it("renders power toggle as pressed when usePower is true", () => {
    render(
      <GameRoomWrapper ctx={{ ...DEFAULT_GAME_ROOM_CTX, usePower: true }}>
        <ActionPanel
          isMyTurn={true}
          myPlayer={{
            player_id: "user-123",
            email: "test@example.com",
            archetype: "skulker",
            hand: [],
            archetype_used: false,
          }}
        />
      </GameRoomWrapper>,
    );

    const btn = screen.getByRole("button", { name: /use power/i });
    expect(btn.getAttribute("aria-pressed")).toBe("true");
    expect(btn.className).not.toMatch(/animate-pulse/);
    expect(btn.className).toMatch(/bg-primary/);
  });

  it("does not render power toggle when archetype already used", () => {
    render(
      <GameRoomWrapper>
        <ActionPanel
          isMyTurn={true}
          myPlayer={{
            player_id: "user-123",
            email: "test@example.com",
            archetype: "skulker",
            hand: [],
            archetype_used: true,
          }}
        />
      </GameRoomWrapper>,
    );

    expect(screen.queryByRole("button", { name: /use power/i })).not.toBeInTheDocument();
  });

  it("calls onUsePowerChange when clicked", async () => {
    const mockOnChange = vi.fn();
    const user = userEvent.setup();
    render(
      <GameRoomWrapper ctx={{ ...DEFAULT_GAME_ROOM_CTX, usePower: false, onUsePowerChange: mockOnChange }}>
        <ActionPanel
          isMyTurn={true}
          myPlayer={{
            player_id: "user-123",
            email: "test@example.com",
            archetype: "martial",
            hand: [],
            archetype_used: false,
          }}
        />
      </GameRoomWrapper>,
    );

    await user.click(screen.getByRole("button", { name: /use power/i }));
    expect(mockOnChange).toHaveBeenCalledWith(true);
  });
});
