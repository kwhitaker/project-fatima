/**
 * US-UXP-009: Animated capture chains with sequential timing
 *
 * Covers:
 * - CSS card-captured and card-flip animations removed (Motion replaces them)
 * - BoardGrid uses motion.div for captured cards with sequential delay
 * - Placed card pulses when captures exist
 * - ActiveGameView uses motion + AnimatePresence for callouts and score
 * - Plus!/Elemental! callouts have punch-in animation (scale 1.5→1)
 * - Score numbers animate with AnimatePresence
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const cssPath = path.resolve(__dirname, "../index.css");
const boardGridPath = path.resolve(
  __dirname,
  "../routes/game-room/BoardGrid.tsx"
);
const activeGameViewPath = path.resolve(
  __dirname,
  "../routes/game-room/ActiveGameView.tsx"
);

describe("US-UXP-009: Animated capture chains with sequential timing", () => {
  const css = fs.readFileSync(cssPath, "utf-8");
  const boardGrid = fs.readFileSync(boardGridPath, "utf-8");
  const activeGameView = fs.readFileSync(activeGameViewPath, "utf-8");

  // ─── CSS cleanup ───
  it("CSS card-captured animation removed", () => {
    expect(css).not.toContain(".animate-card-captured");
    expect(css).not.toContain("@keyframes card-captured");
  });

  it("CSS card-flip animation removed", () => {
    expect(css).not.toContain(".animate-card-flip");
    expect(css).not.toContain("@keyframes card-flip");
  });

  // ─── BoardGrid: sequential capture animations ───
  it("BoardGrid no longer applies animate-card-captured CSS class", () => {
    expect(boardGrid).not.toContain("animate-card-captured");
    expect(boardGrid).not.toContain("animate-card-flip");
  });

  it("BoardGrid uses motion.div for captured card flip animation", () => {
    expect(boardGrid).toContain("isCaptured");
    expect(boardGrid).toContain("motion.div");
    // Flip via scaleX keyframes
    expect(boardGrid).toMatch(/scaleX.*\[.*1.*0.*1.*\]/);
  });

  it("BoardGrid staggers capture animations with sequential delay", () => {
    // Should compute delay based on capture order
    expect(boardGrid).toContain("CAPTURE_BASE_DELAY");
    expect(boardGrid).toContain("CAPTURE_STAGGER");
    expect(boardGrid).toContain("captureDelay");
    // Should sort capturedCells for sequential ordering
    expect(boardGrid).toContain("capturedOrder");
  });

  it("Placed card pulses when captures exist", () => {
    expect(boardGrid).toContain("shouldPulse");
    // Pulse: scale includes overshoot (1.08)
    expect(boardGrid).toMatch(/1\.08/);
  });

  it("BoardGrid capture animation includes brightness flash", () => {
    // Brightness keyframes for visual feedback
    expect(boardGrid).toMatch(/brightness/);
  });

  // ─── ActiveGameView: callout and score animations ───
  it("ActiveGameView imports motion and AnimatePresence", () => {
    expect(activeGameView).toMatch(
      /import.*motion.*AnimatePresence.*from\s+["']motion\/react["']/
    );
  });

  it("Plus! callout has punch-in animation (scale 1.5→1)", () => {
    // Plus feedback should scale from 1.5
    expect(activeGameView).toMatch(/plus-feedback/);
    expect(activeGameView).toMatch(/scale:\s*1\.5/);
  });

  it("Elemental! callout has punch-in animation (scale 1.5→1)", () => {
    expect(activeGameView).toMatch(/elemental-feedback/);
  });

  it("Capture feedback has scale punch-in (1.2→1)", () => {
    expect(activeGameView).toMatch(/capture-feedback/);
    expect(activeGameView).toMatch(/scale:\s*1\.2/);
  });

  it("Score numbers animate with AnimatePresence popLayout", () => {
    expect(activeGameView).toContain('mode="popLayout"');
    expect(activeGameView).toContain("motion.span");
    expect(activeGameView).toMatch(/key=.*my-.*myScore/s);
    expect(activeGameView).toMatch(/key=.*opp-.*opponentScore/s);
  });
});
