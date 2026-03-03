import { motion, AnimatePresence } from "motion/react";
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
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-labelledby="forfeit-dialog-title"
          data-testid="forfeit-dialog"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          onKeyDown={(e) => {
            if (e.key === "Escape") onCancel();
          }}
        >
          <motion.div
            className="bg-card border-2 border-border rounded-none p-6 w-full max-w-sm shadow-xl"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.15 }}
          >
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
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
