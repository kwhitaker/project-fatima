import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { getGame, joinGame, type GameState } from "@/lib/api";

export default function GameRoom() {
  const { gameId } = useParams<{ gameId: string }>();
  const { user } = useAuth();
  const [game, setGame] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);
  const [copied, setCopied] = useState(false);

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

  return (
    <div className="container py-8">
      <h1 className="text-2xl font-bold">Game {gameId}</h1>

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

      {game.status === "active" && (
        <p className="text-muted-foreground mt-2 text-sm">Game in progress.</p>
      )}

      {game.status === "complete" && (
        <p className="text-muted-foreground mt-2 text-sm">Game complete.</p>
      )}
    </div>
  );
}
