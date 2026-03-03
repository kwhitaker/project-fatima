import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const SRC = path.resolve(__dirname, "..");

function read(relPath: string): string {
  return fs.readFileSync(path.join(SRC, relPath), "utf-8");
}

describe("US-UXP-012 — Page transitions and modal animations", () => {
  it("Login page uses motion for entrance animation", () => {
    const src = read("routes/Login.tsx");
    expect(src).toContain('from "motion/react"');
    expect(src).toContain("motion.div");
    expect(src).toContain("initial=");
    expect(src).toContain("animate=");
  });

  it("Games page uses motion for page fade and list stagger", () => {
    const src = read("routes/Games.tsx");
    expect(src).toContain('from "motion/react"');
    expect(src).toContain("motion.div");
    expect(src).toContain("motion.ul");
    expect(src).toContain("motion.li");
    expect(src).toContain("staggerChildren");
  });

  it("ResetPassword page uses motion for entrance animation", () => {
    const src = read("routes/ResetPassword.tsx");
    expect(src).toContain('from "motion/react"');
    expect(src).toContain("motion.div");
  });

  it("ArchetypeModal has AnimatePresence entrance/exit", () => {
    const src = read("routes/game-room/ArchetypeModal.tsx");
    expect(src).toContain("AnimatePresence");
    expect(src).toContain("motion.div");
    expect(src).toContain("exit=");
    // Should NOT have early return null
    expect(src).not.toContain("if (!open) return null");
  });

  it("ForfeitDialog has AnimatePresence entrance/exit", () => {
    const src = read("routes/game-room/ForfeitDialog.tsx");
    expect(src).toContain("AnimatePresence");
    expect(src).toContain("motion.div");
    expect(src).toContain("exit=");
    expect(src).not.toContain("if (!open) return null");
  });

  it("CardInspectPreview uses motion for entrance/exit", () => {
    const src = read("routes/game-room/CardInspectPreview.tsx");
    expect(src).toContain('from "motion/react"');
    expect(src).toContain("motion.div");
    expect(src).toContain("exit=");
  });

  it("GameRoom wraps CardInspectPreview in AnimatePresence", () => {
    const src = read("routes/GameRoom.tsx");
    expect(src).toContain("AnimatePresence");
    expect(src).toContain("CardInspectPreview");
  });

  it("GameRulesDialog has AnimatePresence entrance/exit", () => {
    const src = read("routes/game-room/GameRulesDialog.tsx");
    expect(src).toContain("AnimatePresence");
    expect(src).toContain("motion.div");
    expect(src).toContain("exit=");
    expect(src).not.toContain("if (!open) return null");
  });

  it("Modal animations use scale + opacity pattern", () => {
    for (const file of [
      "routes/game-room/ArchetypeModal.tsx",
      "routes/game-room/ForfeitDialog.tsx",
      "routes/game-room/CardInspectPreview.tsx",
      "routes/game-room/GameRulesDialog.tsx",
    ]) {
      const src = read(file);
      expect(src).toContain("scale: 0.9");
      expect(src).toContain("opacity: 0");
    }
  });

  it("Transition durations are snappy (0.15-0.25s range)", () => {
    for (const file of [
      "routes/game-room/ArchetypeModal.tsx",
      "routes/game-room/ForfeitDialog.tsx",
      "routes/game-room/GameRulesDialog.tsx",
    ]) {
      const src = read(file);
      expect(src).toContain("duration: 0.15");
    }
  });
});
