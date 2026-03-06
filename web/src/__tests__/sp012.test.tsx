/**
 * US-SP-012: Frontend AI commentary display
 */
import { render, screen, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { AiCommentBubble } from "@/routes/game-room/AiCommentBubble";
import { ActiveGameView } from "@/routes/game-room/ActiveGameView";
import {
  GameRoomWrapper,
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
  playMartial: vi.fn(),
  playSkulker: vi.fn(),
  playCaster: vi.fn(),
  playDevout: vi.fn(),
  playIntimidate: vi.fn(),
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

describe("US-SP-012: AI commentary display", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  describe("AiCommentBubble", () => {
    it("renders speech bubble when comment is provided", () => {
      render(
        <AiCommentBubble comment="You amuse me, mortal." difficulty="hard" />,
      );
      expect(
        screen.getByText(/You amuse me, mortal\./),
      ).toBeInTheDocument();
      expect(screen.getByLabelText("ai comment")).toBeInTheDocument();
    });

    it("does not render when comment is null", () => {
      render(<AiCommentBubble comment={null} difficulty="easy" />);
      expect(screen.queryByLabelText("ai comment")).not.toBeInTheDocument();
    });

    it("fades after timeout", () => {
      render(
        <AiCommentBubble comment="Predictable." difficulty="medium" />,
      );
      expect(screen.getByLabelText("ai comment")).toBeInTheDocument();

      act(() => {
        vi.advanceTimersByTime(4000);
      });

      expect(screen.queryByLabelText("ai comment")).not.toBeInTheDocument();
    });

    it("replaces previous comment immediately when new one arrives", () => {
      const { rerender } = render(
        <AiCommentBubble comment="First comment" difficulty="easy" />,
      );
      expect(screen.getByText(/First comment/)).toBeInTheDocument();

      rerender(
        <AiCommentBubble comment="Second comment" difficulty="easy" />,
      );
      expect(screen.queryByText(/First comment/)).not.toBeInTheDocument();
      expect(screen.getByText(/Second comment/)).toBeInTheDocument();
    });

    it.each([
      ["easy", "bg-amber-50"],
      ["medium", "bg-slate-100"],
      ["hard", "bg-red-950/80"],
      ["nightmare", "bg-violet-950/80"],
    ] as [AIDifficulty, string][])(
      "applies %s difficulty styling",
      (difficulty, expectedClass) => {
        render(
          <AiCommentBubble comment="Test" difficulty={difficulty} />,
        );
        const bubble = screen.getByLabelText("ai comment");
        expect(bubble.className).toContain(expectedClass);
      },
    );

    it("has pointer-events-none to not block board interaction", () => {
      render(
        <AiCommentBubble comment="Test" difficulty="easy" />,
      );
      const bubble = screen.getByLabelText("ai comment");
      expect(bubble.className).toContain("pointer-events-none");
    });
  });

  describe("ActiveGameView integration", () => {
    it("shows AI comment bubble when last_move has ai_comment", () => {
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
        last_move: {
          player_index: 1,
          card_key: "c1",
          cell_index: 0,
          captures: [],
          mists_roll: 3,
          mists_effect: "none",
          plus_triggered: false,
          elemental_triggered: false,
          ai_comment: "Your struggle is... entertaining.",
        },
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
        screen.getByText(/Your struggle is\.\.\. entertaining\./),
      ).toBeInTheDocument();
    });

    it("does not show AI comment bubble when ai_comment is null", () => {
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
        last_move: {
          player_index: 1,
          card_key: "c1",
          cell_index: 0,
          captures: [],
          mists_roll: 3,
          mists_effect: "none",
          plus_triggered: false,
          elemental_triggered: false,
          ai_comment: null,
        },
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

      expect(screen.queryByLabelText("ai comment")).not.toBeInTheDocument();
    });

    it("does not show AI comment bubble in human-vs-human games", () => {
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
        last_move: {
          player_index: 1,
          card_key: "c1",
          cell_index: 0,
          captures: [],
          mists_roll: 3,
          mists_effect: "none",
          plus_triggered: false,
          elemental_triggered: false,
        },
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

      expect(screen.queryByLabelText("ai comment")).not.toBeInTheDocument();
    });
  });
});
