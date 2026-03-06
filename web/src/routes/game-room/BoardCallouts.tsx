import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ELEMENT_SYMBOLS } from "@/routes/game-room/BoardGrid";

function steppedEase(steps: number) {
  return (t: number) => Math.floor(t * steps) / steps;
}

/** Auto-dismissing callout key: changes trigger a fresh show → fade cycle. */
function useAutoFade(triggerKey: string | null, durationMs = 2000): boolean {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!triggerKey) {
      setVisible(false);
      return;
    }
    setVisible(true);
    const timer = setTimeout(() => setVisible(false), durationMs);
    return () => clearTimeout(timer);
  }, [triggerKey, durationMs]);
  return visible;
}

/**
 * Board-level event feedback callouts.
 * Renders as an absolutely-positioned overlay on the board container.
 * pointer-events-none so it never blocks cell clicks.
 */
export function BoardCallouts({
  mistsEffect,
  captureCount,
  plusTriggered,
  elementalTriggered,
  elementKey,
  archetypeUsedName,
  changeKey,
}: {
  mistsEffect: "fog" | "omen" | "none" | null;
  captureCount: number;
  plusTriggered: boolean;
  elementalTriggered: boolean;
  elementKey: string | null;
  archetypeUsedName: string | null;
  /** Unique key per move to trigger fresh animations. */
  changeKey: string | null;
}) {
  const showMists = useAutoFade(
    mistsEffect && mistsEffect !== "none" && changeKey
      ? `${changeKey}-${mistsEffect}`
      : null,
    2000,
  );
  const showCapture = useAutoFade(
    captureCount > 0 && changeKey ? `${changeKey}-cap` : null,
    2500,
  );
  const showPlus = useAutoFade(
    plusTriggered && changeKey ? `${changeKey}-plus` : null,
    2500,
  );
  const showElemental = useAutoFade(
    elementalTriggered && changeKey ? `${changeKey}-elem` : null,
    2500,
  );
  const showArchetype = useAutoFade(
    archetypeUsedName && changeKey ? `${changeKey}-arch` : null,
    2500,
  );

  return (
    <div
      className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center gap-2 z-20"
      aria-label="board callouts"
    >
      <AnimatePresence>
        {/* Mists callout */}
        {showMists && mistsEffect === "fog" && (
          <motion.div
            key={`fog-${changeKey}`}
            className="font-heading text-lg sm:text-xl font-bold text-blue-300 drop-shadow-lg"
            style={{
              textShadow:
                "0 0 12px rgba(147,197,253,0.7), 0 2px 0 rgba(30,58,138,0.5)",
            }}
            aria-label="board mists callout"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: [0, 1.3, 1], opacity: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{
              scale: {
                type: "tween",
                times: [0, 0.5, 1],
                duration: 0.4,
                ease: steppedEase(4),
              },
              opacity: { duration: 0.2 },
            }}
          >
            The Mists cloud your vision… −2
          </motion.div>
        )}

        {showMists && mistsEffect === "omen" && (
          <motion.div
            key={`omen-${changeKey}`}
            className="font-heading text-lg sm:text-xl font-bold text-purple-300 drop-shadow-lg"
            style={{
              textShadow:
                "0 0 16px rgba(192,132,252,0.7), 0 2px 0 rgba(88,28,135,0.5)",
            }}
            aria-label="board mists callout"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: [0, 1.3, 1], opacity: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{
              scale: {
                type: "tween",
                times: [0, 0.5, 1],
                duration: 0.4,
                ease: steppedEase(4),
              },
              opacity: { duration: 0.2 },
            }}
          >
            The Mists favor you! +2
          </motion.div>
        )}

        {/* Capture callout */}
        {showCapture && captureCount === 1 && (
          <motion.div
            key={`cap1-${changeKey}`}
            className="font-heading text-base font-semibold text-amber-300 drop-shadow-md"
            aria-label="board capture callout"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            1 card claimed
          </motion.div>
        )}
        {showCapture && captureCount > 1 && (
          <motion.div
            key={`combo-${changeKey}`}
            className="font-heading text-xl sm:text-2xl font-bold text-purple-300 drop-shadow-lg"
            style={{ textShadow: "0 0 14px rgba(192,132,252,0.6)" }}
            aria-label="board capture callout"
            initial={{ scale: 1.5, opacity: 0 }}
            animate={{ scale: [1.5, 0.9, 1], opacity: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{
              scale: {
                type: "tween",
                times: [0, 0.6, 1],
                duration: 0.5,
                ease: steppedEase(4),
              },
              opacity: { duration: 0.2 },
            }}
          >
            Chain! ×{captureCount} claimed
          </motion.div>
        )}

        {/* Plus callout */}
        {showPlus && (
          <motion.div
            key={`plus-${changeKey}`}
            className="font-heading text-2xl sm:text-3xl font-bold text-cyan-300 drop-shadow-lg"
            style={{
              textShadow:
                "0 0 20px rgba(103,232,249,0.8), 0 2px 0 rgba(8,145,178,0.5)",
            }}
            aria-label="board plus callout"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: [0, 1.4, 1], opacity: 1 }}
            exit={{ opacity: 0, scale: 0.6 }}
            transition={{
              scale: {
                type: "tween",
                times: [0, 0.5, 1],
                duration: 0.4,
                ease: steppedEase(4),
              },
              opacity: { duration: 0.15 },
            }}
          >
            Plus!
          </motion.div>
        )}

        {/* Elemental callout */}
        {showElemental && (
          <motion.div
            key={`elem-${changeKey}`}
            className="font-heading text-xl sm:text-2xl font-bold text-yellow-300 drop-shadow-lg"
            style={{
              textShadow:
                "0 0 16px rgba(253,224,71,0.7), 0 2px 0 rgba(161,98,7,0.5)",
            }}
            aria-label="board elemental callout"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: [0, 1.3, 1], opacity: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{
              scale: {
                type: "tween",
                times: [0, 0.5, 1],
                duration: 0.4,
                ease: steppedEase(4),
              },
              opacity: { duration: 0.15 },
            }}
          >
            {elementKey
              ? `${ELEMENT_SYMBOLS[elementKey] ?? ""} ${elementKey.charAt(0).toUpperCase() + elementKey.slice(1)} Elemental!`
              : "Elemental!"}
          </motion.div>
        )}
        {/* Archetype callout */}
        {showArchetype && archetypeUsedName && (
          <motion.div
            key={`arch-${changeKey}`}
            className="font-heading text-xl sm:text-2xl font-bold text-amber-300 drop-shadow-lg"
            style={{
              textShadow:
                "0 0 16px rgba(251,191,36,0.7), 0 2px 0 rgba(146,64,14,0.5)",
            }}
            aria-label="board archetype callout"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: [0, 1.3, 1], opacity: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{
              scale: {
                type: "tween",
                times: [0, 0.5, 1],
                duration: 0.4,
                ease: steppedEase(4),
              },
              opacity: { duration: 0.15 },
            }}
          >
            {archetypeUsedName === "martial"
              ? "Martial Spin!"
              : archetypeUsedName.charAt(0).toUpperCase() +
                archetypeUsedName.slice(1) +
                "!"}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
