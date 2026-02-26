import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../App";

describe("routes", () => {
  it("renders login route", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
  });

  it("renders games route", () => {
    render(
      <MemoryRouter initialEntries={["/games"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByRole("heading", { name: /my games/i })).toBeInTheDocument();
  });

  it("renders game room route with gameId param", () => {
    render(
      <MemoryRouter initialEntries={["/g/abc-123"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByRole("heading", { name: /game abc-123/i })).toBeInTheDocument();
  });

  it("redirects unknown paths to /games", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByRole("heading", { name: /my games/i })).toBeInTheDocument();
  });
});

describe("Button component", () => {
  it("renders shadcn Button on login page", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByRole("button", { name: /send magic link/i })).toBeInTheDocument();
  });

  it("renders shadcn Button on games page", () => {
    render(
      <MemoryRouter initialEntries={["/games"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByRole("button", { name: /create game/i })).toBeInTheDocument();
  });
});
