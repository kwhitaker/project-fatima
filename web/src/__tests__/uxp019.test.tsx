/**
 * US-UXP-019: Card placement animation punch-up
 *
 * Covers:
 * - Slam overshoot (scale past 1.08 then settle)
 * - Impact ripple element on placed cards
 * - Board grid micro-shake on placement
 * - Mists tint CSS classes for Fog (blue) and Omen (gold)
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const boardGridPath = path.resolve(__dirname, "../routes/game-room/BoardGrid.tsx");
const boardGridSrc = fs.readFileSync(boardGridPath, "utf-8");

const cssPath = path.resolve(__dirname, "../index.css");
const cssSrc = fs.readFileSync(cssPath, "utf-8");

const activeViewPath = path.resolve(__dirname, "../routes/game-room/ActiveGameView.tsx");
const activeViewSrc = fs.readFileSync(activeViewPath, "utf-8");

describe("US-UXP-019: Card placement animation punch-up", () => {
  describe("slam overshoot", () => {
    it("placed card scales past 1 (to 1.08) before settling", () => {
      // Non-pulse placement uses keyframes [0, 1.08, 1]
      expect(boardGridSrc).toContain("1.08");
      expect(boardGridSrc).toMatch(/scale:\s*\[0,\s*1\.08,\s*1\]/);
    });
  });

  describe("impact ripple", () => {
    it("renders a ripple motion.div inside placed card content", () => {
      // Ripple scales outward and fades
      expect(boardGridSrc).toContain("Impact ripple");
      expect(boardGridSrc).toMatch(/scale:\s*1\.6/);
      expect(boardGridSrc).toMatch(/opacity:\s*0/);
    });
  });

  describe("board micro-shake", () => {
    it("uses motion.div for the grid container with translateX shake", () => {
      // Grid is a motion.div with x oscillation keyframes
      expect(boardGridSrc).toContain("motion.div");
      expect(boardGridSrc).toMatch(/x:\s*\[0,\s*-2,\s*2,\s*-1,\s*1,\s*0\]/);
    });
  });

  describe("Mists visual feedback", () => {
    it("BoardGrid accepts mistsEffect prop", () => {
      expect(boardGridSrc).toContain("mistsEffect");
      expect(boardGridSrc).toMatch(/mistsEffect\?.*"fog"|"omen"|"none"/);
    });

    it("applies animate-mists-fog class on Fog roll", () => {
      expect(boardGridSrc).toContain("animate-mists-fog");
    });

    it("applies animate-mists-omen class on Omen roll", () => {
      expect(boardGridSrc).toContain("animate-mists-omen");
    });

    it("defines mists-fog-flash keyframes in CSS with blue color", () => {
      expect(cssSrc).toContain("@keyframes mists-fog-flash");
      expect(cssSrc).toContain("rgba(59, 130, 246");
    });

    it("defines mists-omen-flash keyframes in CSS with gold color", () => {
      expect(cssSrc).toContain("@keyframes mists-omen-flash");
      expect(cssSrc).toContain("rgba(234, 179, 8");
    });

    it("ActiveGameView passes mistsEffect to BoardGrid", () => {
      expect(activeViewSrc).toContain("mistsEffect");
      expect(activeViewSrc).toContain("mists_effect");
    });
  });
});
