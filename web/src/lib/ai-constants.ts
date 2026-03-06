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

export const AI_LONG_DESCRIPTIONS: Record<AIDifficulty, string> = {
  easy: "Ireena Kolyana, adopted daughter of the Burgomaster, plays with earnest enthusiasm but little cunning. She places cards on instinct, sometimes stumbling into captures by sheer luck. A forgiving opponent for those still learning the ways of the game.",
  medium: "Rahadin, dusk elf chamberlain to the lord of Castle Ravenloft, approaches the board with ruthless efficiency. He evaluates every legal move and picks the one that claims the most ground. Sentiment is a weakness he long ago discarded.",
  hard: "Strahd von Zarovich, the Devil of Barovia, peers into the fog of possibility itself. He infers what you hold, anticipates your plans, and punishes every misstep. Centuries of undeath have sharpened his mind into something terrible.",
  nightmare: "The Dark Powers are not opponents — they are the rules made flesh. With vast, inscrutable patience they explore thousands of futures before choosing the one where you suffer most. Few mortals endure their gaze for long.",
};
