/**
 * US-UXP-008: Install Motion library + animated card placement
 *
 * Covers config-level checks: motion dependency and CSS cleanup.
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const cssPath = path.resolve(__dirname, "../index.css");
const pkgPath = path.resolve(__dirname, "../../package.json");

describe("US-UXP-008: Motion library + animated card placement", () => {
  const css = fs.readFileSync(cssPath, "utf-8");
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));

  it("motion is listed as a production dependency", () => {
    expect(pkg.dependencies).toHaveProperty("motion");
  });

  it("CSS animate-card-placed class no longer exists", () => {
    expect(css).not.toContain(".animate-card-placed");
    expect(css).not.toContain("@keyframes card-placed");
  });

  it("CSS animate-card-captured removed (replaced by Motion in US-UXP-009)", () => {
    expect(css).not.toContain(".animate-card-captured");
    expect(css).not.toContain("@keyframes card-captured");
  });
});
