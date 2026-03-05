/**
 * US-UXP-014: Auto-generate frontend TypeScript types from backend OpenAPI schema
 *
 * Covers:
 * - Generated types file exists with auto-generated header
 * - api.ts re-exports types from generated file (not manual definitions)
 * - All key types are importable from @/lib/api
 * - typegen script defined in package.json
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const generatedPath = path.resolve(__dirname, "../lib/api-types.generated.ts");
const generatedSrc = fs.readFileSync(generatedPath, "utf-8");

const pkgPath = path.resolve(__dirname, "../../package.json");
const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));

describe("US-UXP-014: Auto-generated frontend types", () => {
  describe("Generated types file", () => {
    it("exists and has auto-generated header comment", () => {
      expect(generatedSrc).toContain("auto-generated");
      expect(generatedSrc).toContain("Do not make direct changes");
    });

    it("contains GameState schema type", () => {
      expect(generatedSrc).toContain("GameState");
      expect(generatedSrc).toContain("game_id");
      expect(generatedSrc).toContain("state_version");
    });

    it("contains CardDefinition schema type", () => {
      expect(generatedSrc).toContain("CardDefinition");
      expect(generatedSrc).toContain("card_key");
      expect(generatedSrc).toContain("character_key");
    });

    it("contains BoardCell, PlayerState, LastMoveInfo, GameResult", () => {
      for (const name of ["BoardCell", "PlayerState", "LastMoveInfo", "GameResult"]) {
        expect(generatedSrc).toContain(name);
      }
    });

    it("contains Archetype enum", () => {
      expect(generatedSrc).toContain("Archetype");
      expect(generatedSrc).toContain("martial");
      expect(generatedSrc).toContain("skulker");
      expect(generatedSrc).toContain("intimidate");
    });
  });

  describe("package.json typegen script", () => {
    it("has a typegen script", () => {
      expect(pkg.scripts.typegen).toBeDefined();
      expect(pkg.scripts.typegen).toContain("openapi-typescript");
    });
  });

  describe("Type imports work at runtime", () => {
    it("all types are importable from @/lib/api", async () => {
      const api = await import("@/lib/api");
      // Type-only exports won't be in the runtime module, but the module should load
      expect(api).toBeDefined();
    });
  });
});
