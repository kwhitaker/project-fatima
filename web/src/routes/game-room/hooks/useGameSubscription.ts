import { useEffect, useState } from "react";

import { supabase } from "@/lib/supabase";

export type RealtimeStatus = "connecting" | "live" | "reconnecting";

export function useGameSubscription(gameId: string | undefined, refetch: () => void) {
  const [realtimeStatus, setRealtimeStatus] = useState<RealtimeStatus>("connecting");

  useEffect(() => {
    if (!gameId) return;

    setRealtimeStatus("connecting");

    let fallbackInterval: ReturnType<typeof setInterval> | null = null;

    const channel = supabase
      .channel(`game:${gameId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "game_events",
          filter: `game_id=eq.${gameId}`,
        },
        (_payload) => {
          refetch();
        }
      )
      .subscribe((status) => {
        const s = status as string;
        if (s === "CLOSED" || s === "CHANNEL_ERROR") {
          setRealtimeStatus("reconnecting");
          if (!fallbackInterval) {
            fallbackInterval = setInterval(refetch, 30_000);
          }
        } else if (s === "SUBSCRIBED") {
          setRealtimeStatus("live");
          if (fallbackInterval) {
            clearInterval(fallbackInterval);
            fallbackInterval = null;
          }
        }
      });

    return () => {
      if (fallbackInterval) clearInterval(fallbackInterval);
      void supabase.removeChannel(channel);
    };
  }, [gameId, refetch]);

  return realtimeStatus;
}
