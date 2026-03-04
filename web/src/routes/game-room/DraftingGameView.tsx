import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { CardDefinition, GameState } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ELEMENT_SYMBOLS } from "@/routes/game-room/BoardGrid";
import { cardEmoji, tierClass } from "@/routes/game-room/CardFace";
import { cardTitle } from "@/routes/game-room/cardTitle";

const HAND_SIZE = 5;

export function DraftingGameView({
  game,
  myIndex,
  cardDefs,
  onSubmitDraft,
}: {
  game: GameState;
  myIndex: number;
  cardDefs: Map<string, CardDefinition>;
  onSubmitDraft: (selectedCards: string[]) => Promise<void>;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const myPlayer = myIndex >= 0 ? game.players[myIndex] : undefined;
  const deal = myPlayer?.deal ?? [];
  const alreadyDrafted = myPlayer ? myPlayer.deal.length === 0 && myPlayer.hand.length > 0 : false;

  // Non-participant or spectator view
  if (myIndex < 0) {
    return (
      <div className="flex-1 flex items-center justify-center" aria-label="drafting spectator view">
        <p className="text-muted-foreground text-sm">Players are drafting...</p>
      </div>
    );
  }

  // Already submitted draft, waiting for opponent
  if (alreadyDrafted) {
    return (
      <div className="flex-1 flex items-center justify-center" aria-label="draft waiting view">
        <p className="text-muted-foreground text-sm">Waiting for opponent to draft...</p>
      </div>
    );
  }

  const toggleCard = (cardKey: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(cardKey)) {
        next.delete(cardKey);
      } else if (next.size < HAND_SIZE) {
        next.add(cardKey);
      }
      return next;
    });
  };

  const canConfirm = selected.size === HAND_SIZE && !submitting;

  const handleConfirm = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await onSubmitDraft(Array.from(selected));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Draft submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 px-4" aria-label="drafting view">
      <h2 className="text-lg font-heading font-semibold">Draft Phase</h2>
      <p className="text-sm text-muted-foreground text-center max-w-md">
        Select {HAND_SIZE} of your {deal.length} dealt cards to keep for the match.
      </p>
      <p className="text-xs text-muted-foreground">
        {selected.size} / {HAND_SIZE} selected
      </p>

      <div className="flex gap-2 flex-wrap justify-center" role="list" aria-label="dealt cards">
        {deal.map((cardKey) => {
          const def = cardDefs.get(cardKey);
          const displayName = def?.name ?? cardKey;
          const isSelected = selected.has(cardKey);
          const isFull = selected.size >= HAND_SIZE;

          return (
            <button
              key={cardKey}
              role="listitem"
              onClick={() => toggleCard(cardKey)}
              disabled={submitting}
              title={cardTitle(cardKey, def)}
              aria-pressed={isSelected}
              className={cn(
                "relative flex aspect-square w-20 sm:w-24 flex-col items-center justify-between p-1.5 sm:p-2 border-2 rounded-none text-xs sm:text-sm bg-card transition-all",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                isSelected
                  ? "border-primary bg-primary/10 ring-2 ring-primary/50 scale-105 -translate-y-1 cursor-pointer"
                  : isFull
                    ? "border-border opacity-40 cursor-not-allowed"
                    : "border-border hover:border-primary hover:bg-accent/20 cursor-pointer",
                tierClass(def?.tier)
              )}
            >
              {cardEmoji(def?.character_key) && (
                <span className="text-xl sm:text-2xl leading-none select-none" aria-hidden="true">
                  {cardEmoji(def?.character_key)}
                </span>
              )}
              <span className={cn(
                "font-semibold truncate max-w-full text-center",
                cardEmoji(def?.character_key) ? "text-[8px] sm:text-[9px]" : "text-[11px] sm:text-xs"
              )}>
                {displayName}
              </span>
              <div className="flex flex-col items-center mt-1 text-[10px] sm:text-[11px] text-muted-foreground w-full">
                <span>{def ? def.sides.n : ""}</span>
                <div className="flex justify-between w-full px-1">
                  <span>{def ? def.sides.w : ""}</span>
                  <span>{def ? def.sides.e : ""}</span>
                </div>
                <span>{def ? def.sides.s : ""}</span>
              </div>
              {def?.element && (
                <span
                  className="absolute bottom-0 left-0 text-[9px] leading-none p-px opacity-70 select-none pointer-events-none"
                  aria-label={`element ${def.element}`}
                >
                  {ELEMENT_SYMBOLS[def.element] ?? def.element}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {error && <p className="text-destructive text-xs">{error}</p>}

      <Button
        onClick={() => void handleConfirm()}
        disabled={!canConfirm}
        className="cursor-pointer"
      >
        {submitting ? "Submitting..." : `Confirm ${HAND_SIZE} cards`}
      </Button>
    </div>
  );
}
