import { supabase } from "@/lib/supabase";

export interface PlayerState {
  player_id: string;
  archetype: "martial" | "skulker" | "caster" | "devout" | "presence" | null;
  hand: string[];
  archetype_used: boolean;
}

export interface GameState {
  game_id: string;
  status: "waiting" | "active" | "complete";
  players: PlayerState[];
  state_version: number;
  round_number: number;
}

async function authHeaders(): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("Not authenticated");
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export async function listGames(): Promise<GameState[]> {
  const headers = await authHeaders();
  const res = await fetch("/api/games", { headers });
  if (!res.ok) throw new Error(`Failed to list games: ${res.status}`);
  return res.json() as Promise<GameState[]>;
}

export async function createGame(): Promise<GameState> {
  const headers = await authHeaders();
  const res = await fetch("/api/games", {
    method: "POST",
    headers,
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`Failed to create game: ${res.status}`);
  return res.json() as Promise<GameState>;
}

export async function getGame(gameId: string): Promise<GameState> {
  const headers = await authHeaders();
  const res = await fetch(`/api/games/${gameId}`, { headers });
  if (!res.ok) throw new Error(`Failed to load game: ${res.status}`);
  return res.json() as Promise<GameState>;
}

export async function joinGame(gameId: string): Promise<GameState> {
  const headers = await authHeaders();
  const res = await fetch(`/api/games/${gameId}/join`, {
    method: "POST",
    headers,
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`Failed to join game: ${res.status}`);
  return res.json() as Promise<GameState>;
}
