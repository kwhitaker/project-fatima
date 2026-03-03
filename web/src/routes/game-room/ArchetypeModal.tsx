import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Button } from "@/components/ui/button";
import type { Archetype } from "@/lib/api";
import { ArchetypePowerAside } from "@/routes/game-room/ArchetypePowerAside";

export function ArchetypeModal({
  open,
  pending,
  error,
  onSelect,
}: {
  open: boolean;
  pending: boolean;
  error: string | null;
  onSelect: (archetype: Archetype) => void | Promise<void>;
}) {
  const [activeArch, setActiveArch] = useState<Archetype>("martial");
  const archetypes: Archetype[] = [
    "martial",
    "skulker",
    "caster",
    "devout",
    "presence",
  ];

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-labelledby="archetype-modal-title"
          data-testid="archetype-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          <motion.div
            className="bg-white border-2 border-zinc-200 rounded-none p-6 w-full max-w-lg shadow-xl dark:bg-zinc-900 dark:border-zinc-700"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.15 }}
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
                    variant="outline"
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
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
