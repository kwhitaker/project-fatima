/**
 * US-UXP-004: Retro pixel fonts (Press Start 2P + VT323)
 *
 * Covers:
 * - Google Fonts are loaded in index.html
 * - Tailwind config extends fontFamily with heading and body
 * - CSS sets VT323 as body font and Press Start 2P for headings
 * - Key UI elements use font-heading class
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const webRoot = path.resolve(__dirname, "../..");

describe("US-UXP-004: Retro pixel fonts", () => {
  it("index.html includes Google Fonts link for Press Start 2P and VT323", () => {
    const html = fs.readFileSync(path.join(webRoot, "index.html"), "utf-8");
    expect(html).toContain("Press+Start+2P");
    expect(html).toContain("VT323");
    expect(html).toContain("fonts.googleapis.com");
    expect(html).toContain("fonts.gstatic.com");
  });

  it("theme defines heading and body font families", () => {
    const css = fs.readFileSync(
      path.join(webRoot, "src/index.css"),
      "utf-8"
    );
    expect(css).toContain("--font-heading");
    expect(css).toContain("--font-body");
    expect(css).toContain('"Press Start 2P"');
    expect(css).toContain("VT323");
  });

  it("index.css sets VT323 as body font-family", () => {
    const css = fs.readFileSync(
      path.join(webRoot, "src/index.css"),
      "utf-8"
    );
    expect(css).toContain('"VT323"');
    expect(css).toMatch(/body\s*\{[^}]*font-family.*VT323/);
  });

  it("index.css sets Press Start 2P for heading elements", () => {
    const css = fs.readFileSync(
      path.join(webRoot, "src/index.css"),
      "utf-8"
    );
    expect(css).toContain('"Press Start 2P"');
    expect(css).toMatch(/h1.*h2.*h3/s);
  });

  it("button component uses font-heading class", () => {
    const button = fs.readFileSync(
      path.join(webRoot, "src/components/ui/button.tsx"),
      "utf-8"
    );
    expect(button).toContain("font-heading");
  });

  it("ActionPanel turn label uses font-heading", () => {
    const panel = fs.readFileSync(
      path.join(webRoot, "src/routes/game-room/ActionPanel.tsx"),
      "utf-8"
    );
    expect(panel).toContain("font-heading");
  });

  it("ActiveGameView score and callouts use font-heading", () => {
    const view = fs.readFileSync(
      path.join(webRoot, "src/routes/game-room/ActiveGameView.tsx"),
      "utf-8"
    );
    // Score bar
    const fontHeadingCount = (view.match(/font-heading/g) ?? []).length;
    // Score + Plus callout + Elemental callout + capture feedback + Info & Actions
    expect(fontHeadingCount).toBeGreaterThanOrEqual(4);
  });

  it("CompleteGameView result text uses font-heading", () => {
    const view = fs.readFileSync(
      path.join(webRoot, "src/routes/game-room/CompleteGameView.tsx"),
      "utf-8"
    );
    expect(view).toContain("font-heading");
  });

  it("HandPanel and HandDrawer labels use font-heading", () => {
    const handPanel = fs.readFileSync(
      path.join(webRoot, "src/routes/game-room/HandPanel.tsx"),
      "utf-8"
    );
    const handDrawer = fs.readFileSync(
      path.join(webRoot, "src/routes/game-room/HandDrawer.tsx"),
      "utf-8"
    );
    expect(handPanel).toContain("font-heading");
    expect(handDrawer).toContain("font-heading");
  });

  it("body font size is at least 18px for VT323 readability", () => {
    const css = fs.readFileSync(
      path.join(webRoot, "src/index.css"),
      "utf-8"
    );
    expect(css).toMatch(/body\s*\{[^}]*font-size:\s*18px/);
  });

  it("fonts include monospace fallback", () => {
    const css = fs.readFileSync(
      path.join(webRoot, "src/index.css"),
      "utf-8"
    );
    // Both font families should have monospace fallback
    expect(css).toMatch(/--font-heading.*monospace/s);
    expect(css).toMatch(/--font-body.*monospace/s);
  });
});
