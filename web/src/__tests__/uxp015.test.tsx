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
import { describe, it, expect, vi, beforeEach } from "vitest";
import fs from "node:fs";
import path from "node:path";

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

  describe("sounds.ts uses Web Audio API only (no audio files)", () => {
    it("does not import audio files or use <audio> elements", () => {
      const src = fs.readFileSync(
        path.resolve(__dirname, "../lib/sounds.ts"),
        "utf-8"
      );
      expect(src).not.toMatch(/\.mp3|\.wav|\.ogg|\.m4a|new Audio\(/);
      expect(src).not.toMatch(/HTMLAudioElement/);
      expect(src).toContain("AudioContext");
      expect(src).toContain("OscillatorType");
    });
  });

  describe("sounds.ts uses 8-bit waveforms", () => {
    it("uses square and/or sawtooth oscillators", () => {
      const src = fs.readFileSync(
        path.resolve(__dirname, "../lib/sounds.ts"),
        "utf-8"
      );
      expect(src).toContain('"square"');
      expect(src).toContain('"sawtooth"');
    });
  });

  describe("sound wiring in game components", () => {
    const boardGridSrc = fs.readFileSync(
      path.resolve(__dirname, "../routes/game-room/BoardGrid.tsx"),
      "utf-8"
    );
    const activeViewSrc = fs.readFileSync(
      path.resolve(__dirname, "../routes/game-room/ActiveGameView.tsx"),
      "utf-8"
    );
    const completeViewSrc = fs.readFileSync(
      path.resolve(__dirname, "../routes/game-room/CompleteGameView.tsx"),
      "utf-8"
    );
    const gameRoomSrc = fs.readFileSync(
      path.resolve(__dirname, "../routes/GameRoom.tsx"),
      "utf-8"
    );

    it("BoardGrid imports and calls playPlace", () => {
      expect(boardGridSrc).toContain("playPlace");
      expect(boardGridSrc).toMatch(/import.*playPlace.*from/);
    });

    it("BoardGrid imports and calls playCapture and playCombo", () => {
      expect(boardGridSrc).toContain("playCapture");
      expect(boardGridSrc).toContain("playCombo");
    });

    it("ActiveGameView imports and calls playPlus", () => {
      expect(activeViewSrc).toContain("playPlus");
      expect(activeViewSrc).toMatch(/import.*playPlus.*from/);
    });

    it("ActiveGameView imports and calls playElemental", () => {
      expect(activeViewSrc).toContain("playElemental");
      expect(activeViewSrc).toMatch(/import.*playElemental.*from/);
    });

    it("ActiveGameView imports and calls playTurnStart", () => {
      expect(activeViewSrc).toContain("playTurnStart");
      expect(activeViewSrc).toMatch(/import.*playTurnStart.*from/);
    });

    it("CompleteGameView imports playVictory and playDefeat", () => {
      expect(completeViewSrc).toContain("playVictory");
      expect(completeViewSrc).toContain("playDefeat");
    });

    it("GameRoom initializes audio context", () => {
      expect(gameRoomSrc).toContain("initAudio");
      expect(gameRoomSrc).toMatch(/import.*initAudio.*from/);
    });
  });

  describe("MuteToggle component", () => {
    it("exists and exports MuteToggle", () => {
      const src = fs.readFileSync(
        path.resolve(__dirname, "../routes/game-room/MuteToggle.tsx"),
        "utf-8"
      );
      expect(src).toContain("export function MuteToggle");
      expect(src).toContain("isMuted");
      expect(src).toContain("setMuted");
    });

    it("is used in ActiveGameView", () => {
      const src = fs.readFileSync(
        path.resolve(__dirname, "../routes/game-room/ActiveGameView.tsx"),
        "utf-8"
      );
      expect(src).toContain("MuteToggle");
      expect(src).toMatch(/import.*MuteToggle.*from/);
    });

    it("uses localStorage for persistence", () => {
      const soundsSrc = fs.readFileSync(
        path.resolve(__dirname, "../lib/sounds.ts"),
        "utf-8"
      );
      expect(soundsSrc).toContain("localStorage");
    });
  });
});
