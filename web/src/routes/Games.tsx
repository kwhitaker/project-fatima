import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { listGames, createGame, type GameState } from "@/lib/api";

const STATUS_LABELS: Record<GameState["status"], string> = {
  waiting: "Waiting",
  active: "Active",
  complete: "Complete",
};

function StatusBadge({ status }: { status: GameState["status"] }) {
  return <span className="text-xs font-medium">{STATUS_LABELS[status]}</span>;
}

export default function Games() {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const [games, setGames] = useState<GameState[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    listGames()
      .then(setGames)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load games")
      )
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const game = await createGame();
      void navigate(`/g/${game.game_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create game");
      setCreating(false);
    }
  };

  return (
    <div className="container py-8">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold">My Games</h1>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => void handleCreate()} disabled={creating}>
            {creating ? "Creating…" : "Create Game"}
          </Button>
          <Button variant="outline" onClick={() => void signOut()}>
            Log out
          </Button>
        </div>
      </div>
      {error && <p className="text-destructive mb-4 text-sm">{error}</p>}
      {loading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : games.length === 0 ? (
        <p className="text-muted-foreground text-sm">No games yet.</p>
      ) : (
        <ul className="space-y-2">
          {games.map((game) => (
            <li key={game.game_id}>
              <button
                className="hover:bg-muted w-full cursor-pointer rounded-lg border p-4 text-left transition-colors"
                onClick={() => void navigate(`/g/${game.game_id}`)}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm">{game.game_id}</span>
                  <StatusBadge status={game.status} />
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
