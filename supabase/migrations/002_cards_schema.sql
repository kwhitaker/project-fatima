-- =============================================================================
-- cards: canonical card definitions matching cards.jsonl schema
-- card_key is the stable unique identifier; definition jsonb holds the full card.
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.cards (
    card_key        text        PRIMARY KEY,
    character_key   text        NOT NULL,
    name            text        NOT NULL,
    version         text        NOT NULL,
    tier            integer     NOT NULL CHECK (tier BETWEEN 1 AND 3),
    rarity          integer     NOT NULL CHECK (rarity BETWEEN 1 AND 100),
    is_named        boolean     NOT NULL DEFAULT false,
    n               integer     NOT NULL CHECK (n BETWEEN 1 AND 10),
    e               integer     NOT NULL CHECK (e BETWEEN 1 AND 10),
    s               integer     NOT NULL CHECK (s BETWEEN 1 AND 10),
    w               integer     NOT NULL CHECK (w BETWEEN 1 AND 10),
    set             text        NOT NULL,
    tags            text[]      NOT NULL DEFAULT '{}',
    definition      jsonb       NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS cards_character_key_idx ON public.cards (character_key);
CREATE INDEX IF NOT EXISTS cards_tier_rarity_idx   ON public.cards (tier, rarity);

-- =============================================================================
-- Row Level Security
-- Cards are publicly readable; inserts/updates go through service role key only.
-- =============================================================================
ALTER TABLE public.cards ENABLE ROW LEVEL SECURITY;

CREATE POLICY "cards_select_public"
    ON public.cards FOR SELECT
    USING (true);
