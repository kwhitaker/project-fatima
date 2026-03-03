import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";

const BAT_COUNT = 12;
const CONFETTI_COUNT = 24;

function randomBetween(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

/** Generate bat flight paths with randomized positions. */
function makeBats() {
  return Array.from({ length: BAT_COUNT }, (_, i) => ({
    id: i,
    startX: randomBetween(-10, 110),
    startY: randomBetween(20, 80),
    endX: randomBetween(-10, 110),
    endY: randomBetween(-10, 30),
    duration: randomBetween(1.5, 2.5),
    delay: randomBetween(0, 0.8),
    size: randomBetween(16, 28),
  }));
}

/** Stepped easing: simulates CSS steps(N) for pixel-style animation. */
function steppedEase(steps: number) {
  return (t: number) => Math.floor(t * steps) / steps;
}

/** Generate confetti particles in blood-red and gold. */
function makeConfetti() {
  const colors = [
    "rgb(180,30,30)", // blood red
    "rgb(220,50,50)", // lighter red
    "rgb(200,160,40)", // gold
    "rgb(230,190,60)", // lighter gold
  ];
  return Array.from({ length: CONFETTI_COUNT }, (_, i) => ({
    id: i,
    x: randomBetween(5, 95),
    y: randomBetween(-20, -5),
    endY: randomBetween(80, 120),
    rotation: randomBetween(0, 360),
    color: colors[i % colors.length],
    duration: randomBetween(1.5, 2.5),
    delay: randomBetween(0, 0.6),
    size: randomBetween(4, 10),
  }));
}

export function VictoryOverlay({ onDismiss }: { onDismiss: () => void }) {
  const [visible, setVisible] = useState(true);
  const [bats] = useState(makeBats);
  const [confetti] = useState(makeConfetti);

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
          transition={{ duration: 0.3 }}
          aria-label="victory overlay"
          data-testid="victory-overlay"
        >
          {/* Dark backdrop */}
          <div className="absolute inset-0 bg-black/70" />

          {/* Confetti particles */}
          {confetti.map((c) => (
            <motion.div
              key={`confetti-${c.id}`}
              className="absolute pointer-events-none"
              style={{
                left: `${c.x}%`,
                width: c.size,
                height: c.size,
                backgroundColor: c.color,
              }}
              initial={{ y: `${c.y}vh`, rotate: 0, opacity: 1 }}
              animate={{
                y: `${c.endY}vh`,
                rotate: c.rotation,
                opacity: [1, 1, 0],
              }}
              transition={{
                duration: c.duration,
                delay: c.delay,
                ease: steppedEase(6),
                repeat: Infinity,
              }}
            />
          ))}

          {/* Bat swarm */}
          {bats.map((bat) => (
            <motion.div
              key={`bat-${bat.id}`}
              className="absolute pointer-events-none select-none"
              style={{ fontSize: bat.size, left: `${bat.startX}%`, top: `${bat.startY}%` }}
              initial={{ x: 0, y: 0, opacity: 0 }}
              animate={{
                x: `${bat.endX - bat.startX}vw`,
                y: `${bat.endY - bat.startY}vh`,
                opacity: [0, 1, 1, 0],
              }}
              transition={{
                duration: bat.duration,
                delay: bat.delay,
                ease: steppedEase(8),
              }}
            >
              🦇
            </motion.div>
          ))}

          {/* VICTORY text — stepped scale-in */}
          <motion.div
            className="relative z-10 text-center"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: [0, 0.5, 1.3, 1], opacity: 1 }}
            transition={{
              scale: {
                type: "tween",
                times: [0, 0.3, 0.7, 1],
                duration: 0.5,
                ease: steppedEase(4),
              },
              opacity: { duration: 0.2 },
            }}
          >
            <h1
              className="font-heading text-4xl sm:text-6xl text-yellow-400 drop-shadow-lg"
              style={{
                textShadow: "0 0 20px rgba(234,179,8,0.6), 0 4px 0 rgb(180,30,30)",
              }}
            >
              VICTORY
            </h1>
            <motion.p
              className="font-body text-lg text-yellow-200/80 mt-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5, duration: 0.3 }}
            >
              The darkness bows before you
            </motion.p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
