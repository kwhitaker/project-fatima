/**
 * US-DR-004: DraftingGameView component tests.
 * Renders the draft phase UI, verifies 8 cards shown, selection, confirm behavior,
 * and tier constraint enforcement (max 1 T3, max 2 T2).
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";

import { DraftingGameView } from "@/routes/game-room/DraftingGameView";
import type { CardDefinition, GameState, PlayerState } from "@/lib/api";
import { makeGame, makePlayer } from "./helpers";

function makeCardDef(key: string, tier: number = 1): CardDefinition {
  return {
    card_key: key,
    character_key: key,
    name: `Card ${key}`,
    version: "1.0",
    tier,
    rarity: 50,
    is_named: false,
    sides: { n: 5, e: 5, s: 5, w: 5 },
    set: "test",
    tags: [],
    element: "shadow",
  };
}

// 8-card deal: 2xT3, 3xT2, 3xT1 (matches new DEAL_TIER_SLOTS)
const DEAL_KEYS = ["t3a", "t3b", "t2a", "t2b", "t2c", "t1a", "t1b", "t1c"];
const DEAL_TIERS: Record<string, number> = {
  t3a: 3, t3b: 3,
  t2a: 2, t2b: 2, t2c: 2,
  t1a: 1, t1b: 1, t1c: 1,
};

function makeDraftingGame(): { game: GameState; cardDefs: Map<string, CardDefinition> } {
  const opponentKeys = DEAL_KEYS.map((k) => `o-${k}`);
  const player: PlayerState = {
    ...makePlayer("user-123"),
    deal: DEAL_KEYS,
    hand: [],
  };
  const opponent: PlayerState = {
    ...makePlayer("opponent"),
    deal: opponentKeys,
    hand: [],
  };
  const game = makeGame({
    status: "drafting",
    players: [player, opponent],
  });
  const cardDefs = new Map<string, CardDefinition>(
    [...DEAL_KEYS, ...opponentKeys].map((k) => {
      const baseKey = k.startsWith("o-") ? k.slice(2) : k;
      return [k, makeCardDef(k, DEAL_TIERS[baseKey] ?? 1)];
    })
  );
  return { game, cardDefs };
}

describe("DraftingGameView", () => {
  let onSubmitDraft: ReturnType<typeof vi.fn>;
  let onLeave: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onSubmitDraft = vi.fn().mockResolvedValue(undefined);
    onLeave = vi.fn();
  });

  it("renders 8 dealt cards", () => {
    const { game, cardDefs } = makeDraftingGame();
    render(
      <DraftingGameView
        game={game}
        myIndex={0}
        cardDefs={cardDefs}
        onSubmitDraft={onSubmitDraft}
        leaving={false}
        onLeave={onLeave}
      />
    );

    const cardList = screen.getByRole("list", { name: /dealt cards/i });
    const cards = within(cardList).getAllByRole("listitem");
    expect(cards).toHaveLength(8);
  });

  it("allows toggling cards on and off", async () => {
    const user = userEvent.setup();
    const { game, cardDefs } = makeDraftingGame();
    render(
      <DraftingGameView
        game={game}
        myIndex={0}
        cardDefs={cardDefs}
        onSubmitDraft={onSubmitDraft}
        leaving={false}
        onLeave={onLeave}
      />
    );

    const firstCard = screen.getByRole("listitem", { name: /Card t3a/i }).closest("button")
      ?? screen.getAllByRole("listitem")[0];
    await user.click(firstCard);
    expect(firstCard).toHaveAttribute("aria-pressed", "true");

    // Click again to deselect
    await user.click(firstCard);
    expect(firstCard).toHaveAttribute("aria-pressed", "false");
  });

  it("enables confirm button only when 5 cards selected", async () => {
    const user = userEvent.setup();
    const { game, cardDefs } = makeDraftingGame();
    render(
      <DraftingGameView
        game={game}
        myIndex={0}
        cardDefs={cardDefs}
        onSubmitDraft={onSubmitDraft}
        leaving={false}
        onLeave={onLeave}
      />
    );

    const confirmBtn = screen.getByRole("button", { name: /confirm 5 cards/i });
    expect(confirmBtn).toBeDisabled();

    // Select 5 valid cards: t3a(T3), t2a(T2), t2b(T2), t1a(T1), t1b(T1)
    const cards = screen.getAllByRole("listitem");
    const validIndices = [0, 2, 3, 5, 6]; // t3a, t2a, t2b, t1a, t1b
    for (const i of validIndices) {
      await user.click(cards[i]);
    }

    expect(confirmBtn).toBeEnabled();
  });

  it("calls onSubmitDraft with selected cards on confirm", async () => {
    const user = userEvent.setup();
    const { game, cardDefs } = makeDraftingGame();
    render(
      <DraftingGameView
        game={game}
        myIndex={0}
        cardDefs={cardDefs}
        onSubmitDraft={onSubmitDraft}
        leaving={false}
        onLeave={onLeave}
      />
    );

    // Select 5 valid cards: t3a, t2a, t2b, t1a, t1b
    const cards = screen.getAllByRole("listitem");
    const validIndices = [0, 2, 3, 5, 6];
    for (const i of validIndices) {
      await user.click(cards[i]);
    }

    const confirmBtn = screen.getByRole("button", { name: /confirm 5 cards/i });
    await user.click(confirmBtn);

    expect(onSubmitDraft).toHaveBeenCalledWith(
      expect.arrayContaining(["t3a", "t2a", "t2b", "t1a", "t1b"])
    );
  });

  it("shows waiting state after player has drafted", () => {
    const { game, cardDefs } = makeDraftingGame();
    // Player already drafted: deal is empty, hand is populated
    const draftedGame = {
      ...game,
      players: [
        { ...game.players[0], deal: [], hand: DEAL_KEYS.slice(0, 5) },
        game.players[1],
      ],
    };
    render(
      <DraftingGameView
        game={draftedGame}
        myIndex={0}
        cardDefs={cardDefs}
        onSubmitDraft={onSubmitDraft}
        leaving={false}
        onLeave={onLeave}
      />
    );

    expect(screen.getByText(/waiting for opponent/i)).toBeTruthy();
  });

  it("shows spectator message for non-participants", () => {
    const { game, cardDefs } = makeDraftingGame();
    render(
      <DraftingGameView
        game={game}
        myIndex={-1}
        cardDefs={cardDefs}
        onSubmitDraft={onSubmitDraft}
        leaving={false}
        onLeave={onLeave}
      />
    );

    expect(screen.getByText(/players are drafting/i)).toBeTruthy();
  });

  it("shows tier constraint instructions", () => {
    const { game, cardDefs } = makeDraftingGame();
    render(
      <DraftingGameView
        game={game}
        myIndex={0}
        cardDefs={cardDefs}
        onSubmitDraft={onSubmitDraft}
        leaving={false}
        onLeave={onLeave}
      />
    );

    expect(screen.getByText(/max 1 Tier 3/i)).toBeTruthy();
    expect(screen.getByText(/max 2 Tier 2/i)).toBeTruthy();
  });

  it("shows tier badge on each card", () => {
    const { game, cardDefs } = makeDraftingGame();
    render(
      <DraftingGameView
        game={game}
        myIndex={0}
        cardDefs={cardDefs}
        onSubmitDraft={onSubmitDraft}
        leaving={false}
        onLeave={onLeave}
      />
    );

    // T3 cards should have a tier badge
    const cardList = screen.getByRole("list", { name: /dealt cards/i });
    const badges = within(cardList).getAllByText(/^T[123]$/);
    expect(badges).toHaveLength(8); // Every card gets a tier badge
  });

  it("disables remaining T3 cards after selecting 1 T3", async () => {
    const user = userEvent.setup();
    const { game, cardDefs } = makeDraftingGame();
    render(
      <DraftingGameView
        game={game}
        myIndex={0}
        cardDefs={cardDefs}
        onSubmitDraft={onSubmitDraft}
        leaving={false}
        onLeave={onLeave}
      />
    );

    const cards = screen.getAllByRole("listitem");
    // First card is t3a (T3), select it
    await user.click(cards[0]);
    expect(cards[0]).toHaveAttribute("aria-pressed", "true");

    // Second card is t3b (T3), should be disabled
    expect(cards[1]).toBeDisabled();
  });

  it("disables remaining T2 cards after selecting 2 T2", async () => {
    const user = userEvent.setup();
    const { game, cardDefs } = makeDraftingGame();
    render(
      <DraftingGameView
        game={game}
        myIndex={0}
        cardDefs={cardDefs}
        onSubmitDraft={onSubmitDraft}
        leaving={false}
        onLeave={onLeave}
      />
    );

    const cards = screen.getAllByRole("listitem");
    // Cards[2] = t2a, Cards[3] = t2b, Cards[4] = t2c
    await user.click(cards[2]); // select t2a
    await user.click(cards[3]); // select t2b

    // t2c should be disabled now (tier limit reached)
    expect(cards[4]).toBeDisabled();
  });

  it("does not allow selecting more than 5 cards", async () => {
    const user = userEvent.setup();
    const { game, cardDefs } = makeDraftingGame();
    render(
      <DraftingGameView
        game={game}
        myIndex={0}
        cardDefs={cardDefs}
        onSubmitDraft={onSubmitDraft}
        leaving={false}
        onLeave={onLeave}
      />
    );

    // Select all 8 cards (only first 5 should stick)
    const cards = screen.getAllByRole("listitem");
    for (const card of cards) {
      await user.click(card);
    }

    const selected = cards.filter((c) => c.getAttribute("aria-pressed") === "true");
    expect(selected).toHaveLength(5);
  });
});
