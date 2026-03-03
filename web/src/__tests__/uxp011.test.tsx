/**
 * US-UXP-011: Sidebar callout and feedback entrance animations
 *
 * Covers:
 * - Last move callout has slide-in entrance/exit animation
 * - Mists feedback has slide-in entrance/exit animation
 * - Turn indicator animates on change (pulse/scale)
 * - Mobile drawer animates height open/close
 * - Capture/Plus/Elemental callouts already animated (verify still present)
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const activeGameViewPath = path.resolve(
  __dirname,
  "../routes/game-room/ActiveGameView.tsx"
);
const actionPanelPath = path.resolve(
  __dirname,
  "../routes/game-room/ActionPanel.tsx"
);

describe("US-UXP-011: Sidebar callout and feedback entrance animations", () => {
  const activeGameView = fs.readFileSync(activeGameViewPath, "utf-8");
  const actionPanel = fs.readFileSync(actionPanelPath, "utf-8");

  // ─── Last move callout animation ───
  it("Last move callout uses motion.div with entrance animation", () => {
    expect(activeGameView).toContain("last move callout");
    // Should use motion.div, not plain div
    expect(activeGameView).toMatch(/motion\.div[\s\S]*?last move callout/);
  });

  it("Last move callout has slide-in from right (x: 20)", () => {
    // initial={{ opacity: 0, x: 20 }} for slide-in entrance
    expect(activeGameView).toMatch(/lastmove-/);
  });

  it("Last move callout wrapped in AnimatePresence for exit animation", () => {
    // AnimatePresence should wrap the last move section
    expect(activeGameView).toMatch(
      /AnimatePresence[\s\S]*?lastmove-[\s\S]*?last move callout/
    );
  });

  // ─── Mists feedback animation ───
  it("Mists feedback uses motion.div with entrance animation", () => {
    expect(activeGameView).toContain("mists feedback");
    expect(activeGameView).toMatch(/motion\.div[\s\S]*?mists feedback/);
  });

  it("Mists feedback wrapped in AnimatePresence for exit animation", () => {
    expect(activeGameView).toMatch(
      /AnimatePresence[\s\S]*?mists-[\s\S]*?mists feedback/
    );
  });

  // ─── Turn indicator animation ───
  it("ActionPanel imports motion and AnimatePresence", () => {
    expect(actionPanel).toMatch(
      /import.*motion.*AnimatePresence.*from\s+["']motion\/react["']/
    );
  });

  it("Turn label uses motion.p with entrance animation", () => {
    expect(actionPanel).toContain("motion.p");
    expect(actionPanel).toMatch(/key=.*my-turn|opp-turn/);
  });

  it("Turn label animates with scale on change", () => {
    expect(actionPanel).toMatch(/scale:\s*0\.9/);
  });

  it("Turn label wrapped in AnimatePresence for swap animation", () => {
    expect(actionPanel).toMatch(/AnimatePresence[\s\S]*?motion\.p/);
  });

  // ─── Mobile drawer height animation ───
  it("Mobile drawer uses motion.div for height animation", () => {
    expect(activeGameView).toContain("mobile-drawer");
    expect(activeGameView).toMatch(/height.*auto/);
  });

  it("Mobile drawer wrapped in AnimatePresence for enter/exit", () => {
    expect(activeGameView).toMatch(
      /AnimatePresence[\s\S]*?mobile-drawer/
    );
  });

  it("Mobile drawer animates from height 0 to auto", () => {
    expect(activeGameView).toMatch(/height:\s*0/);
    expect(activeGameView).toMatch(/height.*"auto"/);
  });

  // ─── Existing animations still present ───
  it("Capture feedback still has AnimatePresence + motion.div", () => {
    expect(activeGameView).toMatch(
      /AnimatePresence[\s\S]*?capture-feedback/
    );
  });

  it("Plus callout still has AnimatePresence + motion.div", () => {
    expect(activeGameView).toMatch(
      /AnimatePresence[\s\S]*?plus-feedback/
    );
  });

  it("Elemental callout still has AnimatePresence + motion.div", () => {
    expect(activeGameView).toMatch(
      /AnimatePresence[\s\S]*?elemental-feedback/
    );
  });

  it("Score numbers still animate with AnimatePresence popLayout", () => {
    expect(activeGameView).toContain('mode="popLayout"');
    expect(activeGameView).toContain("motion.span");
  });
});
