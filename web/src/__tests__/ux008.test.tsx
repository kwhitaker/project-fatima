/**
 * US-UX-008: API: add GET /cards for UI card rendering
 *
 * Covers:
 * - listCards() fetches from /api/cards with auth header
 * - listCards() returns cards with required display fields (card_key, name, version, sides)
 * - getCardDefinitions() returns a Map keyed by card_key
 * - getCardDefinitions() resolves card_key to display fields (name + N/E/S/W sides)
 * - getCardDefinitions() caches results (only one fetch per session)
 */
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: "test-token" } },
      }),
    },
  },
}));

const MOCK_CARDS = [
  {
    card_key: "card_001",
    name: "Test Card",
    version: "v1",
    sides: { n: 4, e: 5, s: 3, w: 2 },
  },
  {
    card_key: "card_002",
    name: "Another Card",
    version: "v2",
    sides: { n: 7, e: 3, s: 8, w: 1 },
  },
];

describe("US-UX-008: Card definitions cache layer", () => {
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.resetModules();
    mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(MOCK_CARDS),
    });
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("listCards fetches from /api/cards", async () => {
    const { listCards } = await import("@/lib/api");
    const cards = await listCards();
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/cards",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      })
    );
    expect(cards).toHaveLength(2);
  });

  it("listCards returns cards with required display fields", async () => {
    const { listCards } = await import("@/lib/api");
    const cards = await listCards();
    const card = cards[0];
    expect(card).toHaveProperty("card_key");
    expect(card).toHaveProperty("name");
    expect(card).toHaveProperty("version");
    expect(card).toHaveProperty("sides");
    expect(card.sides).toMatchObject({ n: 4, e: 5, s: 3, w: 2 });
  });

  it("getCardDefinitions returns a Map keyed by card_key", async () => {
    const { getCardDefinitions } = await import("@/lib/api");
    const defs = await getCardDefinitions();
    expect(defs).toBeInstanceOf(Map);
    expect(defs.size).toBe(2);
    expect(defs.has("card_001")).toBe(true);
    expect(defs.has("card_002")).toBe(true);
  });

  it("getCardDefinitions resolves card_key to display name and sides", async () => {
    const { getCardDefinitions } = await import("@/lib/api");
    const defs = await getCardDefinitions();
    const card = defs.get("card_001");
    expect(card?.name).toBe("Test Card");
    expect(card?.sides.n).toBe(4);
    expect(card?.sides.e).toBe(5);
    expect(card?.sides.s).toBe(3);
    expect(card?.sides.w).toBe(2);
  });

  it("getCardDefinitions caches results (only one fetch per session)", async () => {
    const { getCardDefinitions } = await import("@/lib/api");
    await getCardDefinitions();
    await getCardDefinitions(); // second call should reuse cache
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});
