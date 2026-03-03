/**
 * US-UXP-021: Victory animation
 *
 * Covers:
 * - Full-screen overlay with gothic/8-bit theme
 * - VICTORY text in Press Start 2P with stepped scale-in
 * - Bat swarm particle effect
 * - Blood-red and gold confetti with stepped animations
 * - Owned cards glow/pulse in sequence on the board
 * - Auto-dismiss after ~3s or on click
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const overlayPath = path.resolve(__dirname, "../routes/game-room/VictoryOverlay.tsx");
const overlaySrc = fs.readFileSync(overlayPath, "utf-8");

const completeViewPath = path.resolve(__dirname, "../routes/game-room/CompleteGameView.tsx");
const completeViewSrc = fs.readFileSync(completeViewPath, "utf-8");

const boardGridPath = path.resolve(__dirname, "../routes/game-room/BoardGrid.tsx");
const boardGridSrc = fs.readFileSync(boardGridPath, "utf-8");

const cssPath = path.resolve(__dirname, "../index.css");
const cssSrc = fs.readFileSync(cssPath, "utf-8");

describe("US-UXP-021: Victory animation", () => {
  describe("full-screen overlay", () => {
    it("renders fixed full-screen overlay with dark backdrop", () => {
      expect(overlaySrc).toContain("fixed inset-0 z-50");
      expect(overlaySrc).toContain("bg-black/70");
    });

    it("has victory-overlay test id", () => {
      expect(overlaySrc).toContain('data-testid="victory-overlay"');
    });
  });

  describe("VICTORY text", () => {
    it("displays VICTORY in pixel font with gold color", () => {
      expect(overlaySrc).toContain("VICTORY");
      expect(overlaySrc).toContain("font-heading");
      expect(overlaySrc).toContain("text-yellow-400");
    });

    it("uses stepped scale-in animation", () => {
      expect(overlaySrc).toContain("steppedEase");
      // Scale keyframes include overshoot
      expect(overlaySrc).toMatch(/scale:\s*\[0,\s*0\.5,\s*1\.3,\s*1\]/);
    });
  });

  describe("bat swarm", () => {
    it("renders bat emoji particles", () => {
      expect(overlaySrc).toContain("🦇");
      expect(overlaySrc).toContain("BAT_COUNT");
    });

    it("uses stepped easing for bat flight", () => {
      expect(overlaySrc).toMatch(/ease:\s*steppedEase\(8\)/);
    });
  });

  describe("confetti", () => {
    it("uses blood-red and gold colors", () => {
      expect(overlaySrc).toContain("rgb(180,30,30)");
      expect(overlaySrc).toContain("rgb(200,160,40)");
    });

    it("uses stepped easing for pixel-style animation", () => {
      expect(overlaySrc).toMatch(/ease:\s*steppedEase\(6\)/);
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

  describe("owned card glow on board", () => {
    it("CompleteGameView computes victoryCells for winner", () => {
      expect(completeViewSrc).toContain("victoryCells");
      expect(completeViewSrc).toContain("cell.owner === myIndex");
    });

    it("passes victoryCells prop to BoardGrid", () => {
      expect(completeViewSrc).toContain("victoryCells={victoryCells}");
    });

    it("BoardGrid accepts victoryCells prop", () => {
      expect(boardGridSrc).toContain("victoryCells");
      expect(boardGridSrc).toContain("victory-glow");
    });

    it("CSS defines victory-glow animation with stepped timing", () => {
      expect(cssSrc).toContain("@keyframes victory-glow");
      expect(cssSrc).toContain("animate-victory-glow");
      expect(cssSrc).toContain("steps(4)");
    });

    it("applies staggered animation-delay per owned cell", () => {
      expect(boardGridSrc).toContain("animationDelay");
      expect(boardGridSrc).toMatch(/victoryIdx \* 0\.2/);
    });
  });
});
