/**
 * US-UXP-007: Tier-based card rarity visuals (shiny T2, holographic T3)
 *
 * Covers CSS tier class definitions and animation infrastructure.
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const cssPath = path.resolve(__dirname, "../index.css");

describe("US-UXP-007: Tier-based card rarity visuals", () => {
  const css = fs.readFileSync(cssPath, "utf-8");

  describe("CSS tier classes", () => {
    it(".card-tier-2 exists with conic-gradient border-image", () => {
      expect(css).toContain(".card-tier-2");
      const match = css.match(/\.card-tier-2\s*\{[^}]*\}/);
      expect(match).not.toBeNull();
      expect(match![0]).toContain("border-image");
      expect(match![0]).toContain("conic-gradient");
    });

    it(".card-tier-2 has gold/red metallic palette", () => {
      const match = css.match(/\.card-tier-2\s*\{[^}]*\}/);
      expect(match).not.toBeNull();
      expect(match![0]).toContain("box-shadow");
    });

    it(".card-tier-3 exists with conic-gradient border-image", () => {
      expect(css).toContain(".card-tier-3");
      const match = css.match(/\.card-tier-3\s*\{[^}]*\}/);
      expect(match).not.toBeNull();
      expect(match![0]).toContain("border-image");
      expect(match![0]).toContain("conic-gradient");
    });

    it(".card-tier-3 has prismatic overlay via ::after", () => {
      expect(css).toContain(".card-tier-3::after");
      expect(css).toMatch(/\.card-tier-3::after\s*\{[^}]*mix-blend-mode/);
      expect(css).toMatch(/\.card-tier-3::after\s*\{[^}]*pointer-events:\s*none/);
    });
  });

  describe("CSS animation infrastructure", () => {
    it("@property --tier-angle is defined", () => {
      expect(css).toContain("@property --tier-angle");
    });

    it("@keyframes tier-spin exists", () => {
      expect(css).toContain("@keyframes tier-spin");
    });

    it(":root has tier-spin animation", () => {
      expect(css).toMatch(/animation:\s*tier-spin/);
    });
  });
});
