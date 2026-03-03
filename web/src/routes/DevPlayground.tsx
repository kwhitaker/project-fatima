import { useCallback, useState } from "react";
import type {
  BoardCell,
  CardDefinition,
  GameState,
  LastMoveInfo,
} from "@/lib/api";
import { BoardGrid } from "@/routes/game-room/BoardGrid";
import { VictoryOverlay } from "@/routes/game-room/VictoryOverlay";
import { DefeatOverlay } from "@/routes/game-room/DefeatOverlay";

// ---------------------------------------------------------------------------
// Mock card definitions
// ---------------------------------------------------------------------------

const MOCK_CARDS: CardDefinition[] = [
  { card_key: "c-wolf", character_key: "werewolf-alpha", name: "Werewolf Alpha", version: "1.0", tier: 3, sides: { n: 8, e: 6, s: 3, w: 7 }, element: "nature" },
  { card_key: "c-strahd", character_key: "strahd", name: "Count Strahd", version: "1.0", tier: 3, sides: { n: 9, e: 8, s: 7, w: 3 }, element: "blood" },
  { card_key: "c-zombie", character_key: "zombie-guard", name: "Zombie Guard", version: "1.0", tier: 1, sides: { n: 2, e: 3, s: 5, w: 4 }, element: "shadow" },
  { card_key: "c-cleric", character_key: "cleric-dawn", name: "Cleric of Dawn", version: "1.0", tier: 2, sides: { n: 6, e: 3, s: 4, w: 7 }, element: "holy" },
  { card_key: "c-raven", character_key: "wereraven", name: "Wereraven", version: "1.0", tier: 1, sides: { n: 4, e: 5, s: 3, w: 2 }, element: "nature" },
  { card_key: "c-mage", character_key: "amber-mage", name: "Amber Mage", version: "1.0", tier: 2, sides: { n: 5, e: 7, s: 3, w: 6 }, element: "arcane" },
  { card_key: "c-bat", character_key: "vampire-spawn", name: "Vampire Spawn", version: "1.0", tier: 1, sides: { n: 3, e: 4, s: 6, w: 2 }, element: "blood" },
  { card_key: "c-ghost", character_key: "ghost-knight", name: "Ghost Knight", version: "1.0", tier: 2, sides: { n: 7, e: 3, s: 5, w: 6 }, element: "shadow" },
  { card_key: "c-druid", character_key: "forest-druid", name: "Forest Druid", version: "1.0", tier: 1, sides: { n: 3, e: 5, s: 4, w: 3 }, element: "nature" },
];

const CARD_DEFS = new Map<string, CardDefinition>(
  MOCK_CARDS.map((c) => [c.card_key, c]),
);

const BOARD_ELEMENTS = [
  "blood", "arcane", "holy",
  "shadow", "nature", "blood",
  "arcane", "shadow", "holy",
];

// ---------------------------------------------------------------------------
// Scenario helpers
// ---------------------------------------------------------------------------

function emptyBoard(): (BoardCell | null)[] {
  return Array(9).fill(null);
}

function filledBoard(myIndex: 0 | 1): (BoardCell | null)[] {
  const keys = MOCK_CARDS.map((c) => c.card_key);
  return keys.map((card_key, i) => ({
    card_key,
    owner: (i % 2 === 0 ? myIndex : ((1 - myIndex) as 0 | 1)) as 0 | 1,
  }));
}

function makeGame(overrides: Partial<GameState> = {}): GameState {
  return {
    game_id: "dev-playground",
    status: "active",
    players: [
      { player_id: "me", archetype: "skulker", hand: ["c-wolf", "c-cleric"], archetype_used: false },
      { player_id: "opp", archetype: "caster", hand: ["c-zombie", "c-bat"], archetype_used: false },
    ],
    board: emptyBoard(),
    current_player_index: 0,
    starting_player_index: 0,
    state_version: 1,
    round_number: 1,
    result: null,
    board_elements: BOARD_ELEMENTS,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Scenario definitions
// ---------------------------------------------------------------------------

interface Scenario {
  label: string;
  description: string;
}

const SCENARIOS: Scenario[] = [
  { label: "Card placement", description: "Card placed at center with slam animation" },
  { label: "Single capture", description: "One card captured with flip animation" },
  { label: "Combo chain (4)", description: "4-card combo chain with escalating brightness" },
  { label: "Plus trigger", description: "Plus rule triggered with cyan callout" },
  { label: "Elemental trigger", description: "Elemental match with gold callout" },
  { label: "Plus + Elemental", description: "Both Plus and Elemental on same move" },
  { label: "Fog (Mists)", description: "Fog mists effect on placement" },
  { label: "Omen (Mists)", description: "Omen mists effect on placement" },
  { label: "Victory screen", description: "Victory overlay with bats and confetti" },
  { label: "Defeat screen", description: "Defeat overlay with fog and vignette" },
  { label: "Early finish", description: "Game ends with clinch (empty cells marked \u2715)" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DevPlayground() {
  const [activeScenario, setActiveScenario] = useState<number | null>(null);
  const [placedCells, setPlacedCells] = useState<Set<number>>(new Set());
  const [capturedCells, setCapturedCells] = useState<Set<number>>(new Set());
  const [showVictory, setShowVictory] = useState(false);
  const [showDefeat, setShowDefeat] = useState(false);
  const [game, setGame] = useState<GameState>(makeGame());
  const [lastMove, setLastMove] = useState<LastMoveInfo | null>(null);
  const [victoryCells, setVictoryCells] = useState<number[]>([]);
  const [mistsEffect, setMistsEffect] = useState<"fog" | "omen" | "none" | null>(null);
  const [earlyFinish, setEarlyFinish] = useState(false);

  const reset = useCallback(() => {
    setPlacedCells(new Set());
    setCapturedCells(new Set());
    setShowVictory(false);
    setShowDefeat(false);
    setLastMove(null);
    setVictoryCells([]);
    setMistsEffect(null);
    setEarlyFinish(false);
    setGame(makeGame());
    setActiveScenario(null);
  }, []);

  const runScenario = useCallback(
    (index: number) => {
      reset();
      // Use setTimeout so state clears before re-applying
      setTimeout(() => {
        setActiveScenario(index);

        switch (index) {
          case 0: {
            // Card placement
            const board = emptyBoard();
            board[4] = { card_key: "c-strahd", owner: 0 };
            setGame(makeGame({ board }));
            setPlacedCells(new Set([4]));
            setLastMove({ player_index: 0, card_key: "c-strahd", cell_index: 4, mists_roll: 3, mists_effect: "none" });
            break;
          }
          case 1: {
            // Single capture
            const board = emptyBoard();
            board[4] = { card_key: "c-strahd", owner: 0 };
            board[5] = { card_key: "c-zombie", owner: 0 }; // just captured
            setGame(makeGame({ board }));
            setPlacedCells(new Set([4]));
            setCapturedCells(new Set([5]));
            setLastMove({ player_index: 0, card_key: "c-strahd", cell_index: 4, mists_roll: 4, mists_effect: "none" });
            break;
          }
          case 2: {
            // Combo chain (4 captures)
            const board: (BoardCell | null)[] = emptyBoard();
            board[4] = { card_key: "c-strahd", owner: 0 };
            board[1] = { card_key: "c-zombie", owner: 0 };
            board[3] = { card_key: "c-raven", owner: 0 };
            board[5] = { card_key: "c-bat", owner: 0 };
            board[7] = { card_key: "c-druid", owner: 0 };
            setGame(makeGame({ board }));
            setPlacedCells(new Set([4]));
            setCapturedCells(new Set([1, 3, 5, 7]));
            setLastMove({ player_index: 0, card_key: "c-strahd", cell_index: 4, mists_roll: 5, mists_effect: "none" });
            break;
          }
          case 3: {
            // Plus trigger
            const board: (BoardCell | null)[] = emptyBoard();
            board[4] = { card_key: "c-cleric", owner: 0 };
            board[1] = { card_key: "c-zombie", owner: 0 };
            board[5] = { card_key: "c-bat", owner: 0 };
            setGame(makeGame({ board }));
            setPlacedCells(new Set([4]));
            setCapturedCells(new Set([1, 5]));
            setLastMove({ player_index: 0, card_key: "c-cleric", cell_index: 4, mists_roll: 3, mists_effect: "none", plus_triggered: true });
            break;
          }
          case 4: {
            // Elemental trigger (card element matches cell element)
            const board: (BoardCell | null)[] = emptyBoard();
            board[0] = { card_key: "c-bat", owner: 0 }; // blood card on blood cell
            board[1] = { card_key: "c-zombie", owner: 0 };
            setGame(makeGame({ board, board_elements: BOARD_ELEMENTS }));
            setPlacedCells(new Set([0]));
            setCapturedCells(new Set([1]));
            setLastMove({ player_index: 0, card_key: "c-bat", cell_index: 0, mists_roll: 4, mists_effect: "none", elemental_triggered: true });
            break;
          }
          case 5: {
            // Plus + Elemental combined
            const board: (BoardCell | null)[] = emptyBoard();
            board[0] = { card_key: "c-bat", owner: 0 }; // blood on blood
            board[1] = { card_key: "c-zombie", owner: 0 };
            board[3] = { card_key: "c-raven", owner: 0 };
            setGame(makeGame({ board, board_elements: BOARD_ELEMENTS }));
            setPlacedCells(new Set([0]));
            setCapturedCells(new Set([1, 3]));
            setLastMove({ player_index: 0, card_key: "c-bat", cell_index: 0, mists_roll: 2, mists_effect: "none", plus_triggered: true, elemental_triggered: true });
            break;
          }
          case 6: {
            // Fog mists
            const board = emptyBoard();
            board[4] = { card_key: "c-wolf", owner: 0 };
            setGame(makeGame({ board }));
            setPlacedCells(new Set([4]));
            setMistsEffect("fog");
            setLastMove({ player_index: 0, card_key: "c-wolf", cell_index: 4, mists_roll: 1, mists_effect: "fog" });
            break;
          }
          case 7: {
            // Omen mists
            const board = emptyBoard();
            board[4] = { card_key: "c-wolf", owner: 0 };
            setGame(makeGame({ board }));
            setPlacedCells(new Set([4]));
            setMistsEffect("omen");
            setLastMove({ player_index: 0, card_key: "c-wolf", cell_index: 4, mists_roll: 6, mists_effect: "omen" });
            break;
          }
          case 8: {
            // Victory
            const board = filledBoard(0);
            setGame(makeGame({
              status: "complete",
              board,
              result: { winner: 0, is_draw: false, completion_reason: "board_full" },
            }));
            setVictoryCells([0, 2, 4, 6, 8]);
            setShowVictory(true);
            break;
          }
          case 9: {
            // Defeat
            const board = filledBoard(0);
            setGame(makeGame({
              status: "complete",
              board,
              result: { winner: 1, is_draw: false, completion_reason: "board_full" },
            }));
            setShowDefeat(true);
            break;
          }
          case 10: {
            // Early finish
            const board: (BoardCell | null)[] = emptyBoard();
            board[0] = { card_key: "c-strahd", owner: 0 };
            board[1] = { card_key: "c-wolf", owner: 0 };
            board[2] = { card_key: "c-cleric", owner: 0 };
            board[3] = { card_key: "c-mage", owner: 0 };
            board[4] = { card_key: "c-ghost", owner: 0 };
            board[6] = { card_key: "c-zombie", owner: 1 };
            // cells 5, 7, 8 empty — clinch
            setGame(makeGame({
              status: "complete",
              board,
              result: { winner: 0, is_draw: false, early_finish: true },
            }));
            setVictoryCells([0, 1, 2, 3, 4]);
            setEarlyFinish(true);
            break;
          }
        }
      }, 50);
    },
    [reset],
  );

  return (
    <div className="min-h-screen bg-background text-foreground p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-heading text-primary">Dev Playground</h1>
          <p className="text-sm font-body text-muted-foreground mt-1">
            Trigger animations and effects without a real game
          </p>
        </div>

        {/* Scenario buttons */}
        <div className="flex flex-wrap gap-2" data-testid="scenario-buttons">
          {SCENARIOS.map((s, i) => (
            <button
              key={i}
              onClick={() => runScenario(i)}
              className={`px-3 py-2 border-2 font-body text-sm transition-colors ${
                activeScenario === i
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card hover:border-accent"
              }`}
              title={s.description}
            >
              {s.label}
            </button>
          ))}
          <button
            onClick={reset}
            className="px-3 py-2 border-2 border-border bg-card font-body text-sm hover:border-destructive hover:text-destructive transition-colors"
          >
            Reset
          </button>
        </div>

        {/* Active scenario label */}
        {activeScenario !== null && (
          <p className="text-sm font-body text-accent">
            Active: {SCENARIOS[activeScenario].label} &mdash;{" "}
            {SCENARIOS[activeScenario].description}
          </p>
        )}

        {/* Overlays */}
        {showVictory && (
          <VictoryOverlay onDismiss={() => setShowVictory(false)} />
        )}
        {showDefeat && (
          <DefeatOverlay onDismiss={() => setShowDefeat(false)} />
        )}

        {/* Board */}
        <div className="flex justify-center">
          <div className="w-full max-w-md">
            <BoardGrid
              board={game.board}
              myIndex={0}
              cardDefs={CARD_DEFS}
              placedCells={placedCells}
              capturedCells={capturedCells}
              lastMoveCellIndex={lastMove?.cell_index ?? null}
              boardElements={game.board_elements}
              mistsEffect={mistsEffect}
              victoryCells={victoryCells}
              earlyFinish={earlyFinish}
              onCellInspect={() => {}}
            />
          </div>
        </div>

        {/* Last move info */}
        {lastMove && (
          <div className="p-3 border-2 border-border bg-card font-body text-sm space-y-1" data-testid="last-move-info">
            <p>
              <span className="text-muted-foreground">Card:</span>{" "}
              {CARD_DEFS.get(lastMove.card_key)?.name ?? lastMove.card_key}
              {" → cell "}
              {lastMove.cell_index}
            </p>
            <p>
              <span className="text-muted-foreground">Mists:</span>{" "}
              {lastMove.mists_effect} (roll {lastMove.mists_roll})
            </p>
            {lastMove.plus_triggered && (
              <p className="text-cyan-400 font-heading text-xs">Plus!</p>
            )}
            {lastMove.elemental_triggered && (
              <p className="text-yellow-400 font-heading text-xs">Elemental!</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
