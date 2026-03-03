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

const apiPath = path.resolve(__dirname, "../lib/api.ts");
const apiSrc = fs.readFileSync(apiPath, "utf-8");

const completeViewPath = path.resolve(__dirname, "../routes/game-room/CompleteGameView.tsx");
const completeViewSrc = fs.readFileSync(completeViewPath, "utf-8");

const boardGridPath = path.resolve(__dirname, "../routes/game-room/BoardGrid.tsx");
const boardGridSrc = fs.readFileSync(boardGridPath, "utf-8");

describe("US-UXP-023: Auto-complete statistically decided games", () => {
  describe("GameResult type", () => {
    it("includes early_finish field", () => {
      expect(apiSrc).toContain("early_finish");
    });
  });

  describe("CompleteGameView early finish messaging", () => {
    it("reads early_finish from game result", () => {
      expect(completeViewSrc).toContain("early_finish");
    });

    it("shows 'Inevitable victory' for winner", () => {
      expect(completeViewSrc).toContain("Inevitable victory");
    });

    it("shows 'The darkness claims this match' for loser", () => {
      expect(completeViewSrc).toContain("The darkness claims this match");
    });

    it("passes earlyFinish prop to BoardGrid", () => {
      expect(completeViewSrc).toContain("earlyFinish={earlyFinish}");
    });
  });

  describe("BoardGrid unplayed cell styling", () => {
    it("accepts earlyFinish prop", () => {
      expect(boardGridSrc).toContain("earlyFinish");
    });

    it("shows cross marker on unplayed cells when earlyFinish", () => {
      expect(boardGridSrc).toContain("✕");
      expect(boardGridSrc).toContain("unplayed cell");
    });

    it("uses dashed border for unplayed cells", () => {
      expect(boardGridSrc).toContain("border-dashed");
    });

    it("dims unplayed cells with reduced opacity", () => {
      expect(boardGridSrc).toContain("opacity-50");
    });
  });
});
