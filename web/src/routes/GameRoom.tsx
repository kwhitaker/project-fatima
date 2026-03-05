import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { getCardDefinitions, getGame, joinGame, leaveGame, placeCard, selectArchetype, submitDraft, type Archetype, type CardDefinition, type GameState } from "@/lib/api";
import { AI_DISPLAY_NAMES } from "@/lib/ai-constants";
import { initAudio } from "@/lib/sounds";

import { CardInspectPreview } from "@/routes/game-room/CardInspectPreview";
import { ActiveGameView } from "@/routes/game-room/ActiveGameView";
import { CompleteGameView } from "@/routes/game-room/CompleteGameView";
import { DraftingGameView } from "@/routes/game-room/DraftingGameView";
import { WaitingGameView } from "@/routes/game-room/WaitingGameView";
import { GameRulesDialog } from "@/routes/game-room/GameRulesDialog";
import { GameRoomProvider } from "@/routes/game-room/GameRoomContext";

import { useBoardDiffAnimations } from "@/routes/game-room/hooks/useBoardDiffAnimations";
import { useGameSubscription } from "@/routes/game-room/hooks/useGameSubscription";

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
  const [intimidatePendingCell, setIntimidatePendingCell] = useState<number | null>(null);
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);
  const [showRules, setShowRules] = useState(false);
  const [cardDefs, setCardDefs] = useState<Map<string, CardDefinition>>(new Map());
  const [previewCard, setPreviewCard] = useState<{ cardKey: string; def?: CardDefinition } | null>(null);
  const lastPreviewCard = useRef<{ cardKey: string; def?: CardDefinition }>({ cardKey: "" });
  if (previewCard) lastPreviewCard.current = previewCard;

  const { placedCells, capturedCells } = useBoardDiffAnimations(game?.board ?? null);

  // Initialize Web Audio on first user interaction
  useEffect(() => {
    const handler = () => { initAudio(); window.removeEventListener("click", handler); };
    window.addEventListener("click", handler);
    return () => window.removeEventListener("click", handler);
  }, []);

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
    const callerId = user?.id ?? "";
    const myIdx = game.players.findIndex((p) => p.player_id === callerId);
    const myPlr = myIdx >= 0 ? game.players[myIdx] : undefined;

    // Intimidate two-step: first click sets pending placement, second click picks target
    if (usePower && myPlr?.archetype === "intimidate" && intimidatePendingCell === null) {
      setIntimidatePendingCell(cellIndex);
      return;
    }

    setMovePending(true);
    setMoveError(null);
    const placementCell = intimidatePendingCell ?? cellIndex;
    const idempotencyKey = crypto.randomUUID();
    try {
      let updated: GameState;
      if (usePower) {
        updated = await placeCard(
          gameId, selectedCard, placementCell, game.state_version, idempotencyKey,
          {
            useArchetype: true,
            skulkerBoostSide: myPlr?.archetype === "skulker" ? (powerSide ?? undefined) : undefined,
            intimidateTargetCell: myPlr?.archetype === "intimidate" ? cellIndex : undefined,
            martialRotationDirection: myPlr?.archetype === "martial" ? (powerSide as "cw" | "ccw" ?? undefined) : undefined,
          }
        );
      } else {
        updated = await placeCard(gameId, selectedCard, placementCell, game.state_version, idempotencyKey);
      }
      setGame(updated);
      setSelectedCard(null);
      setUsePower(false);
      setPowerSide(null);
      setIntimidatePendingCell(null);
    } catch (e: unknown) {
      const errStatus = (e as { status?: number }).status;
      setMoveError(e instanceof Error ? e.message : "Move failed");
      if (errStatus === 409 || errStatus === 422) {
        const fresh = await getGame(gameId).catch(() => null);
        if (fresh) setGame(fresh);
      }
      setIntimidatePendingCell(null);
    } finally {
      setMovePending(false);
    }
  };

  const handleSubmitDraft = async (selectedCards: string[]) => {
    if (!gameId) return;
    const updated = await submitDraft(gameId, selectedCards);
    setGame(updated);
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

  // Score: cells owned on board + cards remaining in hand (hand-in-score)
  const board = game.board ?? [];
  const myCells = myIndex >= 0
    ? board.filter((c) => c !== null && c.owner === myIndex).length
    : 0;
  const opponentCells = myIndex >= 0
    ? board.filter((c) => c !== null && c.owner === opponentIndex).length
    : 0;
  const myScore = myCells + (myPlayer?.hand.length ?? 0);
  const opponentScore = opponentCells + (opponentPlayer?.hand.length ?? 0);

  const opponentDisplayName =
    opponentPlayer?.player_type === "ai" && opponentPlayer.ai_difficulty
      ? AI_DISPLAY_NAMES[opponentPlayer.ai_difficulty]
      : opponentPlayer?.email ?? "opponent";

  const titleText =
    game.status === "waiting"
      ? "Waiting for opponent"
      : game.status === "drafting"
        ? "Draft Phase"
        : `Playing against ${opponentDisplayName}`;

  return (
    <div className="container py-4 flex-1 min-h-0 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-base font-semibold">{titleText}</h1>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            asChild
            className="hover:bg-accent cursor-pointer text-xs"
          >
            <Link to="/games">← Back to Games</Link>
          </Button>
        </div>
      </div>

      {/* Realtime status indicator + manual refresh */}
      <div className="flex items-center gap-2 mb-1">
        <span
          aria-label="realtime status"
          className={cn(
            "inline-flex items-center gap-1 px-1.5 py-px rounded-none border text-[10px]",
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
          className="cursor-pointer text-xs"
        >
          Refresh
        </Button>
      </div>

      {game.status === "drafting" ? (
        <DraftingGameView
          game={game}
          myIndex={myIndex}
          cardDefs={cardDefs}
          onSubmitDraft={handleSubmitDraft}
          leaving={leaving}
          onLeave={() => void handleLeave()}
          isAiGame={game.players.some((p) => p.player_type === "ai")}
        />
      ) : game.status === "active" ? (
        <GameRoomProvider
          value={{
            selectedCard,
            onSelectCard: setSelectedCard,
            selectedCardElement,
            movePending,
            usePower,
            onUsePowerChange: (next) => {
              setUsePower(next);
              setPowerSide(null);
              setIntimidatePendingCell(null);
            },
            powerSide,
            onPowerSideToggle: (side) => {
              setPowerSide(powerSide === side ? null : side);
            },
            intimidatePendingCell,
            onCancelIntimidatePending: () => setIntimidatePendingCell(null),
            archetypePending,
            archetypeError,
            onSelectArchetype: (arch) => void handleSelectArchetype(arch),
            onPreviewCard: (cardKey, def) => setPreviewCard({ cardKey, def }),
            leaving,
            onOpenLeaveConfirm: () => setShowLeaveConfirm(true),
            showLeaveConfirm,
            onCloseLeaveConfirm: () => setShowLeaveConfirm(false),
            onConfirmLeave: () => {
              setShowLeaveConfirm(false);
              void handleLeave();
            },
            onShowRules: () => setShowRules(true),
          }}
        >
          <ActiveGameView
            game={game}
            myIndex={myIndex}
            myPlayer={myPlayer}
            opponentPlayer={opponentPlayer}
            myScore={myScore}
            opponentScore={opponentScore}
            cardDefs={cardDefs}
            placedCells={placedCells}
            capturedCells={capturedCells}
            onPlaceCard={(cellIndex) => void handlePlaceCard(cellIndex)}
            boardElements={game.board_elements ?? null}
            moveError={moveError}
          />
        </GameRoomProvider>
      ) : game.status === "waiting" ? (
        <WaitingGameView
          game={game}
          isParticipant={isParticipant}
          isFull={isFull}
          copied={copied}
          onCopyLink={handleCopyLink}
          joining={joining}
          onJoin={() => void handleJoin()}
          leaving={leaving}
          onCancel={isParticipant ? () => void handleLeave() : undefined}
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
      <CardInspectPreview
        open={previewCard !== null}
        cardKey={lastPreviewCard.current.cardKey}
        def={lastPreviewCard.current.def}
        onClose={() => setPreviewCard(null)}
      />

      <GameRulesDialog open={showRules} onClose={() => setShowRules(false)} />
    </div>
  );
}
