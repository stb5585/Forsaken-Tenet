# Ability YAML Definitions

This directory contains **197 YAML files** defining abilities in the game.
Definitions are loaded on first use by `ability_loader`; parsed YAML is cached
by file path and modification time, while each call still receives a
deep-copied definition and a fresh ability instance. Abilities are instantiated
as one of 12 data-driven classes. Wrapper classes in the `abilities` package
delegate to the YAML loader.

## Foundational Taxonomy Migration

Every YAML ability declares an immutable ID equal to its filename stem plus
complete canonical metadata:

```yaml
id: fireball
aliases: [Fireball]
taxonomy:
  origin: arcane
  method: projection
  primary_intent: damage
  activation: active
  form: direct
  traits: []
targeting:
  scope: single_opponent
  loss_policy: retarget_focus
  hostile: true
```

Closed values and typed models live in `src/core/contracts`. Secondary traits
must be namespaced and registered centrally in
`src/core/data/ability_traits.py`; `internal.*` traits never appear in
player-facing descriptions. `legacy_taxonomy_allowlist.txt` is deliberately
empty and retained as evidence that the migration gate is closed. Validate
the complete inventory with:

```bash
./.venv/bin/python tools/validate_ability_taxonomy.py --require-complete
```

CI runs the same complete-only check. Each aliases list preserves both the
legacy Python class token and display name; shared display names are valid for
upgrade families, while shared non-display aliases fail validation. Legacy
`type` and `subtype` fields below continue to select execution classes during
the compatibility period; they are not the canonical taxonomy.

New saves serialize abilities by slug. YAML abilities declare their own slug;
active Python abilities in the player progression catalogs receive a validated
canonical slug from their unique catalog display name. A display-name change is
therefore an identity migration and must preserve the old slug as a read-only
compatibility input. Class tokens and display names otherwise remain read-only
compatibility inputs; new code must not persist them.

## Progression Ownership

Combat YAML defines what an ability does; it does not define when a player
learns it. `src/core/progression_manifest.py` and
`src/core/progression.py` own class-authored specialization paths,
prerequisites, talents, rating nodes, promotion gates, point costs, explicit
positions, and semantic icon keys. Trees can expose multiple independent
first-tier nodes. Ordinary abilities, talents, combat ratings, and primary
attributes cost one point; first promotions cost two points and second
promotions cost three. Combat-rating nodes grant `+10` in base trees, `+20`
in first-promotion trees, and `+30` in terminal trees, while primary attributes
grant `+1`.
Combat-rating nodes are deliberately ungated by global level. Authored
inherited entry abilities may also omit a level gate. Weapon Discipline arts
are gated only by discipline ranks 1, 5, and 10.
Ability upgrades require their earlier form and atomically replace it in the
active spellbook.

Quest, Class Ring, Power Core, vow, contract, summon-bond, and Weapon
Discipline rewards remain outside ability trees. Pathfinder's runtime
`NaturalAttunement` Skill grants `+3 Defense` and `+3 Magic Defense` for three
turns at a cost of 5 MP.

## Quick Reference — Ability Types

| YAML `type:` | DataDriven Class | Count | Description |
|---|---|---:|---|
| `Skill` | `DataDrivenSkill` | 81 | Physical/weapon abilities, fallback for unknown types |
| `Spell` | `DataDrivenSpell` | 47 | Offensive magic (elemental, arcane) |
| `Support` | `DataDrivenSupportSpell` | 18 | Buff/utility spells (Bless, Protect, Shell, etc.) |
| `Status` | `DataDrivenStatusSpell` | 14 | Debuff/status-inflicting spells (Doom, Blind, etc.) |
| `StatusSkill` | `DataDrivenStatusSkill` | 7 | Physical-stat-based status infliction (Disarm, Goad) |
| `Heal` | `DataDrivenHealSpell` | 8 | Healing spells (Heal, Cure, Raise, etc.) |
| `CustomSpell` | `DataDrivenCustomSpell` | 5 | Abilities with unique execution logic (Disintegrate, etc.) |
| `WeaponSpell` | `DataDrivenWeaponSpell` | 3 | Hybrid weapon+spell attacks (Smite, Dispel Slash) |
| `MagicMissile` | `DataDrivenMagicMissileSpell` | 4 | Multi-projectile spells with configurable missile count |
| `ChargingSkill` | `DataDrivenChargingSkill` | 7 | Multi-turn charge abilities (Charge, Crushing Blow, Shadow Strike, Dragon Breath ×3) |
| `Movement` | `DataDrivenMovementSpell` | 2 | Non-combat world-state abilities (Sanctuary, Teleport) |
| `JumpSkill` | `DataDrivenJumpSkill` | 1 | Jump with full modification system (13 mods) |

## YAML Format

### Required Fields

Every ability YAML must include:

```yaml
name: Ability Name
type: Spell           # See type table above
subtype: Fire         # Category for elemental/thematic grouping
description: >-
  Description text shown to the player.
cost: 10              # Mana cost (0 if none)
```

### Common Optional Fields

```yaml
damage_mod: 2.0         # Damage multiplier
crit: 10                # Critical hit chance bonus
weapon: true            # Uses equipped weapon stats
self_target: true       # Targets caster instead of enemy
ignore_armor: true      # Bypasses target defense
school: Arcane          # Magic school for resistance checks
combat: false           # Cannot be used in combat (Movement spells)
target_status_damage_multiplier:
  status: Stun          # Optional conditional multiplier for weapon skills
  multiplier: 1.5
```

### Charging Fields

For multi-turn abilities (`ChargingSkill`, `JumpSkill`, and some `Skill`/`Stealth`/`HolySpell`/`SummonSpell` types):

```yaml
charge_time: 1                # Turns to charge before executing
delay: 1                      # Action queue delay (usually = charge_time)
priority: NORMAL              # Action queue priority: NORMAL | HIGH | LOW
telegraph_message: "..."      # Message shown to Seeker/Inquisitor during charge
prone_while_charging: true    # Makes user vulnerable while charging
```

### Status Fields

For `Status` and `StatusSkill` types:

```yaml
# StatusSkill-specific
status_name: Disarm           # Status effect to apply
physical: true                # Physical (stat-based) vs magical check
actor_stat: strength          # Actor stat for contest
target_use_check_mod: speed   # Target stat for resistance
duration: 3                   # Status duration in turns (-1 = permanent)

# Status spell messages
messages:
  success: "{target} is afflicted!"
  immune: "{target} is immune."
  already: "{target} already has this status."
  resist: "The magic has no effect."
```

### Movement Fields

For `Movement` type abilities:

```yaml
movement_type: sanctuary    # sanctuary | teleport
combat: false               # Teleport cannot be used in combat
```

## Effect System

Effects define what happens when an ability executes. They are composable and can be nested.

### Simple Effects

```yaml
effects:
  # Direct damage
  - type: damage
    base: 100
    scaling: {stat: intelligence, ratio: 1.5}
    element: Fire
    ignore_defense: true

  # Status application
  - type: status_apply
    status_name: Stun
    duration: 3

  # Healing
  - type: heal
    target: self
    amount_percent: 0.3
```

### Stat Contest Wrapper

Many abilities wrap their effect in a stat contest — the effect only triggers if the actor wins the check:

```yaml
effects:
  - type: stat_contest
    actor_stat: intel
    actor_divisor: 2
    target_stat: wisdom
    target_lo_divisor: 4
    target_hi_divisor: 1
    effect:
      type: dynamic_dot
      dot_type: DOT
      duration: 2
      damage_lo_fraction: 0.25
      damage_hi_fraction: 0.5
```

### Compound / Chaining Effects

```yaml
# Multi-buff (Support spells)
- type: multi_buff
  stats: {Attack: 10, Defense: 8}
  duration: 5

# Ability chain — cast another ability as a sub-effect
- type: ability_chain
  ability_name: Heal
  target_self: true
  special: true
  use_method: cast

# Specialized execution effects
- type: charge_execute       # ChargingSkill execution
  dmg_mod: 1.25
  stun_duration: 1

- type: shadow_strike_execute  # Shadow Strike — guaranteed crit + blind
  dmg_mod: 2.0
  blind_chance: 0.6
  blind_duration: 2

- type: jump_execute         # JumpSkill execution
  base_dmg_mod: 2.0

- type: disintegrate         # CustomSpell — instant kill or massive damage
- type: holy_followup        # WeaponSpell — bonus holy damage
```

### Dynamic Effects

These apply runtime-calculated damage, DoTs, or debuffs:

```yaml
- type: dynamic_dot           # Damage over time
- type: dynamic_extra_damage  # Conditional bonus damage
- type: dynamic_multi_debuff  # Multiple debuffs in one effect
- type: dynamic_status_dot    # Status + DoT combo
```

## Examples by Type

### Spell — `fireball.yaml`

```yaml
name: Fireball
type: Spell
subtype: Fire
description: A giant ball of fire that consumes the enemy.
cost: 10
damage_mod: 2.0
crit: 10
school: Arcane
effects:
  - type: stat_contest
    actor_stat: intel
    actor_divisor: 2
    target_stat: wisdom
    effect:
      type: dynamic_dot
      dot_type: DOT
      duration: 2
      damage_lo_fraction: 0.25
      damage_hi_fraction: 0.5
```

### Skill — `backstab.yaml`

```yaml
name: Backstab
type: Skill
subtype: Stealth
description: Strike a stunned opponent in the back, ignoring defense.
cost: 6
weapon: true
damage_mod: 2.0
ignore_armor: true
requires_incapacitated: true
```

### Status — `doom.yaml`

```yaml
name: Doom
type: Status
subtype: Death
description: "Places a timer on the enemy's life."
cost: 15
messages:
  success: "A timer has been placed on {target}'s life."
  immune: "{target} is immune to death spells."
effects:
  - type: stat_contest
    actor_stat: charisma
    effect:
      type: status_apply
      status_name: Doom
      duration: 5
      skip_if_active: true
```

### ChargingSkill — `charge.yaml`

```yaml
name: Charge
type: ChargingSkill
subtype: Offensive
cost: 10
weapon: true
damage_mod: 1.25
charge_time: 1
telegraph_message: "lowering their head and building momentum"
effects:
  - type: charge_execute
    dmg_mod: 1.25
    stun_duration: 1
priority: NORMAL
delay: 1
```

### Movement — `sanctuary.yaml`

```yaml
name: Sanctuary
type: Movement
subtype: Movement
cost: 100
movement_type: sanctuary
```

## Charging & Telegraph System

Charging abilities take multiple turns to execute:

1. **Turn 1-N**: Ability charges — player is committed, telegraph shown
2. **Turn N+1**: Ability fires with full effect

During charging:
- Character cannot perform other actions
- `prone_while_charging: true` makes the user vulnerable
- Telegraph system reveals intent to Seeker/Inquisitor class

**Standard classes see:**
```
The Dragon is preparing something...
```

**Seeker/Inquisitor sees:**
```
The Dragon is inhaling deeply, flames flickering in its throat!
```

The `telegraph_message` YAML field provides the detailed version.

## Architecture

### Loading Pipeline

```
abilities/<domain>.py (class Foo)
  → __new__ → ability_loader._load_yaml_ability("foo.yaml")
    → parse YAML → EffectFactory.create_effect(effect_data)
    → AbilityFactory routes type → DataDriven* class
      → returns fully configured ability instance
```

### Key Files

| File | Role |
|---|---|
| `ability_loader.py` | YAML parsing, `EffectFactory`, `AbilityFactory`, type routing |
| `data_driven_abilities.py` | 12 `DataDriven*` classes that implement ability behavior |
| `effects/common.py` | Reusable conditional, status, resource, and scaling effects |
| `effects/enemy.py` | Enemy- and spell-specific effects |
| `effects/skills.py` | Equipment and player skill effects |
| `effects/special.py` | Advanced and bespoke ability effects |
| `effects/summon.py` | Summon companion ultimate effects |
| `effects/composite.py` | Backward-compatible re-exports for legacy imports |
| `effects/__init__.py` | Public effect exports |
| `abilities/` | Ability base types, focused wrapper modules, and progression catalogs |
| `abilities/__init__.py` | Public ability exports only |

### Adding a New Ability

1. Create `ability_name.yaml` in this directory
2. Set `type:` to match an existing DataDriven class (see type table)
3. Define `effects:` using available effect types from `EffectFactory`
4. Add a wrapper class in the appropriate `abilities/` implementation module if the ability needs to be referenced by name:
   ```python
   class MyAbility:
       def __new__(cls):
           return _load_yaml_ability("my_ability.yaml", cls_name="MyAbility")
   ```
5. Run tests: `.venv/bin/python -m pytest tests/test_data_driven_abilities.py -v`

For charging abilities, also set `charge_time`, `delay`, `priority`, and `telegraph_message`.

## Future Features

### Cooldowns (Planned)

```yaml
cooldown: 3  # Cannot reuse for 3 turns after execution
```

Candidates: Dim Mak, Arcane Blast, Disintegrate, Detonate, ultimates.

### Companion Ultimate Attacks

11 summon companions each learn an ultimate ability at level 10:

| Xenid | Ultimate | Type | Element | Key Mechanic |
|---|---|---|---|---|
| Patagon | Titanic Slam | Skill | Physical | 4× weapon damage + guaranteed stun |
| Dilong | Devour | Skill | Earth | 3 bites at (STR+CON)×1.5 each |
| Agloolik | Absolute Zero | Spell | Ice | 3× intel + 3-turn stun + permanent defense reduction |
| Cacus | Eruption | Spell | Fire | 3.5× (STR+INT) + Burn DOT + self defense buff |
| Izulu | Thunderstrike | Spell | Electric | 3× intel + 2 chain hits + stun |
| Hala | Wind Shrapnel | Spell | Wind | 5 hits at 1.2× intel, 25% crit each |
| Lamashtu | Oblivion | Spell | Shadow | 4× intel + 20% instant kill + stat drain |
| Seraphim | Divine Judgment | Spell | Holy | 3× wisdom (2× vs undead) + heal owner + cleanse |
| Bardi | Oblivion | Spell | Shadow | 4× intel + 20% instant kill + stat drain |
| Kobalos | Grand Heist | Skill | — | Steal gold + random debuff + Gold Toss finisher |
| Tiamat | Maelstrom Vortex | Spell | Water | 3× intel + Blind/Silence/Terrify |
| Zahhak | Cataclysm | Spell | Non-elemental | Cast 3 random spells + dragon breath + self power up |

## Notes

- YAML files are parsed on first use and cached until their modification time changes
- Effect composition allows complex behavior without Python code changes
- YAML format enables balance tuning without touching source
- The `DataDrivenSkill` fallback handles types without explicit routing
- Data-driven ability behavior is covered by `tests/test_data_driven_abilities.py`
- Event system emits `SPELL_CAST`/`SKILL_USE` events for analytics and UI
