import { Button } from "@/components/ui/button";
import type { CardDefinition } from "@/lib/api";
import { ELEMENT_SYMBOLS } from "@/routes/game-room/BoardGrid";

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
    <div
      role="dialog"
      aria-modal="true"
      aria-label="card preview"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      <div className="bg-white border border-zinc-200 rounded-lg p-6 w-full max-w-xs shadow-xl dark:bg-zinc-900 dark:border-zinc-700">
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
      </div>
    </div>
  );
}
