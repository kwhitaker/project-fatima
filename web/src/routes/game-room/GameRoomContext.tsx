import { createContext, useContext, type ReactNode } from "react";
import type { Archetype, CardDefinition } from "@/lib/api";

interface GameRoomContextValue {
  // Card selection
  selectedCard: string | null;
  onSelectCard: (cardKey: string | null) => void;
  selectedCardElement: string | null;
  movePending: boolean;

  // Power system
  usePower: boolean;
  onUsePowerChange: (next: boolean) => void;
  powerSide: string | null;
  onPowerSideToggle: (side: string) => void;
  intimidatePendingCell: number | null;
  onCancelIntimidatePending: () => void;

  // Archetype modal
  archetypePending: boolean;
  archetypeError: string | null;
  onSelectArchetype: (archetype: Archetype) => void | Promise<void>;

  // Card preview
  onPreviewCard: (cardKey: string, def?: CardDefinition) => void;

  // Leave / forfeit
  leaving: boolean;
  onOpenLeaveConfirm: () => void;
  showLeaveConfirm: boolean;
  onCloseLeaveConfirm: () => void;
  onConfirmLeave: () => void;

  // Rules
  onShowRules: () => void;
}

const GameRoomCtx = createContext<GameRoomContextValue | null>(null);

export function useGameRoom(): GameRoomContextValue {
  const ctx = useContext(GameRoomCtx);
  if (!ctx) throw new Error("useGameRoom must be used within a GameRoomProvider");
  return ctx;
}

export function GameRoomProvider({
  value,
  children,
}: {
  value: GameRoomContextValue;
  children: ReactNode;
}) {
  return <GameRoomCtx.Provider value={value}>{children}</GameRoomCtx.Provider>;
}
