import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";

const FOG_COUNT = 18;

function randomBetween(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

/** Stepped easing: simulates CSS steps(N) for pixel-style animation. */
function steppedEase(steps: number) {
  return (t: number) => Math.floor(t * steps) / steps;
}

/** Generate drifting fog/mist particles. */
function makeFogParticles() {
  return Array.from({ length: FOG_COUNT }, (_, i) => ({
    id: i,
    startX: randomBetween(-20, 110),
    y: randomBetween(10, 90),
    drift: randomBetween(30, 80),
    duration: randomBetween(3, 6),
    delay: randomBetween(0, 2),
    size: randomBetween(40, 100),
    opacity: randomBetween(0.08, 0.25),
  }));
}

export function DefeatOverlay({ onDismiss }: { onDismiss: () => void }) {
  const [visible, setVisible] = useState(true);
  const [fog] = useState(makeFogParticles);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(false), 3000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!visible) {
      const exit = setTimeout(onDismiss, 400);
      return () => clearTimeout(exit);
    }
  }, [visible, onDismiss]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center cursor-pointer"
          onClick={() => setVisible(false)}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5 }}
          aria-label="defeat overlay"
          data-testid="defeat-overlay"
        >
          {/* Dark backdrop with desaturation hint */}
          <div className="absolute inset-0 bg-black/80" />

          {/* Red vignette — radial gradient overlay */}
          <div
            className="absolute inset-0 pointer-events-none"
            data-testid="defeat-vignette"
            style={{
              background:
                "radial-gradient(ellipse at center, transparent 40%, rgba(100,0,0,0.6) 100%)",
            }}
          />

          {/* Fog particles drifting horizontally */}
          {fog.map((f) => (
            <motion.div
              key={`fog-${f.id}`}
              className="absolute pointer-events-none"
              data-testid="fog-particle"
              style={{
                left: `${f.startX}%`,
                top: `${f.y}%`,
                width: f.size,
                height: f.size * 0.4,
                borderRadius: "50%",
                backgroundColor: "rgba(180,180,200,0.15)",
                filter: "blur(8px)",
              }}
              initial={{ x: 0, opacity: 0 }}
              animate={{
                x: `${f.drift}vw`,
                opacity: [0, f.opacity, f.opacity, 0],
              }}
              transition={{
                duration: f.duration,
                delay: f.delay,
                ease: steppedEase(6),
                repeat: Infinity,
              }}
            />
          ))}

          {/* DEFEAT text — slow solemn fade-in */}
          <motion.div
            className="relative z-10 text-center"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 1.2,
              ease: steppedEase(6),
            }}
          >
            <h1
              className="font-heading text-4xl sm:text-6xl text-red-500"
              style={{
                textShadow:
                  "0 0 30px rgba(150,0,0,0.8), 0 0 60px rgba(100,0,0,0.4), 0 4px 0 rgb(60,0,0)",
              }}
            >
              DEFEAT
            </h1>
            <motion.p
              className="font-body text-lg text-red-300/70 mt-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.0, duration: 0.5 }}
            >
              The darkness claims another soul
            </motion.p>
          </motion.div>

          {/* Desaturation filter applied to content behind via mix-blend */}
          <div
            className="absolute inset-0 pointer-events-none"
            data-testid="defeat-desaturate"
            style={{
              backdropFilter: "grayscale(0.7)",
              WebkitBackdropFilter: "grayscale(0.7)",
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
