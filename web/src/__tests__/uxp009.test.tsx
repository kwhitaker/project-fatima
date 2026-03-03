/**
 * US-UXP-009: Animated capture chains with sequential timing
 *
 * Verifies CSS animations were removed (replaced by Motion).
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const cssPath = path.resolve(__dirname, "../index.css");

describe("US-UXP-009: Animated capture chains with sequential timing", () => {
  const css = fs.readFileSync(cssPath, "utf-8");

  it("CSS card-captured animation removed", () => {
    expect(css).not.toContain(".animate-card-captured");
    expect(css).not.toContain("@keyframes card-captured");
  });

  it("CSS card-flip animation removed", () => {
    expect(css).not.toContain(".animate-card-flip");
    expect(css).not.toContain("@keyframes card-flip");
  });
});
