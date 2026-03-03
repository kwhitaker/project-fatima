/**
 * US-UXP-006: 8-bit stepped animations for card capture and flip
 *
 * Verifies that old CSS animations were removed (replaced by Motion in US-UXP-009).
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const cssPath = path.resolve(__dirname, "../index.css");

describe("US-UXP-006: 8-bit stepped animations", () => {
  const css = fs.readFileSync(cssPath, "utf-8");

  it("CSS card-captured/card-flip removed (replaced by Motion in US-UXP-009)", () => {
    expect(css).not.toContain(".animate-card-captured");
    expect(css).not.toContain("@keyframes card-captured");
    expect(css).not.toContain(".animate-card-flip");
    expect(css).not.toContain("@keyframes card-flip");
  });
});
