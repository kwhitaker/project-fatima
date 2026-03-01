import type { CardDefinition } from "@/lib/api";

export function cardTitle(cardKey: string, def?: CardDefinition) {
  const name = def?.name ?? cardKey;
  const tier = def?.tier;
  return tier != null ? `${name} (Tier ${tier})` : name;
}
