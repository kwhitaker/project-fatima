import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { getCardDefinitions, getGame, joinGame, leaveGame, placeCard, selectArchetype, type Archetype, type CardDefinition, type GameState } from "@/lib/api";

import { CardInspectPreview } from "@/routes/game-room/CardInspectPreview";
import { ActiveGameView } from "@/routes/game-room/ActiveGameView";
import { CompleteGameView } from "@/routes/game-room/CompleteGameView";
import { WaitingGameView } from "@/routes/game-room/WaitingGameView";
import { GameRulesDialog } from "@/routes/game-room/GameRulesDialog";

import { useBoardDiffAnimations } from "@/routes/game-room/hooks/useBoardDiffAnimations";
import { useGameSubscription } from "@/routes/game-room/hooks/useGameSubscription";
import { useMeasuredHeight } from "@/routes/game-room/hooks/useMeasuredHeight";

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
  const [drawerOpen, setDrawerOpen] = useState(true);
  const { ref: drawerRef, height: drawerHeight } = useMeasuredHeight<HTMLDivElement>([
    drawerOpen,
  ]);
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);
  const [showRules, setShowRules] = useState(false);
  const [cardDefs, setCardDefs] = useState<Map<string, CardDefinition>>(new Map());
  const [previewCard, setPreviewCard] = useState<{ cardKey: string; def?: CardDefinition } | null>(null);

  const { placedCells, capturedCells } = useBoardDiffAnimations(game?.board ?? null);

  const selectedCardElement =
    (selectedCard && cardDefs.get(selectedCard)?.element) ?? null;

  const refetchGame = useCallback(() => {
    if (!gameId) return;
    void getGame(gameId).then(setGame).catch(() => null);
  }, [gameId]);

  const realtimeStatus = useGameSubscription(gameId, refetchGame);

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

  const handleRefresh = () => {
    refetchGame();
  };

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
    <div className="container py-4 min-h-[100dvh] flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold">{titleText}</h1>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowRules(true)}
            className="cursor-pointer"
          >
            Rules
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate("/games")}
            className="hover:bg-accent cursor-pointer"
          >
            ← Back to Games
          </Button>
        </div>
      </div>

      {/* Realtime status indicator + manual refresh */}
      <div className="flex items-center gap-3 mb-4">
        <span
          aria-label="realtime status"
          className={cn(
            "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-xs",
            realtimeStatus === "live"
              ? "bg-green-50 border-green-200 text-green-700 dark:bg-green-950/50 dark:border-green-800 dark:text-green-400"
              : "bg-yellow-50 border-yellow-200 text-yellow-700 dark:bg-yellow-950/50 dark:border-yellow-800 dark:text-yellow-400"
          )}
        >
          <span
            className={cn(
              "w-1.5 h-1.5 rounded-full",
              realtimeStatus === "live" ? "bg-green-500" : "bg-yellow-500 animate-pulse"
            )}
          />
          {realtimeStatus === "live" ? "Live" : "Reconnecting…"}
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          aria-label="refresh game"
          className="cursor-pointer"
        >
          Refresh
        </Button>
      </div>

      {game.status === "active" ? (
        <ActiveGameView
          game={game}
          myIndex={myIndex}
          myPlayer={myPlayer}
          opponentPlayer={opponentPlayer}
          myScore={myScore}
          opponentScore={opponentScore}
          cardDefs={cardDefs}
          selectedCard={selectedCard}
          onSelectCard={setSelectedCard}
          movePending={movePending}
          moveError={moveError}
          usePower={usePower}
          onUsePowerChange={(next) => {
            setUsePower(next);
            setPowerSide(null);
          }}
          powerSide={powerSide}
          onPowerSideToggle={(side) => {
            setPowerSide(powerSide === side ? null : side);
          }}
          placedCells={placedCells}
          capturedCells={capturedCells}
          onPlaceCard={(cellIndex) => void handlePlaceCard(cellIndex)}
          onPreviewCard={(cardKey, def) => setPreviewCard({ cardKey, def })}
          drawerHeight={drawerHeight}
          drawerRef={drawerRef}
          drawerOpen={drawerOpen}
          onToggleDrawer={() => setDrawerOpen(!drawerOpen)}
          leaving={leaving}
          onOpenLeaveConfirm={() => setShowLeaveConfirm(true)}
          showLeaveConfirm={showLeaveConfirm}
          onCloseLeaveConfirm={() => setShowLeaveConfirm(false)}
          onConfirmLeave={() => {
            setShowLeaveConfirm(false);
            void handleLeave();
          }}
          archetypePending={archetypePending}
          archetypeError={archetypeError}
          onSelectArchetype={(arch) => void handleSelectArchetype(arch)}
          boardElements={game.board_elements ?? null}
          selectedCardElement={selectedCardElement}
        />
      ) : game.status === "waiting" ? (
        <WaitingGameView
          game={game}
          isParticipant={isParticipant}
          isFull={isFull}
          copied={copied}
          onCopyLink={handleCopyLink}
          joining={joining}
          onJoin={() => void handleJoin()}
        />
      ) : (
        <CompleteGameView
          game={game}
          myIndex={myIndex}
          myScore={myScore}
          opponentScore={opponentScore}
          cardDefs={cardDefs}
          onPreviewCard={(cardKey, def) => setPreviewCard({ cardKey, def })}
        />
      )}

      {/* Card inspect preview dialog */}
      {previewCard !== null && (
        <CardInspectPreview
          cardKey={previewCard.cardKey}
          def={previewCard.def}
          onClose={() => setPreviewCard(null)}
        />
      )}

      <GameRulesDialog open={showRules} onClose={() => setShowRules(false)} />
    </div>
  );
}
