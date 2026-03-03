import type { BoardCell, CardDefinition } from "@/lib/api";
import { cn } from "@/lib/utils";
import { CardFace } from "@/routes/game-room/CardFace";
import { cardTitle } from "@/routes/game-room/cardTitle";

export const ELEMENT_SYMBOLS: Record<string, string> = {
  blood: "🩸",
  holy: "✦",
  arcane: "✧",
  shadow: "◆",
  nature: "✿",
};

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
}) {
  return (
    <div className="w-full max-w-[22rem] sm:max-w-[28rem] md:max-w-[34rem] lg:max-w-[40rem] mx-auto">
      <div className="grid grid-cols-3 gap-2 sm:gap-3" aria-label="game board">
        {board.map((cell, i) => {
          const isPlaced = placedCells?.has(i) ?? false;
          const isCaptured = capturedCells?.has(i) ?? false;
          const isLastMove = lastMoveCellIndex != null && i === lastMoveCellIndex;
          const elementLabel = boardElements?.[i];
          const isElementMatch =
            selectedCardElement != null &&
            elementLabel != null &&
            elementLabel === selectedCardElement;

          const cellClass = cn(
            "aspect-square w-full border rounded flex items-center justify-center text-xs text-center relative",
            cell === null
              ? "bg-muted text-muted-foreground"
              : cell.owner === myIndex
                ? "bg-blue-200 text-blue-900 dark:bg-blue-800 dark:text-blue-100"
                : "bg-red-200 text-red-900 dark:bg-red-800 dark:text-red-100",
            isPlaced && "animate-card-placed",
            isCaptured && "animate-card-captured",
            isElementMatch && !isLastMove && "ring-2 ring-emerald-500 dark:ring-emerald-400",
            isLastMove && "ring-2 ring-yellow-400 dark:ring-yellow-300"
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

          if (canPlace && cell === null) {
            return (
              <button
                key={i}
                aria-label={`cell ${i}`}
                onClick={() => onCellClick?.(i)}
                className={cn(
                  cellClass,
                  "hover:bg-accent cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                )}
                data-last-move={isLastMove ? "true" : undefined}
                title={elementTitle}
              >
                {elementBadge}
              </button>
            );
          }

          if (cell !== null && onCellInspect) {
            const def = cardDefs?.get(cell.card_key);
            return (
              <button
                key={i}
                className={cn(
                  cellClass,
                  "cursor-pointer hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                )}
                data-anim={isPlaced ? "placed" : isCaptured ? "captured" : undefined}
                data-last-move={isLastMove ? "true" : undefined}
                onClick={() => onCellInspect(cell.card_key)}
                aria-label={`inspect ${cardDefs?.get(cell.card_key)?.name ?? cell.card_key}`}
                title={elementTitle ? `${cardTitle(cell.card_key, def)} — ${elementTitle}` : cardTitle(cell.card_key, def)}
              >
                {elementBadge}
                <CardFace cardKey={cell.card_key} def={def} />
              </button>
            );
          }

          return (
            <div
              key={i}
              className={cellClass}
              data-anim={isPlaced ? "placed" : isCaptured ? "captured" : undefined}
              data-last-move={isLastMove ? "true" : undefined}
              title={
                cell
                  ? elementTitle
                    ? `${cardTitle(cell.card_key, cardDefs?.get(cell.card_key))} — ${elementTitle}`
                    : cardTitle(cell.card_key, cardDefs?.get(cell.card_key))
                  : elementTitle
              }
            >
              {elementBadge}
              {cell ? (
                <CardFace cardKey={cell.card_key} def={cardDefs?.get(cell.card_key)} />
              ) : (
                ""
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
