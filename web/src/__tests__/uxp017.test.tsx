/**
 * US-UXP-017: Castlevania theme audit — buttons & interactive elements
 *
 * Covers:
 * - Button outline variant has visible dark-mode border + bg tint
 * - Button ghost variant uses accent (gold) text color
 * - Archetype buttons promoted to default variant
 * - Game list items use accent hover, not muted
 * - Login inputs have hover:border-accent
 * - Dialogs use bg-card/border-border instead of hardcoded zinc
 * - No hardcoded zinc color classes remain
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const buttonPath = path.resolve(__dirname, "../components/ui/button.tsx");
const archetypeModalPath = path.resolve(__dirname, "../routes/game-room/ArchetypeModal.tsx");
const gamesPath = path.resolve(__dirname, "../routes/Games.tsx");
const loginPath = path.resolve(__dirname, "../routes/Login.tsx");
const gameRulesDialogPath = path.resolve(__dirname, "../routes/game-room/GameRulesDialog.tsx");
const forfeitDialogPath = path.resolve(__dirname, "../routes/game-room/ForfeitDialog.tsx");
const cardInspectPath = path.resolve(__dirname, "../routes/game-room/CardInspectPreview.tsx");
const handDrawerPath = path.resolve(__dirname, "../routes/game-room/HandDrawer.tsx");
const handPanelPath = path.resolve(__dirname, "../routes/game-room/HandPanel.tsx");

describe("US-UXP-017: Castlevania theme audit — buttons & interactive elements", () => {
  const buttonSrc = fs.readFileSync(buttonPath, "utf-8");

  describe("button variants", () => {
    it("outline variant has visible dark-mode border (muted-foreground)", () => {
      expect(buttonSrc).toContain("dark:border-muted-foreground");
    });

    it("outline variant has subtle dark-mode bg tint", () => {
      expect(buttonSrc).toContain("dark:bg-muted/30");
    });

    it("outline variant has hover:border-accent", () => {
      expect(buttonSrc).toContain("hover:border-accent");
    });

    it("ghost variant uses accent text color by default", () => {
      // Ghost buttons should show gold text, not default foreground
      const ghostLine = buttonSrc.match(/ghost:\s*"([^"]+)"/);
      expect(ghostLine).not.toBeNull();
      expect(ghostLine![1]).toContain("text-accent");
    });
  });

  describe("archetype buttons promoted to default variant", () => {
    const archetypeSrc = fs.readFileSync(archetypeModalPath, "utf-8");

    it("archetype selection buttons use default variant (blood-red)", () => {
      expect(archetypeSrc).toContain('variant="default"');
      expect(archetypeSrc).not.toContain('variant="outline"');
    });
  });

  describe("game list hover", () => {
    const gamesSrc = fs.readFileSync(gamesPath, "utf-8");

    it("game list items use accent hover instead of muted", () => {
      expect(gamesSrc).toContain("hover:bg-accent");
      expect(gamesSrc).toContain("hover:border-accent");
      expect(gamesSrc).not.toContain("hover:bg-muted");
    });
  });

  describe("login inputs", () => {
    const loginSrc = fs.readFileSync(loginPath, "utf-8");

    it("inputs have hover:border-accent for gold hover", () => {
      expect(loginSrc).toContain("hover:border-accent");
    });

    it("mode toggle links use accent text color", () => {
      expect(loginSrc).toContain("text-accent");
    });
  });

  describe("no hardcoded zinc colors in src/", () => {
    const srcDir = path.resolve(__dirname, "..");
    const tsxFiles = findTsxFiles(srcDir);

    it("no zinc color classes remain in any TSX file", () => {
      const zincFiles: string[] = [];
      for (const file of tsxFiles) {
        const content = fs.readFileSync(file, "utf-8");
        if (/\bzinc-\d+/.test(content)) {
          zincFiles.push(path.relative(srcDir, file));
        }
      }
      expect(zincFiles).toEqual([]);
    });
  });

  describe("dialogs use theme tokens", () => {
    it("GameRulesDialog uses bg-card and border-border", () => {
      const src = fs.readFileSync(gameRulesDialogPath, "utf-8");
      expect(src).toContain("bg-card");
      expect(src).toContain("border-border");
      expect(src).not.toMatch(/bg-white\b/);
    });

    it("ForfeitDialog uses bg-card and border-border", () => {
      const src = fs.readFileSync(forfeitDialogPath, "utf-8");
      expect(src).toContain("bg-card");
      expect(src).toContain("border-border");
      expect(src).not.toMatch(/bg-white\b/);
    });

    it("CardInspectPreview uses bg-card and border-border", () => {
      const src = fs.readFileSync(cardInspectPath, "utf-8");
      expect(src).toContain("bg-card");
      expect(src).toContain("border-border");
      expect(src).not.toMatch(/bg-white\b/);
    });

    it("HandDrawer uses bg-card instead of bg-white", () => {
      const src = fs.readFileSync(handDrawerPath, "utf-8");
      expect(src).toContain("bg-card");
      expect(src).not.toMatch(/bg-white\b/);
    });
  });

  describe("info buttons use theme hover", () => {
    it("HandPanel info button has hover:border-accent", () => {
      const src = fs.readFileSync(handPanelPath, "utf-8");
      expect(src).toContain("hover:border-accent");
    });

    it("HandDrawer info button has hover:border-accent", () => {
      const src = fs.readFileSync(handDrawerPath, "utf-8");
      expect(src).toContain("hover:border-accent");
    });
  });
});

/** Recursively find all .tsx files under a directory */
function findTsxFiles(dir: string): string[] {
  const results: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && entry.name !== "node_modules") {
      results.push(...findTsxFiles(full));
    } else if (entry.name.endsWith(".tsx")) {
      results.push(full);
    }
  }
  return results;
}
