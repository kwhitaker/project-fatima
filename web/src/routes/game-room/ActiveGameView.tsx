import type React from "react";

import type { Archetype, CardDefinition, GameState, PlayerState } from "@/lib/api";
import { cn } from "@/lib/utils";
import { BoardGrid } from "@/routes/game-room/BoardGrid";
import { ArchetypeModal } from "@/routes/game-room/ArchetypeModal";
import { HandDrawer } from "@/routes/game-room/HandDrawer";

export function ActiveGameView({
  game,
  myIndex,
  myPlayer,
  opponentPlayer,
  myScore,
  opponentScore,
  cardDefs,
  selectedCard,
  onSelectCard,
  movePending,
  moveError,
  usePower,
  onUsePowerChange,
  powerSide,
  onPowerSideToggle,
  placedCells,
  capturedCells,
  onPlaceCard,
  onPreviewCard,
  drawerHeight,
  drawerRef,
  drawerOpen,
  onToggleDrawer,
  leaving,
  onOpenLeaveConfirm,
  showLeaveConfirm,
  onCloseLeaveConfirm,
  onConfirmLeave,
  archetypePending,
  archetypeError,
  onSelectArchetype,
}: {
  game: GameState;
  myIndex: number;
  myPlayer?: PlayerState;
  opponentPlayer?: PlayerState;
  myScore: number;
  opponentScore: number;
  cardDefs: Map<string, CardDefinition>;
  selectedCard: string | null;
  onSelectCard: (cardKey: string | null) => void;
  movePending: boolean;
  moveError: string | null;
  usePower: boolean;
  onUsePowerChange: (next: boolean) => void;
  powerSide: string | null;
  onPowerSideToggle: (side: "n" | "e" | "s" | "w") => void;
  placedCells: Set<number>;
  capturedCells: Set<number>;
  onPlaceCard: (cellIndex: number) => void | Promise<void>;
  onPreviewCard: (cardKey: string, def?: CardDefinition) => void;
  drawerHeight: number;
  drawerRef: React.RefObject<HTMLDivElement | null>;
  drawerOpen: boolean;
  onToggleDrawer: () => void;
  leaving: boolean;
  onOpenLeaveConfirm: () => void;
  showLeaveConfirm: boolean;
  onCloseLeaveConfirm: () => void;
  onConfirmLeave: () => void;
  archetypePending: boolean;
  archetypeError: string | null;
  onSelectArchetype: (archetype: Archetype) => void | Promise<void>;
}) {
  const canPlace =
    !!myPlayer?.archetype &&
    game.current_player_index === myIndex &&
    selectedCard !== null &&
    !movePending &&
    (!usePower ||
      !(myPlayer?.archetype === "skulker" || myPlayer?.archetype === "presence") ||
      powerSide !== null);

  return (
    <>
      <div className="flex-1 min-h-0 overflow-y-auto" style={{ paddingBottom: drawerHeight + 12 }}>
        <div className="space-y-4">
          {/* Turn indicator */}
          <p className="text-lg font-semibold">
            {game.current_player_index === myIndex ? "Your turn" : "Opponent's turn"}
          </p>

          {/* Score */}
          <p className="text-sm text-muted-foreground">
            Score — You: {myScore} | Opponent: {opponentScore}
          </p>

          {/* Last move callout */}
          {game.last_move != null && (
            <div
              className="text-sm p-2 rounded border bg-muted border-border text-muted-foreground dark:bg-muted/40 dark:text-muted-foreground"
              aria-label="last move callout"
              aria-live="polite"
            >
              {game.last_move.player_index === myIndex ? "You" : "Opponent"} played{" "}
              <span className="font-medium">
                {cardDefs.get(game.last_move.card_key)?.name ?? game.last_move.card_key}
              </span>
            </div>
          )}

          {/* Mists feedback */}
          {game.last_move != null && (
            <div
              className={cn(
                "p-3 rounded border text-sm",
                game.last_move.mists_effect === "fog" &&
                  "bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-950/50 dark:border-blue-800 dark:text-blue-300",
                game.last_move.mists_effect === "omen" &&
                  "bg-purple-50 border-purple-200 text-purple-800 dark:bg-purple-950/50 dark:border-purple-800 dark:text-purple-300",
                game.last_move.mists_effect === "none" &&
                  "bg-muted border-border text-muted-foreground"
              )}
              aria-label="mists feedback"
            >
              <span className="font-medium">Mists (roll: {game.last_move.mists_roll})</span>
              {game.last_move.mists_effect === "fog" && " — Fog: −2 to comparisons"}
              {game.last_move.mists_effect === "omen" && " — Omen: +2 to comparisons"}
            </div>
          )}

          {/* Capture feedback: single flip or combo */}
          {capturedCells.size > 0 && (
            <div
              className={cn(
                "text-sm font-semibold p-2 rounded border",
                capturedCells.size === 1
                  ? "bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/50 dark:border-amber-800 dark:text-amber-300"
                  : "bg-purple-50 border-purple-200 text-purple-800 dark:bg-purple-950/50 dark:border-purple-800 dark:text-purple-300"
              )}
              aria-live="polite"
              aria-label="capture feedback"
            >
              {capturedCells.size === 1
                ? "1 card captured!"
                : `Combo! ×${capturedCells.size} captured`}
            </div>
          )}

          {/* Board */}
          <BoardGrid
            board={game.board}
            myIndex={myIndex}
            canPlace={canPlace}
            onCellClick={(i) => void onPlaceCard(i)}
            onCellInspect={(cardKey) => onPreviewCard(cardKey, cardDefs.get(cardKey))}
            placedCells={placedCells}
            capturedCells={capturedCells}
            cardDefs={cardDefs}
            lastMoveCellIndex={game.last_move?.cell_index ?? null}
          />

          {/* Move error */}
          {moveError && <p className="text-destructive text-sm">{moveError}</p>}
        </div>
      </div>

      <ArchetypeModal
        open={!!myPlayer && !myPlayer.archetype}
        pending={archetypePending}
        error={archetypeError}
        onSelect={onSelectArchetype}
      />

      <HandDrawer
        drawerRef={drawerRef}
        open={drawerOpen}
        onToggle={onToggleDrawer}
        game={game}
        myIndex={myIndex}
        myPlayer={myPlayer}
        opponentPlayer={opponentPlayer}
        cardDefs={cardDefs}
        selectedCard={selectedCard}
        onSelectCard={onSelectCard}
        movePending={movePending}
        usePower={usePower}
        onUsePowerChange={onUsePowerChange}
        powerSide={powerSide}
        onPowerSideToggle={onPowerSideToggle}
        onPreviewCard={onPreviewCard}
        leaving={leaving}
        onOpenLeaveConfirm={onOpenLeaveConfirm}
        showLeaveConfirm={showLeaveConfirm}
        onCloseLeaveConfirm={onCloseLeaveConfirm}
        onConfirmLeave={onConfirmLeave}
      />
    </>
  );
}
