import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { Archetype, CardDefinition, GameState, PlayerState } from "@/lib/api";
import { cn } from "@/lib/utils";
import { BoardGrid } from "@/routes/game-room/BoardGrid";
import { ArchetypeModal } from "@/routes/game-room/ArchetypeModal";
import { ArchetypePowerAside } from "@/routes/game-room/ArchetypePowerAside";
import { ForfeitDialog } from "@/routes/game-room/ForfeitDialog";
import { HandPanel } from "@/routes/game-room/HandPanel";

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
  leaving,
  onOpenLeaveConfirm,
  showLeaveConfirm,
  onCloseLeaveConfirm,
  onConfirmLeave,
  archetypePending,
  archetypeError,
  onSelectArchetype,
  boardElements,
  selectedCardElement,
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
  leaving: boolean;
  onOpenLeaveConfirm: () => void;
  showLeaveConfirm: boolean;
  onCloseLeaveConfirm: () => void;
  onConfirmLeave: () => void;
  archetypePending: boolean;
  archetypeError: string | null;
  onSelectArchetype: (archetype: Archetype) => void | Promise<void>;
  boardElements?: string[] | null;
  selectedCardElement?: string | null;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const canPlace =
    !!myPlayer?.archetype &&
    game.current_player_index === myIndex &&
    selectedCard !== null &&
    !movePending &&
    (!usePower ||
      !(myPlayer?.archetype === "skulker" || myPlayer?.archetype === "presence") ||
      powerSide !== null);

  const isMyTurn = game.current_player_index === myIndex;

  /* ─── Secondary sidebar content (shared between desktop sidebar & mobile drawer) ─── */
  const secondaryContent = (
    <div className="space-y-4" aria-label="secondary info">
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
            "p-2 rounded border text-sm",
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

      {/* Capture feedback */}
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

      {/* Plus! callout */}
      {game.last_move?.plus_triggered === true && (
        <div
          className="text-sm font-semibold p-2 rounded border bg-cyan-50 border-cyan-200 text-cyan-800 dark:bg-cyan-950/50 dark:border-cyan-800 dark:text-cyan-300"
          aria-live="polite"
          aria-label="plus feedback"
        >
          Plus!
        </div>
      )}

      {/* Elemental! callout */}
      {game.last_move != null && game.last_move.elemental_triggered === true && (
        <div
          className="text-sm font-semibold p-2 rounded border bg-yellow-50 border-yellow-400 text-yellow-900 dark:bg-yellow-950/50 dark:border-yellow-700 dark:text-yellow-300"
          aria-live="polite"
          aria-label="elemental feedback"
        >
          {(() => {
            const elemKey = boardElements?.[game.last_move!.cell_index];
            return elemKey
              ? elemKey.charAt(0).toUpperCase() + elemKey.slice(1) + " Elemental!"
              : "Elemental!";
          })()}
        </div>
      )}

      {/* Opponent hand count */}
      <div>
        <p className="text-xs text-muted-foreground">Opponent's hand</p>
        <p className="text-sm">{opponentPlayer?.hand.length ?? 0} cards</p>
      </div>

      {/* Archetypes */}
      <div className="flex gap-6">
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

      {/* Archetype power details */}
      {(myPlayer?.archetype || opponentPlayer?.archetype) && (
        <div className="grid gap-2">
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

      {/* Leave */}
      <Button variant="outline" size="sm" onClick={onOpenLeaveConfirm} disabled={leaving}>
        Leave Game
      </Button>

      <ForfeitDialog
        open={showLeaveConfirm}
        leaving={leaving}
        onCancel={onCloseLeaveConfirm}
        onConfirm={onConfirmLeave}
      />
    </div>
  );

  return (
    <>
      {/* Main two-column layout: play area (left) + sidebar (right on desktop) */}
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-4">
        {/* ─── Primary play area: board + hand ─── */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Turn & score bar */}
          <div className="flex items-center justify-between">
            <p className="text-lg font-semibold">
              {isMyTurn ? "Your turn" : "Opponent's turn"}
            </p>
            <p className="text-sm text-muted-foreground">
              You: {myScore} | Opp: {opponentScore}
            </p>
          </div>

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
            boardElements={boardElements}
            selectedCardElement={selectedCardElement}
          />

          {/* Move error */}
          {moveError && <p className="text-destructive text-sm">{moveError}</p>}

          {/* Power toggle (near hand, only when relevant) */}
          {myPlayer?.archetype &&
            !myPlayer.archetype_used &&
            isMyTurn && (
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

          {/* Hand panel (always visible, in-flow) */}
          <HandPanel
            game={game}
            myIndex={myIndex}
            myPlayer={myPlayer}
            cardDefs={cardDefs}
            selectedCard={selectedCard}
            onSelectCard={onSelectCard}
            movePending={movePending}
            onPreviewCard={onPreviewCard}
          />
        </div>

        {/* ─── Desktop sidebar (hidden on mobile, visible lg+) ─── */}
        <aside
          className="hidden lg:block w-72 shrink-0 overflow-y-auto"
          aria-label="game sidebar"
        >
          {secondaryContent}
        </aside>

        {/* ─── Mobile secondary drawer (visible below lg) ─── */}
        <div className="lg:hidden">
          <button
            type="button"
            onClick={() => setSidebarOpen((v) => !v)}
            className="w-full flex items-center justify-between px-3 py-2 rounded border border-border bg-muted/50 text-sm cursor-pointer"
            aria-label="toggle secondary info"
            aria-expanded={sidebarOpen}
          >
            <span className="font-medium">Info & Actions</span>
            <span className="text-xs text-muted-foreground">
              {sidebarOpen ? "Hide" : "Show"}
            </span>
          </button>
          {sidebarOpen && (
            <div className="mt-2 p-3 rounded border border-border bg-muted/20">
              {secondaryContent}
            </div>
          )}
        </div>
      </div>

      <ArchetypeModal
        open={!!myPlayer && !myPlayer.archetype}
        pending={archetypePending}
        error={archetypeError}
        onSelect={onSelectArchetype}
      />
    </>
  );
}
