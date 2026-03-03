import type { CardDefinition, GameState, PlayerState } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ELEMENT_SYMBOLS } from "@/routes/game-room/BoardGrid";
import { cardEmoji, tierClass } from "@/routes/game-room/CardFace";
import { cardTitle } from "@/routes/game-room/cardTitle";
import { motion } from "motion/react";

export function HandPanel({
  game,
  myIndex,
  myPlayer,
  cardDefs,
  selectedCard,
  onSelectCard,
  movePending,
  onPreviewCard,
}: {
  game: GameState;
  myIndex: number;
  myPlayer?: PlayerState;
  cardDefs: Map<string, CardDefinition>;
  selectedCard: string | null;
  onSelectCard: (cardKey: string | null) => void;
  movePending: boolean;
  onPreviewCard: (cardKey: string, def?: CardDefinition) => void;
}) {
  const isMyTurn = game.current_player_index === myIndex;

  return (
    <div aria-label="hand panel">
      <p className="text-sm font-heading font-medium mb-1">Your hand</p>
      <motion.div
        className="flex gap-2 flex-wrap"
        initial="hidden"
        animate="visible"
        variants={{ visible: { transition: { staggerChildren: 0.05 } } }}
      >
        {myPlayer?.hand.map((cardKey) => {
          const def = cardDefs.get(cardKey);
          const displayName = def?.name ?? cardKey;
          const disabled =
            !myPlayer?.archetype ||
            !isMyTurn ||
            movePending;
          return (
            <motion.div
              key={cardKey}
              className="relative"
              variants={{
                hidden: { opacity: 0, y: 20 },
                visible: { opacity: 1, y: 0 },
              }}
              transition={{ type: "spring", stiffness: 300, damping: 24 }}
            >
              <button
                onClick={() => onSelectCard(selectedCard === cardKey ? null : cardKey)}
                disabled={disabled}
                title={cardTitle(cardKey, def)}
                className={cn(
                  "flex aspect-square w-20 sm:w-24 flex-col items-center justify-between p-1.5 sm:p-2 border-2 border-border rounded-none text-xs sm:text-sm transition-transform hover:scale-105",
                  "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                  selectedCard === cardKey
                    ? "border-primary bg-primary/10 ring-2 ring-primary/50 scale-105 shadow-md cursor-pointer"
                    : "border-border hover:border-primary hover:bg-accent/80 cursor-pointer",
                  tierClass(def?.tier)
                )}
                aria-pressed={selectedCard === cardKey}
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
              <button
                aria-label={`inspect ${displayName}`}
                onClick={() => onPreviewCard(cardKey, def)}
                title={`Preview: ${cardTitle(cardKey, def)}`}
                className="absolute -top-2 -right-2 w-5 h-5 rounded-none bg-muted border-2 border-border text-[10px] leading-none flex items-center justify-center hover:bg-accent cursor-pointer dark:bg-zinc-800 dark:border-zinc-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
                tabIndex={0}
              >
                ⓘ
              </button>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
