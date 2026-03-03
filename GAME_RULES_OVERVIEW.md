# Game Rules Overview (CoS Triple-Triad-ish)

Turn-based 3x3 card-capture game inspired by Triple Triad, flavored with Curse of Strahd.

## Design Goals

- Mostly strategy, with a small amount of randomness.
- Lighthearted; "canon minigame" for the campaign.
- MVP uses only card side stats + player archetype power (no card keywords/abilities).

## Components

### Board

- A 3x3 grid (9 cells).
- Each grid cell holds at most one card.
- Each cell has an elemental affiliation (see Elemental System below).

### Cards

- Each card has 4 side values: North, East, South, West (integers 1–10).
- Each card has an elemental affiliation: `blood`, `holy`, `arcane`, `shadow`, or `nature`.
- Each card represents a Curse of Strahd character/monster/NPC.
- Each named character can have multiple distinct versions (Tier I / Tier II / Tier III).
- **Weak-side rule**: every card must have at least one side ≤ 3. Cards where all four sides are ≥ 4 are invalid. This ensures filler cards remain threatening on at least one edge, preventing the game from collapsing to a race for the highest stats.

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
- When the second player joins, 9 board elements are generated deterministically from the game seed (one per cell).

MVP note (scope): deck building + card inventory management is out of scope. We can ship MVP with
prebuilt decks, but still implement deck-validation rules so future deck building uses the same
constraints.

## Turn Structure

- Players alternate turns.
- On your turn, choose 1 card from your hand and place it into an empty board cell.
- Resolve "Mists" randomness for this placement.
- Check for Plus rule captures (pre-step, before standard comparison).
- Resolve standard captures against orthogonally adjacent enemy cards.
- Repeat until the board is full (9 placements).

## Captures (Core Mechanic)

When a card is placed, it battles any orthogonally adjacent enemy cards.

- Compare the placed card's side value that touches the neighbor against the neighbor's touching
  side value.
- If the placed card's value (plus any modifiers — see Mists and Elemental below) is higher, it
  captures (flips) that neighbor.
- If it is equal or lower, no capture.

Notes:

- Captures can chain ("combos"): when a card is captured, it may immediately capture any
  orthogonally adjacent enemy cards using the same strict greater-than rule.
- Combos continue until no new captures occur.
- Mists/archetype/elemental modifiers apply only to the initially placed card's comparisons for
  that placement; combo captures use raw printed side values.
- Ownership is binary (a card is controlled by one player at a time).

## Plus Rule

The Plus rule fires as a pre-step before standard comparison captures:

1. For each orthogonally adjacent opponent-owned card, compute: **placed card's attacking side value + neighbor's facing side value** (both raw printed values — no Mists or Elemental modifier).
2. If 2 or more such sums are equal, all neighbors contributing to that shared sum are captured immediately, regardless of whether the placed card's side is higher or lower.
3. Plus-captured cards enter the standard BFS combo chain (with no modifiers on combo steps).
4. After Plus resolves, standard comparison captures still run for any remaining adjacent opponent cards not yet captured by Plus.

Example: placing a card with N=6 and W=3. Cell above has S=7 (sum = 6+7 = 13). Cell to the left has E=10 (sum = 3+10 = 13). Both sums match → Plus triggers, both captured.

Key constraint: Plus uses **raw printed side values only**. Mists modifier and Elemental bonus do not affect Plus sum calculations.

## Randomness: Mists of Barovia

After placing a card, roll 1d6 and apply only for this placement's initial comparisons:

- 1: Fog: placed card is **−2** on all side comparisons this placement
- 6: Omen: placed card is **+2** on all side comparisons this placement
- 2-5: no effect

Rules details:

- The modifier applies only when comparing values during this placement's initial battles (not combo chain captures).
- The modifier does not permanently change the card's printed side values.
- Devout archetype negates Fog entirely (modifier → 0 regardless of magnitude).

## Elemental System

Each card has an element (`blood`, `holy`, `arcane`, `shadow`, `nature`). Each board cell also has an element, generated deterministically from the game seed when the match begins.

**Elemental bonus**: If the placed card's element matches the cell's element, the card receives **+1 on all its side comparisons** for that placement's initial battles.

Stacking: Mists modifier and Elemental bonus stack additively. A Fog roll (−2) plus an elemental match (+1) yields a net −1 modifier for that placement.

Scope constraints:

- Elemental bonus applies only to the placed card's initial comparisons; combo chain captures use raw printed values.
- Plus rule sum calculations use raw printed values — Elemental bonus does NOT apply to Plus sums.
- Board elements are fixed for the duration of the game (generated once at match start).

Thematic element assignments (from `ralph/card_elements.json`):

- `blood`: undead, vampires, disease-related
- `holy`: clerics, paladins, radiant/divine entities
- `arcane`: spellcasters, constructs, magic items
- `shadow`: shadow creatures, assassins, thieves, criminals
- `nature`: beasts, druids, nature-aligned, wereravens

## Win Condition

- When the board is full, the player controlling more cards wins.
- If tied, optional "Sudden Death": replay using the 9 cards you ended the previous game owning.

## Sudden Death

- Same `game_id`, `round_number++`; each player's deck = the 9 cards they owned at board-full.
- Cap: 3 Sudden Death rounds, then declare a draw.

## Player Archetypes (Once-Per-Game Power)

Each player has an archetype based on their primary stat. Once per game, they may use a special
ability to influence the board.

MVP guidance:

- Keep powers simple, board-focused, and easy to validate.
- Powers should not add ongoing passive rules.

Implemented powers:

- **Martial** (STR/DEX): After placing, rotate the placed card once before resolving captures.
- **Skulker** (DEX): After placement, add +2 to one chosen side for this placement only.
- **Caster** (INT): Reroll the Mists die for your placement.
- **Devout** (WIS): Treat Fog (1) as no effect for your placement (negate the −2 modifier entirely).
- **Presence** (CHA): Force one adjacent comparison to be re-evaluated with +1 for you (this placement).

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

## Implemented Game Systems

All of the following are active in the current codebase:

- Standard comparison captures + BFS combo chain
- Weak-side card rule (all cards guaranteed to have min side ≤ 3)
- Mists of Barovia (±2 modifier, not ±1)
- Plus rule (sum-matching pre-capture step)
- Elemental system (board cell elements + placed card element → +1 bonus on match)
- Player archetypes (all five implemented)
- Sudden Death (up to 3 rounds, then draw)
- Named character uniqueness + rarity slots + copy limits

## Future Expansion Ideas (Post-MVP)

- Add card keywords tied to CoS tags (Undead/Holy/Vistani/etc.).
- Add deck building + inventory, matchmaking, and rewards/progression.
