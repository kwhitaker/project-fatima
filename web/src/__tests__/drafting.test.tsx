/**
 * US-DR-008: DraftingGameView component tests.
 * Renders the draft phase UI, verifies 7 cards shown, selection, confirm behavior.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";

import { DraftingGameView } from "@/routes/game-room/DraftingGameView";
import type { CardDefinition, GameState, PlayerState } from "@/lib/api";
import { makeGame, makePlayer } from "./helpers";

function makeCardDef(key: string): CardDefinition {
  return {
    card_key: key,
    character_key: key,
    name: `Card ${key}`,
    version: "1.0",
    tier: 1,
    rarity: 50,
    is_named: false,
    sides: { n: 5, e: 5, s: 5, w: 5 },
    set: "test",
    tags: [],
    element: "shadow",
  };
}

const DEAL_KEYS = ["d0", "d1", "d2", "d3", "d4", "d5", "d6"];

function makeDraftingGame(): { game: GameState; cardDefs: Map<string, CardDefinition> } {
  const player: PlayerState = {
    ...makePlayer("user-123"),
    deal: DEAL_KEYS,
    hand: [],
  };
  const opponent: PlayerState = {
    ...makePlayer("opponent"),
    deal: ["o0", "o1", "o2", "o3", "o4", "o5", "o6"],
    hand: [],
  };
  const game = makeGame({
    status: "drafting",
    players: [player, opponent],
  });
  const cardDefs = new Map<string, CardDefinition>(
    [...DEAL_KEYS, "o0", "o1", "o2", "o3", "o4", "o5", "o6"].map((k) => [k, makeCardDef(k)])
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

  it("renders 7 dealt cards", () => {
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
    expect(cards).toHaveLength(7);
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

    const firstCard = screen.getByRole("listitem", { name: /Card d0/i }).closest("button")
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

    // Select 5 cards
    const cards = screen.getAllByRole("listitem");
    for (let i = 0; i < 5; i++) {
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

    // Select first 5 cards
    const cards = screen.getAllByRole("listitem");
    for (let i = 0; i < 5; i++) {
      await user.click(cards[i]);
    }

    const confirmBtn = screen.getByRole("button", { name: /confirm 5 cards/i });
    await user.click(confirmBtn);

    expect(onSubmitDraft).toHaveBeenCalledWith(
      expect.arrayContaining(DEAL_KEYS.slice(0, 5))
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

    // Select all 7 cards (only first 5 should stick)
    const cards = screen.getAllByRole("listitem");
    for (const card of cards) {
      await user.click(card);
    }

    const selected = cards.filter((c) => c.getAttribute("aria-pressed") === "true");
    expect(selected).toHaveLength(5);
  });
});
