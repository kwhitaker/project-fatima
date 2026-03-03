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
const handDrawerPath = path.resolve(
  __dirname,
  "../routes/game-room/HandDrawer.tsx"
);

describe("US-UXP-010: Hand card selection and deselection motion", () => {
  const handPanel = fs.readFileSync(handPanelPath, "utf-8");
  const handDrawer = fs.readFileSync(handDrawerPath, "utf-8");

  // ─── motion.button for hand cards ───
  it("HandPanel uses motion.button for hand cards", () => {
    expect(handPanel).toContain("motion.button");
  });

  it("HandDrawer uses motion.button for hand cards", () => {
    expect(handDrawer).toContain("motion.button");
  });

  // ─── Selected card lift animation ───
  it("HandPanel animates selected card with y offset and scale", () => {
    // Selected card should lift (negative y) and scale up
    expect(handPanel).toMatch(/scale:\s*1\.1/);
    expect(handPanel).toMatch(/y:\s*-8/);
  });

  it("HandDrawer animates selected card with y offset and scale", () => {
    expect(handDrawer).toMatch(/scale:\s*1\.1/);
    expect(handDrawer).toMatch(/y:\s*-8/);
  });

  // ─── Box shadow glow on selected card ───
  it("HandPanel applies box shadow glow on selected card", () => {
    expect(handPanel).toMatch(/boxShadow/);
  });

  it("HandDrawer applies box shadow glow on selected card", () => {
    expect(handDrawer).toMatch(/boxShadow/);
  });

  // ─── Non-selected cards dim ───
  it("HandPanel dims non-selected cards when a card is selected", () => {
    expect(handPanel).toMatch(/opacity.*0\.7/);
  });

  it("HandDrawer dims non-selected cards when a card is selected", () => {
    expect(handDrawer).toMatch(/opacity.*0\.7/);
  });

  // ─── AnimatePresence for exit animations ───
  it("HandPanel uses AnimatePresence for card exit", () => {
    expect(handPanel).toContain("AnimatePresence");
  });

  it("HandDrawer uses AnimatePresence for card exit", () => {
    expect(handDrawer).toContain("AnimatePresence");
  });

  // ─── layout prop for smooth gap-closing ───
  it("HandPanel cards have layout prop for gap-closing animation", () => {
    expect(handPanel).toMatch(/layout/);
  });

  it("HandDrawer cards have layout prop for gap-closing animation", () => {
    expect(handDrawer).toMatch(/layout/);
  });

  // ─── whileHover for preview lift ───
  it("HandPanel has whileHover for card preview lift", () => {
    expect(handPanel).toContain("whileHover");
  });

  it("HandDrawer has whileHover for card preview lift", () => {
    expect(handDrawer).toContain("whileHover");
  });

  // ─── Exit animation on card removal ───
  it("HandPanel cards have exit animation (scale to 0)", () => {
    expect(handPanel).toMatch(/exit=\{\{.*scale:\s*0/s);
  });

  it("HandDrawer cards have exit animation (scale to 0)", () => {
    expect(handDrawer).toMatch(/exit=\{\{.*scale:\s*0/s);
  });
});
