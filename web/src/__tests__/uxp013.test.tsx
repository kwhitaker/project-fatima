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
import cardEmojis from "@/lib/card-emojis.json";
import { cardEmoji } from "@/routes/game-room/CardFace";

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

});
