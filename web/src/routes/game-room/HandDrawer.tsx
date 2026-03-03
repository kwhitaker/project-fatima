import { useState, type RefObject } from "react";

import { Button } from "@/components/ui/button";
import type { CardDefinition, GameState, PlayerState } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ArchetypePowerAside } from "@/routes/game-room/ArchetypePowerAside";
import { ELEMENT_SYMBOLS } from "@/routes/game-room/BoardGrid";
import { tierClass } from "@/routes/game-room/CardFace";
import { cardTitle } from "@/routes/game-room/cardTitle";
import { ForfeitDialog } from "@/routes/game-room/ForfeitDialog";
import { motion } from "motion/react";

export function HandDrawer({
  drawerRef,
  open,
  onToggle,
  game,
  myIndex,
  myPlayer,
  opponentPlayer,
  cardDefs,
  selectedCard,
  onSelectCard,
  movePending,
  usePower,
  onUsePowerChange,
  powerSide,
  onPowerSideToggle,
  onPreviewCard,
  leaving,
  onOpenLeaveConfirm,
  showLeaveConfirm,
  onCloseLeaveConfirm,
  onConfirmLeave,
}: {
  drawerRef: RefObject<HTMLDivElement | null>;
  open: boolean;
  onToggle: () => void;
  game: GameState;
  myIndex: number;
  myPlayer?: PlayerState;
  opponentPlayer?: PlayerState;
  cardDefs: Map<string, CardDefinition>;
  selectedCard: string | null;
  onSelectCard: (cardKey: string | null) => void;
  movePending: boolean;
  usePower: boolean;
  onUsePowerChange: (next: boolean) => void;
  powerSide: string | null;
  onPowerSideToggle: (side: "n" | "e" | "s" | "w") => void;
  onPreviewCard: (cardKey: string, def?: CardDefinition) => void;
  leaving: boolean;
  onOpenLeaveConfirm: () => void;
  showLeaveConfirm: boolean;
  onCloseLeaveConfirm: () => void;
  onConfirmLeave: () => void;
}) {
  const [showArchetypePowers, setShowArchetypePowers] = useState(false);

  return (
    <div className="fixed inset-x-0 bottom-0 z-40">
      <div
        ref={drawerRef}
        className="bg-white/95 dark:bg-zinc-900/95 border-2 border-zinc-200 dark:border-zinc-700 rounded-none shadow-[0_-10px_30px_rgba(0,0,0,0.15)]"
      >
        <button
          type="button"
          className="w-full px-4 py-2.5 flex items-center justify-between cursor-pointer"
          aria-label="toggle hand drawer"
          aria-expanded={open}
          onClick={onToggle}
        >
          <div className="flex items-center gap-3">
            <span className="h-1.5 w-12 bg-zinc-300 dark:bg-zinc-700" />
            <span className="text-sm font-heading font-semibold">Hand & Players</span>
          </div>
          <span className="text-xs text-muted-foreground">{open ? "Hide" : "Show"}</span>
        </button>

        <div
          className={cn(
            "overflow-hidden transition-[max-height] duration-200 ease-out",
            open ? "max-h-[60vh]" : "max-h-0"
          )}
        >
          <div className="px-4 pb-4 overflow-y-auto max-h-[60vh]">
            <div className="space-y-4">
              {/* Use Power toggle */}
              {myPlayer?.archetype &&
                !myPlayer.archetype_used &&
                game.current_player_index === myIndex && (
                  <div>
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
                    {usePower &&
                      (myPlayer.archetype === "skulker" ||
                        myPlayer.archetype === "presence") && (
                        <div className="flex gap-2 mt-2">
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

              {/* My hand */}
              <div>
                <p className="text-sm font-heading font-medium mb-1">Your hand</p>
                {game.current_player_index === myIndex && !movePending && (
                  <p className="text-xs text-muted-foreground mb-2">
                    {selectedCard
                      ? `"${selectedCard}" selected — click an empty cell to place it`
                      : "Click a card to select it, then click an empty cell on the board"}
                  </p>
                )}
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
                      game.current_player_index !== myIndex ||
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
                            "flex aspect-square w-24 sm:w-28 flex-col items-center justify-between p-2 border-2 border-border rounded-none text-xs sm:text-sm transition-transform hover:scale-105",
                            "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100",
                            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                            selectedCard === cardKey
                              ? "border-primary bg-primary/10 cursor-pointer"
                              : "border-border hover:border-primary hover:bg-accent/80 cursor-pointer",
                            tierClass(def?.tier)
                          )}
                          aria-pressed={selectedCard === cardKey}
                        >
                          <span className="font-semibold truncate max-w-full text-center">
                            {displayName}
                          </span>
                          <div className="flex flex-col items-center mt-1 text-[11px] sm:text-[12px] text-muted-foreground w-full">
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

              {/* Opponent hand */}
              <div>
                <p className="text-sm font-medium mb-1">Opponent's hand</p>
                <p className="text-sm text-muted-foreground">
                  {opponentPlayer?.hand.length ?? 0} cards
                </p>
              </div>

              {/* Archetypes */}
              <div className="flex gap-8">
                <div>
                  <p className="text-xs text-muted-foreground">Your archetype</p>
                  <p className="text-sm capitalize">{myPlayer?.archetype ?? "None"}</p>
                  {myPlayer?.archetype && (
                    <p className="text-xs text-muted-foreground">
                      {myPlayer.archetype_used ? "Used" : "Available"}
                    </p>
                  )}
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Opponent archetype</p>
                  <p className="text-sm capitalize">{opponentPlayer?.archetype ?? "None"}</p>
                  {opponentPlayer?.archetype && (
                    <p className="text-xs text-muted-foreground">
                      {opponentPlayer.archetype_used ? "Used" : "Available"}
                    </p>
                  )}
                </div>
              </div>

              {(myPlayer?.archetype || opponentPlayer?.archetype) && (
                <div>
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <p className="text-sm font-medium">Archetype powers</p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowArchetypePowers((v) => !v)}
                      className="h-8 px-2"
                      aria-label={
                        showArchetypePowers
                          ? "hide archetype powers"
                          : "show archetype powers"
                      }
                    >
                      {showArchetypePowers ? "Hide" : "Show"}
                    </Button>
                  </div>
                  {showArchetypePowers && (
                    <div className="grid gap-2 sm:grid-cols-2">
                      {myPlayer?.archetype && (
                        <ArchetypePowerAside
                          archetype={myPlayer.archetype}
                          label="your archetype power"
                        />
                      )}
                      {opponentPlayer?.archetype && (
                        <ArchetypePowerAside
                          archetype={opponentPlayer.archetype}
                          label="opponent archetype power"
                        />
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Leave — opens forfeit confirmation dialog */}
              <Button variant="outline" onClick={onOpenLeaveConfirm} disabled={leaving}>
                Leave Game
              </Button>

              <ForfeitDialog
                open={showLeaveConfirm}
                leaving={leaving}
                onCancel={onCloseLeaveConfirm}
                onConfirm={onConfirmLeave}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
