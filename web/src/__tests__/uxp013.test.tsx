/**
 * US-UXP-013: Emoji card faces from character mapping
 *
 * Covers:
 * - card-emojis.json is bundled and loadable
 * - cardEmoji helper returns correct emoji by character_key
 * - cardEmoji returns undefined for unknown keys
 * - CardDefinition includes character_key
 * - CardFace, HandPanel, CardInspectPreview reference cardEmoji
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

import cardEmojis from "@/lib/card-emojis.json";
import { cardEmoji } from "@/routes/game-room/CardFace";

const apiPath = path.resolve(__dirname, "../lib/api-types.generated.ts");
const cardFacePath = path.resolve(__dirname, "../routes/game-room/CardFace.tsx");
const boardGridPath = path.resolve(__dirname, "../routes/game-room/BoardGrid.tsx");
const handPanelPath = path.resolve(__dirname, "../routes/game-room/HandPanel.tsx");
const cardInspectPath = path.resolve(__dirname, "../routes/game-room/CardInspectPreview.tsx");

describe("US-UXP-013: Emoji card faces from character mapping", () => {
  describe("card-emojis.json mapping", () => {
    it("is a non-empty object", () => {
      expect(typeof cardEmojis).toBe("object");
      expect(Object.keys(cardEmojis).length).toBeGreaterThan(0);
    });

    it("contains expected character keys", () => {
      const map = cardEmojis as Record<string, string>;
      expect(map.strahd_von_zarovich).toBe("🧛");
      expect(map.zombie).toBe("🧟");
      expect(map.werewolf).toBe("🌕🐺");
    });

    it("all values are non-empty strings", () => {
      for (const [key, val] of Object.entries(cardEmojis)) {
        expect(typeof val).toBe("string");
        expect((val as string).length).toBeGreaterThan(0);
      }
    });
  });

  describe("cardEmoji helper", () => {
    it("returns correct emoji for known character_key", () => {
      expect(cardEmoji("strahd_von_zarovich")).toBe("🧛");
      expect(cardEmoji("werewolf")).toBe("🌕🐺");
    });

    it("returns undefined for unknown character_key", () => {
      expect(cardEmoji("nonexistent_character")).toBeUndefined();
    });

    it("returns undefined for undefined input", () => {
      expect(cardEmoji(undefined)).toBeUndefined();
    });
  });

  describe("CardDefinition includes character_key", () => {
    it("api.ts CardDefinition has character_key field", () => {
      const src = fs.readFileSync(apiPath, "utf-8");
      expect(src).toMatch(/character_key:\s*string/);
    });
  });

  describe("Component wiring", () => {
    it("CardFace imports card-emojis.json and uses cardEmoji", () => {
      const src = fs.readFileSync(cardFacePath, "utf-8");
      expect(src).toContain("card-emojis.json");
      expect(src).toContain("cardEmoji");
      expect(src).toContain("character_key");
    });

    it("HandPanel imports and uses cardEmoji", () => {
      const src = fs.readFileSync(handPanelPath, "utf-8");
      expect(src).toContain("cardEmoji");
      expect(src).toContain("character_key");
    });

    it("CardInspectPreview imports and uses cardEmoji", () => {
      const src = fs.readFileSync(cardInspectPath, "utf-8");
      expect(src).toContain("cardEmoji");
      expect(src).toContain("character_key");
    });
  });
});
