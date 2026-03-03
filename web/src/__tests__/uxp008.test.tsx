/**
 * US-UXP-008: Install Motion library + animated card placement
 *
 * Covers:
 * - motion is installed as a dependency
 * - CSS animate-card-placed class is removed (replaced by Motion)
 * - BoardGrid uses motion.div for placed card spring animation
 * - BoardGrid uses motion.button with whileHover for empty cells
 * - HandPanel uses motion.div with stagger variants
 * - HandDrawer uses motion.div with stagger variants
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const cssPath = path.resolve(__dirname, "../index.css");
const boardGridPath = path.resolve(
  __dirname,
  "../routes/game-room/BoardGrid.tsx"
);
const handPanelPath = path.resolve(
  __dirname,
  "../routes/game-room/HandPanel.tsx"
);
const handDrawerPath = path.resolve(
  __dirname,
  "../routes/game-room/HandDrawer.tsx"
);
const pkgPath = path.resolve(__dirname, "../../package.json");

describe("US-UXP-008: Motion library + animated card placement", () => {
  const css = fs.readFileSync(cssPath, "utf-8");
  const boardGrid = fs.readFileSync(boardGridPath, "utf-8");
  const handPanel = fs.readFileSync(handPanelPath, "utf-8");
  const handDrawer = fs.readFileSync(handDrawerPath, "utf-8");
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));

  it("motion is listed as a production dependency", () => {
    expect(pkg.dependencies).toHaveProperty("motion");
  });

  it("CSS animate-card-placed class no longer exists", () => {
    expect(css).not.toContain(".animate-card-placed");
    expect(css).not.toContain("@keyframes card-placed");
  });

  it("CSS animate-card-captured removed (replaced by Motion in US-UXP-009)", () => {
    expect(css).not.toContain(".animate-card-captured");
    expect(css).not.toContain("@keyframes card-captured");
  });

  it("BoardGrid imports motion from motion/react", () => {
    expect(boardGrid).toMatch(/import.*motion.*from\s+["']motion\/react["']/);
  });

  it("BoardGrid uses motion.div for placed cards with scale animation", () => {
    expect(boardGrid).toContain("motion.div");
    expect(boardGrid).toContain("isPlaced");
    expect(boardGrid).toContain("initial={{ scale: 0, opacity: 0 }}");
    // Non-pulse uses slam overshoot [0, 1.08, 1], pulse uses [0, 1, 1.08, 1]
    expect(boardGrid).toContain("1.08");
  });

  it("BoardGrid uses motion.button with whileHover for empty cells", () => {
    expect(boardGrid).toContain("motion.button");
    expect(boardGrid).toContain("whileHover");
  });

  it("HandPanel imports motion and uses stagger variants", () => {
    expect(handPanel).toMatch(/import.*motion.*from\s+["']motion\/react["']/);
    expect(handPanel).toContain("staggerChildren");
    expect(handPanel).toContain("motion.div");
    expect(handPanel).toContain("variants");
  });

  it("HandDrawer imports motion and uses stagger variants", () => {
    expect(handDrawer).toMatch(/import.*motion.*from\s+["']motion\/react["']/);
    expect(handDrawer).toContain("staggerChildren");
    expect(handDrawer).toContain("motion.div");
    expect(handDrawer).toContain("variants");
  });

  it("HandPanel hand cards animate in from below with opacity", () => {
    // Each card should have hidden/visible variants with y and opacity
    expect(handPanel).toMatch(/hidden.*opacity.*0.*y.*20/s);
    expect(handPanel).toMatch(/visible.*opacity.*1.*y.*0/s);
  });

  it("HandDrawer hand cards animate in from below with opacity", () => {
    expect(handDrawer).toMatch(/hidden.*opacity.*0.*y.*20/s);
    expect(handDrawer).toMatch(/visible.*opacity.*1.*y.*0/s);
  });
});
