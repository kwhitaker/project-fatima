import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";

const SD_TEXT: Record<number, { heading: string; subtitle: string }> = {
  2: {
    heading: "Sudden Death",
    subtitle: "The souls are bound. Play on.",
  },
  3: {
    heading: "Sudden Death II",
    subtitle: "The Mists refuse to release you.",
  },
  4: {
    heading: "Final Sudden Death",
    subtitle: "Barovia trembles. This ends now.",
  },
};

/**
 * Full-screen overlay banner shown when Sudden Death begins.
 * Detects round_number transitions (> 1) and auto-dismisses after 3.5s.
 */
export function SuddenDeathBanner({ roundNumber }: { roundNumber: number }) {
  const [visible, setVisible] = useState(false);
  const [displayRound, setDisplayRound] = useState(roundNumber);
  const prevRoundRef = useRef(roundNumber);

  useEffect(() => {
    if (roundNumber > 1 && roundNumber !== prevRoundRef.current) {
      setDisplayRound(roundNumber);
      setVisible(true);
      const timer = setTimeout(() => setVisible(false), 3500);
      prevRoundRef.current = roundNumber;
      return () => clearTimeout(timer);
    }
    prevRoundRef.current = roundNumber;
  }, [roundNumber]);

  const text = SD_TEXT[displayRound] ?? SD_TEXT[4];

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key={`sd-banner-${displayRound}`}
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/75 cursor-pointer"
          role="alert"
          aria-label="sudden death banner"
          onClick={() => setVisible(false)}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          <motion.h2
            className="font-heading text-4xl sm:text-5xl md:text-6xl font-bold text-red-500 drop-shadow-lg text-center"
            style={{
              textShadow:
                "0 0 30px rgba(220,38,38,0.8), 0 0 60px rgba(220,38,38,0.4), 0 4px 0 rgba(127,29,29,0.6)",
            }}
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: [0.5, 1.15, 1], opacity: 1 }}
            transition={{
              scale: {
                type: "tween",
                times: [0, 0.6, 1],
                duration: 0.5,
              },
              opacity: { duration: 0.2 },
            }}
          >
            {text.heading}
          </motion.h2>
          <motion.p
            className="mt-4 text-lg sm:text-xl text-stone-400 font-heading text-center px-4"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
          >
            {text.subtitle}
          </motion.p>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
