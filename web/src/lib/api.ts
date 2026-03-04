import { supabase } from "@/lib/supabase";
import type { components } from "./api-types.generated";

// Re-export backend types from auto-generated schema
export type CardSides = components["schemas"]["CardSides"];
export type CardDefinition = components["schemas"]["CardDefinition"];
export type PlayerState = components["schemas"]["PlayerState"];
export type BoardCell = components["schemas"]["BoardCell"];
export type GameResult = components["schemas"]["GameResult"];
export type LastMoveInfo = components["schemas"]["LastMoveInfo"];
export type GameState = components["schemas"]["GameState"];
export type Archetype = components["schemas"]["Archetype"];

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
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body.detail;
    } catch {
      // ignore parse error
    }
    const err = new Error(detail ?? `Failed to create game: ${res.status}`);
    Object.assign(err, { status: res.status });
    throw err;
  }
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
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body.detail;
    } catch {
      // ignore parse error
    }
    const err = new Error(detail ?? `Failed to join game: ${res.status}`);
    Object.assign(err, { status: res.status });
    throw err;
  }
  return res.json() as Promise<GameState>;
}

export async function placeCard(
  gameId: string,
  cardKey: string,
  cellIndex: number,
  stateVersion: number,
  idempotencyKey: string,
  powerOptions?: {
    useArchetype?: boolean;
    skulkerBoostSide?: string;
    intimidateTargetCell?: number;
    martialRotationDirection?: "cw" | "ccw";
  }
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
      ...(powerOptions?.useArchetype && { use_archetype: true }),
      ...(powerOptions?.skulkerBoostSide && { skulker_boost_side: powerOptions.skulkerBoostSide }),
      ...(powerOptions?.intimidateTargetCell != null && { intimidate_target_cell: powerOptions.intimidateTargetCell }),
      ...(powerOptions?.martialRotationDirection && { martial_rotation_direction: powerOptions.martialRotationDirection }),
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

// ---------------------------------------------------------------------------
// Card definitions (fetch + module-level cache)
// ---------------------------------------------------------------------------

let _cardCache: Map<string, CardDefinition> | null = null;

export async function listCards(): Promise<CardDefinition[]> {
  const headers = await authHeaders();
  const res = await fetch("/api/cards", { headers });
  if (!res.ok) throw new Error(`Failed to list cards: ${res.status}`);
  return res.json() as Promise<CardDefinition[]>;
}

/** Fetch card definitions once and cache them for the session. */
export async function getCardDefinitions(): Promise<Map<string, CardDefinition>> {
  if (_cardCache) return _cardCache;
  const cards = await listCards();
  _cardCache = new Map(cards.map((c) => [c.card_key, c]));
  return _cardCache;
}
