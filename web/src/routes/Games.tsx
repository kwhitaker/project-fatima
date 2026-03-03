import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { listGames, createGame, type GameState } from "@/lib/api";

const STATUS_LABELS: Record<GameState["status"], string> = {
  waiting: "Waiting",
  active: "Active",
  complete: "Complete",
};

function StatusBadge({ status, isOpen }: { status: GameState["status"]; isOpen?: boolean }) {
  if (isOpen) {
    return <span className="text-xs font-semibold text-emerald-400">Open</span>;
  }
  return <span className="text-xs font-medium">{STATUS_LABELS[status]}</span>;
}

function ResultBadge({ label }: { label: string }) {
  const colorClass =
    label === "Win"
      ? "text-green-400"
      : label === "Loss"
        ? "text-red-400"
        : label === "Forfeit"
          ? "text-yellow-400"
          : "text-muted-foreground";
  return <span className={`text-xs font-semibold ${colorClass}`}>{label}</span>;
}

function getDisplayName(game: GameState, myId: string): string {
  const isParticipant = game.players.some((p) => p.player_id === myId);

  if (!isParticipant) {
    // Open game: show host email
    return game.players[0]?.email ?? "Waiting...";
  }

  if (game.players.length < 2) return "Waiting...";
  const opponent = game.players.find((p) => p.player_id !== myId);
  return opponent?.email ?? "Waiting...";
}

function getResultLabel(game: GameState, myId: string): string | null {
  if (!game.result) return null;
  const myIndex = game.players.findIndex((p) => p.player_id === myId);
  if (myIndex === -1) return null;

  if (game.result.is_draw) return "Draw";

  if (game.result.completion_reason === "forfeit") {
    if (game.result.forfeit_by_index === myIndex) return "Forfeit";
    return "Win";
  }

  if (game.result.winner === myIndex) return "Win";
  return "Loss";
}

export default function Games() {
  const { user, signOut } = useAuth();
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

  const myId = user?.id ?? "";

  return (
    <motion.div
      className="container py-8"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.15 }}
    >
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
        <motion.ul
          className="space-y-2"
          initial="hidden"
          animate="visible"
          variants={{ visible: { transition: { staggerChildren: 0.04 } } }}
        >
          {games.map((game) => {
            const isOpen = !game.players.some((p) => p.player_id === myId);
            const displayName = getDisplayName(game, myId);
            const shortId = game.game_id.slice(0, 8);
            const resultLabel = getResultLabel(game, myId);
            return (
              <motion.li
                key={game.game_id}
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  visible: { opacity: 1, y: 0 },
                }}
                transition={{ duration: 0.15 }}
              >
                <Link
                  to={`/g/${game.game_id}`}
                  className="hover:bg-accent/20 hover:border-accent block w-full cursor-pointer rounded-none border-2 border-border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex min-w-0 flex-col">
                      <span className="truncate font-medium">{displayName}</span>
                      <span
                        className="text-muted-foreground font-mono text-xs"
                        title={game.game_id}
                      >
                        {shortId}
                      </span>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <StatusBadge status={game.status} isOpen={isOpen} />
                      {resultLabel && <ResultBadge label={resultLabel} />}
                    </div>
                  </div>
                </Link>
              </motion.li>
            );
          })}
        </motion.ul>
      )}
    </motion.div>
  );
}
