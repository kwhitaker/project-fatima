# Game Rules Overview (CoS Triple-Triad-ish)

Turn-based 3x3 card-capture game inspired by Triple Triad, flavored with Curse of Strahd.

## Design Goals

- Mostly strategy, with a small amount of randomness.
- Lighthearted; "canon minigame" for the campaign.
- MVP uses only card side stats + player archetype power (no card keywords/abilities).

## Components

### Board

- A 3x3 grid.
- Each grid cell holds at most one card.

### Cards

- Each card has 4 side values: North, East, South, West (integers).
- Each card represents a Curse of Strahd character/monster/NPC.
- Each named character can have multiple distinct versions (Tier I / Tier II / Tier III).

### Rarity + Tier

- Card rarity is a numeric value (UI maps it to text labels later).
- Cards also have a tier: I, II, III.
- Higher rarity/tier implies higher strength (implemented via a "power budget" and/or caps).

MVP balance approach (subject to tuning):

- Each (rarity, tier) maps to a total stat budget across the 4 sides, and a per-side max cap.
- Building a card means distributing the budget across N/E/S/W within the cap.

## Match Setup

- Each player brings a 10-card deck.
- Each match uses a 5-card hand per player.

MVP note (scope): deck building + card inventory management is out of scope. We can ship MVP with
prebuilt decks, but still implement deck-validation rules so future deck building uses the same
constraints.

## Turn Structure

- Players alternate turns.
- On your turn, choose 1 card from your hand and place it into an empty board cell.
- Resolve "Mists" randomness for this placement.
- Resolve captures against orthogonally adjacent enemy cards.
- Repeat until the board is full (9 placements).

## Captures (Core Mechanic)

When a card is placed, it battles any orthogonally adjacent enemy cards.

- Compare the placed card's side value that touches the neighbor against the neighbor's touching
  side value.
- If the placed card's value is higher, it captures (flips) that neighbor.
- If it is equal or lower, no capture.

Notes:

- MVP uses only the placed card to initiate comparisons (no chain/combos).
- Ownership is binary (a card is controlled by one player at a time).

## Randomness: Mists of Barovia

After placing a card, roll 1d6 and apply only for this placement's comparisons:

- 1: Fog: placed card is -1 on all side comparisons this turn
- 6: Omen: placed card is +1 on all side comparisons this turn
- 2-5: no effect

Rules details:

- The modifier applies only when comparing values during this placement's battles.
- The modifier does not permanently change the card's printed side values.

## Win Condition

- When the board is full, the player controlling more cards wins.
- If tied, optional "Sudden Death": replay using the 9 cards you ended the previous game owning.

## Player Archetypes (Once-Per-Game Power)

Each player has an archetype based on their primary stat. Once per game, they may use a special
ability to influence the board.

MVP guidance:

- Keep powers simple, board-focused, and easy to validate.
- Powers should not add ongoing passive rules.

Candidate powers (pick a small set):

- Martial (STR/DEX): After placing, rotate the placed card once before resolving captures.
- Skulker (DEX): After placement, add +2 to one chosen side for this placement only.
- Caster (INT): Reroll the Mists die for your placement.
- Devout (WIS): Treat Fog (1) as no effect for your placement (negate the -1).
- Presence (CHA): Force one adjacent comparison to be re-evaluated with +1 for you (this placement).

## Deck Anti-Stacking Rules

We want to prevent "stacked" decks and ensure powerful named cards feel unique.

### Named Character Uniqueness (Recommended)

- All named characters/NPCs/unique monsters are UNIQUE BY CHARACTER.
- A deck may include at most one version of a named character total across all tiers.
  - Example: you cannot run both "Strahd I" and "Strahd III" in the same deck.

"Generic" enemies (e.g., Zombie) are not considered named characters.

### Copy Limits (By Exact Card Version)

Max copies of the exact same card version in a deck:

- Common-ish versions: max 2
- Higher rarity versions: typically max 1

Exact thresholds depend on the numeric rarity mapping; implement as a lookup table.

### Rarity Slots (Chosen Constraint)

Decks are constrained by rarity-slot caps (based on numeric rarity).

- Ultra-rare: max 1
- Very rare: max 2
- Rare: max 3
- Remaining cards must be lower rarity

The UI can translate numeric rarity into these buckets.

## MVP Defaults (So We Can Implement Fast)

- No card keywords/abilities.
- No elemental tiles.
- No Same/Plus/combos.
- Use Mists randomness.
- Enforce: named character uniqueness + rarity slots + copy limits.

## Future Expansion Ideas (Post-MVP)

- Add optional rule modules (Same/Plus/Combo, elemental tiles, etc.).
- Add card keywords tied to CoS tags (Undead/Holy/Vistani/etc.).
- Add deck building + inventory, matchmaking, and rewards/progression.
