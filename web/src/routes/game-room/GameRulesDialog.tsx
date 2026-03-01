import { Button } from "@/components/ui/button";
import { ArchetypePowerAside } from "@/routes/game-room/ArchetypePowerAside";

export function GameRulesDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="game-rules-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      <div className="bg-white border border-zinc-200 rounded-lg w-full max-w-2xl shadow-xl dark:bg-zinc-900 dark:border-zinc-700 max-h-[85vh] overflow-hidden">
        <div className="p-6 overflow-y-auto max-h-[85vh]">
          <div className="flex items-start justify-between gap-4">
            <h2 id="game-rules-title" className="text-lg font-bold">
              How To Play
            </h2>
            <Button variant="outline" size="sm" onClick={onClose} autoFocus>
              Close
            </Button>
          </div>

          <div className="mt-4 space-y-5 text-sm">
            <section className="space-y-2">
              <h3 className="font-semibold text-base">Goal</h3>
              <p className="text-muted-foreground">
                Take more cards than your opponent by the time the 3x3 board is full.
              </p>
            </section>

            <section className="space-y-2">
              <h3 className="font-semibold text-base">Your Turn</h3>
              <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                <li>Pick a card from your hand.</li>
                <li>Place it on any empty square.</li>
                <li>The Mists roll happens (a small random bonus or penalty).</li>
                <li>Fights happen and cards may flip.</li>
              </ul>
            </section>

            <section className="space-y-2">
              <h3 className="font-semibold text-base">Captures (Flips)</h3>
              <p className="text-muted-foreground">
                When you place a card, it battles enemy cards next to it (up, down, left, right).
              </p>
              <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                <li>Compare the touching numbers.</li>
                <li>If your number is higher, you capture that card. It flips to your side.</li>
                <li>If it is tied or lower, nothing happens.</li>
              </ul>
            </section>

            <section className="space-y-2">
              <h3 className="font-semibold text-base">Combos</h3>
              <p className="text-muted-foreground">
                A flipped card can flip more cards right away. This can chain.
              </p>
            </section>

            <section className="space-y-2">
              <h3 className="font-semibold text-base">The Mists</h3>
              <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                <li>Roll 1: Fog. Your placed card is -2 in fights this turn.</li>
                <li>Roll 6: Omen. Your placed card is +2 in fights this turn.</li>
                <li>Roll 2-5: No effect.</li>
              </ul>
              <p className="text-muted-foreground">
                This bonus or penalty is only for the card you just placed, and only for that turn.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="font-semibold text-base">Archetypes (Once Per Game)</h3>
              <p className="text-muted-foreground">
                Each player picks one power. You can use your power once per game.
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                <ArchetypePowerAside archetype="martial" showName />
                <ArchetypePowerAside archetype="skulker" showName />
                <ArchetypePowerAside archetype="caster" showName />
                <ArchetypePowerAside archetype="devout" showName />
                <ArchetypePowerAside archetype="presence" showName />
              </div>
            </section>

            <section className="space-y-2">
              <h3 className="font-semibold text-base">Winning</h3>
              <p className="text-muted-foreground">
                When all 9 squares are filled, the player who controls more cards wins.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
