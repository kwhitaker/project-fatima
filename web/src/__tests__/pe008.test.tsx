/**
 * US-PE-008: DevPlayground complete archetype effects showcase
 *
 * Verifies all 5 archetype effects have dedicated scenarios in DevPlayground
 * and the "Archetype Effects" section header is rendered.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

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
  playMartial: vi.fn(),
  playSkulker: vi.fn(),
  playCaster: vi.fn(),
  playDevout: vi.fn(),
  playIntimidate: vi.fn(),
  isMuted: () => false,
  toggleMute: vi.fn(),
  initAudio: vi.fn(),
}));

import DevPlayground from "@/routes/DevPlayground";

describe("US-PE-008: DevPlayground archetype effects showcase", () => {
  it("renders 'Archetype Effects' section header", () => {
    render(<DevPlayground />);
    expect(screen.getByText("Archetype Effects")).toBeInTheDocument();
  });

  it.each([
    "Martial: Spin CW",
    "Martial: Spin CCW",
    "Skulker: Boost N",
    "Caster: Omen Aura",
    "Devout: Ward Shield",
    "Intimidate: Shudder",
  ])("has scenario button for '%s'", (label) => {
    render(<DevPlayground />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("all 5 archetypes are represented in scenario buttons", () => {
    render(<DevPlayground />);
    const buttons = screen.getAllByRole("button");
    const archetypeLabels = buttons
      .map((b) => b.textContent ?? "")
      .filter((t) => /^(Martial|Skulker|Caster|Devout|Intimidate):/.test(t));
    const archetypes = new Set(archetypeLabels.map((l) => l.split(":")[0]));
    expect(archetypes).toEqual(
      new Set(["Martial", "Skulker", "Caster", "Devout", "Intimidate"]),
    );
  });
});
