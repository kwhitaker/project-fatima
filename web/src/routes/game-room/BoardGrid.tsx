import type { BoardCell, CardDefinition } from "@/lib/api";
import { cn } from "@/lib/utils";
import { CardFace } from "@/routes/game-room/CardFace";
import { cardTitle } from "@/routes/game-room/cardTitle";

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
}) {
  return (
    <div className="w-full max-w-[22rem] sm:max-w-[28rem] md:max-w-[34rem] lg:max-w-[40rem] mx-auto">
      <div className="grid grid-cols-3 gap-2 sm:gap-3" aria-label="game board">
        {board.map((cell, i) => {
          const isPlaced = placedCells?.has(i) ?? false;
          const isCaptured = capturedCells?.has(i) ?? false;
          const isLastMove = lastMoveCellIndex != null && i === lastMoveCellIndex;
          const cellClass = cn(
            "aspect-square w-full border rounded flex items-center justify-center text-xs text-center",
            cell === null
              ? "bg-muted text-muted-foreground"
              : cell.owner === myIndex
                ? "bg-blue-200 text-blue-900 dark:bg-blue-800 dark:text-blue-100"
                : "bg-red-200 text-red-900 dark:bg-red-800 dark:text-red-100",
            isPlaced && "animate-card-placed",
            isCaptured && "animate-card-captured",
            isLastMove && "ring-2 ring-yellow-400 dark:ring-yellow-300"
          );

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
              />
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
                title={cardTitle(cell.card_key, def)}
              >
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
              title={cell ? cardTitle(cell.card_key, cardDefs?.get(cell.card_key)) : undefined}
            >
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
