/**
 * US-UXP-010: Hand card selection and deselection motion
 *
 * Covers:
 * - motion.button wraps hand cards for animation
 * - Selected card lifts with scale, y-offset, and box shadow
 * - Non-selected cards dim when another card is selected
 * - AnimatePresence wraps hand list for exit animations
 * - layout prop for smooth gap-closing when cards leave
 * - Hover animation on hand cards
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const handPanelPath = path.resolve(
  __dirname,
  "../routes/game-room/HandPanel.tsx"
);
describe("US-UXP-010: Hand card selection and deselection motion", () => {
  const handPanel = fs.readFileSync(handPanelPath, "utf-8");

  // ─── motion.button for hand cards ───
  it("HandPanel uses motion.button for hand cards", () => {
    expect(handPanel).toContain("motion.button");
  });

  // ─── Selected card lift animation ───
  it("HandPanel animates selected card with y offset and scale", () => {
    // Selected card should lift (negative y) and scale up
    expect(handPanel).toMatch(/scale:\s*1\.1/);
    expect(handPanel).toMatch(/y:\s*-8/);
  });

  // ─── Box shadow glow on selected card ───
  it("HandPanel applies box shadow glow on selected card", () => {
    expect(handPanel).toMatch(/boxShadow/);
  });

  // ─── Non-selected cards dim ───
  it("HandPanel dims non-selected cards when a card is selected", () => {
    expect(handPanel).toMatch(/opacity.*0\.7/);
  });

  // ─── AnimatePresence for exit animations ───
  it("HandPanel uses AnimatePresence for card exit", () => {
    expect(handPanel).toContain("AnimatePresence");
  });

  // ─── layout prop for smooth gap-closing ───
  it("HandPanel cards have layout prop for gap-closing animation", () => {
    expect(handPanel).toMatch(/layout/);
  });

  // ─── whileHover for preview lift ───
  it("HandPanel has whileHover for card preview lift", () => {
    expect(handPanel).toContain("whileHover");
  });

  // ─── Exit animation on card removal ───
  it("HandPanel cards have exit animation (scale to 0)", () => {
    expect(handPanel).toMatch(/exit=\{\{.*scale:\s*0/s);
  });

});
