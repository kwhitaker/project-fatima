import { useEffect, useRef, useState } from "react";

import type { BoardCell } from "@/lib/api";

export function useBoardDiffAnimations(board: (BoardCell | null)[] | null) {
  const prevBoardRef = useRef<(BoardCell | null)[] | null>(null);
  const [placedCells, setPlacedCells] = useState<Set<number>>(new Set());
  const [capturedCells, setCapturedCells] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!board) return;
    const prev = prevBoardRef.current;
    prevBoardRef.current = board;
    if (!prev) return;

    const placed = new Set<number>();
    const captured = new Set<number>();

    board.forEach((cell, i) => {
      const prevCell = prev[i];
      if (prevCell === null && cell !== null) {
        placed.add(i);
      } else if (prevCell !== null && cell !== null && prevCell.owner !== cell.owner) {
        captured.add(i);
      }
    });

    setPlacedCells(placed);
    setCapturedCells(captured);
  }, [board]);

  return { placedCells, capturedCells };
}
