import type { CardDefinition } from "@/lib/api";
import { cn } from "@/lib/utils";

export function tierClass(tier?: number): string {
  if (tier === 2) return "card-tier-2";
  if (tier === 3) return "card-tier-3";
  return "";
}

export function CardFace({
  cardKey,
  def,
  tier,
}: {
  cardKey: string;
  def?: CardDefinition;
  tier?: number;
}) {
  const name = def?.name ?? cardKey;
  const t = tier ?? def?.tier;
  return (
    <div className={cn("flex flex-col items-center justify-between w-full h-full p-1", tierClass(t))}>
      <span className="text-[10px] sm:text-[11px] font-bold leading-none">
        {def?.sides.n ?? ""}
      </span>
      <div className="flex items-center justify-between w-full">
        <span className="text-[10px] sm:text-[11px] leading-none">
          {def?.sides.w ?? ""}
        </span>
        <span className="text-[10px] sm:text-[11px] font-semibold leading-tight text-center truncate max-w-[52px] sm:max-w-[64px]">
          {name}
        </span>
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
