/**
 * US-SP-011: Frontend AI opponent display in game room
 */
import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { ActionPanel } from "@/routes/game-room/ActionPanel";
import { DraftingGameView } from "@/routes/game-room/DraftingGameView";
import { ActiveGameView } from "@/routes/game-room/ActiveGameView";
import {
  GameRoomWrapper,
  DEFAULT_GAME_ROOM_CTX,
  makeGame,
  makePlayer,
  EMPTY_BOARD,
} from "./helpers";
import type { AIDifficulty, PlayerState } from "@/lib/api";

// Mock motion/react
vi.mock("motion/react", () => {
  const React = require("react");
  return {
    motion: new Proxy(
      {},
      {
        get: (_target: unknown, prop: string) =>
          React.forwardRef((props: Record<string, unknown>, ref: unknown) =>
            React.createElement(prop, { ...props, ref }),
          ),
      },
    ),
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  };
});

// Mock sounds
vi.mock("@/lib/sounds", () => ({
  playPlus: vi.fn(),
  playElemental: vi.fn(),
  playTurnStart: vi.fn(),
  isMuted: () => false,
  toggleMute: vi.fn(),
  initAudio: vi.fn(),
}));

function makeAiPlayer(
  difficulty: AIDifficulty,
  overrides?: Partial<PlayerState>,
): PlayerState {
  return makePlayer("00000000-0000-0000-0000-000000000001", "ai@bot", {
    player_type: "ai",
    ai_difficulty: difficulty,
    archetype: "skulker",
    hand: ["c1", "c2"],
    ...overrides,
  });
}

describe("US-SP-011: AI opponent display in game room", () => {
  describe("ActionPanel: AI thinking indicator", () => {
    it.each([
      ["easy", "Ireena is thinking..."],
      ["medium", "Rahadin calculates..."],
      ["hard", "Strahd contemplates..."],
      ["nightmare", "The Dark Powers stir..."],
    ] as [AIDifficulty, string][])(
      "shows '%s' thinking text when opponent is AI (%s)",
      (difficulty, expectedText) => {
        render(
          <GameRoomWrapper>
            <ActionPanel
              isMyTurn={false}
              myPlayer={makePlayer("user-123")}
              opponentPlayer={makeAiPlayer(difficulty)}
            />
          </GameRoomWrapper>,
        );
        expect(screen.getByText(expectedText)).toBeInTheDocument();
      },
    );

    it("shows 'Opponent's turn' for human opponents", () => {
      render(
        <GameRoomWrapper>
          <ActionPanel
            isMyTurn={false}
            myPlayer={makePlayer("user-123")}
            opponentPlayer={makePlayer("opp-456")}
          />
        </GameRoomWrapper>,
      );
      expect(screen.getByText("Opponent's turn")).toBeInTheDocument();
    });

    it("shows 'Your turn' when it is the player's turn regardless of AI opponent", () => {
      render(
        <GameRoomWrapper>
          <ActionPanel
            isMyTurn={true}
            myPlayer={makePlayer("user-123", undefined, {
              archetype: "skulker",
            })}
            opponentPlayer={makeAiPlayer("hard")}
          />
        </GameRoomWrapper>,
      );
      expect(screen.getByText("Your turn")).toBeInTheDocument();
    });
  });

  describe("ActiveGameView: AI character name in score bar", () => {
    it("displays AI character name instead of 'Opp' in score bar", () => {
      const game = makeGame({
        status: "active",
        current_player_index: 0,
        board: EMPTY_BOARD,
        players: [
          makePlayer("user-123", "test@example.com", {
            archetype: "skulker",
            hand: ["c1", "c2", "c3", "c4", "c5"],
          }),
          makeAiPlayer("hard"),
        ],
      });

      render(
        <GameRoomWrapper>
          <ActiveGameView
            game={game}
            myIndex={0}
            myPlayer={game.players[0]}
            opponentPlayer={game.players[1]}
            myScore={5}
            opponentScore={2}
            cardDefs={new Map()}
            placedCells={new Set()}
            capturedCells={new Set()}
            onPlaceCard={() => {}}
            moveError={null}
          />
        </GameRoomWrapper>,
      );

      expect(
        screen.getByText(/Strahd von Zarovich/),
      ).toBeInTheDocument();
    });

    it("displays 'Opp' for human opponents in score bar", () => {
      const game = makeGame({
        status: "active",
        current_player_index: 0,
        board: EMPTY_BOARD,
        players: [
          makePlayer("user-123", "test@example.com", {
            archetype: "skulker",
            hand: ["c1", "c2", "c3", "c4", "c5"],
          }),
          makePlayer("opp-456", "opp@example.com", {
            archetype: "martial",
            hand: ["c6", "c7"],
          }),
        ],
      });

      render(
        <GameRoomWrapper>
          <ActiveGameView
            game={game}
            myIndex={0}
            myPlayer={game.players[0]}
            opponentPlayer={game.players[1]}
            myScore={5}
            opponentScore={2}
            cardDefs={new Map()}
            placedCells={new Set()}
            capturedCells={new Set()}
            onPlaceCard={() => {}}
            moveError={null}
          />
        </GameRoomWrapper>,
      );

      expect(screen.getByText(/Opp:/)).toBeInTheDocument();
    });
  });

  describe("DraftingGameView: AI game messaging", () => {
    it("shows 'Waiting for game to begin...' after draft in AI game", () => {
      const game = makeGame({
        status: "drafting",
        players: [
          makePlayer("user-123", "test@example.com", {
            deal: [],
            hand: ["c1", "c2", "c3", "c4", "c5"],
          }),
          makeAiPlayer("easy"),
        ],
      });

      render(
        <DraftingGameView
          game={game}
          myIndex={0}
          cardDefs={new Map()}
          onSubmitDraft={async () => {}}
          leaving={false}
          onLeave={() => {}}
          isAiGame={true}
        />,
      );

      expect(
        screen.getByText("Waiting for game to begin..."),
      ).toBeInTheDocument();
    });

    it("shows 'Waiting for opponent to draft...' in human game", () => {
      const game = makeGame({
        status: "drafting",
        players: [
          makePlayer("user-123", "test@example.com", {
            deal: [],
            hand: ["c1", "c2", "c3", "c4", "c5"],
          }),
          makePlayer("opp-456"),
        ],
      });

      render(
        <DraftingGameView
          game={game}
          myIndex={0}
          cardDefs={new Map()}
          onSubmitDraft={async () => {}}
          leaving={false}
          onLeave={() => {}}
          isAiGame={false}
        />,
      );

      expect(
        screen.getByText("Waiting for opponent to draft..."),
      ).toBeInTheDocument();
    });
  });
});
