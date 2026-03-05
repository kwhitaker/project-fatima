import type { ReactNode } from "react";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";

export function ModalShell({
  open,
  onClose,
  maxWidth = "max-w-sm",
  className,
  children,
  "aria-labelledby": ariaLabelledBy,
  "aria-label": ariaLabel,
  "data-testid": dataTestId,
}: {
  open: boolean;
  onClose: () => void;
  maxWidth?: string;
  className?: string;
  children: ReactNode;
  "aria-labelledby"?: string;
  "aria-label"?: string;
  "data-testid"?: string;
}) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-labelledby={ariaLabelledBy}
          aria-label={ariaLabel}
          data-testid={dataTestId}
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
            className={cn(
              "bg-card border-2 border-border rounded-none p-6 w-full mx-4 shadow-xl",
              maxWidth,
              className,
            )}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.15 }}
          >
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
