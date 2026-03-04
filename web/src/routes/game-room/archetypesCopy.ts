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
    powerTitle: "Reroll the Mists",
    powerText:
      "When you roll the Mists, you may roll again. You must use the new roll. Use it once per game.",
  },
  devout: {
    name: "Devout",
    powerTitle: "Negate Fog",
    powerText:
      "If you roll a 1 (Fog), ignore it. You do not get -2 for this move. Use it once per game.",
  },
  intimidate: {
    name: "Intimidate",
    powerTitle: "Weaken an enemy card",
    powerText:
      "After you place a card, pick an adjacent opponent card. Its facing side becomes its weakest side for this comparison only. Use it once per game.",
  },
};
