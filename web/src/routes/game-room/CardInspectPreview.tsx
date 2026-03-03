import { Button } from "@/components/ui/button";
import { ModalShell } from "@/components/ui/ModalShell";
import type { CardDefinition } from "@/lib/api";
import { ELEMENT_SYMBOLS } from "@/routes/game-room/BoardGrid";
import { cardEmoji, tierClass } from "@/routes/game-room/CardFace";

export function CardInspectPreview({
  open,
  cardKey,
  def,
  onClose,
}: {
  open: boolean;
  cardKey: string;
  def?: CardDefinition;
  onClose: () => void;
}) {
  const name = def?.name ?? cardKey;
  return (
    <ModalShell
      open={open}
      onClose={onClose}
      maxWidth="max-w-xs"
      className={tierClass(def?.tier)}
      aria-label="card preview"
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
    </ModalShell>
  );
}
