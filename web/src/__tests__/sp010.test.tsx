/**
 * US-SP-010: Games list rework — My Games, Open Games, Play vs AI sections
 */
import { render, screen, waitFor, within } from "@testing-library/react";
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

    it("opens confirmation modal on click and creates game on Challenge", async () => {
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

      // Confirmation modal should appear with long description
      const modal = screen.getByTestId("ai-confirm-modal");
      expect(modal).toBeInTheDocument();
      expect(
        within(modal).getByText("Strahd von Zarovich"),
      ).toBeInTheDocument();
      expect(within(modal).getByText("Hard")).toBeInTheDocument();
      expect(
        within(modal).getByText(/peers into the fog of possibility/),
      ).toBeInTheDocument();

      // Click Challenge to confirm
      await user.click(within(modal).getByRole("button", { name: /challenge/i }));

      expect(createGameVsAi).toHaveBeenCalledWith("hard");
      expect(mockNavigate).toHaveBeenCalledWith("/g/ai-game-id");
    });

    it("closes confirmation modal on Cancel", async () => {
      vi.mocked(listGames).mockResolvedValue([]);

      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      await screen.findByText("Play vs AI");
      await user.click(screen.getByTestId("ai-easy"));

      // Modal opens
      expect(screen.getByTestId("ai-confirm-modal")).toBeInTheDocument();

      // Cancel
      await user.click(screen.getByRole("button", { name: /cancel/i }));

      // Modal gone after exit animation — no createGameVsAi call
      await waitFor(() => {
        expect(screen.queryByTestId("ai-confirm-modal")).not.toBeInTheDocument();
      });
      expect(createGameVsAi).not.toHaveBeenCalled();
    });

    it("closes confirmation modal on Escape key", async () => {
      vi.mocked(listGames).mockResolvedValue([]);

      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      await screen.findByText("Play vs AI");
      await user.click(screen.getByTestId("ai-medium"));

      expect(screen.getByTestId("ai-confirm-modal")).toBeInTheDocument();

      await user.keyboard("{Escape}");

      await waitFor(() => {
        expect(screen.queryByTestId("ai-confirm-modal")).not.toBeInTheDocument();
      });
      expect(createGameVsAi).not.toHaveBeenCalled();
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

  describe("My Games collapse toggle", () => {
    beforeEach(() => {
      localStorage.clear();
    });

    it("collapses and expands My Games list on toggle click", async () => {
      const aiGame = makeGame({
        game_id: "my-ai-game",
        status: "active",
        players: [
          makePlayer("user-123", "test@example.com"),
          {
            ...makePlayer("00000000-0000-0000-0000-000000000001", "ai@bot"),
            player_type: "ai" as const,
            ai_difficulty: "medium" as const,
          },
        ],
      });
      vi.mocked(listGames).mockResolvedValue([aiGame]);

      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      // Games list is visible by default
      await screen.findByText("Rahadin");
      const toggle = screen.getByRole("button", { name: /my games/i });
      expect(toggle).toHaveAttribute("aria-expanded", "true");

      // Collapse
      await user.click(toggle);
      expect(toggle).toHaveAttribute("aria-expanded", "false");

      // Expand again
      await user.click(toggle);
      expect(toggle).toHaveAttribute("aria-expanded", "true");
    });

    it("persists collapse state to localStorage", async () => {
      vi.mocked(listGames).mockResolvedValue([]);

      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      const toggle = await screen.findByRole("button", { name: /my games/i });
      await user.click(toggle);
      expect(localStorage.getItem("fatima:myGamesCollapsed")).toBe("true");

      await user.click(toggle);
      expect(localStorage.getItem("fatima:myGamesCollapsed")).toBe("false");
    });

    it("shows game count badge", async () => {
      vi.mocked(listGames).mockResolvedValue([
        makeGame({
          game_id: "game-1",
          status: "active",
          players: [makePlayer("user-123", "test@example.com"), makePlayer("p2")],
        }),
        makeGame({
          game_id: "game-2",
          status: "complete",
          players: [makePlayer("user-123", "test@example.com"), makePlayer("p3")],
          result: { winner: 0, is_draw: false },
        }),
      ]);

      render(
        <MemoryRouter>
          <Games />
        </MemoryRouter>,
      );

      await screen.findByText("(2)");
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
      expect(within(section).getByText("Challenge Another Player")).toBeInTheDocument();
    });
  });
});
