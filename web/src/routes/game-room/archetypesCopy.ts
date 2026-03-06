import type { Archetype } from "@/lib/api";

export type ArchetypeCopy = {
  name: string;
  powerTitle: string;
  powerText: string;
};

export const ARCHETYPE_COPY: Record<Archetype, ArchetypeCopy> = {
  martial: {
    name: "Martial",
    powerTitle: "Spin your card",
    powerText:
      "After you place a card, choose CW or CCW to spin it one step before fights start. Use it once per game.",
  },
  skulker: {
    name: "Skulker",
    powerTitle: "+3 on one side",
    powerText:
      "After you place a card, pick N/E/S/W. That side gets +3 for this move only. Use it once per game.",
  },
  caster: {
    name: "Caster",
    powerTitle: "Guaranteed Omen",
    powerText:
      "Your Mists result is always +2 for this placement. Use it once per game.",
  },
  devout: {
    name: "Devout",
    powerTitle: "Ward",
    powerText:
      "After placing, choose one of your cards on the board. It cannot be captured by the opponent's next placement. Use it once per game.",
  },
  intimidate: {
    name: "Intimidate",
    powerTitle: "Weaken an enemy card",
    powerText:
      "After you place a card, pick an adjacent opponent card. Its facing side is reduced by 3 (min 1) for this comparison only. Use it once per game.",
  },
};
