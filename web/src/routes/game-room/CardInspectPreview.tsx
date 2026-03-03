import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import type { CardDefinition } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ELEMENT_SYMBOLS } from "@/routes/game-room/BoardGrid";
import { cardEmoji, tierClass } from "@/routes/game-room/CardFace";

export function CardInspectPreview({
  cardKey,
  def,
  onClose,
}: {
  cardKey: string;
  def?: CardDefinition;
  onClose: () => void;
}) {
  const name = def?.name ?? cardKey;
  return (
    <motion.div
      role="dialog"
      aria-modal="true"
      aria-label="card preview"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      <motion.div
        className={cn("bg-card border-2 border-border rounded-none p-6 w-full max-w-xs shadow-xl", tierClass(def?.tier))}
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ duration: 0.15 }}
      >
        {cardEmoji(def?.character_key) && (
          <div className="text-4xl leading-none text-center mb-2 select-none" aria-hidden="true">
            {cardEmoji(def?.character_key)}
          </div>
        )}
        <h2 className="text-lg font-bold mb-3">{name}</h2>
        <div className="text-sm text-muted-foreground mb-3">
          {def?.element
            ? `Element: ${ELEMENT_SYMBOLS[def.element] ?? ""} ${def.element.charAt(0).toUpperCase() + def.element.slice(1)}`
            : "Element: —"}
        </div>
        <div className="grid grid-cols-3 gap-1 text-sm text-center mb-4">
          <div />
          <div className="font-semibold">N: {def?.sides.n ?? "—"}</div>
          <div />
          <div className="font-semibold">W: {def?.sides.w ?? "—"}</div>
          <div />
          <div className="font-semibold">E: {def?.sides.e ?? "—"}</div>
          <div />
          <div className="font-semibold">S: {def?.sides.s ?? "—"}</div>
          <div />
        </div>
        <Button variant="outline" className="w-full" onClick={onClose} autoFocus>
          Close
        </Button>
      </motion.div>
    </motion.div>
  );
}
