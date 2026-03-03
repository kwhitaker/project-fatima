import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ModalShell } from "@/components/ui/ModalShell";
import type { Archetype } from "@/lib/api";
import { ArchetypePowerAside } from "@/routes/game-room/ArchetypePowerAside";
import { useGameRoom } from "@/routes/game-room/GameRoomContext";

export function ArchetypeModal({ open }: { open: boolean }) {
  const { archetypePending: pending, archetypeError: error, onSelectArchetype: onSelect } = useGameRoom();
  const [activeArch, setActiveArch] = useState<Archetype>("martial");
  const archetypes: Archetype[] = [
    "martial",
    "skulker",
    "caster",
    "devout",
    "intimidate",
  ];

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
              variant="default"
              className="capitalize w-full justify-start"
              onClick={() => void onSelect(arch)}
              disabled={pending}
              onFocus={() => setActiveArch(arch)}
              onMouseEnter={() => setActiveArch(arch)}
            >
              {arch}
            </Button>
          ))}
        </div>
        <div aria-live="polite" aria-atomic="true">
          <ArchetypePowerAside
            archetype={activeArch}
            label="archetype power details"
            showName
          />
        </div>
      </div>
      {error && <p className="text-destructive text-sm mt-3">{error}</p>}
    </ModalShell>
  );
}
