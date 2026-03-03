import { useEffect, useMemo, useRef } from "react";
import type { BoardCell, CardDefinition } from "@/lib/api";
import { cn } from "@/lib/utils";
import { CardFace, tierClass } from "@/routes/game-room/CardFace";
import { cardTitle } from "@/routes/game-room/cardTitle";
import { motion, AnimatePresence } from "motion/react";

export const ELEMENT_SYMBOLS: Record<string, string> = {
  blood: "🩸",
  holy: "✦",
  arcane: "✧",
  shadow: "◆",
  nature: "✿",
};

/** Delay before captures start (let placement animation finish). */
const CAPTURE_BASE_DELAY = 0.35;
/** Delay between each sequential capture. */
const CAPTURE_STAGGER = 0.3;
/** Duration of each capture flip animation. */
const CAPTURE_FLIP_DURATION = 0.3;

export function BoardGrid({
  board,
  myIndex,
  canPlace = false,
  onCellClick,
  onCellInspect,
  placedCells,
  capturedCells,
  cardDefs,
  lastMoveCellIndex,
  boardElements,
  selectedCardElement,
  mistsEffect,
  victoryCells,
  intimidatePendingCell,
  earlyFinish,
}: {
  board: (BoardCell | null)[];
  myIndex: number;
  canPlace?: boolean;
  onCellClick?: (index: number) => void;
  onCellInspect?: (cardKey: string) => void;
  placedCells?: Set<number>;
  capturedCells?: Set<number>;
  cardDefs?: Map<string, CardDefinition>;
  lastMoveCellIndex?: number | null;
  boardElements?: string[] | null;
  selectedCardElement?: string | null;
  mistsEffect?: "fog" | "omen" | "none" | null;
  victoryCells?: number[];
  intimidatePendingCell?: number | null;
  earlyFinish?: boolean;
}) {
  // Sort captured cells by index for sequential animation (top-left → bottom-right)
  const capturedOrder = useMemo(() => {
    if (!capturedCells || capturedCells.size === 0) return [];
    return Array.from(capturedCells).sort((a, b) => a - b);
  }, [capturedCells]);

  // Build a map from cell index → capture sequence position
  const captureSeqMap = useMemo(() => {
    const m = new Map<number, number>();
    capturedOrder.forEach((cellIdx, seqIdx) => m.set(cellIdx, seqIdx));
    return m;
  }, [capturedOrder]);

  // Emit custom capture-step events as sound hook points
  const emittedRef = useRef<string | null>(null);
  useEffect(() => {
    const key = capturedOrder.length > 0 ? capturedOrder.join(",") : null;
    if (key && key !== emittedRef.current) {
      emittedRef.current = key;
      capturedOrder.forEach((cellIdx, seqIdx) => {
        const delay = (CAPTURE_BASE_DELAY + seqIdx * CAPTURE_STAGGER) * 1000;
        setTimeout(() => {
          window.dispatchEvent(
            new CustomEvent("capture-step", {
              detail: { cellIndex: cellIdx, step: seqIdx + 1, total: capturedOrder.length },
            })
          );
        }, delay);
      });
    }
  }, [capturedOrder]);

  // Micro-shake: derive a key from placed cells so the shake replays on each new placement
  const shakeKey = placedCells && placedCells.size > 0
    ? Array.from(placedCells).sort().join(",")
    : "none";

  return (
    <div
      className="mx-auto aspect-square"
      style={{ width: 'min(100%, 24rem, calc(100dvh - 20rem))' }}
    >
      <motion.div
        key={shakeKey}
        className="grid grid-cols-3 gap-2 sm:gap-3"
        aria-label="game board"
        animate={shakeKey !== "none"
          ? { x: [0, -2, 2, -1, 1, 0] }
          : { x: 0 }
        }
        transition={shakeKey !== "none"
          ? { duration: 0.2, ease: "easeOut" }
          : { duration: 0 }
        }
      >
        {board.map((cell, i) => {
          const isPlaced = placedCells?.has(i) ?? false;
          const isCaptured = capturedCells?.has(i) ?? false;
          const isLastMove = lastMoveCellIndex != null && i === lastMoveCellIndex;
          const elementLabel = boardElements?.[i];
          const isElementMatch =
            cell === null &&
            selectedCardElement != null &&
            elementLabel != null &&
            elementLabel === selectedCardElement;

          const def = cell ? cardDefs?.get(cell.card_key) : undefined;

          // Victory glow: staggered delay based on position in victoryCells array
          const victoryIdx = victoryCells?.indexOf(i) ?? -1;

          const cellClass = cn(
            "aspect-square w-full border-[3px] border-border rounded-none flex items-center justify-center text-xs text-center relative overflow-hidden",
            cell === null
              ? earlyFinish ? "bg-muted/50 text-muted-foreground opacity-50 border-dashed" : "bg-muted text-muted-foreground"
              : cell.owner === myIndex
                ? "bg-blue-200 text-blue-900 dark:bg-blue-800 dark:text-blue-100"
                : "bg-red-200 text-red-900 dark:bg-red-800 dark:text-red-100",
            isElementMatch && !isLastMove && "ring-2 ring-emerald-500 dark:ring-emerald-400",
            isLastMove && "ring-2 ring-yellow-400 dark:ring-yellow-300",
            cell && tierClass(def?.tier)
          );

          const elementTitle = elementLabel
            ? `Element: ${elementLabel.charAt(0).toUpperCase() + elementLabel.slice(1)}`
            : undefined;

          const elementBadge = elementLabel ? (
            <span
              key="element-badge"
              className="absolute top-0 left-0 text-[8px] leading-none p-px opacity-70 select-none pointer-events-none"
              aria-label={`element ${elementLabel}`}
            >
              {ELEMENT_SYMBOLS[elementLabel] ?? elementLabel}
            </span>
          ) : null;

          // Compute capture delay for sequential animation
          const captureSeq = captureSeqMap.get(i);
          const captureDelay = captureSeq != null
            ? CAPTURE_BASE_DELAY + captureSeq * CAPTURE_STAGGER
            : 0;

          // Should the placed card pulse when captures resolve?
          const shouldPulse = isPlaced && capturedOrder.length > 0;

          if (canPlace && cell === null) {
            return (
              <motion.button
                key={i}
                aria-label={`cell ${i}`}
                onClick={() => onCellClick?.(i)}
                className={cn(
                  cellClass,
                  "hover:bg-accent cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                )}
                data-last-move={isLastMove ? "true" : undefined}
                title={elementTitle}
                whileHover={{ scale: 1.05 }}
                transition={{ type: "spring", stiffness: 400, damping: 25 }}
              >
                {elementBadge}
              </motion.button>
            );
          }

          // Mists tint class for placed card
          const mistsTintClass = isPlaced && mistsEffect === "fog"
            ? "animate-mists-fog"
            : isPlaced && mistsEffect === "omen"
              ? "animate-mists-omen"
              : undefined;

          // Card content with appropriate animation
          const cardContent = cell ? (
            isPlaced ? (
              <motion.div
                className={cn("w-full h-full flex items-center justify-center relative", mistsTintClass)}
                initial={{ scale: 0, opacity: 0 }}
                animate={shouldPulse
                  ? { scale: [0, 1, 1.08, 1], opacity: 1 }
                  : { scale: [0, 1.08, 1], opacity: 1 }
                }
                transition={shouldPulse
                  ? {
                      scale: {
                        type: "tween",
                        ease: "easeOut",
                        times: [0, 0.6, 0.8, 1],
                        duration: CAPTURE_BASE_DELAY + 0.2,
                      },
                      opacity: { type: "tween", ease: "easeOut", duration: 0.15 },
                    }
                  : {
                      scale: {
                        type: "tween",
                        ease: "easeOut",
                        times: [0, 0.7, 1],
                        duration: 0.25,
                      },
                      opacity: { type: "tween", ease: "easeOut", duration: 0.15 },
                    }
                }
              >
                <CardFace cardKey={cell.card_key} def={def} />
                {/* Impact ripple */}
                <motion.div
                  className="absolute inset-0 pointer-events-none border-2 border-foreground/50"
                  initial={{ scale: 0.8, opacity: 0.8 }}
                  animate={{ scale: 1.6, opacity: 0 }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                />
              </motion.div>
            ) : isCaptured ? (
              <motion.div
                className="w-full h-full flex items-center justify-center relative"
                data-anim="captured"
                initial={{ scaleX: 1, filter: "brightness(1)" }}
                animate={{
                  scaleX: [1, 0, 1],
                  filter: [
                    "brightness(1)",
                    `brightness(${2 + (captureSeq ?? 0) * 0.2})`,
                    "brightness(1)",
                  ],
                }}
                transition={{
                  duration: CAPTURE_FLIP_DURATION,
                  delay: captureDelay,
                  ease: "easeInOut",
                }}
              >
                <CardFace cardKey={cell.card_key} def={def} />
                {/* Ownership color wipe at flip midpoint */}
                <motion.div
                  className="absolute inset-0 pointer-events-none"
                  style={{ backgroundColor: cell.owner === myIndex ? "rgba(59,130,246,0.3)" : "rgba(239,68,68,0.3)" }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: [0, 1, 0] }}
                  transition={{
                    duration: CAPTURE_FLIP_DURATION,
                    delay: captureDelay,
                    ease: "easeInOut",
                  }}
                />
                {/* Combo counter overlay */}
                {capturedOrder.length > 1 && captureSeq != null && (
                  <motion.span
                    className="absolute top-0 right-0 text-xs font-heading font-bold text-yellow-300 drop-shadow-md pointer-events-none z-10"
                    data-testid="combo-counter"
                    initial={{ scale: 1.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ delay: captureDelay + CAPTURE_FLIP_DURATION * 0.5, duration: 0.2 }}
                  >
                    +{captureSeq + 1}
                  </motion.span>
                )}
                {/* Chain pulse ring */}
                <motion.div
                  className="absolute inset-0 pointer-events-none border-2 border-yellow-400"
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1.3, opacity: [0, 0.8, 0] }}
                  transition={{
                    duration: 0.3,
                    delay: captureDelay,
                    ease: "easeOut",
                  }}
                />
              </motion.div>
            ) : (
              <CardFace cardKey={cell.card_key} def={def} />
            )
          ) : earlyFinish ? (
            <span className="text-muted-foreground/40 font-heading text-lg select-none" aria-label="unplayed cell">✕</span>
          ) : (
            ""
          );

          const victoryGlowClass = victoryIdx >= 0 ? "animate-victory-glow" : undefined;
          const victoryGlowStyle = victoryIdx >= 0
            ? { animationDelay: `${victoryIdx * 0.2}s` }
            : undefined;

          // When intimidate is pending, clicking an occupied cell selects it as the target
          const isIntimidateTarget = intimidatePendingCell != null && cell !== null && onCellClick;

          if (cell !== null && (onCellInspect || isIntimidateTarget)) {
            return (
              <button
                key={i}
                className={cn(
                  cellClass,
                  victoryGlowClass,
                  "cursor-pointer hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                  isIntimidateTarget && "ring-2 ring-orange-400 dark:ring-orange-300"
                )}
                style={victoryGlowStyle}
                data-anim={isPlaced ? "placed" : isCaptured ? "captured" : victoryIdx >= 0 ? "victory-glow" : undefined}
                data-last-move={isLastMove ? "true" : undefined}
                onClick={() => {
                  if (isIntimidateTarget) {
                    onCellClick!(i);
                  } else if (onCellInspect) {
                    onCellInspect(cell.card_key);
                  }
                }}
                aria-label={isIntimidateTarget ? `intimidate target cell ${i}` : `inspect ${def?.name ?? cell.card_key}`}
                title={elementTitle ? `${cardTitle(cell.card_key, def)} — ${elementTitle}` : cardTitle(cell.card_key, def)}
              >
                {elementBadge}
                {cardContent}
              </button>
            );
          }

          return (
            <div
              key={i}
              className={cn(cellClass, victoryGlowClass)}
              style={victoryGlowStyle}
              data-anim={isPlaced ? "placed" : isCaptured ? "captured" : victoryIdx >= 0 ? "victory-glow" : undefined}
              data-last-move={isLastMove ? "true" : undefined}
              title={
                cell
                  ? elementTitle
                    ? `${cardTitle(cell.card_key, def)} — ${elementTitle}`
                    : cardTitle(cell.card_key, def)
                  : elementTitle
              }
            >
              {elementBadge}
              {cardContent}
            </div>
          );
        })}
      </motion.div>
    </div>
  );
}
