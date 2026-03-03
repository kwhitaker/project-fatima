import type { CardDefinition, GameState } from "@/lib/api";
import { BoardGrid } from "@/routes/game-room/BoardGrid";

export function CompleteGameView({
  game,
  myIndex,
  myScore,
  opponentScore,
  cardDefs,
  onPreviewCard,
}: {
  game: GameState;
  myIndex: number;
  myScore: number;
  opponentScore: number;
  cardDefs: Map<string, CardDefinition>;
  onPreviewCard: (cardKey: string, def?: CardDefinition) => void;
}) {
  return (
    <div className="flex-1 min-h-0 overflow-y-auto">
      <div className="mt-4 space-y-4">
        {/* Result banner */}
        <div className="p-4 rounded border">
          {game.result?.is_draw ? (
            <p className="text-xl font-heading font-bold">Draw!</p>
          ) : game.result?.winner === myIndex ? (
            <p className="text-xl font-heading font-bold text-green-600 dark:text-green-400">You win!</p>
          ) : (
            <p className="text-xl font-heading font-bold text-red-600 dark:text-red-400">You lose!</p>
          )}
        </div>

        {/* Final score */}
        <p className="text-sm text-muted-foreground">
          Score — You: {myScore} | Opponent: {opponentScore}
        </p>

        {/* Final board */}
        <BoardGrid
          board={game.board}
          myIndex={myIndex}
          cardDefs={cardDefs}
          onCellInspect={(cardKey) => onPreviewCard(cardKey, cardDefs.get(cardKey))}
        />
      </div>
    </div>
  );
}
