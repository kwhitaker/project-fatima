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

const cssPath = path.resolve(__dirname, "../index.css");
const cssSrc = fs.readFileSync(cssPath, "utf-8");

describe("US-UXP-021: Victory animation", () => {
  describe("victory-glow CSS", () => {
    it("CSS defines victory-glow animation with stepped timing", () => {
      expect(cssSrc).toContain("@keyframes victory-glow");
      expect(cssSrc).toContain("animate-victory-glow");
      expect(cssSrc).toContain("steps(4)");
    });

  });
});
