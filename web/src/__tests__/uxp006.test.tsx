/**
 * US-UXP-006: 8-bit stepped animations for card capture and flip
 *
 * Original story added CSS stepped animations (card-captured, card-flip).
 * US-UXP-009 replaced these with Motion-powered animations.
 * These tests now verify the Motion-based capture animations exist in BoardGrid.
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const cssPath = path.resolve(__dirname, "../index.css");
const boardGridPath = path.resolve(
  __dirname,
  "../routes/game-room/BoardGrid.tsx"
);

describe("US-UXP-006: 8-bit stepped animations", () => {
  const css = fs.readFileSync(cssPath, "utf-8");
  const boardGrid = fs.readFileSync(boardGridPath, "utf-8");

  it("CSS card-captured/card-flip removed (replaced by Motion in US-UXP-009)", () => {
    expect(css).not.toContain(".animate-card-captured");
    expect(css).not.toContain("@keyframes card-captured");
    expect(css).not.toContain(".animate-card-flip");
    expect(css).not.toContain("@keyframes card-flip");
  });

  it("BoardGrid uses Motion for capture flip animation (scaleX keyframes)", () => {
    expect(boardGrid).toContain("isCaptured");
    expect(boardGrid).toMatch(/scaleX.*\[.*1.*0.*1.*\]/);
  });

  it("BoardGrid uses Motion for capture brightness flash", () => {
    expect(boardGrid).toMatch(/brightness/);
  });
});
