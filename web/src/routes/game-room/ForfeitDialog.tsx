import { Button } from "@/components/ui/button";
import { ModalShell } from "@/components/ui/ModalShell";

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
  return (
    <ModalShell
      open={open}
      onClose={onCancel}
      maxWidth="max-w-sm"
      aria-labelledby="forfeit-dialog-title"
      data-testid="forfeit-dialog"
    >
      <h2 id="forfeit-dialog-title" className="text-lg font-bold mb-1">
        Forfeit Game?
      </h2>
      <p className="text-sm text-muted-foreground mb-4">
        Leaving now will count as a forfeit. Your opponent will be awarded the win.
      </p>
      <div className="flex flex-wrap gap-2 justify-end">
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
    </ModalShell>
  );
}
