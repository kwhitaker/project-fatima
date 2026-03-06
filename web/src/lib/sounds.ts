/**
 * Procedural 8-bit sound effects via Web Audio API.
 * No external audio files — pure oscillator synthesis.
 *
 * Usage:
 *   import { initAudio, playPlace, playCapture, ... } from "@/lib/sounds";
 *   // Call initAudio() on first user gesture (click/tap)
 *   // Then call play* functions fire-and-forget
 */

const MASTER_GAIN = 0.12;
const MUTE_KEY = "yugi-strahd-muted";

let ctx: AudioContext | null = null;
let masterGain: GainNode | null = null;
let muted = typeof localStorage !== "undefined" && localStorage.getItem(MUTE_KEY) === "true";

/** Lazy-init AudioContext on first user gesture. Returns true if ready. */
export function initAudio(): boolean {
  if (ctx) return true;
  try {
    ctx = new AudioContext();
    masterGain = ctx.createGain();
    masterGain.gain.value = muted ? 0 : MASTER_GAIN;
    masterGain.connect(ctx.destination);
    return true;
  } catch {
    return false;
  }
}

export function isMuted(): boolean {
  return muted;
}

export function setMuted(value: boolean): void {
  muted = value;
  localStorage.setItem(MUTE_KEY, String(value));
  if (masterGain) {
    masterGain.gain.value = muted ? 0 : MASTER_GAIN;
  }
}

// ── Helpers ──────────────────────────────────────────────────

function osc(
  type: OscillatorType,
  freq: number,
  startTime: number,
  duration: number,
  gain: number,
  freqEnd?: number,
): void {
  if (!ctx || !masterGain) return;
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type;
  o.frequency.setValueAtTime(freq, startTime);
  if (freqEnd !== undefined) {
    o.frequency.linearRampToValueAtTime(freqEnd, startTime + duration);
  }
  g.gain.setValueAtTime(gain, startTime);
  g.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
  o.connect(g);
  g.connect(masterGain);
  o.start(startTime);
  o.stop(startTime + duration);
}

function now(): number {
  return ctx ? ctx.currentTime : 0;
}

// ── Sound effects ────────────────────────────────────────────

/** Short low-frequency thud for card placement */
export function playPlace(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  osc("sine", 120, t, 0.08, 0.8);
  osc("square", 80, t, 0.06, 0.3);
}

/** Quick rising tone for a single capture */
export function playCapture(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  osc("square", 300, t, 0.12, 0.6, 500);
}

/** Rapid ascending arpeggio for multi-captures (combo) */
export function playCombo(count: number): void {
  if (!ctx || !masterGain) return;
  const t = now();
  const notes = [330, 440, 550, 660];
  const steps = Math.min(count + 1, notes.length);
  for (let i = 0; i < steps; i++) {
    osc("square", notes[i], t + i * 0.06, 0.08, 0.5);
  }
}

/** Bright two-tone chime for Plus trigger */
export function playPlus(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  osc("square", 660, t, 0.1, 0.5);
  osc("square", 880, t + 0.08, 0.1, 0.5);
}

/** Shimmery descending tone for Elemental trigger */
export function playElemental(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  osc("sawtooth", 800, t, 0.2, 0.4, 400);
  osc("sine", 1200, t, 0.15, 0.2, 600);
}

/** Subtle soft tick for turn start */
export function playTurnStart(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  osc("square", 1000, t, 0.03, 0.3);
}

/** Triumphant 4-note ascending fanfare */
export function playVictory(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  const notes = [330, 440, 550, 660];
  for (let i = 0; i < notes.length; i++) {
    osc("square", notes[i], t + i * 0.15, 0.2, 0.6);
  }
  // Sustain final note
  osc("sawtooth", 660, t + 0.6, 0.4, 0.3);
}

/** Descending minor tone for defeat */
export function playDefeat(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  osc("sawtooth", 400, t, 0.3, 0.5, 200);
  osc("square", 300, t + 0.2, 0.4, 0.3, 150);
}

// ── Archetype sound effects ─────────────────────────────────

/** Quick rising sweep (whoosh) for Martial */
export function playMartial(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  osc("sawtooth", 200, t, 0.15, 0.5, 800);
  osc("sine", 150, t + 0.05, 0.12, 0.3, 600);
}

/** Sharp staccato burst for Skulker */
export function playSkulker(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  osc("square", 600, t, 0.04, 0.7);
  osc("square", 900, t + 0.05, 0.04, 0.5);
  osc("square", 1200, t + 0.1, 0.03, 0.3);
}

/** Deep resonant hum for Caster */
export function playCaster(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  osc("sine", 100, t, 0.4, 0.6);
  osc("sine", 150, t, 0.35, 0.4);
  osc("sawtooth", 200, t + 0.1, 0.3, 0.2, 180);
}

/** Gentle chime/bell for Devout */
export function playDevout(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  osc("sine", 880, t, 0.2, 0.5);
  osc("sine", 1320, t + 0.05, 0.25, 0.3);
  osc("sine", 1760, t + 0.1, 0.2, 0.2);
}

/** Low aggressive rumble for Intimidate */
export function playIntimidate(): void {
  if (!ctx || !masterGain) return;
  const t = now();
  osc("sawtooth", 80, t, 0.25, 0.7, 50);
  osc("square", 60, t + 0.05, 0.2, 0.5, 40);
  osc("sawtooth", 120, t + 0.1, 0.15, 0.3, 60);
}
