/**
 * US-UXP-022: Defeat animation
 *
 * Covers:
 * - Full-screen dark overlay with fog/mist effect
 * - 'DEFEAT' text in Press Start 2P with slow fade-in
 * - Screen desaturation (CSS grayscale)
 * - Pixel-art fog/mist particles drifting across screen
 * - Red vignette effect at screen edges
 * - Auto-dismiss after ~3s or on click
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const overlayPath = path.resolve(__dirname, "../routes/game-room/DefeatOverlay.tsx");
const overlaySrc = fs.readFileSync(overlayPath, "utf-8");

const completeViewPath = path.resolve(__dirname, "../routes/game-room/CompleteGameView.tsx");
const completeViewSrc = fs.readFileSync(completeViewPath, "utf-8");

describe("US-UXP-022: Defeat animation", () => {
  describe("full-screen overlay", () => {
    it("renders fixed full-screen overlay with dark backdrop", () => {
      expect(overlaySrc).toContain("fixed inset-0 z-50");
      expect(overlaySrc).toContain("bg-black/80");
    });

    it("has defeat-overlay test id", () => {
      expect(overlaySrc).toContain('data-testid="defeat-overlay"');
    });
  });

  describe("DEFEAT text", () => {
    it("displays DEFEAT in pixel font with red color", () => {
      expect(overlaySrc).toContain("DEFEAT");
      expect(overlaySrc).toContain("font-heading");
      expect(overlaySrc).toContain("text-red-500");
    });

    it("uses slow solemn fade-in (not punchy scale)", () => {
      // Duration should be > 1s for solemn feel
      expect(overlaySrc).toMatch(/duration:\s*1\.2/);
      // Uses stepped easing
      expect(overlaySrc).toContain("steppedEase");
    });

    it("has red text-shadow glow effect", () => {
      expect(overlaySrc).toContain("textShadow");
      expect(overlaySrc).toMatch(/rgba\(150,0,0/);
    });
  });

  describe("fog/mist particles", () => {
    it("generates multiple fog particles", () => {
      expect(overlaySrc).toContain("FOG_COUNT");
      expect(overlaySrc).toContain("makeFogParticles");
    });

    it("fog particles drift horizontally", () => {
      // Particles move in x direction (drift)
      expect(overlaySrc).toContain("drift");
      expect(overlaySrc).toMatch(/x:\s*`\$\{f\.drift\}vw`/);
    });

    it("uses stepped easing for pixel-style fog", () => {
      expect(overlaySrc).toMatch(/ease:\s*steppedEase\(6\)/);
    });

    it("fog particles have blur filter for misty effect", () => {
      expect(overlaySrc).toContain("blur(8px)");
    });
  });

  describe("red vignette", () => {
    it("has radial-gradient vignette with dark red edges", () => {
      expect(overlaySrc).toContain("radial-gradient");
      expect(overlaySrc).toContain("rgba(100,0,0");
      expect(overlaySrc).toContain('data-testid="defeat-vignette"');
    });
  });

  describe("desaturation", () => {
    it("applies grayscale backdrop filter", () => {
      expect(overlaySrc).toContain("grayscale(0.7)");
      expect(overlaySrc).toContain("backdropFilter");
      expect(overlaySrc).toContain('data-testid="defeat-desaturate"');
    });
  });

  describe("auto-dismiss", () => {
    it("auto-dismisses after ~3 seconds", () => {
      expect(overlaySrc).toContain("setTimeout(() => setVisible(false), 3000)");
    });

    it("dismisses on click", () => {
      expect(overlaySrc).toContain("onClick={() => setVisible(false)}");
    });
  });

  describe("CompleteGameView integration", () => {
    it("detects loser state", () => {
      expect(completeViewSrc).toContain("isLoser");
    });

    it("shows DefeatOverlay when player lost", () => {
      expect(completeViewSrc).toContain("showDefeat");
      expect(completeViewSrc).toContain("DefeatOverlay");
    });

    it("imports DefeatOverlay", () => {
      expect(completeViewSrc).toContain('import { DefeatOverlay }');
    });
  });
});
