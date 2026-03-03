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

  it("ModalShell provides AnimatePresence entrance/exit for all modals", () => {
    const src = read("components/ui/ModalShell.tsx");
    expect(src).toContain("AnimatePresence");
    expect(src).toContain("motion.div");
    expect(src).toContain("exit=");
    expect(src).toContain("scale: 0.9");
    expect(src).toContain("opacity: 0");
    expect(src).toContain("duration: 0.15");
  });

  it("All 4 modal components use ModalShell", () => {
    for (const file of [
      "routes/game-room/ArchetypeModal.tsx",
      "routes/game-room/ForfeitDialog.tsx",
      "routes/game-room/CardInspectPreview.tsx",
      "routes/game-room/GameRulesDialog.tsx",
    ]) {
      const src = read(file);
      expect(src).toContain("ModalShell");
      // Should NOT have early return null
      expect(src).not.toContain("if (!open) return null");
    }
  });

  it("GameRoom renders CardInspectPreview with open prop", () => {
    const src = read("routes/GameRoom.tsx");
    expect(src).toContain("CardInspectPreview");
    expect(src).toContain("open=");
  });
});
