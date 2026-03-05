import { Button } from "@/components/ui/button";
import type { CardDefinition, PlayerState } from "@/lib/api";
import { AI_THINKING_TEXT } from "@/lib/ai-constants";
import { cn } from "@/lib/utils";
import { useGameRoom } from "@/routes/game-room/GameRoomContext";
import { motion, AnimatePresence } from "motion/react";

export function ActionPanel({
  isMyTurn,
  selectedCardDef,
  myPlayer,
  opponentPlayer,
}: {
  isMyTurn: boolean;
  selectedCardDef?: CardDefinition;
  myPlayer?: PlayerState;
  opponentPlayer?: PlayerState;
}) {
  const {
    selectedCard,
    onSelectCard,
    movePending,
    usePower,
    onUsePowerChange,
    powerSide,
    onPowerSideToggle,
    intimidatePendingCell,
    onCancelIntimidatePending,
  } = useGameRoom();
  const hasArchetype = !!myPlayer?.archetype;
  const powerAvailable =
    hasArchetype && !myPlayer!.archetype_used && isMyTurn;
  const needsSkulkerDirection =
    usePower && myPlayer?.archetype === "skulker";
  const needsMartialDirection =
    usePower && myPlayer?.archetype === "martial";
  const isIntimidate = usePower && myPlayer?.archetype === "intimidate";

  // Determine step text (shown below the turn label on my turn)
  let stepText: string | null;
  if (!isMyTurn) {
    stepText = null; // turn label covers it
  } else if (movePending) {
    stepText = "Placing…";
  } else if (!hasArchetype) {
    stepText = "Pick an archetype to begin";
  } else if (selectedCard === null) {
    stepText = "Select a card";
  } else if ((needsSkulkerDirection || needsMartialDirection) && powerSide === null) {
    stepText = "Choose a direction for your power";
  } else if (isIntimidate && intimidatePendingCell !== null) {
    stepText = "Click an adjacent opponent card to debuff";
  } else {
    stepText = "Choose a cell";
  }

  return (
    <div
      className="rounded border border-border bg-muted/30 p-2 space-y-1 dark:bg-muted/20"
      aria-label="action panel"
    >
      {/* Turn label */}
      <AnimatePresence mode="wait">
        <motion.p
          key={isMyTurn ? "my-turn" : "opp-turn"}
          className={cn(
            "text-xs font-heading font-semibold leading-relaxed",
            !isMyTurn && "text-muted-foreground"
          )}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        >
          {isMyTurn
            ? "Your turn"
            : opponentPlayer?.player_type === "ai" && opponentPlayer.ai_difficulty
              ? AI_THINKING_TEXT[opponentPlayer.ai_difficulty]
              : "Opponent's turn"}
        </motion.p>
      </AnimatePresence>

      {/* Step indicator (my turn only) */}
      {stepText !== null && (
        <p className="text-sm text-muted-foreground" data-testid="action-step">
          {stepText}
        </p>
      )}

      {/* Selected card summary + cancel */}
      {selectedCard !== null && (
        <div className="flex items-center gap-2" aria-label="selected card summary">
          <span className="text-sm">
            {selectedCardDef?.name ?? selectedCard}
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => onSelectCard(null)}
            disabled={movePending}
          >
            Cancel
          </Button>
        </div>
      )}

      {/* Archetype power controls */}
      {powerAvailable && (
        <div className="space-y-2">
          <button
            type="button"
            aria-label="Use Power"
            aria-pressed={usePower}
            disabled={movePending}
            onClick={() => onUsePowerChange(!usePower)}
            className={cn(
              "w-full py-1.5 px-3 rounded border-2 text-sm font-heading font-semibold cursor-pointer transition-colors",
              usePower
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-muted/50 text-foreground border-border hover:border-primary/50",
              !usePower && "animate-pulse",
            )}
          >
            ⚡ Use Power
          </button>
          {needsSkulkerDirection && (
            <div className="flex gap-2">
              {(["n", "e", "s", "w"] as const).map((side) => (
                <Button
                  key={side}
                  variant={powerSide === side ? "default" : "outline"}
                  size="sm"
                  onClick={() => onPowerSideToggle(side)}
                >
                  {side}
                </Button>
              ))}
            </div>
          )}
          {needsMartialDirection && (
            <div className="flex gap-2" data-testid="martial-direction-toggle">
              {(["cw", "ccw"] as const).map((dir) => (
                <Button
                  key={dir}
                  variant={powerSide === dir ? "default" : "outline"}
                  size="sm"
                  onClick={() => onPowerSideToggle(dir)}
                >
                  {dir === "cw" ? "CW" : "CCW"}
                </Button>
              ))}
            </div>
          )}
          {isIntimidate && intimidatePendingCell !== null && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                Placing at cell {intimidatePendingCell}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={onCancelIntimidatePending}
              >
                Cancel
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
