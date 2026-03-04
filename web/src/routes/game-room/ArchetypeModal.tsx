import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ModalShell } from "@/components/ui/ModalShell";
import type { Archetype } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ArchetypePowerAside } from "@/routes/game-room/ArchetypePowerAside";
import { useGameRoom } from "@/routes/game-room/GameRoomContext";

export function ArchetypeModal({ open }: { open: boolean }) {
  const { archetypePending: pending, archetypeError: error, onSelectArchetype: onSelect } = useGameRoom();
  const [activeArch, setActiveArch] = useState<Archetype>("martial");
  const [selectedArch, setSelectedArch] = useState<Archetype | null>(null);
  const archetypes: Archetype[] = [
    "martial",
    "skulker",
    "caster",
    "devout",
    "intimidate",
  ];
  // Preview follows selection first, then hover/focus
  const previewArch = selectedArch ?? activeArch;

  return (
    <ModalShell
      open={open}
      onClose={() => {}}
      maxWidth="max-w-lg"
      aria-labelledby="archetype-modal-title"
      data-testid="archetype-modal"
    >
      <h2 id="archetype-modal-title" className="text-lg font-bold mb-1">
        Choose Your Archetype
      </h2>
      <p className="text-sm text-muted-foreground mb-4">
        Select a once-per-game power before you can place cards.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          {archetypes.map((arch) => (
            <Button
              key={arch}
              variant={selectedArch === arch ? "default" : "outline"}
              className={cn(
                "capitalize w-full justify-start",
                selectedArch === arch && "ring-2 ring-primary ring-offset-1",
              )}
              onClick={() => setSelectedArch(arch)}
              disabled={pending}
              onFocus={() => setActiveArch(arch)}
              onMouseEnter={() => setActiveArch(arch)}
              aria-pressed={selectedArch === arch}
            >
              {arch}
            </Button>
          ))}
        </div>
        <div aria-live="polite" aria-atomic="true">
          <ArchetypePowerAside
            archetype={previewArch}
            label="archetype power details"
            showName
          />
        </div>
      </div>
      <Button
        className="w-full mt-4"
        disabled={selectedArch === null || pending}
        onClick={() => selectedArch && void onSelect(selectedArch)}
        aria-label="confirm archetype"
      >
        {pending ? "Confirming…" : "Confirm"}
      </Button>
      {error && <p className="text-destructive text-sm mt-3">{error}</p>}
    </ModalShell>
  );
}
