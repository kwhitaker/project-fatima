-- =============================================================================
-- profiles: maps auth.users -> app profile fields
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id          uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username    text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- games: metadata + players + current_state snapshot + state_version
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.games (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    player1_id      uuid        REFERENCES public.profiles(id),
    player2_id      uuid        REFERENCES public.profiles(id),
    status          text        NOT NULL DEFAULT 'waiting',
    current_state   jsonb,
    state_version   integer     NOT NULL DEFAULT 0,
    seed            bigint      NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- game_events: append-only event log ordered by (game_id, seq)
-- Drives Supabase Realtime subscriptions filtered by game_id.
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.game_events (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id     uuid        NOT NULL REFERENCES public.games(id) ON DELETE CASCADE,
    seq         integer     NOT NULL,
    event_type  text        NOT NULL,
    payload     jsonb       NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (game_id, seq)
);

CREATE INDEX IF NOT EXISTS game_events_game_id_seq_idx
    ON public.game_events (game_id, seq);

-- =============================================================================
-- Row Level Security
-- Clients can read only games/events for games they participate in.
-- FastAPI writes using the service role key (bypasses RLS).
-- =============================================================================
ALTER TABLE public.profiles    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.games       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.game_events ENABLE ROW LEVEL SECURITY;

-- profiles: a user can read their own profile
CREATE POLICY "profiles_select_own"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

-- games: participants can read their game
CREATE POLICY "games_select_participant"
    ON public.games FOR SELECT
    USING (
        auth.uid() = player1_id
        OR auth.uid() = player2_id
    );

-- game_events: participants can read events for their game
CREATE POLICY "game_events_select_participant"
    ON public.game_events FOR SELECT
    USING (
        EXISTS (
            SELECT 1
            FROM public.games g
            WHERE g.id = game_id
              AND (g.player1_id = auth.uid() OR g.player2_id = auth.uid())
        )
    );

-- No client INSERT/UPDATE/DELETE policies on games or game_events:
-- all writes go through FastAPI with the service role key.
