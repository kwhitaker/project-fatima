# Cards Spec (Import + Balance)

This repo stores a generated card pool for the Barovia/Curse of Strahd-inspired, Triple-Triad-ish
minigame.

The canonical source file is `cards.jsonl` (JSON Lines): one JSON object per line.

## Why JSON Lines

- Easy to generate via scripts/AI.
- Easy to stream-import into a database.
- Diffs/merges are manageable (one card per line).

## File(s)

- `cards.jsonl`: card definitions.

## Card Object Schema

Required fields (MVP):

- `card_key` (string)
  - Stable, human-readable unique key for the specific card version.
  - Example: `strahd_iii`, `zombie_i`.
- `character_key` (string)
  - Stable key shared across versions of the same named character.
  - Used to enforce "named uniqueness" across tiers.
  - Example: `strahd_von_zarovich`.
- `name` (string)
  - Display name (character/monster name).
- `version` (string)
  - Display label to distinguish variants (e.g., tier flavor).
- `tier` (int)
  - One of: `1`, `2`, `3`.
- `rarity` (int)
  - Numeric rarity scale: `1..100`.
- `is_named` (bool)
  - True for NPCs/unique monsters/unique entities.
  - False for generic enemies (Zombie, Dire Wolf, etc.).
- `sides` (object)
  - `{ "n": int, "e": int, "s": int, "w": int }`
  - Side values are integers `1..10`.
- `set` (string)
  - Card set identifier (used for grouping).

Optional fields:

- `tags` (array of strings)
  - Non-binding metadata for UI, search, or future rules modules.

## ID Strategy (DB)

The JSONL file does not include a database primary key.

- Recommended DB `id`: NanoID stored as text.
- Alternative: UUID.

`card_key` is the stable identifier in git; the DB `id` can be generated on import.

## Balance Model (MVP)

MVP is "pure stats" (no card keywords). Strength comes from rarity + tier.

Constraints:

- Side values: `1..10`.
- Each card must meet the sum budget for its tier and rarity bucket.
- Each card must not exceed the per-side cap for its tier and rarity bucket.

### Rarity Buckets (Derived From Numeric `rarity`)

- `1..49`: common bucket
- `50..74`: uncommon bucket
- `75..89`: rare bucket
- `90..96`: very_rare bucket
- `97..100`: ultra bucket

### Stat Budgets and Caps

Each (tier, bucket) maps to `(sum_budget, side_cap)`.

Tier 1:

- common: (16, cap 6)
- uncommon: (18, cap 7)
- rare: (20, cap 8)
- very_rare: (22, cap 9)
- ultra: (24, cap 9)

Tier 2:

- common: (20, cap 7)
- uncommon: (22, cap 8)
- rare: (24, cap 9)
- very_rare: (26, cap 10)
- ultra: (28, cap 10)

Tier 3:

- common: (24, cap 8)
- uncommon: (26, cap 9)
- rare: (28, cap 10)
- very_rare: (30, cap 10)
- ultra: (32, cap 10)

Notes:

- Budgets are tuned to keep strong cards strong without making capture outcomes trivial.
- Caps prevent one-side "auto-win" numbers from dominating.

## Deck Validation Hooks (MVP+)

Even if MVP ships with prebuilt decks, implement these rules in a deck validator.

### Named Character Uniqueness

- If `is_named == true`, only one card per `character_key` may appear in a 10-card deck.
- This prevents running multiple tiers/versions of the same named character.

### Copy Limits (By Exact Card Version)

Enforce via `card_key`.

- Default: 2 copies for low-rarity cards; 1 copy for higher-rarity cards.
- Implement as a lookup table driven by rarity bucket.

### Rarity Slots

Also driven by rarity bucket:

- ultra: max 1
- very_rare: max 2
- rare: max 3
- remaining cards must be uncommon/common

## Import Expectations

- Importer should validate:
  - JSON schema presence/types.
  - `card_key` uniqueness.
  - `rarity` in `1..100`.
  - `tier` in `{1,2,3}`.
  - side values in `1..10`.
  - sum budget and cap compliance.

## Example Entry

```json
{"card_key":"strahd_iii","character_key":"strahd_von_zarovich","name":"Strahd von Zarovich","version":"Strahd III","tier":3,"rarity":100,"is_named":true,"sides":{"n":10,"e":9,"s":7,"w":6},"set":"barovia_200y_v1","tags":["boss","ravenloft"]}
```
