# PRD: Character Sheets (Simplified 5e)

## Overview

Add character sheet management to the D&D Party Inventory Manager. Characters belong to a party (inventory) but have their own separate inventory of items. Equipped items can modify character stats.

## Core Concepts

- **Characters** belong to an inventory (party) and share the same slug/passphrase auth
- **Character inventory** is separate from the party inventory — characters have their own items
- **Equipment** — items in a character's inventory can be equipped, modifying computed stats
- **XP → Level** — XP is the source of truth; level is derived from 5e XP thresholds
- **Stat modifiers** — equipped items can modify ability scores, AC, etc. via `stat_modifiers` in item properties

## 5e XP Thresholds

| Level | XP Required |
|-------|------------|
| 1 | 0 |
| 2 | 300 |
| 3 | 900 |
| 4 | 2,700 |
| 5 | 6,500 |
| 6 | 14,000 |
| 7 | 23,000 |
| 8 | 34,000 |
| 9 | 48,000 |
| 10 | 64,000 |
| 11 | 85,000 |
| 12 | 100,000 |
| 13 | 120,000 |
| 14 | 140,000 |
| 15 | 165,000 |
| 16 | 195,000 |
| 17 | 225,000 |
| 18 | 265,000 |
| 19 | 305,000 |
| 20 | 355,000 |

## Proficiency Bonus (derived from level)

| Levels | Bonus |
|--------|-------|
| 1-4 | +2 |
| 5-8 | +3 |
| 9-12 | +4 |
| 13-16 | +5 |
| 17-20 | +6 |

## Data Model

### Character

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| inventory_id | UUID | FK to inventories (party) |
| name | str | Character name |
| race | str | Character race (e.g. "Human", "Elf") |
| character_class | str | Character class (e.g. "Fighter", "Wizard") |
| xp | int | Current experience points (default 0) |
| level | computed | Derived from XP using 5e thresholds |
| proficiency_bonus | computed | Derived from level |
| strength | int | Base STR score (default 10) |
| dexterity | int | Base DEX score (default 10) |
| constitution | int | Base CON score (default 10) |
| intelligence | int | Base INT score (default 10) |
| wisdom | int | Base WIS score (default 10) |
| charisma | int | Base CHA score (default 10) |
| max_hp | int | Maximum hit points |
| current_hp | int | Current hit points |
| base_ac | int | Base armor class (default 10) |
| speed | int | Movement speed in feet (default 30) |
| created_at | datetime | Creation timestamp |
| updated_at | datetime | Last update timestamp |

### Character Items

Reuse the existing `Item` model structure but with a `character_id` FK instead of `inventory_id`. Create a new `CharacterItem` table that mirrors the item structure but belongs to a character.

A `CharacterItem` has an additional field:
- `is_equipped: bool` (default False)

When equipped, if the item's `properties` dict contains `stat_modifiers`, those are applied to compute effective stats.

Each CharacterItem has two optional dicts for stat effects:

**`stat_modifiers`** — Additive bonuses (e.g. +2 STR):
```json
{"stat_modifiers": {"strength": 2, "ac": 2}}
```

**`stat_overrides`** — Set stat to a fixed value (e.g. Gauntlets of Ogre Power):
```json
{"stat_overrides": {"strength": 19}}
```

### Stat Resolution Order

1. Start with **base stat**
2. Apply **overrides** — if multiple items override the same stat, take the highest value. Only apply if override > base.
3. Apply all **additive modifiers** on top

Example: Base STR 12, Gauntlets of Ogre Power (override 19), +1 STR ring (modifier +1)
→ max(12, 19) = 19, then 19 + 1 = 20

### Computed Stats (returned by API, not stored)

For each of the 6 ability scores, the API returns:
- **base** — the raw score set on the character
- **effective** — after equipment overrides + modifiers
- **modifier** — floor((effective - 10) / 2)

Additional computed fields:
- `effective_ac` = base_ac + sum of equipped item ac modifiers (or highest ac override + modifiers)
- `level` = derived from XP using 5e thresholds
- `proficiency_bonus` = derived from level
- `xp_to_next_level` = next threshold - current XP (null at level 20)

### Item Stat Display

Each item in a character's inventory should expose its stat impact for display:
- Additive modifiers shown as "+2 STR", "+1 AC"
- Overrides shown as "Sets STR to 19"

## API Endpoints

All under `/api/inventories/{slug}/characters`. Same `X-Passphrase` auth as party inventory.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/characters` | List all characters in party |
| POST | `/characters` | Create a new character |
| GET | `/characters/{id}` | Get character with computed stats |
| PATCH | `/characters/{id}` | Update character fields |
| DELETE | `/characters/{id}` | Delete character |
| GET | `/characters/{id}/items` | List character's items |
| POST | `/characters/{id}/items` | Add item to character |
| PATCH | `/characters/{id}/items/{item_id}` | Update character item |
| DELETE | `/characters/{id}/items/{item_id}` | Remove item from character |
| POST | `/characters/{id}/items/{item_id}/equip` | Equip an item |
| POST | `/characters/{id}/items/{item_id}/unequip` | Unequip an item |

## Frontend

### Character List View
- Show all characters in the party as cards
- Each card shows: name, race, class, level, HP
- Click to open character detail

### Character Detail View
- **Profile section**: name, race, class, level, XP (with progress bar to next level)
- **Stats section**: 6 ability scores with modifiers, AC, HP, speed, proficiency bonus
  - Show base stat and effective stat (with equipment bonus) side by side
- **Inventory section**: list of character's items
  - Toggle equipped/unequipped
  - Equipped items visually distinct
  - Add/remove items (reuse existing item form components)

### Navigation
- Add "Characters" tab/section alongside existing inventory views
- Character management accessible from party page

## Out of Scope (v1)
- Spell slots / spellcasting
- Skill proficiencies / saving throws
- Feats / class features
- Multiclassing
- Transfer items between party inventory and character inventory
- Equipment slots (head, body, etc.) — any item can be equipped
- Attunement limits
- SSE real-time sync for character changes (can add later)
