import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import type { Archetype, CardDefinition, GameState, PlayerState } from "@/lib/api";
import { cn } from "@/lib/utils";
import { BoardGrid } from "@/routes/game-room/BoardGrid";
import { ArchetypeModal } from "@/routes/game-room/ArchetypeModal";
import { ArchetypePowerAside } from "@/routes/game-room/ArchetypePowerAside";
import { ForfeitDialog } from "@/routes/game-room/ForfeitDialog";
import { HandPanel } from "@/routes/game-room/HandPanel";
import { ActionPanel } from "@/routes/game-room/ActionPanel";
import { MuteToggle } from "@/routes/game-room/MuteToggle";
import { motion, AnimatePresence } from "motion/react";
import { playPlus, playElemental, playTurnStart } from "@/lib/sounds";

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
  onShowRules,
  intimidatePendingCell,
  onCancelIntimidatePending,
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
  onShowRules: () => void;
  intimidatePendingCell: number | null;
  onCancelIntimidatePending: () => void;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const canPlace =
    !!myPlayer?.archetype &&
    game.current_player_index === myIndex &&
    selectedCard !== null &&
    !movePending &&
    (!usePower ||
      myPlayer?.archetype === "intimidate" ||
      myPlayer?.archetype !== "skulker" ||
      powerSide !== null);

  const isMyTurn = game.current_player_index === myIndex;

  // Sound: play turn start when it becomes my turn
  const prevTurnRef = useRef<boolean | null>(null);
  useEffect(() => {
    if (prevTurnRef.current === false && isMyTurn) {
      playTurnStart();
    }
    prevTurnRef.current = isMyTurn;
  }, [isMyTurn]);

  // Sound: Plus trigger
  const prevPlusRef = useRef<string | null>(null);
  useEffect(() => {
    const key = game.last_move?.plus_triggered ? `${game.last_move.cell_index}` : null;
    if (key && key !== prevPlusRef.current) {
      playPlus();
    }
    prevPlusRef.current = key;
  }, [game.last_move?.plus_triggered, game.last_move?.cell_index]);

  // Sound: Elemental trigger
  const prevElemRef = useRef<string | null>(null);
  useEffect(() => {
    const key = game.last_move?.elemental_triggered ? `${game.last_move.cell_index}` : null;
    if (key && key !== prevElemRef.current) {
      playElemental();
    }
    prevElemRef.current = key;
  }, [game.last_move?.elemental_triggered, game.last_move?.cell_index]);

  /* ─── Secondary sidebar content (shared between desktop sidebar & mobile drawer) ─── */
  const secondaryContent = (
    <div className="space-y-4" aria-label="secondary info">
      {/* Last move callout */}
      <AnimatePresence>
        {game.last_move != null && (
          <motion.div
            key={`lastmove-${game.last_move.cell_index}-${game.last_move.card_key}`}
            className="text-sm p-2 rounded border bg-muted border-border text-muted-foreground dark:bg-muted/40 dark:text-muted-foreground"
            aria-label="last move callout"
            aria-live="polite"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          >
            {game.last_move.player_index === myIndex ? "You" : "Opponent"} played{" "}
            <span className="font-medium">
              {cardDefs.get(game.last_move.card_key)?.name ?? game.last_move.card_key}
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mists feedback */}
      <AnimatePresence>
        {game.last_move != null && (
          <motion.div
            key={`mists-${game.last_move.cell_index}-${game.last_move.mists_roll}`}
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
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          >
            <span className="font-medium">Mists (roll: {game.last_move.mists_roll})</span>
            {game.last_move.mists_effect === "fog" && " — Fog: −2 to comparisons"}
            {game.last_move.mists_effect === "omen" && " — Omen: +2 to comparisons"}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Capture feedback */}
      <AnimatePresence>
        {capturedCells.size > 0 && (
          <motion.div
            key="capture-feedback"
            className={cn(
              "text-sm font-heading font-semibold p-2 rounded border",
              capturedCells.size === 1
                ? "bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/50 dark:border-amber-800 dark:text-amber-300"
                : "bg-purple-50 border-purple-200 text-purple-800 dark:bg-purple-950/50 dark:border-purple-800 dark:text-purple-300"
            )}
            aria-live="polite"
            aria-label="capture feedback"
            initial={{ scale: 1.2, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ type: "spring", stiffness: 400, damping: 20 }}
          >
            {capturedCells.size === 1
              ? "1 card captured!"
              : `Combo! ×${capturedCells.size} captured`}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Plus! callout */}
      <AnimatePresence>
        {game.last_move?.plus_triggered === true && (
          <motion.div
            key="plus-feedback"
            className="text-sm font-heading font-semibold p-2 rounded border bg-cyan-50 border-cyan-200 text-cyan-800 dark:bg-cyan-950/50 dark:border-cyan-800 dark:text-cyan-300"
            aria-live="polite"
            aria-label="plus feedback"
            initial={{ scale: 1.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ type: "spring", stiffness: 500, damping: 25 }}
          >
            Plus!
          </motion.div>
        )}
      </AnimatePresence>

      {/* Elemental! callout */}
      <AnimatePresence>
        {game.last_move != null && game.last_move.elemental_triggered === true && (
          <motion.div
            key="elemental-feedback"
            className="text-sm font-heading font-semibold p-2 rounded border bg-yellow-50 border-yellow-400 text-yellow-900 dark:bg-yellow-950/50 dark:border-yellow-700 dark:text-yellow-300"
            aria-live="polite"
            aria-label="elemental feedback"
            initial={{ scale: 1.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ type: "spring", stiffness: 500, damping: 25 }}
          >
            {(() => {
              const elemKey = boardElements?.[game.last_move!.cell_index];
              return elemKey
                ? elemKey.charAt(0).toUpperCase() + elemKey.slice(1) + " Elemental!"
                : "Elemental!";
            })()}
          </motion.div>
        )}
      </AnimatePresence>

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

      {/* Rules */}
      <Button variant="outline" size="sm" onClick={onShowRules}>
        Rules
      </Button>

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
        <div className="flex-1 min-w-0 min-h-0 flex flex-col gap-2">
          {/* Score bar + mute toggle */}
          <div className="flex items-center justify-end gap-2 shrink-0">
            <p className="text-sm font-heading text-muted-foreground flex items-center gap-0">
              You:&nbsp;
              <AnimatePresence mode="popLayout">
                <motion.span
                  key={`my-${myScore}`}
                  initial={{ y: -12, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: 12, opacity: 0 }}
                  transition={{ type: "spring", stiffness: 400, damping: 25 }}
                  aria-label="your score"
                >
                  {myScore}
                </motion.span>
              </AnimatePresence>
              &nbsp;|&nbsp;Opp:&nbsp;
              <AnimatePresence mode="popLayout">
                <motion.span
                  key={`opp-${opponentScore}`}
                  initial={{ y: -12, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: 12, opacity: 0 }}
                  transition={{ type: "spring", stiffness: 400, damping: 25 }}
                  aria-label="opponent score"
                >
                  {opponentScore}
                </motion.span>
              </AnimatePresence>
            </p>
            <MuteToggle />
          </div>

          {/* Board: centered, takes remaining vertical space */}
          <div className="flex-1 min-h-0 flex items-center justify-center overflow-hidden">
            <BoardGrid
              board={game.board ?? []}
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
              mistsEffect={placedCells.size > 0 ? (game.last_move?.mists_effect as "none" | "fog" | "omen" | null) : null}
              intimidatePendingCell={intimidatePendingCell}
            />
          </div>

          {/* Move error */}
          {moveError && <p className="text-destructive text-sm shrink-0">{moveError}</p>}

          {/* Bottom section: action panel + hand, side by side on sm+ */}
          <div className="shrink-0 flex flex-col sm:flex-row gap-2 items-start">
            <div className="w-full sm:w-52 shrink-0">
              <ActionPanel
                isMyTurn={isMyTurn}
                selectedCard={selectedCard}
                selectedCardDef={selectedCard ? cardDefs.get(selectedCard) : undefined}
                onDeselectCard={() => onSelectCard(null)}
                movePending={movePending}
                myPlayer={myPlayer}
                usePower={usePower}
                onUsePowerChange={onUsePowerChange}
                powerSide={powerSide}
                onPowerSideToggle={onPowerSideToggle}
                intimidatePendingCell={intimidatePendingCell}
                onCancelIntimidatePending={onCancelIntimidatePending}
              />
            </div>
            <div className="w-full sm:flex-1 sm:min-w-0">
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
          </div>
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
            <span className="font-heading font-medium">Info & Actions</span>
            <span className="text-xs text-muted-foreground">
              {sidebarOpen ? "Hide" : "Show"}
            </span>
          </button>
          <AnimatePresence initial={false}>
            {sidebarOpen && (
              <motion.div
                key="mobile-drawer"
                className="mt-2 p-3 rounded border border-border bg-muted/20 overflow-hidden"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 35 }}
              >
                {secondaryContent}
              </motion.div>
            )}
          </AnimatePresence>
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
