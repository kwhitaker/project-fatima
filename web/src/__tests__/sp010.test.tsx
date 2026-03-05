/**
 * US-SP-010: Games list rework — My Games, Open Games, Play vs AI sections
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Games from "../routes/Games";
import { makeGame, makePlayer } from "./helpers";
import type { GameState } from "@/lib/api";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "user-123", email: "test@example.com" },
    signOut: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  listGames: vi.fn(),
  createGame: vi.fn(),
  createGameVsAi: vi.fn(),
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
    },
  },
}));

const { listGames, createGameVsAi } = await import("@/lib/api");

function makeAiPlayer(difficulty: "easy" | "medium" | "hard" | "nightmare") {
  return {
    ...makePlayer("00000000-0000-0000-0000-000000000001", "ai@bot"),
    player_type: "ai" as const,
    ai_difficulty: difficulty,
  };
}

describe("US-SP-010: Games list rework", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Play vs AI section", () => {
    it("renders four difficulty options with character names and flavor text", async () => {
      vi.mocked(listGames).mockResolvedValue([]);

      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      await screen.findByText("Play vs AI");

      expect(screen.getByText("Ireena Kolyana")).toBeInTheDocument();
      expect(screen.getByText("Rahadin")).toBeInTheDocument();
      expect(screen.getByText("Strahd von Zarovich")).toBeInTheDocument();
      expect(screen.getByText("The Dark Powers")).toBeInTheDocument();

      expect(
        screen.getByText("A sheltered noble still learning the game."),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          "Strahd's chamberlain plays with cold precision.",
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByText("The lord of Barovia does not lose."),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          "Ancient forces that see through every stratagem.",
        ),
      ).toBeInTheDocument();

      // Difficulty labels
      expect(screen.getByTestId("ai-easy")).toBeInTheDocument();
      expect(screen.getByTestId("ai-medium")).toBeInTheDocument();
      expect(screen.getByTestId("ai-hard")).toBeInTheDocument();
      expect(screen.getByTestId("ai-nightmare")).toBeInTheDocument();
    });

    it("calls createGameVsAi and navigates on click", async () => {
      vi.mocked(listGames).mockResolvedValue([]);
      const aiGame = makeGame({
        game_id: "ai-game-id",
        players: [makePlayer("user-123"), makeAiPlayer("hard")],
      });
      vi.mocked(createGameVsAi).mockResolvedValue(aiGame);

      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      await screen.findByText("Play vs AI");
      await user.click(screen.getByTestId("ai-hard"));

      expect(createGameVsAi).toHaveBeenCalledWith("hard");
      expect(mockNavigate).toHaveBeenCalledWith("/g/ai-game-id");
    });
  });

  describe("My Games section", () => {
    it("shows AI opponent character name and difficulty badge", async () => {
      const aiGame = makeGame({
        game_id: "my-ai-game",
        status: "active",
        players: [
          makePlayer("user-123", "test@example.com"),
          makeAiPlayer("medium"),
        ],
      });
      vi.mocked(listGames).mockResolvedValue([aiGame]);

      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      // Wait for My Games section to populate — "Rahadin" appears twice
      // (Play vs AI card + My Games row), so find the one inside My Games
      const myGamesHeading = await screen.findByText("My Games");
      const myGamesSection = myGamesHeading.closest("section")!;
      expect(within(myGamesSection).getByText("Rahadin")).toBeInTheDocument();
      expect(within(myGamesSection).getByText("Medium")).toBeInTheDocument();
    });

    it("shows human opponent email for multiplayer games", async () => {
      const humanGame = makeGame({
        game_id: "my-human-game",
        status: "active",
        players: [
          makePlayer("user-123", "test@example.com"),
          makePlayer("user-456", "opponent@example.com"),
        ],
      });
      vi.mocked(listGames).mockResolvedValue([humanGame]);

      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      await screen.findByText("opponent@example.com");
    });
  });

  describe("Open Games section", () => {
    it("shows joinable lobbies from other players", async () => {
      const openGame = makeGame({
        game_id: "open-game-1",
        status: "waiting",
        players: [makePlayer("other-user", "host@example.com")],
        created_at: "2026-03-05T10:00:00+00:00",
      });
      vi.mocked(listGames).mockResolvedValue([openGame]);

      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      await screen.findByText("host@example.com");
      expect(screen.getByText("Join")).toBeInTheDocument();
    });

    it("does not show own waiting games in Open Games", async () => {
      const myWaitingGame = makeGame({
        game_id: "my-waiting-game",
        status: "waiting",
        players: [makePlayer("user-123", "test@example.com")],
      });
      vi.mocked(listGames).mockResolvedValue([myWaitingGame]);

      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      // Should appear in My Games, not in Open Games
      await screen.findByText("My Games");
      expect(screen.getByText("No open games available.")).toBeInTheDocument();
    });

    it("has Create Game button in Open Games section", async () => {
      vi.mocked(listGames).mockResolvedValue([]);

      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      // The Create Game button should be inside Open Games section
      const openGamesHeading = await screen.findByText("Open Games");
      const section = openGamesHeading.closest("section")!;
      expect(within(section).getByText("Create Game")).toBeInTheDocument();
    });
  });
});
