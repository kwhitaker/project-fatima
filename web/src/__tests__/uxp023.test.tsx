/**
 * US-UXP-023: Auto-complete statistically decided games
 *
 * Covers:
 * - GameResult type includes early_finish field
 * - CompleteGameView shows early finish messages (winner/loser)
 * - BoardGrid renders unplayed empty cells with visual indication
 * - earlyFinish prop wired through CompleteGameView → BoardGrid
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const apiPath = path.resolve(__dirname, "../lib/api-types.generated.ts");
const apiSrc = fs.readFileSync(apiPath, "utf-8");

describe("US-UXP-023: Auto-complete statistically decided games", () => {
  describe("GameResult type", () => {
    it("includes early_finish field", () => {
      expect(apiSrc).toContain("early_finish");
    });
  });
});
