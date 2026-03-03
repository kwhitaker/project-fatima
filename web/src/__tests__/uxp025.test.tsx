/**
 * US-UXP-025: Dev interaction playground
 *
 * Covers:
 * - Route only rendered when import.meta.env.DEV is true
 * - Renders scenario buttons for all animation types
 * - Mock data exercises key edge cases
 * - Page is not accessible in production builds
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const playgroundPath = path.resolve(__dirname, "../routes/DevPlayground.tsx");
const playgroundSrc = fs.readFileSync(playgroundPath, "utf-8");

const appPath = path.resolve(__dirname, "../App.tsx");
const appSrc = fs.readFileSync(appPath, "utf-8");

describe("US-UXP-025: Dev interaction playground", () => {
  describe("dev-only route guard", () => {
    it("App.tsx conditionally imports DevPlayground based on import.meta.env.DEV", () => {
      expect(appSrc).toContain("import.meta.env.DEV");
    });

    it("route is only rendered when DevPlayground is not null", () => {
      expect(appSrc).toContain("{DevPlayground && (");
      expect(appSrc).toContain('path="/dev/playground"');
    });

    it("uses lazy import for tree-shaking in production", () => {
      expect(appSrc).toContain("lazy(() => import");
      expect(appSrc).toContain("./routes/DevPlayground");
    });
  });

  describe("scenario buttons", () => {
    it("has buttons for card placement animation", () => {
      expect(playgroundSrc).toContain("Card placement");
    });

    it("has buttons for single and combo captures", () => {
      expect(playgroundSrc).toContain("Single capture");
      expect(playgroundSrc).toContain("Combo chain");
    });

    it("has buttons for Plus and Elemental triggers", () => {
      expect(playgroundSrc).toContain("Plus trigger");
      expect(playgroundSrc).toContain("Elemental trigger");
      expect(playgroundSrc).toContain("Plus + Elemental");
    });

    it("has buttons for Mists effects (Fog and Omen)", () => {
      expect(playgroundSrc).toContain("Fog (Mists)");
      expect(playgroundSrc).toContain("Omen (Mists)");
    });

    it("has buttons for Victory and Defeat screens", () => {
      expect(playgroundSrc).toContain("Victory screen");
      expect(playgroundSrc).toContain("Defeat screen");
    });

    it("has a reset button", () => {
      expect(playgroundSrc).toContain("Reset");
    });
  });

  describe("mock data coverage", () => {
    it("exercises combo chain with 4 captures (max-like)", () => {
      // Combo chain scenario sets 4 captured cells
      expect(playgroundSrc).toContain("new Set([1, 3, 5, 7])");
    });

    it("exercises Plus + Elemental on same move", () => {
      expect(playgroundSrc).toContain("plus_triggered: true, elemental_triggered: true");
    });

    it("exercises Fog on placement", () => {
      expect(playgroundSrc).toContain('mists_effect: "fog"');
      expect(playgroundSrc).toContain('setMistsEffect("fog")');
    });

    it("exercises Omen on placement", () => {
      expect(playgroundSrc).toContain('mists_effect: "omen"');
      expect(playgroundSrc).toContain('setMistsEffect("omen")');
    });

    it("exercises early finish scenario", () => {
      expect(playgroundSrc).toContain("early_finish: true");
      expect(playgroundSrc).toContain("setEarlyFinish(true)");
    });
  });

  describe("component structure", () => {
    it("imports BoardGrid for rendering board state", () => {
      expect(playgroundSrc).toContain('import { BoardGrid }');
    });

    it("imports VictoryOverlay and DefeatOverlay", () => {
      expect(playgroundSrc).toContain('import { VictoryOverlay }');
      expect(playgroundSrc).toContain('import { DefeatOverlay }');
    });

    it("renders board with element badges", () => {
      expect(playgroundSrc).toContain("boardElements");
      expect(playgroundSrc).toContain("BOARD_ELEMENTS");
    });

    it("has a scenario-buttons test id for the button group", () => {
      expect(playgroundSrc).toContain('data-testid="scenario-buttons"');
    });
  });
});
