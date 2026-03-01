import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { getCardDefinitions, getGame, joinGame, leaveGame, placeCard, selectArchetype, type Archetype, type BoardCell, type CardDefinition, type GameState } from "@/lib/api";
import { supabase } from "@/lib/supabase";

function CardFace({ cardKey, def }: { cardKey: string; def?: CardDefinition }) {
  const name = def?.name ?? cardKey;
  return (
    <div className="flex flex-col items-center justify-between w-full h-full p-0.5">
      <span className="text-[9px] font-bold leading-none">{def?.sides.n ?? ""}</span>
      <div className="flex items-center justify-between w-full">
        <span className="text-[9px] leading-none">{def?.sides.w ?? ""}</span>
        <span className="text-[9px] font-semibold leading-tight text-center truncate max-w-[34px]">{name}</span>
        <span className="text-[9px] leading-none">{def?.sides.e ?? ""}</span>
      </div>
      <span className="text-[9px] font-bold leading-none">{def?.sides.s ?? ""}</span>
    </div>
  );
}

function BoardGrid({
  board,
  myIndex,
  canPlace = false,
  onCellClick,
  placedCells,
  capturedCells,
  cardDefs,
}: {
  board: (BoardCell | null)[];
  myIndex: number;
  canPlace?: boolean;
  onCellClick?: (index: number) => void;
  placedCells?: Set<number>;
  capturedCells?: Set<number>;
  cardDefs?: Map<string, CardDefinition>;
}) {
  return (
    <div
      className="grid grid-cols-3 gap-1.5 sm:gap-2 w-fit"
      aria-label="game board"
    >
      {board.map((cell, i) => {
        const isPlaced = placedCells?.has(i) ?? false;
        const isCaptured = capturedCells?.has(i) ?? false;
        const cellClass = cn(
          "w-16 h-16 sm:w-20 sm:h-20 border rounded flex items-center justify-center text-xs text-center p-0.5",
          cell === null
            ? "bg-muted text-muted-foreground"
            : cell.owner === myIndex
            ? "bg-blue-200 text-blue-900 dark:bg-blue-800 dark:text-blue-100"
            : "bg-red-200 text-red-900 dark:bg-red-800 dark:text-red-100",
          isPlaced && "animate-card-placed",
          isCaptured && "animate-card-captured"
        );
        if (canPlace && cell === null) {
          return (
            <button
              key={i}
              aria-label={`cell ${i}`}
              onClick={() => onCellClick?.(i)}
              className={cn(cellClass, "hover:bg-accent cursor-pointer")}
            />
          );
        }
        return (
          <div
            key={i}
            className={cellClass}
            data-anim={isPlaced ? "placed" : isCaptured ? "captured" : undefined}
          >
            {cell ? (
              <CardFace cardKey={cell.card_key} def={cardDefs?.get(cell.card_key)} />
            ) : ""}
          </div>
        );
      })}
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
  const [moveError, setMoveError] = useState<string | null>(null);
  const [movePending, setMovePending] = useState(false);
  const [archetypePending, setArchetypePending] = useState(false);
  const [archetypeError, setArchetypeError] = useState<string | null>(null);
  const [usePower, setUsePower] = useState(false);
  const [powerSide, setPowerSide] = useState<string | null>(null);
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);
  const [cardDefs, setCardDefs] = useState<Map<string, CardDefinition>>(new Map());

  // Animation tracking: diff prev board vs new board on each game update
  const prevBoardRef = useRef<(BoardCell | null)[] | null>(null);
  const [placedCells, setPlacedCells] = useState<Set<number>>(new Set());
  const [capturedCells, setCapturedCells] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!game) return;
    const prev = prevBoardRef.current;
    prevBoardRef.current = game.board;
    if (!prev) return;

    const placed = new Set<number>();
    const captured = new Set<number>();
    game.board.forEach((cell, i) => {
      const prevCell = prev[i];
      if (prevCell === null && cell !== null) {
        placed.add(i);
      } else if (prevCell !== null && cell !== null && prevCell.owner !== cell.owner) {
        captured.add(i);
      }
    });
    setPlacedCells(placed);
    setCapturedCells(captured);
  }, [game]);

  useEffect(() => {
    if (!gameId) return;
    Promise.all([
      getGame(gameId),
      getCardDefinitions().catch(() => new Map<string, CardDefinition>()),
    ])
      .then(([g, defs]) => {
        setGame(g);
        setCardDefs(defs);
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load game")
      )
      .finally(() => setLoading(false));
  }, [gameId]);

  // Realtime subscription: refetch snapshot on game_events INSERT
  useEffect(() => {
    if (!gameId) return;

    const refetch = () => {
      void getGame(gameId).then(setGame).catch(() => null);
    };

    let fallbackInterval: ReturnType<typeof setInterval> | null = null;

    const channel = supabase
      .channel(`game:${gameId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "game_events",
          filter: `game_id=eq.${gameId}`,
        },
        (_payload) => { refetch(); }
      )
      .subscribe((status) => {
        const s = status as string;
        if (s === "CLOSED" || s === "CHANNEL_ERROR") {
          if (!fallbackInterval) {
            fallbackInterval = setInterval(refetch, 30_000);
          }
        } else if (s === "SUBSCRIBED") {
          if (fallbackInterval) {
            clearInterval(fallbackInterval);
            fallbackInterval = null;
          }
        }
      });

    return () => {
      if (fallbackInterval) clearInterval(fallbackInterval);
      void supabase.removeChannel(channel);
    };
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

  const handlePlaceCard = async (cellIndex: number) => {
    if (!selectedCard || !game || !gameId) return;
    setMovePending(true);
    setMoveError(null);
    const callerId = user?.id ?? "";
    const myIdx = game.players.findIndex((p) => p.player_id === callerId);
    const myPlr = myIdx >= 0 ? game.players[myIdx] : undefined;
    const idempotencyKey = crypto.randomUUID();
    try {
      let updated: GameState;
      if (usePower) {
        updated = await placeCard(
          gameId, selectedCard, cellIndex, game.state_version, idempotencyKey,
          {
            useArchetype: true,
            skulkerBoostSide: myPlr?.archetype === "skulker" ? (powerSide ?? undefined) : undefined,
            presenceBoostDirection: myPlr?.archetype === "presence" ? (powerSide ?? undefined) : undefined,
          }
        );
      } else {
        updated = await placeCard(gameId, selectedCard, cellIndex, game.state_version, idempotencyKey);
      }
      setGame(updated);
      setSelectedCard(null);
      setUsePower(false);
      setPowerSide(null);
    } catch (e: unknown) {
      const errStatus = (e as { status?: number }).status;
      setMoveError(e instanceof Error ? e.message : "Move failed");
      if (errStatus === 409 || errStatus === 422) {
        const fresh = await getGame(gameId).catch(() => null);
        if (fresh) setGame(fresh);
      }
    } finally {
      setMovePending(false);
    }
  };

  const handleSelectArchetype = async (archetype: Archetype) => {
    if (!gameId || !game) return;
    setArchetypePending(true);
    setArchetypeError(null);
    try {
      const updated = await selectArchetype(gameId, archetype);
      setGame(updated);
    } catch (e: unknown) {
      setArchetypeError(e instanceof Error ? e.message : "Failed to select archetype");
    } finally {
      setArchetypePending(false);
    }
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

  const titleText =
    game.status === "waiting"
      ? "Waiting for opponent"
      : `Playing against ${opponentPlayer?.email ?? "opponent"}`;

  return (
    <div className="container py-8">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold">{titleText}</h1>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate("/games")}
          className="hover:bg-accent cursor-pointer"
        >
          ← Back to Games
        </Button>
      </div>

      {/* WAITING */}
      {game.status === "waiting" && (
        <div className="mt-4 space-y-4">
          <p className="text-muted-foreground text-sm">
            Waiting for players… ({game.players.length}/2)
          </p>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <span className="font-mono text-sm break-all">{window.location.href}</span>
            <Button variant="outline" size="sm" onClick={handleCopyLink} className="shrink-0">
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

          {/* Mists feedback */}
          {game.last_move != null && (
            <div
              className={cn(
                "p-3 rounded border text-sm",
                game.last_move.mists_effect === "fog" && "bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-950/50 dark:border-blue-800 dark:text-blue-300",
                game.last_move.mists_effect === "omen" && "bg-purple-50 border-purple-200 text-purple-800 dark:bg-purple-950/50 dark:border-purple-800 dark:text-purple-300",
                game.last_move.mists_effect === "none" && "bg-muted border-border text-muted-foreground"
              )}
              aria-label="mists feedback"
            >
              <span className="font-medium">Mists (roll: {game.last_move.mists_roll})</span>
              {game.last_move.mists_effect === "fog" && " — Fog: −1 to comparisons"}
              {game.last_move.mists_effect === "omen" && " — Omen: +1 to comparisons"}
            </div>
          )}

          {/* Capture feedback: single flip or combo */}
          {capturedCells.size > 0 && (
            <div
              className={cn(
                "text-sm font-semibold p-2 rounded border",
                capturedCells.size === 1
                  ? "bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/50 dark:border-amber-800 dark:text-amber-300"
                  : "bg-purple-50 border-purple-200 text-purple-800 dark:bg-purple-950/50 dark:border-purple-800 dark:text-purple-300"
              )}
              aria-live="polite"
              aria-label="capture feedback"
            >
              {capturedCells.size === 1
                ? "1 card captured!"
                : `Combo! ×${capturedCells.size} captured`}
            </div>
          )}

          {/* Board */}
          <BoardGrid
            board={game.board}
            myIndex={myIndex}
            canPlace={
              !!myPlayer?.archetype &&
              game.current_player_index === myIndex &&
              selectedCard !== null &&
              !movePending &&
              (!usePower ||
                !(myPlayer?.archetype === "skulker" || myPlayer?.archetype === "presence") ||
                powerSide !== null)
            }
            onCellClick={(i) => void handlePlaceCard(i)}
            placedCells={placedCells}
            capturedCells={capturedCells}
            cardDefs={cardDefs}
          />

          {/* Move error */}
          {moveError && (
            <p className="text-destructive text-sm">{moveError}</p>
          )}

          {/* Archetype selection: unskippable blocking modal */}
          {myPlayer && !myPlayer.archetype && (
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="archetype-modal-title"
              data-testid="archetype-modal"
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
            >
              <div className="bg-background border rounded-lg p-6 w-full max-w-sm shadow-xl">
                <h2 id="archetype-modal-title" className="text-lg font-bold mb-1">
                  Choose Your Archetype
                </h2>
                <p className="text-sm text-muted-foreground mb-4">
                  Select a once-per-game power before you can place cards.
                </p>
                <div className="flex flex-col gap-2">
                  {(["martial", "skulker", "caster", "devout", "presence"] as const).map((arch) => (
                    <Button
                      key={arch}
                      variant="outline"
                      className="capitalize w-full justify-start"
                      onClick={() => void handleSelectArchetype(arch)}
                      disabled={archetypePending}
                    >
                      {arch}
                    </Button>
                  ))}
                </div>
                {archetypeError && (
                  <p className="text-destructive text-sm mt-3">{archetypeError}</p>
                )}
              </div>
            </div>
          )}

          {/* Use Power toggle */}
          {myPlayer?.archetype && !myPlayer.archetype_used && game.current_player_index === myIndex && (
            <div>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  aria-label="Use Power"
                  checked={usePower}
                  onChange={(e) => {
                    setUsePower(e.target.checked);
                    setPowerSide(null);
                  }}
                  disabled={movePending}
                />
                Use Power
              </label>
              {usePower && (myPlayer.archetype === "skulker" || myPlayer.archetype === "presence") && (
                <div className="flex gap-2 mt-2">
                  {(["n", "e", "s", "w"] as const).map((side) => (
                    <Button
                      key={side}
                      variant={powerSide === side ? "default" : "outline"}
                      size="sm"
                      onClick={() => setPowerSide(powerSide === side ? null : side)}
                    >
                      {side}
                    </Button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* My hand */}
          <div>
            <p className="text-sm font-medium mb-1">Your hand</p>
            {game.current_player_index === myIndex && !movePending && (
              <p className="text-xs text-muted-foreground mb-2">
                {selectedCard
                  ? `"${selectedCard}" selected — click an empty cell to place it`
                  : "Click a card to select it, then click an empty cell on the board"}
              </p>
            )}
            <div className="flex gap-2 flex-wrap">
              {myPlayer?.hand.map((cardKey) => {
                const def = cardDefs.get(cardKey);
                return (
                  <button
                    key={cardKey}
                    onClick={() =>
                      setSelectedCard(selectedCard === cardKey ? null : cardKey)
                    }
                    disabled={!myPlayer?.archetype || game.current_player_index !== myIndex || movePending}
                    className={cn(
                      "flex flex-col items-center min-w-[4rem] px-2 py-1.5 border rounded text-xs transition-transform hover:scale-105",
                      "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100",
                      selectedCard === cardKey
                        ? "border-primary bg-primary/10 cursor-pointer"
                        : "border-border hover:border-primary hover:bg-accent/80 cursor-pointer"
                    )}
                    aria-pressed={selectedCard === cardKey}
                  >
                    <span className="font-semibold truncate max-w-[5rem] text-center">{def?.name ?? cardKey}</span>
                    <div className="flex flex-col items-center mt-0.5 text-[9px] text-muted-foreground w-full">
                      <span>{def ? def.sides.n : ""}</span>
                      <div className="flex justify-between w-full px-1">
                        <span>{def ? def.sides.w : ""}</span>
                        <span>{def ? def.sides.e : ""}</span>
                      </div>
                      <span>{def ? def.sides.s : ""}</span>
                    </div>
                  </button>
                );
              })}
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

          {/* Leave — opens forfeit confirmation dialog */}
          <Button variant="outline" onClick={() => setShowLeaveConfirm(true)} disabled={leaving}>
            Leave Game
          </Button>

          {/* Forfeit confirmation dialog */}
          {showLeaveConfirm && (
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="forfeit-dialog-title"
              data-testid="forfeit-dialog"
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
              onKeyDown={(e) => { if (e.key === "Escape") setShowLeaveConfirm(false); }}
            >
              <div className="bg-background border rounded-lg p-6 w-full max-w-sm shadow-xl">
                <h2 id="forfeit-dialog-title" className="text-lg font-bold mb-1">
                  Forfeit Game?
                </h2>
                <p className="text-sm text-muted-foreground mb-4">
                  Leaving now will count as a forfeit. Your opponent will be awarded the win.
                </p>
                <div className="flex gap-2 justify-end">
                  <Button
                    variant="outline"
                    onClick={() => setShowLeaveConfirm(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    data-confirm
                    onClick={() => { setShowLeaveConfirm(false); void handleLeave(); }}
                    disabled={leaving}
                  >
                    {leaving ? "Leaving…" : "Forfeit & Leave"}
                  </Button>
                </div>
              </div>
            </div>
          )}
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
              <p className="text-xl font-bold text-green-600 dark:text-green-400">You win!</p>
            ) : (
              <p className="text-xl font-bold text-red-600 dark:text-red-400">You lose!</p>
            )}
          </div>

          {/* Final score */}
          <p className="text-sm text-muted-foreground">
            Score — You: {myScore} | Opponent: {opponentScore}
          </p>

          {/* Final board */}
          <BoardGrid board={game.board} myIndex={myIndex} cardDefs={cardDefs} />
        </div>
      )}
    </div>
  );
}
