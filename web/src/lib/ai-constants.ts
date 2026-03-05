import type { AIDifficulty } from "./api";

export const AI_DISPLAY_NAMES: Record<AIDifficulty, string> = {
  easy: "Ireena Kolyana",
  medium: "Rahadin",
  hard: "Strahd von Zarovich",
  nightmare: "The Dark Powers",
};

export const AI_THINKING_TEXT: Record<AIDifficulty, string> = {
  easy: "Ireena is thinking...",
  medium: "Rahadin calculates...",
  hard: "Strahd contemplates...",
  nightmare: "The Dark Powers stir...",
};
