-- Migration 004: add element column to cards table
-- The default 'shadow' is a placeholder only; the seed script overwrites it
-- with the correct element from cards.jsonl for every row it upserts.
ALTER TABLE public.cards
    ADD COLUMN IF NOT EXISTS element text NOT NULL DEFAULT 'shadow';
