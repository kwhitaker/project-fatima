import { Button } from "@/components/ui/button";
import { ModalShell } from "@/components/ui/ModalShell";
import { ArchetypePowerAside } from "@/routes/game-room/ArchetypePowerAside";

export function GameRulesDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <ModalShell
      open={open}
      onClose={onClose}
      maxWidth="max-w-2xl"
      className="p-0 max-h-[85vh] overflow-hidden"
      aria-labelledby="game-rules-title"
    >
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

          <section className="space-y-2">
            <h3 className="font-semibold text-base">Plus Rule</h3>
            <p className="text-muted-foreground">
              A hidden capture that rewards knowing your cards' numbers.
            </p>
            <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
              <li>Before normal fights, look at each adjacent enemy card.</li>
              <li>Add your touching side to their touching side (raw printed numbers only — Mists and Elemental do not apply).</li>
              <li>If 2 or more of those sums are equal, all matching enemies are captured immediately — even if your side is lower.</li>
              <li>Plus-captured cards then trigger normal combo chains.</li>
            </ul>
            <p className="text-muted-foreground text-xs">
              Example: you place a card, N=6 faces an enemy with S=7 (sum 13), and W=3 faces an enemy with E=10 (sum 13). Both sums match → Plus fires, both captured.
            </p>
          </section>

          <section className="space-y-2">
            <h3 className="font-semibold text-base">Elemental System</h3>
            <p className="text-muted-foreground">
              Every card and every board cell has an element: Blood 🩸, Holy ✦, Arcane ✧, Shadow ◆, or Nature ✿.
            </p>
            <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
              <li>If your card's element matches the cell you place it on, your card gets +1 on all its comparisons for that placement.</li>
              <li>This bonus stacks with the Mists modifier.</li>
              <li>Combo chain captures and Plus rule sums always use raw printed values — Elemental does not apply.</li>
            </ul>
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
              <ArchetypePowerAside archetype="intimidate" showName />
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
    </ModalShell>
  );
}
