import type { Archetype } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ARCHETYPE_COPY } from "@/routes/game-room/archetypesCopy";

export function ArchetypePowerAside({
  archetype,
  label,
  showName = false,
  className,
}: {
  archetype: Archetype;
  label?: string;
  showName?: boolean;
  className?: string;
}) {
  const copy = ARCHETYPE_COPY[archetype];
  return (
    <aside
      aria-label={label ?? "archetype power"}
      className={cn(
        "rounded-lg border border-border bg-muted/40 p-3 text-sm",
        "dark:bg-muted/20",
        className
      )}
    >
      <p className="font-semibold">
        {showName ? `${copy.name}: ` : ""}
        {copy.powerTitle}
      </p>
      <p className="text-muted-foreground mt-1">{copy.powerText}</p>
    </aside>
  );
}
