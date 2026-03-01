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
      "After you place a card, it spins one step clockwise before fights start. Use it once per game.",
  },
  skulker: {
    name: "Skulker",
    powerTitle: "+2 on one side",
    powerText:
      "After you place a card, pick N/E/S/W. That side gets +2 for this move only. Use it once per game.",
  },
  caster: {
    name: "Caster",
    powerTitle: "Reroll the Mists",
    powerText:
      "When you roll the Mists, you may roll again. You must use the new roll. Use it once per game.",
  },
  devout: {
    name: "Devout",
    powerTitle: "Ignore a 1",
    powerText:
      "If you roll a 1, ignore it. You do not get -1 for this move. Use it once per game.",
  },
  presence: {
    name: "Presence",
    powerTitle: "+1 in one direction",
    powerText:
      "After you place a card, pick N/E/S/W. That side gets +1 for this move only. Use it once per game.",
  },
};
