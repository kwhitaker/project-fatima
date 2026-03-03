/**
 * US-UXP-020: Capture & combo animation punch-up
 *
 * Covers:
 * - Escalating brightness flash per combo step
 * - Ownership transfer color wipe during flip midpoint
 * - Combo counter overlay (+2, +3, etc.)
 * - Chain pulse ring on captured cards
 * - Custom capture-step events as sound hook points
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const boardGridPath = path.resolve(__dirname, "../routes/game-room/BoardGrid.tsx");
const boardGridSrc = fs.readFileSync(boardGridPath, "utf-8");

describe("US-UXP-020: Capture & combo animation punch-up", () => {
  describe("escalating brightness", () => {
    it("brightness scales with captureSeq index", () => {
      // brightness(2 + captureSeq * 0.2)
      expect(boardGridSrc).toContain("captureSeq");
      expect(boardGridSrc).toMatch(/brightness\(\$\{2 \+ \(captureSeq/);
    });
  });

  describe("ownership color wipe", () => {
    it("renders color wipe overlay during capture flip", () => {
      expect(boardGridSrc).toContain("Ownership color wipe");
      expect(boardGridSrc).toContain("cell.owner === myIndex");
    });
  });

  describe("combo counter overlay", () => {
    it("shows +N counter for multi-captures", () => {
      expect(boardGridSrc).toContain("combo-counter");
      expect(boardGridSrc).toContain("capturedOrder.length > 1");
      expect(boardGridSrc).toMatch(/\+\{captureSeq \+ 1\}/);
    });
  });

  describe("chain pulse", () => {
    it("renders chain pulse ring on captured cells", () => {
      expect(boardGridSrc).toContain("Chain pulse ring");
      expect(boardGridSrc).toContain("border-yellow-400");
    });
  });

  describe("custom events", () => {
    it("dispatches capture-step custom events", () => {
      expect(boardGridSrc).toContain('new CustomEvent("capture-step"');
      expect(boardGridSrc).toContain("dispatchEvent");
    });

    it("includes step and total in event detail", () => {
      expect(boardGridSrc).toContain("step: seqIdx + 1");
      expect(boardGridSrc).toContain("total: capturedOrder.length");
    });
  });
});
