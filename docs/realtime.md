# Realtime Event Subscription Contract

This document describes how clients subscribe to game updates via Supabase Realtime.

## Overview

The server appends a row to the `game_events` table for every game action (move, join,
archetype selection, forfeit, etc.). Clients subscribe to inserts on that table filtered
by `game_id` and refetch the current snapshot on each event.

## Subscribing

Use the Supabase JavaScript (or compatible) client. Authenticate with the player's JWT
before subscribing — the Realtime channel inherits the same RLS context.

```js
const channel = supabase
  .channel(`game:${gameId}`)
  .on(
    "postgres_changes",
    {
      event:  "INSERT",
      schema: "public",
      table:  "game_events",
      filter: `game_id=eq.${gameId}`,
    },
    async (_payload) => {
      // MVP behaviour: refetch the full snapshot
      const { data } = await supabase
        .from("games")
        .select("current_state")
        .eq("id", gameId)
        .single();
      // update local UI state with data.current_state …
    }
  )
  .subscribe();
```

Unsubscribe when the component unmounts or the game reaches a terminal state:

```js
supabase.removeChannel(channel);
```

## Event Payload Shape

Each row inserted into `game_events` has the following columns:

| Column       | Type        | Description                                            |
|--------------|-------------|--------------------------------------------------------|
| `id`         | `uuid`      | Unique event identifier.                               |
| `game_id`    | `uuid`      | Foreign key to `games.id`.                            |
| `seq`        | `integer`   | Monotonically increasing per game (starts at 1).      |
| `event_type` | `text`      | One of the values below.                               |
| `payload`    | `jsonb`     | Event-specific data (see below).                       |
| `created_at` | `timestamptz` | Server timestamp of insertion.                       |

### `event_type` values

| `event_type`        | `payload` fields                                           |
|---------------------|------------------------------------------------------------|
| `player_joined`     | `{ "player_id": "<id>" }`                                  |
| `archetype_selected`| `{ "player_id": "<id>", "archetype": "<name>" }`          |
| `card_placed`       | `{ "player_id": "<id>", "card_key": "<key>", "cell_index": 0–8 }` |
| `game_forfeited`    | `{ "forfeit_by": "<id>", "winner": "<id>" }`               |

### `seq` ordering

`seq` is scoped to the `game_id`. The first event for a game has `seq = 1`; each
subsequent insert increments it by one. A `UNIQUE (game_id, seq)` constraint in the
database prevents gaps or duplicates. Clients may use `seq` to detect missed events and
re-sync if needed.

## MVP Client Behaviour

On every Realtime INSERT for the subscribed `game_id`:

1. Call `GET /games/{game_id}` to retrieve the latest `GameState` snapshot.
2. Replace local state with the returned snapshot.

This approach is simple and avoids client-side event-sourcing logic. The `state_version`
field in `GameState` allows clients to detect stale responses if desired.

## RLS Notes

- Clients can subscribe to and read `game_events` only for games they participate in
  (enforced by the `game_events_select_participant` RLS policy).
- All writes to `game_events` go through the FastAPI service using the Supabase service
  role key; clients cannot insert or update events directly.
