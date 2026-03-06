import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import {
  listGames,
  createGame,
  createGameVsAi,
  type GameState,
  type AIDifficulty,
} from "@/lib/api";
import { AI_DISPLAY_NAMES, AI_LONG_DESCRIPTIONS } from "@/lib/ai-constants";
import { ModalShell } from "@/components/ui/ModalShell";
import { GameRulesDialog } from "@/routes/game-room/GameRulesDialog";

const STORAGE_KEY_MY_GAMES = "fatima:myGamesCollapsed";

const STATUS_LABELS: Record<GameState["status"], string> = {
  waiting: "Waiting",
  drafting: "Drafting",
  active: "Active",
  complete: "Complete",
};

const AI_FLAVOR_TEXT: Record<AIDifficulty, string> = {
  easy: "A sheltered noble still learning the game.",
  medium: "Strahd's chamberlain plays with cold precision.",
  hard: "The lord of Barovia does not lose.",
  nightmare: "Ancient forces that see through every stratagem.",
};

const DIFFICULTY_LABELS: Record<AIDifficulty, string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
  nightmare: "Nightmare",
};

function StatusBadge({ status }: { status: GameState["status"] }) {
  return <span className="text-xs font-medium">{STATUS_LABELS[status]}</span>;
}

function DifficultyBadge({ difficulty }: { difficulty: AIDifficulty }) {
  return (
    <span className="text-xs font-semibold text-violet-400">
      {DIFFICULTY_LABELS[difficulty]}
    </span>
  );
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

function getOpponentName(game: GameState, myId: string): string {
  if (game.players.length < 2) return "Waiting...";
  const opponent = game.players.find((p) => p.player_id !== myId);
  if (!opponent) return "Waiting...";
  if (opponent.player_type === "ai" && opponent.ai_difficulty) {
    return AI_DISPLAY_NAMES[opponent.ai_difficulty];
  }
  return opponent.email ?? "Unknown";
}

function getAiDifficulty(game: GameState, myId: string): AIDifficulty | null {
  const opponent = game.players.find((p) => p.player_id !== myId);
  if (opponent?.player_type === "ai" && opponent.ai_difficulty) {
    return opponent.ai_difficulty;
  }
  return null;
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

function isAiGame(game: GameState): boolean {
  return game.players.some((p) => p.player_type === "ai");
}

export default function Games() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [games, setGames] = useState<GameState[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [creatingAi, setCreatingAi] = useState<AIDifficulty | null>(null);
  const [nightmareError, setNightmareError] = useState<string | null>(null);
  const [selectedAi, setSelectedAi] = useState<AIDifficulty | null>(null);
  const [showRules, setShowRules] = useState(false);
  const [myGamesCollapsed, setMyGamesCollapsed] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY_MY_GAMES) === "true";
    } catch {
      return false;
    }
  });

  const toggleMyGames = () => {
    setMyGamesCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY_MY_GAMES, String(next));
      } catch {
        // storage unavailable
      }
      return next;
    });
  };

  useEffect(() => {
    listGames()
      .then(setGames)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load games"),
      )
      .finally(() => setLoading(false));
  }, []);

  const myId = user?.id ?? "";

  const myGames = games.filter((g) =>
    g.players.some((p) => p.player_id === myId),
  );

  const hasActiveGame = myGames.some(
    (g) => g.status !== "complete",
  );

  const openGames = games.filter(
    (g) =>
      g.status === "waiting" &&
      g.players.length === 1 &&
      !g.players.some((p) => p.player_id === myId) &&
      !isAiGame(g),
  );

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

  const handleCreateAi = async (difficulty: AIDifficulty) => {
    setCreatingAi(difficulty);
    setNightmareError(null);
    try {
      const game = await createGameVsAi(difficulty);
      void navigate(`/g/${game.game_id}`);
    } catch (e: unknown) {
      const status = (e as { status?: number }).status;
      if (difficulty === "nightmare" && status === 503) {
        setNightmareError(
          "The Dark Powers are occupied with another mortal.",
        );
      } else {
        setError(e instanceof Error ? e.message : "Failed to create AI game");
      }
      setCreatingAi(null);
    }
  };

  return (
    <motion.div
      className="mx-auto max-w-3xl overflow-x-hidden px-4 py-8 sm:px-6 lg:px-8"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.15 }}
    >
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold">Games</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowRules(true)}>
            How to Play
          </Button>
          <Button variant="outline" onClick={() => void signOut()}>
            Log out
          </Button>
        </div>
      </div>

      {error && <p className="text-destructive mb-4 text-sm">{error}</p>}

      {/* Play vs AI */}
      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Play vs AI</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {(["easy", "medium", "hard", "nightmare"] as const).map(
            (difficulty) => (
              <button
                key={difficulty}
                data-testid={`ai-${difficulty}`}
                disabled={creatingAi !== null || hasActiveGame}
                onClick={() => setSelectedAi(difficulty)}
                className="hover:bg-accent/20 hover:border-accent cursor-pointer rounded-none border-2 border-border p-4 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                title={
                  hasActiveGame
                    ? "Finish or forfeit your current game first"
                    : difficulty === "nightmare"
                      ? "Only 2 players can face Nightmare difficulty at a time. Try again shortly if unavailable."
                      : undefined
                }
              >
                <div className="mb-1 font-semibold">
                  {AI_DISPLAY_NAMES[difficulty]}
                </div>
                <div className="text-xs font-medium text-violet-400">
                  {DIFFICULTY_LABELS[difficulty]}
                </div>
                <div className="text-muted-foreground mt-1 text-xs">
                  {AI_FLAVOR_TEXT[difficulty]}
                </div>
                {difficulty === "nightmare" && (
                  <div className="mt-1 text-[10px] italic text-amber-500/70">
                    Few may commune with The Dark Powers at once.
                  </div>
                )}
              </button>
            ),
          )}
        </div>
      </section>

      {/* Open Games */}
      <section className="mb-8">
        <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-lg font-semibold">Open Games</h2>
          <Button
            onClick={() => void handleCreate()}
            disabled={creating || hasActiveGame}
            title={hasActiveGame ? "Finish or forfeit your current game first" : undefined}
          >
            {creating ? "Creating..." : "Challenge Another Player"}
          </Button>
        </div>
        {loading ? (
          <p className="text-muted-foreground text-sm">Loading...</p>
        ) : openGames.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            No open games available.
          </p>
        ) : (
          <motion.ul
            className="space-y-2"
            initial="hidden"
            animate="visible"
            variants={{ visible: { transition: { staggerChildren: 0.04 } } }}
          >
            {openGames.map((game) => {
              const hostEmail =
                game.players[0]?.email ?? "Unknown";
              return (
                <motion.li
                  key={game.game_id}
                  variants={{
                    hidden: { opacity: 0, y: 10 },
                    visible: { opacity: 1, y: 0 },
                  }}
                  transition={{ duration: 0.15 }}
                >
                  {hasActiveGame ? (
                    <div
                      className="block w-full rounded-none border-2 border-border p-4 text-left opacity-50 cursor-not-allowed"
                      title="Finish or forfeit your current game first"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex min-w-0 flex-col">
                          <span className="truncate font-medium">
                            {hostEmail}
                          </span>
                          {game.created_at && (
                            <span className="text-muted-foreground text-xs">
                              {new Date(game.created_at).toLocaleString()}
                            </span>
                          )}
                        </div>
                        <span className="text-xs font-semibold text-muted-foreground">
                          Join
                        </span>
                      </div>
                    </div>
                  ) : (
                    <Link
                      to={`/g/${game.game_id}`}
                      className="hover:bg-accent/20 hover:border-accent block w-full cursor-pointer rounded-none border-2 border-border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex min-w-0 flex-col">
                          <span className="truncate font-medium">
                            {hostEmail}
                          </span>
                          {game.created_at && (
                            <span className="text-muted-foreground text-xs">
                              {new Date(game.created_at).toLocaleString()}
                            </span>
                          )}
                        </div>
                        <span className="text-xs font-semibold text-emerald-400">
                          Join
                        </span>
                      </div>
                    </Link>
                  )}
                </motion.li>
              );
            })}
          </motion.ul>
        )}
      </section>

      {/* My Games */}
      <section className="mb-8">
        <button
          type="button"
          onClick={toggleMyGames}
          className="mb-3 flex w-full cursor-pointer items-center gap-2 text-left"
          aria-expanded={!myGamesCollapsed}
          aria-controls="my-games-list"
        >
          <svg
            className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 ${myGamesCollapsed ? "" : "rotate-90"}`}
            viewBox="0 0 16 16"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M6 3l5 5-5 5V3z" />
          </svg>
          <h2 className="text-lg font-semibold">My Games</h2>
          {myGames.length > 0 && (
            <span className="text-xs text-muted-foreground">({myGames.length})</span>
          )}
        </button>
        <AnimatePresence initial={false}>
          {!myGamesCollapsed && (
            <motion.div
              id="my-games-list"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              style={{ overflow: "hidden" }}
            >
              {loading ? (
                <p className="text-muted-foreground text-sm">Loading...</p>
              ) : myGames.length === 0 ? (
                <p className="text-muted-foreground text-sm">No games yet.</p>
              ) : (
                <motion.ul
                  className="space-y-2"
                  initial="hidden"
                  animate="visible"
                  variants={{ visible: { transition: { staggerChildren: 0.04 } } }}
                >
                  {myGames.map((game) => {
                    const displayName = getOpponentName(game, myId);
                    const shortId = game.game_id.slice(0, 8);
                    const resultLabel = getResultLabel(game, myId);
                    const aiDiff = getAiDifficulty(game, myId);
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
                              <span className="truncate font-medium">
                                {displayName}
                              </span>
                              <span
                                className="text-muted-foreground font-mono text-xs"
                                title={game.game_id}
                              >
                                {shortId}
                              </span>
                            </div>
                            <div className="flex shrink-0 flex-col items-end gap-1">
                              {aiDiff && <DifficultyBadge difficulty={aiDiff} />}
                              <StatusBadge status={game.status} />
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
          )}
        </AnimatePresence>
      </section>

      {/* AI Confirmation Modal */}
      <ModalShell
        open={selectedAi !== null}
        onClose={() => setSelectedAi(null)}
        maxWidth="max-w-md"
        aria-label="Confirm AI opponent"
        data-testid="ai-confirm-modal"
      >
        {selectedAi && (
          <div className="flex flex-col gap-4">
            <div>
              <h2 className="text-xl font-bold">
                {AI_DISPLAY_NAMES[selectedAi]}
              </h2>
              <span className="text-sm font-semibold text-violet-400">
                {DIFFICULTY_LABELS[selectedAi]}
              </span>
            </div>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {AI_LONG_DESCRIPTIONS[selectedAi]}
            </p>
            {selectedAi === "nightmare" && (
              <p className="text-xs italic text-amber-500/70">
                Few may commune with The Dark Powers at once.
              </p>
            )}
            {nightmareError && selectedAi === "nightmare" && (
              <p
                className="text-xs font-medium text-red-400"
                role="alert"
                aria-label="nightmare error"
              >
                {nightmareError}
              </p>
            )}
            <div className="flex gap-3 pt-2">
              <Button
                className="flex-1"
                disabled={creatingAi !== null}
                onClick={() => void handleCreateAi(selectedAi)}
              >
                {creatingAi ? "Summoning..." : "Challenge"}
              </Button>
              <Button
                variant="outline"
                className="flex-1"
                disabled={creatingAi !== null}
                onClick={() => setSelectedAi(null)}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </ModalShell>

      <GameRulesDialog open={showRules} onClose={() => setShowRules(false)} />
    </motion.div>
  );
}
