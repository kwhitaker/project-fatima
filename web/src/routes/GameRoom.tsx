import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { getGame, joinGame, leaveGame, type BoardCell, type GameState } from "@/lib/api";

function BoardGrid({
  board,
  myIndex,
}: {
  board: (BoardCell | null)[];
  myIndex: number;
}) {
  return (
    <div
      className="grid grid-cols-3 gap-2 w-fit"
      aria-label="game board"
    >
      {board.map((cell, i) => (
        <div
          key={i}
          className={cn(
            "w-20 h-20 border rounded flex items-center justify-center text-xs text-center p-1 break-all",
            cell === null
              ? "bg-muted text-muted-foreground"
              : cell.owner === myIndex
              ? "bg-blue-200 text-blue-900"
              : "bg-red-200 text-red-900"
          )}
        >
          {cell ? cell.card_key : ""}
        </div>
      ))}
    </div>
  );
}

export default function GameRoom() {
  const { gameId } = useParams<{ gameId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [game, setGame] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [selectedCard, setSelectedCard] = useState<string | null>(null);

  useEffect(() => {
    if (!gameId) return;
    getGame(gameId)
      .then(setGame)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load game")
      )
      .finally(() => setLoading(false));
  }, [gameId]);

  const handleJoin = async () => {
    if (!gameId) return;
    setJoining(true);
    try {
      const updated = await joinGame(gameId);
      setGame(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to join game");
    } finally {
      setJoining(false);
    }
  };

  const handleLeave = async () => {
    if (!gameId || !game) return;
    setLeaving(true);
    try {
      await leaveGame(gameId, game.state_version);
    } catch {
      // ignore errors — navigate away regardless
    } finally {
      setLeaving(false);
    }
    navigate("/games");
  };

  const handleCopyLink = () => {
    void navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="container py-8">
        <p className="text-muted-foreground text-sm">Loading…</p>
      </div>
    );
  }

  if (error || !game) {
    return (
      <div className="container py-8">
        <p className="text-destructive text-sm">{error ?? "Game not found"}</p>
      </div>
    );
  }

  const callerId = user?.id ?? "";
  const isParticipant = game.players.some((p) => p.player_id === callerId);
  const isFull = game.players.length >= 2;

  // Derive player indices for active/complete views
  const myIndex = game.players.findIndex((p) => p.player_id === callerId);
  const opponentIndex = myIndex === 0 ? 1 : 0;
  const myPlayer = myIndex >= 0 ? game.players[myIndex] : undefined;
  const opponentPlayer = myIndex >= 0 ? game.players[opponentIndex] : undefined;

  // Score: count board cells owned by each player
  const myScore = myIndex >= 0
    ? game.board.filter((c) => c !== null && c.owner === myIndex).length
    : 0;
  const opponentScore = myIndex >= 0
    ? game.board.filter((c) => c !== null && c.owner === opponentIndex).length
    : 0;

  return (
    <div className="container py-8">
      <h1 className="text-2xl font-bold">Game {gameId}</h1>

      {/* WAITING */}
      {game.status === "waiting" && (
        <div className="mt-4 space-y-4">
          <p className="text-muted-foreground text-sm">
            Waiting for players… ({game.players.length}/2)
          </p>

          <div className="flex items-center gap-2">
            <span className="font-mono text-sm break-all">{window.location.href}</span>
            <Button variant="outline" size="sm" onClick={handleCopyLink}>
              {copied ? "Copied!" : "Copy Link"}
            </Button>
          </div>

          {!isParticipant && !isFull && (
            <Button onClick={() => void handleJoin()} disabled={joining}>
              {joining ? "Joining…" : "Join Game"}
            </Button>
          )}
          {!isParticipant && isFull && (
            <p className="text-muted-foreground text-sm">
              This game is full. You cannot join.
            </p>
          )}
        </div>
      )}

      {/* ACTIVE */}
      {game.status === "active" && (
        <div className="mt-4 space-y-4">
          {/* Turn indicator */}
          <p className="text-lg font-semibold">
            {game.current_player_index === myIndex
              ? "Your turn"
              : "Opponent's turn"}
          </p>

          {/* Score */}
          <p className="text-sm text-muted-foreground">
            Score — You: {myScore} | Opponent: {opponentScore}
          </p>

          {/* Board */}
          <BoardGrid board={game.board} myIndex={myIndex} />

          {/* My hand */}
          <div>
            <p className="text-sm font-medium mb-1">Your hand</p>
            <div className="flex gap-2 flex-wrap">
              {myPlayer?.hand.map((cardKey) => (
                <button
                  key={cardKey}
                  onClick={() =>
                    setSelectedCard(selectedCard === cardKey ? null : cardKey)
                  }
                  className={cn(
                    "px-3 py-2 border rounded text-xs font-mono",
                    selectedCard === cardKey
                      ? "border-primary bg-primary/10"
                      : "border-border hover:border-primary/50"
                  )}
                  aria-pressed={selectedCard === cardKey}
                >
                  {cardKey}
                </button>
              ))}
            </div>
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

          {/* Leave */}
          <Button variant="outline" onClick={() => void handleLeave()} disabled={leaving}>
            {leaving ? "Leaving…" : "Leave Game"}
          </Button>
        </div>
      )}

      {/* COMPLETE */}
      {game.status === "complete" && (
        <div className="mt-4 space-y-4">
          {/* Result banner */}
          <div className="p-4 rounded border">
            {game.result?.is_draw ? (
              <p className="text-xl font-bold">Draw!</p>
            ) : game.result?.winner === myIndex ? (
              <p className="text-xl font-bold text-green-600">You win!</p>
            ) : (
              <p className="text-xl font-bold text-red-600">You lose!</p>
            )}
          </div>

          {/* Final score */}
          <p className="text-sm text-muted-foreground">
            Score — You: {myScore} | Opponent: {opponentScore}
          </p>

          {/* Final board */}
          <BoardGrid board={game.board} myIndex={myIndex} />

          {/* Leave */}
          <Button variant="outline" onClick={() => void handleLeave()} disabled={leaving}>
            {leaving ? "Leaving…" : "Leave Game"}
          </Button>
        </div>
      )}
    </div>
  );
}
