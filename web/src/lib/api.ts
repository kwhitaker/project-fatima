import { supabase } from "@/lib/supabase";

export interface PlayerState {
  player_id: string;
  archetype: "martial" | "skulker" | "caster" | "devout" | "presence" | null;
  hand: string[];
  archetype_used: boolean;
}

export interface BoardCell {
  card_key: string;
  owner: 0 | 1;
}

export interface GameResult {
  winner: 0 | 1 | null;
  is_draw: boolean;
}

export interface GameState {
  game_id: string;
  status: "waiting" | "active" | "complete";
  players: PlayerState[];
  board: (BoardCell | null)[];
  current_player_index: number;
  starting_player_index: number;
  state_version: number;
  round_number: number;
  result: GameResult | null;
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

export async function placeCard(
  gameId: string,
  cardKey: string,
  cellIndex: number,
  stateVersion: number,
  idempotencyKey: string
): Promise<GameState> {
  const headers = await authHeaders();
  const res = await fetch(`/api/games/${gameId}/moves`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      card_key: cardKey,
      cell_index: cellIndex,
      state_version: stateVersion,
      idempotency_key: idempotencyKey,
    }),
  });
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body.detail;
    } catch {
      // ignore parse error
    }
    const err = new Error(detail ?? `Move failed: ${res.status}`);
    Object.assign(err, { status: res.status });
    throw err;
  }
  return res.json() as Promise<GameState>;
}

export type Archetype = "martial" | "skulker" | "caster" | "devout" | "presence";

export async function selectArchetype(
  gameId: string,
  archetype: Archetype
): Promise<GameState> {
  const headers = await authHeaders();
  const res = await fetch(`/api/games/${gameId}/archetype`, {
    method: "POST",
    headers,
    body: JSON.stringify({ archetype }),
  });
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body.detail;
    } catch {
      // ignore parse error
    }
    const err = new Error(detail ?? `Failed to select archetype: ${res.status}`);
    Object.assign(err, { status: res.status });
    throw err;
  }
  return res.json() as Promise<GameState>;
}

export async function leaveGame(
  gameId: string,
  stateVersion: number
): Promise<GameState | null> {
  const headers = await authHeaders();
  const res = await fetch(`/api/games/${gameId}/leave`, {
    method: "POST",
    headers,
    body: JSON.stringify({ state_version: stateVersion }),
  });
  if (res.status === 204) return null;
  if (!res.ok) throw new Error(`Failed to leave game: ${res.status}`);
  return res.json() as Promise<GameState>;
}
