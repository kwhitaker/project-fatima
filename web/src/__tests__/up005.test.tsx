import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect } from "vitest";
import { ArchetypeModal } from "@/routes/game-room/ArchetypeModal";
import { GameRoomWrapper, DEFAULT_GAME_ROOM_CTX } from "./helpers";

describe("US-UP-005: Archetype selection confirm", () => {
  it("clicking an archetype does NOT call onSelectArchetype", async () => {
    const mockSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <GameRoomWrapper ctx={{ ...DEFAULT_GAME_ROOM_CTX, onSelectArchetype: mockSelect }}>
        <ArchetypeModal open={true} />
      </GameRoomWrapper>,
    );

    await user.click(screen.getByRole("button", { name: /skulker/i }));
    expect(mockSelect).not.toHaveBeenCalled();
  });

  it("confirm button is disabled until archetype selected", () => {
    render(
      <GameRoomWrapper>
        <ArchetypeModal open={true} />
      </GameRoomWrapper>,
    );

    const confirmBtn = screen.getByRole("button", { name: /confirm archetype/i });
    expect(confirmBtn).toBeDisabled();
  });

  it("clicking Confirm calls onSelectArchetype with selected archetype", async () => {
    const mockSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <GameRoomWrapper ctx={{ ...DEFAULT_GAME_ROOM_CTX, onSelectArchetype: mockSelect }}>
        <ArchetypeModal open={true} />
      </GameRoomWrapper>,
    );

    // Select an archetype
    await user.click(screen.getByRole("button", { name: /caster/i }));
    // Confirm button should now be enabled
    const confirmBtn = screen.getByRole("button", { name: /confirm archetype/i });
    expect(confirmBtn).not.toBeDisabled();
    // Click confirm
    await user.click(confirmBtn);
    expect(mockSelect).toHaveBeenCalledWith("caster");
  });

  it("selected archetype has visual ring indicator", async () => {
    const user = userEvent.setup();
    render(
      <GameRoomWrapper>
        <ArchetypeModal open={true} />
      </GameRoomWrapper>,
    );

    const btn = screen.getByRole("button", { name: /martial/i });
    await user.click(btn);
    expect(btn.getAttribute("aria-pressed")).toBe("true");
    expect(btn.className).toMatch(/ring-2/);
  });
});
