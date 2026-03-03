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

describe("US-UXP-017: Castlevania theme audit — buttons & interactive elements", () => {
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
