import { Button } from "@/components/ui/button";
import type { CardDefinition, PlayerState } from "@/lib/api";
import { cn } from "@/lib/utils";

export function ActionPanel({
  isMyTurn,
  selectedCard,
  selectedCardDef,
  onDeselectCard,
  movePending,
  myPlayer,
  usePower,
  onUsePowerChange,
  powerSide,
  onPowerSideToggle,
}: {
  isMyTurn: boolean;
  selectedCard: string | null;
  selectedCardDef?: CardDefinition;
  onDeselectCard: () => void;
  movePending: boolean;
  myPlayer?: PlayerState;
  usePower: boolean;
  onUsePowerChange: (next: boolean) => void;
  powerSide: string | null;
  onPowerSideToggle: (side: "n" | "e" | "s" | "w") => void;
}) {
  const hasArchetype = !!myPlayer?.archetype;
  const powerAvailable =
    hasArchetype && !myPlayer!.archetype_used && isMyTurn;
  const needsDirection =
    usePower &&
    (myPlayer?.archetype === "skulker" || myPlayer?.archetype === "presence");

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
  } else if (needsDirection && powerSide === null) {
    stepText = "Choose a direction for your power";
  } else {
    stepText = "Choose a cell";
  }

  return (
    <div
      className="rounded border border-border bg-muted/30 p-2 space-y-1 dark:bg-muted/20"
      aria-label="action panel"
    >
      {/* Turn label */}
      <p
        className={cn(
          "text-sm font-semibold",
          !isMyTurn && "text-muted-foreground"
        )}
      >
        {isMyTurn ? "Your turn" : "Opponent's turn"}
      </p>

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
            onClick={onDeselectCard}
            disabled={movePending}
          >
            Cancel
          </Button>
        </div>
      )}

      {/* Archetype power controls */}
      {powerAvailable && (
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              aria-label="Use Power"
              checked={usePower}
              onChange={(e) => onUsePowerChange(e.target.checked)}
              disabled={movePending}
            />
            Use Power
          </label>
          {needsDirection && (
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
        </div>
      )}
    </div>
  );
}
