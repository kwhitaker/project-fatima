/**
 * US-UXP-006: 8-bit stepped animations for card capture and flip
 *
 * Covers:
 * - card-captured uses steps(3) timing (CSS)
 * - card-flip keyframes and class exist with steps(3) (CSS)
 * - BoardGrid applies card-flip class to captured cells
 * - card-placed animation is now handled by Motion (US-UXP-008),
 *   so CSS animate-card-placed no longer exists
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

  it("animate-card-captured uses steps(3) timing function", () => {
    const match = css.match(/\.animate-card-captured\s*\{[^}]*\}/);
    expect(match).not.toBeNull();
    expect(match![0]).toContain("steps(3)");
    expect(match![0]).not.toContain("ease-in-out");
  });

  it("card-flip keyframes exist with scaleX squash-and-stretch", () => {
    expect(css).toContain("@keyframes card-flip");
    expect(css).toMatch(/scaleX\(0\.1\)/);
  });

  it("animate-card-flip class uses steps(3) timing", () => {
    const match = css.match(/\.animate-card-flip\s*\{[^}]*\}/);
    expect(match).not.toBeNull();
    expect(match![0]).toContain("steps(3)");
    expect(match![0]).toContain("card-flip");
  });

  it("BoardGrid applies animate-card-flip to captured cells", () => {
    const boardGrid = fs.readFileSync(boardGridPath, "utf-8");
    expect(boardGrid).toContain("animate-card-flip");
    expect(boardGrid).toMatch(/isCaptured.*animate-card-captured.*animate-card-flip/);
  });

  it("card-captured animation duration is 0.55s", () => {
    const match = css.match(/\.animate-card-captured\s*\{[^}]*\}/);
    expect(match![0]).toContain("0.55s");
  });

  it("card-flip animation duration is 0.3s", () => {
    const match = css.match(/\.animate-card-flip\s*\{[^}]*\}/);
    expect(match![0]).toContain("0.3s");
  });
});
