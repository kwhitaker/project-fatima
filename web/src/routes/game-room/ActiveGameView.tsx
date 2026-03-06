import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import type {
  Archetype,
  CardDefinition,
  GameState,
  PlayerState,
} from "@/lib/api";
import { AI_DISPLAY_NAMES } from "@/lib/ai-constants";
import { cn } from "@/lib/utils";
import { AiCommentBubble } from "@/routes/game-room/AiCommentBubble";
import { BoardGrid } from "@/routes/game-room/BoardGrid";
import { BoardCallouts } from "@/routes/game-room/BoardCallouts";
import { ArchetypeModal } from "@/routes/game-room/ArchetypeModal";
import { ARCHETYPE_COPY } from "@/routes/game-room/archetypesCopy";
import { ForfeitDialog } from "@/routes/game-room/ForfeitDialog";
import { HandPanel } from "@/routes/game-room/HandPanel";
import { ActionPanel } from "@/routes/game-room/ActionPanel";
import { MuteToggle } from "@/routes/game-room/MuteToggle";
import { SuddenDeathBanner } from "@/routes/game-room/SuddenDeathBanner";
import { useGameRoom } from "@/routes/game-room/GameRoomContext";
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
  placedCells,
  capturedCells,
  onPlaceCard,
  boardElements,
  moveError,
}: {
  game: GameState;
  myIndex: number;
  myPlayer?: PlayerState;
  opponentPlayer?: PlayerState;
  myScore: number;
  opponentScore: number;
  cardDefs: Map<string, CardDefinition>;
  placedCells: Set<number>;
  capturedCells: Set<number>;
  onPlaceCard: (cellIndex: number) => void | Promise<void>;
  boardElements?: string[] | null;
  moveError: string | null;
}) {
  const {
    selectedCard,
    selectedCardElement,
    movePending,
    usePower,
    powerSide,
    intimidatePendingCell,
    devoutWardPendingCell,
    onPreviewCard,
    leaving,
    onOpenLeaveConfirm,
    showLeaveConfirm,
    onCloseLeaveConfirm,
    onConfirmLeave,
    onShowRules,
  } = useGameRoom();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const canPlace =
    !!myPlayer?.archetype &&
    game.current_player_index === myIndex &&
    selectedCard !== null &&
    !movePending &&
    (!usePower ||
      myPlayer?.archetype === "intimidate" ||
      myPlayer?.archetype === "devout" ||
      (myPlayer?.archetype !== "skulker" &&
        myPlayer?.archetype !== "martial") ||
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
    const key = game.last_move?.plus_triggered
      ? `${game.last_move.cell_index}`
      : null;
    if (key && key !== prevPlusRef.current) {
      playPlus();
    }
    prevPlusRef.current = key;
  }, [game.last_move?.plus_triggered, game.last_move?.cell_index]);

  // Sound: Elemental trigger
  const prevElemRef = useRef<string | null>(null);
  useEffect(() => {
    const key = game.last_move?.elemental_triggered
      ? `${game.last_move.cell_index}`
      : null;
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
            {game.last_move.player_index === myIndex ? "You" : "Opponent"}{" "}
            played{" "}
            <span className="font-medium">
              {cardDefs.get(game.last_move.card_key)?.name ??
                game.last_move.card_key}
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
                "bg-muted border-border text-muted-foreground",
            )}
            aria-label="mists feedback"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          >
            <span className="font-medium">
              Mists (roll: {game.last_move.mists_roll})
            </span>
            {game.last_move.mists_effect === "fog" &&
              " — Fog: −2 to comparisons"}
            {game.last_move.mists_effect === "omen" &&
              " — Omen: +2 to comparisons"}
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
                : "bg-purple-50 border-purple-200 text-purple-800 dark:bg-purple-950/50 dark:border-purple-800 dark:text-purple-300",
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
        {game.last_move != null &&
          game.last_move.elemental_triggered === true && (
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
                  ? elemKey.charAt(0).toUpperCase() +
                      elemKey.slice(1) +
                      " Elemental!"
                  : "Elemental!";
              })()}
            </motion.div>
          )}
      </AnimatePresence>

      {/* Opponent hand + archetypes (compact grid) */}
      <div className="grid grid-cols-[1fr_1fr_auto] gap-x-4 gap-y-1 items-baseline text-sm">
        {/* Row: You */}
        <ArchetypeTooltipName
          label="You"
          archetype={myPlayer?.archetype ?? null}
          used={myPlayer?.archetype_used ?? false}
        />
        {/* Row: Opponent */}
        <ArchetypeTooltipName
          label="Opp"
          archetype={opponentPlayer?.archetype ?? null}
          used={opponentPlayer?.archetype_used ?? false}
          extra={`${opponentPlayer?.hand.length ?? 0} cards`}
        />
      </div>

      {/* Rules */}
      <Button variant="outline" size="sm" onClick={onShowRules}>
        Rules
      </Button>

      {/* Leave */}
      <Button
        variant="outline"
        size="sm"
        onClick={onOpenLeaveConfirm}
        disabled={leaving}
      >
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
              &nbsp;|&nbsp;{opponentPlayer?.player_type === "ai" && opponentPlayer.ai_difficulty
                ? AI_DISPLAY_NAMES[opponentPlayer.ai_difficulty]
                : "Opp"}:&nbsp;
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

          {/* AI comment bubble */}
          {opponentPlayer?.player_type === "ai" && (
            <AiCommentBubble
              comment={game.last_move?.ai_comment}
              difficulty={opponentPlayer.ai_difficulty}
            />
          )}

          {/* Board: centered, takes remaining vertical space */}
          <div className="flex-1 min-h-0 flex items-center justify-center overflow-hidden relative">
            <BoardGrid
              board={game.board ?? []}
              myIndex={myIndex}
              canPlace={canPlace}
              onCellClick={(i) => void onPlaceCard(i)}
              onCellInspect={(cardKey) =>
                onPreviewCard(cardKey, cardDefs.get(cardKey))
              }
              placedCells={placedCells}
              capturedCells={capturedCells}
              cardDefs={cardDefs}
              lastMoveCellIndex={game.last_move?.cell_index ?? null}
              boardElements={boardElements}
              selectedCardElement={selectedCardElement}
              mistsEffect={
                placedCells.size > 0
                  ? (game.last_move?.mists_effect as
                      | "none"
                      | "fog"
                      | "omen"
                      | null)
                  : null
              }
              intimidatePendingCell={intimidatePendingCell}
              devoutWardPendingCell={devoutWardPendingCell}
              wardedCell={game.warded_cell ?? null}
              archetypeUsedName={game.last_move?.archetype_used_name ?? null}
              martialRotationDirection={(game.last_move?.martial_rotation_direction as "cw" | "ccw" | null) ?? null}
              skulkerBoostSide={(game.last_move?.skulker_boost_side as "n" | "e" | "s" | "w" | null) ?? null}
            />
            <BoardCallouts
              mistsEffect={
                placedCells.size > 0
                  ? (game.last_move?.mists_effect as
                      | "none"
                      | "fog"
                      | "omen"
                      | null)
                  : null
              }
              captureCount={capturedCells.size}
              plusTriggered={game.last_move?.plus_triggered === true}
              elementalTriggered={game.last_move?.elemental_triggered === true}
              elementKey={
                game.last_move?.elemental_triggered
                  ? (boardElements?.[game.last_move.cell_index] ?? null)
                  : null
              }
              archetypeUsedName={game.last_move?.archetype_used_name ?? null}
              changeKey={
                game.last_move
                  ? `${game.last_move.cell_index}-${game.last_move.card_key}`
                  : null
              }
            />
          </div>

          {/* Move error */}
          {moveError && (
            <p className="text-destructive text-sm shrink-0">{moveError}</p>
          )}

          {/* Bottom section: action panel + hand, side by side on sm+ */}
          <div className="shrink-0 flex flex-col sm:flex-row gap-2 items-start">
            <div className="w-full sm:w-52 shrink-0">
              <ActionPanel
                isMyTurn={isMyTurn}
                selectedCardDef={
                  selectedCard ? cardDefs.get(selectedCard) : undefined
                }
                myPlayer={myPlayer}
                opponentPlayer={opponentPlayer}
              />
            </div>
            <div className="w-full sm:flex-1 sm:min-w-0">
              <HandPanel
                game={game}
                myIndex={myIndex}
                myPlayer={myPlayer}
                cardDefs={cardDefs}
              />
            </div>
          </div>
        </div>

        {/* ─── Desktop sidebar (hidden on mobile, visible lg+) ─── */}
        <aside
          className="hidden lg:block w-72 shrink-0 overflow-y-auto overflow-x-hidden"
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

      <ArchetypeModal open={!!myPlayer && !myPlayer.archetype} />
      <SuddenDeathBanner roundNumber={game.round_number} />
    </>
  );
}

/** Compact archetype display with hover/tap tooltip for power details. */
function ArchetypeTooltipName({
  label,
  archetype,
  used,
  extra,
}: {
  label: string;
  archetype: Archetype | null;
  used: boolean;
  extra?: string;
}) {
  const copy = archetype ? ARCHETYPE_COPY[archetype] : null;
  return (
    <>
      <span className="text-xs text-muted-foreground">{label}</span>
      {archetype && copy ? (
        <span
          className="group relative cursor-help"
          aria-label={`${label} archetype`}
        >
          <span className="capitalize underline decoration-dotted underline-offset-2">
            {archetype}
          </span>
          <span className="text-xs text-muted-foreground ml-1">
            {used ? "Used" : "Available"}
          </span>
          {/* Tooltip */}
          <span
            role="tooltip"
            className={cn(
              "absolute bottom-full left-1/2 -translate-x-1/2 mb-1 w-56 p-2 rounded border-2 border-border bg-popover text-popover-foreground text-xs shadow-md",
              "opacity-0 scale-95 pointer-events-none group-hover:opacity-100 group-hover:scale-100 group-focus:opacity-100 group-focus:scale-100",
              "transition-all duration-150 z-30",
            )}
          >
            <p className="font-semibold">{copy.powerTitle}</p>
            <p className="text-muted-foreground mt-0.5">{copy.powerText}</p>
          </span>
        </span>
      ) : (
        <span className="text-muted-foreground">—</span>
      )}
      {extra ? (
        <span className="text-xs text-muted-foreground">{extra}</span>
      ) : (
        <span />
      )}
    </>
  );
}
