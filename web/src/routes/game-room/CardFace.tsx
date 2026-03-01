import type { CardDefinition } from "@/lib/api";

export function CardFace({
  cardKey,
  def,
}: {
  cardKey: string;
  def?: CardDefinition;
}) {
  const name = def?.name ?? cardKey;
  return (
    <div className="flex flex-col items-center justify-between w-full h-full p-1">
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
