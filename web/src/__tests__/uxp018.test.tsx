/**
 * US-UXP-018: Login page branding (title + vampire emoji)
 *
 * Covers:
 * - Vampire emoji visual centerpiece above login form
 * - "Yugi-Strahd" title in Press Start 2P font
 * - Tagline "A Curse of Strahd Card Game" in VT323
 * - Existing form functionality preserved
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const loginPath = path.resolve(__dirname, "../routes/Login.tsx");
const loginSrc = fs.readFileSync(loginPath, "utf-8");

describe("US-UXP-018: Login page branding", () => {
  it("has a vampire emoji (🧛) as visual centerpiece", () => {
    expect(loginSrc).toContain("🧛");
  });

  it("displays 'Yugi-Strahd' title with font-heading", () => {
    expect(loginSrc).toContain("Yugi-Strahd");
    expect(loginSrc).toMatch(/font-heading/);
  });

  it("displays tagline 'A Curse of Strahd Card Game'", () => {
    expect(loginSrc).toContain("A Curse of Strahd Card Game");
  });

  it("still renders sign-in form with submit button", () => {
    expect(loginSrc).toContain('type="submit"');
    expect(loginSrc).toContain('type="email"');
    expect(loginSrc).toContain('type="password"');
  });

  it("still supports mode switching (signup, forgot)", () => {
    expect(loginSrc).toContain("switchMode");
    expect(loginSrc).toContain('"signup"');
    expect(loginSrc).toContain('"forgot"');
  });
});
