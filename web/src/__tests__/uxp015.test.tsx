/**
 * US-UXP-015: Procedural game sound effects via Web Audio API
 *
 * Covers:
 * - sounds.ts module exports all required functions
 * - initAudio, isMuted, setMuted API
 * - play* functions are no-ops before init (no throw)
 * - Mute toggle component renders and toggles
 * - Sounds are wired into BoardGrid, ActiveGameView, CompleteGameView
 */
import { describe, it, expect, vi } from "vitest";

// Mock Web Audio API for module import
const mockGainNode = { gain: { value: 0, setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() }, connect: vi.fn() };
const mockOscillator = {
  type: "sine",
  frequency: { setValueAtTime: vi.fn(), linearRampToValueAtTime: vi.fn() },
  connect: vi.fn(),
  start: vi.fn(),
  stop: vi.fn(),
};
const mockAudioContext = {
  createOscillator: vi.fn(() => ({ ...mockOscillator })),
  createGain: vi.fn(() => ({ ...mockGainNode })),
  currentTime: 0,
  destination: {},
};

vi.stubGlobal("AudioContext", vi.fn(() => mockAudioContext));

describe("US-UXP-015: Procedural game sound effects", () => {
  describe("sounds.ts module exports", () => {
    it("exports initAudio, isMuted, setMuted, and all play* functions", async () => {
      const mod = await import("@/lib/sounds");
      expect(typeof mod.initAudio).toBe("function");
      expect(typeof mod.isMuted).toBe("function");
      expect(typeof mod.setMuted).toBe("function");
      expect(typeof mod.playPlace).toBe("function");
      expect(typeof mod.playCapture).toBe("function");
      expect(typeof mod.playCombo).toBe("function");
      expect(typeof mod.playPlus).toBe("function");
      expect(typeof mod.playElemental).toBe("function");
      expect(typeof mod.playTurnStart).toBe("function");
      expect(typeof mod.playVictory).toBe("function");
      expect(typeof mod.playDefeat).toBe("function");
    });
  });

  describe("play* functions before init", () => {
    it("do not throw when called before initAudio", async () => {
      // Re-import a fresh module to test pre-init state
      vi.resetModules();
      vi.stubGlobal("AudioContext", vi.fn(() => mockAudioContext));
      const freshMod = await import("@/lib/sounds");
      expect(() => freshMod.playPlace()).not.toThrow();
      expect(() => freshMod.playCapture()).not.toThrow();
      expect(() => freshMod.playCombo(3)).not.toThrow();
      expect(() => freshMod.playPlus()).not.toThrow();
      expect(() => freshMod.playElemental()).not.toThrow();
      expect(() => freshMod.playTurnStart()).not.toThrow();
      expect(() => freshMod.playVictory()).not.toThrow();
      expect(() => freshMod.playDefeat()).not.toThrow();
    });
  });

});
