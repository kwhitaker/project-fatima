-- =============================================================================
-- Add idempotency_key column to game_events (store already uses it)
-- =============================================================================
ALTER TABLE public.game_events
    ADD COLUMN IF NOT EXISTS idempotency_key text;

CREATE UNIQUE INDEX IF NOT EXISTS game_events_idempotency_key_idx
    ON public.game_events (game_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
