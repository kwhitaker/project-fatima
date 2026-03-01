import { Button } from "@/components/ui/button";

export function ForfeitDialog({
  open,
  leaving,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  leaving: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="forfeit-dialog-title"
      data-testid="forfeit-dialog"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      onKeyDown={(e) => {
        if (e.key === "Escape") onCancel();
      }}
    >
      <div className="bg-white border border-zinc-200 rounded-lg p-6 w-full max-w-sm shadow-xl dark:bg-zinc-900 dark:border-zinc-700">
        <h2 id="forfeit-dialog-title" className="text-lg font-bold mb-1">
          Forfeit Game?
        </h2>
        <p className="text-sm text-muted-foreground mb-4">
          Leaving now will count as a forfeit. Your opponent will be awarded the win.
        </p>
        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            data-confirm
            onClick={onConfirm}
            disabled={leaving}
          >
            {leaving ? "Leaving…" : "Forfeit & Leave"}
          </Button>
        </div>
      </div>
    </div>
  );
}
