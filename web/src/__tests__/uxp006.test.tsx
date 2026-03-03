/**
 * US-UXP-006: 8-bit stepped animations for card placement and capture
 *
 * Covers:
 * - card-placed uses steps(4) timing
 * - card-captured uses steps(3) timing
 * - card-flip keyframes and class exist with steps(3)
 * - BoardGrid applies card-flip class to captured cells
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

  it("animate-card-placed uses steps(4) timing function", () => {
    const match = css.match(/\.animate-card-placed\s*\{[^}]*\}/);
    expect(match).not.toBeNull();
    expect(match![0]).toContain("steps(4)");
    expect(match![0]).not.toContain("ease-out");
  });

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
    // Flip should be applied alongside card-captured
    expect(boardGrid).toMatch(/isCaptured.*animate-card-captured.*animate-card-flip/);
  });

  it("card-placed animation duration is 0.4s", () => {
    const match = css.match(/\.animate-card-placed\s*\{[^}]*\}/);
    expect(match![0]).toContain("0.4s");
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
