/**
 * US-UXP-007: Tier-based card rarity visuals (shiny T2, holographic T3)
 *
 * Covers:
 * - .card-tier-2 and .card-tier-3 CSS classes exist with correct styling
 * - @property --tier-angle and @keyframes tier-spin exist
 * - :root has tier-spin animation
 * - CardFace exports tierClass helper and accepts tier prop
 * - BoardGrid, HandPanel, CardInspectPreview apply tier classes
 * - Tier 3 has ::after pseudo-element overlay
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const cssPath = path.resolve(__dirname, "../index.css");
const cardFacePath = path.resolve(__dirname, "../routes/game-room/CardFace.tsx");
const boardGridPath = path.resolve(__dirname, "../routes/game-room/BoardGrid.tsx");
const handPanelPath = path.resolve(__dirname, "../routes/game-room/HandPanel.tsx");
const cardInspectPath = path.resolve(__dirname, "../routes/game-room/CardInspectPreview.tsx");

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

  describe("CardFace component", () => {
    const cardFace = fs.readFileSync(cardFacePath, "utf-8");

    it("exports tierClass helper", () => {
      expect(cardFace).toContain("export function tierClass");
    });

    it("accepts tier prop", () => {
      expect(cardFace).toMatch(/tier\??:\s*number/);
    });

    it("applies card-tier-* class via tierClass", () => {
      expect(cardFace).toContain("tierClass");
      expect(cardFace).toContain("card-tier-2");
      expect(cardFace).toContain("card-tier-3");
    });
  });

  describe("Component wiring", () => {
    it("BoardGrid imports tierClass and applies it to cells", () => {
      const src = fs.readFileSync(boardGridPath, "utf-8");
      expect(src).toContain("tierClass");
      expect(src).toMatch(/tierClass\(.*tier/);
    });

    it("HandPanel imports tierClass and applies it to card buttons", () => {
      const src = fs.readFileSync(handPanelPath, "utf-8");
      expect(src).toContain("tierClass");
      expect(src).toMatch(/tierClass\(.*tier/);
    });

    it("CardInspectPreview imports tierClass and applies it", () => {
      const src = fs.readFileSync(cardInspectPath, "utf-8");
      expect(src).toContain("tierClass");
      expect(src).toMatch(/tierClass\(.*tier/);
    });
  });
});
