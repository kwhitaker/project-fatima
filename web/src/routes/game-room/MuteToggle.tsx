import { useState } from "react";
import { isMuted, setMuted } from "@/lib/sounds";

export function MuteToggle() {
  const [muted, setMutedState] = useState(isMuted);

  const toggle = () => {
    const next = !muted;
    setMuted(next);
    setMutedState(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      className="text-lg leading-none p-1 border-2 border-border hover:border-accent cursor-pointer"
      aria-label={muted ? "unmute sounds" : "mute sounds"}
      title={muted ? "Unmute" : "Mute"}
    >
      {muted ? "\uD83D\uDD07" : "\uD83D\uDD0A"}
    </button>
  );
}
