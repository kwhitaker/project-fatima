import { Button } from "@/components/ui/button";
import type { GameState } from "@/lib/api";

export function WaitingGameView({
  game,
  isParticipant,
  isFull,
  copied,
  onCopyLink,
  joining,
  onJoin,
}: {
  game: GameState;
  isParticipant: boolean;
  isFull: boolean;
  copied: boolean;
  onCopyLink: () => void;
  joining: boolean;
  onJoin: () => void | Promise<void>;
}) {
  return (
    <div className="flex-1 min-h-0 overflow-y-auto">
      <div className="mt-4 space-y-4">
        <p className="text-muted-foreground text-sm">
          Waiting for players… ({game.players.length}/2)
        </p>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <span className="font-mono text-sm break-all">{window.location.href}</span>
          <Button variant="outline" size="sm" onClick={onCopyLink} className="shrink-0">
            {copied ? "Copied!" : "Copy Link"}
          </Button>
        </div>

        {!isParticipant && !isFull && (
          <Button onClick={() => void onJoin()} disabled={joining}>
            {joining ? "Joining…" : "Join Game"}
          </Button>
        )}
        {!isParticipant && isFull && (
          <p className="text-muted-foreground text-sm">This game is full. You cannot join.</p>
        )}
      </div>
    </div>
  );
}
