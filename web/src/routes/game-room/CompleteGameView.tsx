import { useCallback, useEffect, useMemo, useState } from "react";
import type { CardDefinition, GameState } from "@/lib/api";
import { BoardGrid } from "@/routes/game-room/BoardGrid";
import { VictoryOverlay } from "@/routes/game-room/VictoryOverlay";
import { DefeatOverlay } from "@/routes/game-room/DefeatOverlay";
import { playVictory, playDefeat } from "@/lib/sounds";

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
  const isWinner = game.result?.winner === myIndex && !game.result?.is_draw;
  const isLoser =
    game.result?.winner !== undefined &&
    game.result.winner !== myIndex &&
    !game.result.is_draw;
  const [showVictory, setShowVictory] = useState(isWinner);
  const [showDefeat, setShowDefeat] = useState(isLoser);
  const dismissVictory = useCallback(() => setShowVictory(false), []);
  const dismissDefeat = useCallback(() => setShowDefeat(false), []);

  // Play victory/defeat sound on mount
  useEffect(() => {
    if (isWinner) playVictory();
    else if (isLoser) playDefeat();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Cells owned by the winner for sequential victory glow
  const victoryCells = useMemo(() => {
    if (!isWinner) return undefined;
    return (game.board ?? [])
      .map((cell, i) => (cell && cell.owner === myIndex ? i : -1))
      .filter((i) => i >= 0);
  }, [game.board, isWinner, myIndex]);

  const earlyFinish = game.result?.early_finish === true;

  return (
    <div className="flex-1 min-h-0 overflow-y-auto">
      {showVictory && <VictoryOverlay onDismiss={dismissVictory} />}
      {showDefeat && <DefeatOverlay onDismiss={dismissDefeat} />}
      <div className="mt-4 space-y-4">
        {/* Result banner */}
        <div className="p-4 rounded border">
          {game.result?.is_draw ? (
            <p className="text-xl font-heading font-bold">Draw!</p>
          ) : isWinner ? (
            <p className="text-xl font-heading font-bold text-green-600 dark:text-green-400">You win!</p>
          ) : (
            <p className="text-xl font-heading font-bold text-red-600 dark:text-red-400">You lose!</p>
          )}
          {earlyFinish && (
            <p className="text-sm font-body text-muted-foreground mt-1">
              {isWinner ? "Inevitable victory" : "The darkness claims this match"}
            </p>
          )}
        </div>

        {/* Final score */}
        <p className="text-sm text-muted-foreground">
          Score — You: {myScore} | Opponent: {opponentScore}
        </p>

        {/* Final board */}
        <BoardGrid
          board={game.board ?? []}
          myIndex={myIndex}
          cardDefs={cardDefs}
          onCellInspect={(cardKey) => onPreviewCard(cardKey, cardDefs.get(cardKey))}
          victoryCells={victoryCells}
          earlyFinish={earlyFinish}
        />
      </div>
    </div>
  );
}
