/**
 * US-SP-019: Frontend Nightmare difficulty limited-availability notice
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Games from "../routes/Games";

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

describe("US-SP-019: Nightmare limited-availability notice", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows availability text only on nightmare card", async () => {
    vi.mocked(listGames).mockResolvedValue([]);

    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>,
    );

    await screen.findByText("Play vs AI");

    // Availability text should appear on nightmare card
    expect(
      screen.getByText("Few may commune with The Dark Powers at once."),
    ).toBeInTheDocument();

    // Should not appear on other difficulty cards
    const easyCard = screen.getByTestId("ai-easy");
    expect(easyCard.textContent).not.toContain("Few may commune");
  });

  it("has tooltip text on nightmare card", async () => {
    vi.mocked(listGames).mockResolvedValue([]);

    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>,
    );

    await screen.findByText("Play vs AI");

    const nightmareCard = screen.getByTestId("ai-nightmare");
    expect(nightmareCard.getAttribute("title")).toBe(
      "Only 2 players can face Nightmare difficulty at a time. Try again shortly if unavailable.",
    );

    // Other cards should not have this tooltip
    const easyCard = screen.getByTestId("ai-easy");
    expect(easyCard.getAttribute("title")).toBeNull();
  });

  it("shows themed error when 503 returned for nightmare", async () => {
    vi.mocked(listGames).mockResolvedValue([]);
    vi.mocked(createGameVsAi).mockRejectedValue(
      Object.assign(new Error("Service unavailable"), { status: 503 }),
    );

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Games />
      </MemoryRouter>,
    );

    await screen.findByText("Play vs AI");
    await user.click(screen.getByTestId("ai-nightmare"));

    // Confirmation modal opens — click Challenge (exact match, not "Challenge Another Player")
    const modal = screen.getByTestId("ai-confirm-modal");
    await user.click(within(modal).getByRole("button", { name: /^challenge$/i }));

    expect(
      await screen.findByText(
        "The Dark Powers are occupied with another mortal.",
      ),
    ).toBeInTheDocument();

    // Should not navigate
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
