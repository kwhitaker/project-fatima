import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import type { AIDifficulty } from "@/lib/api";
import { cn } from "@/lib/utils";

const BUBBLE_DURATION_MS = 3500;

const STYLE_BY_DIFFICULTY: Record<AIDifficulty, string> = {
  easy: "bg-amber-50 border-amber-300 text-amber-900 dark:bg-amber-950/60 dark:border-amber-700 dark:text-amber-200",
  medium: "bg-slate-100 border-slate-400 text-slate-800 dark:bg-slate-800/60 dark:border-slate-600 dark:text-slate-200",
  hard: "bg-red-950/80 border-red-700 text-red-100 dark:bg-red-950/80 dark:border-red-600 dark:text-red-200",
  nightmare: "bg-violet-950/80 border-violet-600 text-violet-100 shadow-[0_0_12px_rgba(139,92,246,0.3)] dark:bg-violet-950/90 dark:border-violet-500 dark:text-violet-200 dark:shadow-[0_0_16px_rgba(139,92,246,0.4)]",
};

export function AiCommentBubble({
  comment,
  difficulty,
}: {
  comment: string | null | undefined;
  difficulty: AIDifficulty | null | undefined;
}) {
  const [visible, setVisible] = useState(false);
  const [displayedComment, setDisplayedComment] = useState<string | null>(null);

  useEffect(() => {
    if (comment) {
      setDisplayedComment(comment);
      setVisible(true);
      const timer = setTimeout(() => setVisible(false), BUBBLE_DURATION_MS);
      return () => clearTimeout(timer);
    } else {
      setVisible(false);
    }
  }, [comment]);

  const style = difficulty ? STYLE_BY_DIFFICULTY[difficulty] : STYLE_BY_DIFFICULTY.easy;

  return (
    <AnimatePresence>
      {visible && displayedComment && (
        <motion.div
          key={displayedComment}
          className={cn(
            "pointer-events-none text-sm italic px-3 py-1.5 rounded-lg border-2 max-w-64",
            style,
          )}
          aria-label="ai comment"
          aria-live="polite"
          initial={{ opacity: 0, y: -8, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.9 }}
          transition={{ type: "spring", stiffness: 400, damping: 25 }}
        >
          &ldquo;{displayedComment}&rdquo;
        </motion.div>
      )}
    </AnimatePresence>
  );
}
