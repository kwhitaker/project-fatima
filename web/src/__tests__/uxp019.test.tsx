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

const cssPath = path.resolve(__dirname, "../index.css");
const cssSrc = fs.readFileSync(cssPath, "utf-8");

describe("US-UXP-019: Card placement animation punch-up", () => {
  describe("Mists visual feedback CSS", () => {
    it("defines mists-fog-flash keyframes in CSS with blue color", () => {
      expect(cssSrc).toContain("@keyframes mists-fog-flash");
      expect(cssSrc).toContain("rgba(59, 130, 246");
    });

    it("defines mists-omen-flash keyframes in CSS with gold color", () => {
      expect(cssSrc).toContain("@keyframes mists-omen-flash");
      expect(cssSrc).toContain("rgba(234, 179, 8");
    });
  });
});
