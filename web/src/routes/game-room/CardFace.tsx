import type { CardDefinition } from "@/lib/api";
import cardEmojis from "@/lib/card-emojis.json";
import { cn } from "@/lib/utils";

const emojiMap = cardEmojis as Record<string, string>;

/** Look up the emoji for a card by character_key. Returns undefined if not found. */
export function cardEmoji(characterKey?: string): string | undefined {
  if (!characterKey) return undefined;
  return emojiMap[characterKey];
}

export function tierClass(tier?: number): string {
  if (tier === 2) return "card-tier-2";
  if (tier === 3) return "card-tier-3";
  return "";
}

export function CardFace({
  cardKey,
  def,
  tier,
  emojiSize = "text-2xl sm:text-3xl",
}: {
  cardKey: string;
  def?: CardDefinition;
  tier?: number;
  emojiSize?: string;
}) {
  const name = def?.name ?? cardKey;
  const t = tier ?? def?.tier;
  const emoji = cardEmoji(def?.character_key);
  return (
    <div className={cn("flex flex-col items-center justify-between w-full h-full p-1", tierClass(t))}>
      <span className="text-[10px] sm:text-[11px] font-bold leading-none">
        {def?.sides.n ?? ""}
      </span>
      <div className="flex items-center justify-between w-full">
        <span className="text-[10px] sm:text-[11px] leading-none">
          {def?.sides.w ?? ""}
        </span>
        <div className="flex flex-col items-center min-w-0">
          {emoji && (
            <span className={cn(emojiSize, "leading-none select-none")} aria-hidden="true">
              {emoji}
            </span>
          )}
          <span className={cn(
            "font-semibold leading-tight text-center truncate max-w-[52px] sm:max-w-[64px]",
            emoji ? "text-[7px] sm:text-[8px]" : "text-[10px] sm:text-[11px]"
          )}>
            {name}
          </span>
        </div>
        <span className="text-[10px] sm:text-[11px] leading-none">
          {def?.sides.e ?? ""}
        </span>
      </div>
      <span className="text-[10px] sm:text-[11px] font-bold leading-none">
        {def?.sides.s ?? ""}
      </span>
    </div>
  );
}
