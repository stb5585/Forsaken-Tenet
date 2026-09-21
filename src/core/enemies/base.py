"""Shared enemy behavior and creature-type base classes."""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable
from textwrap import wrap

from .. import items
from ..character import Character, Combat, Resource, Stats, StatusEffect
from ..combat.action_queue import ActionPriority
from ..constants import ENEMY_LOW_HEALTH_THRESHOLD
from ..identity import ENEMY_TYPES

AbilityFactory = Callable[[], object]


def _fixed_resistances(**overrides: float) -> dict[str, float]:
    resistances = {
        "Fire": 0.0,
        "Ice": 0.0,
        "Electric": 0.0,
        "Water": 0.0,
        "Earth": 0.0,
        "Wind": 0.0,
        "Shadow": 0.0,
        "Holy": 0.0,
        "Poison": 0.0,
        "Physical": 0.0,
    }
    resistances.update(overrides)
    return resistances


def _build_spellbook(
    *,
    spells: Iterable[AbilityFactory] = (),
    skills: Iterable[AbilityFactory] = (),
) -> dict[str, dict[str, object]]:
    spellbook: dict[str, dict[str, object]] = {"Spells": {}, "Skills": {}}
    for ability_ctor in spells:
        ability = ability_ctor()
        spellbook["Spells"][ability.name] = ability
    for ability_ctor in skills:
        ability = ability_ctor()
        spellbook["Skills"][ability.name] = ability
    return spellbook


class Enemy(Character):
    """
    Same as player character with notable exceptions
    cls: just the name of the enemy (used for transforming and other class checks)
    experience: number of experience points awarded for defeating the enemy
    enemy_typ: defines the base type template used for enemy
    picture(str): file that contains the ascii art for the enemy
    """

    enemy_id: str

    def __init_subclass__(cls, *, enemy_id: str | None = None, **kwargs: object) -> None:
        """Register every enemy type at definition time for strict persistence."""
        super().__init_subclass__(**kwargs)
        cls.enemy_id = ENEMY_TYPES.register(cls, enemy_id)

    _DEBUFF_REAPPLY_RULES = {
        "Enfeeble": {"stat_all": ["Attack", "Defense"]},
        "Weaken Mind": {"stat_all": ["Magic", "Magic Defense"]},
        "Ruin": {"stat_all": ["Attack", "Defense", "Magic", "Magic Defense"]},
        "Sleeping Powder": {"status": "Sleep"},
        "Sleep": {"status": "Sleep"},
        # Stun-lock prevention: avoid wasting stun attempts while the target
        # is already stunned or is in the short post-stun immunity window
        # (Character.apply_stun uses status_effects["Stun"].extra).
        "Stupefy": {"status": "Stun"},
        "Berserk": {"status": "Berserk"},
        "Howl": {"status": "Stun"},
        # Charging skills that often apply stun; skip when the target cannot be stunned.
        "Charge": {"status": "Stun"},
        "Crushing Blow": {"status": "Stun"},
        "Trip": {"physical": "Prone"},
        "Goad": {"status": "Berserk"},
        "Blinding Fog": {"status": "Blind"},
    }

    def __init__(
        self,
        name: str,
        health: int,
        mana: int,
        strength: int,
        intel: int,
        wisdom: int,
        con: int,
        charisma: int,
        dex: int,
        attack: int,
        defense: int,
        magic: int,
        magic_def: int,
        exp: int,
    ) -> None:
        super().__init__(
            name,
            Resource(health + con, health + con),
            Resource(mana + intel, mana + intel),
            Stats(strength, intel, wisdom, con, charisma, dex),
            Combat(attack, defense, magic, magic_def),
        )
        self.name = name
        self.cls = self
        self.experience = exp
        self.enemy_typ: str = ""
        self.action_stack: list[dict] = []
        self.last_action_stack_entry: dict | None = None
        self._debuff_failure_cooldowns: dict[str, int] = {}
        # Ability names that can only be used once per combat by this enemy.
        self.single_use_abilities: set[str] = set()
        self._used_single_use_abilities: set[str] = set()
        self.picture: str = "test.txt"

    def __str__(self) -> str:
        return (
            f"{self.name} | "
            f"Health: {self.health.current}/{self.health.max} | "
            f"Mana: {self.mana.current}/{self.mana.max}"
        )

    def inspect(self) -> str:
        stats_str = [
            "{:15}{:>4}".format("Strength:", f"{self.stats.strength}"),
            "{:15}{:>4}".format("Intelligence:", f"{self.stats.intel}"),
            "{:15}{:>4}".format("Wisdom:", f"{self.stats.wisdom}"),
            "{:15}{:>4}".format("Constitution:", f"{self.stats.con}"),
            "{:15}{:>4}".format("Charisma:", f"{self.stats.charisma}"),
            "{:15}{:>4}".format("Dexterity:", f"{self.stats.dex}"),
        ]
        stats_str = "\n".join(stats_str)
        resist_str = [
            "{:12}{:>6}  {:12}{:>6}".format(
                "Fire:", f"{self.resistance['Fire']}", "Ice:", f"{self.resistance['Ice']}"
            ),
            "{:12}{:>6}  {:12}{:>6}".format(
                "Electric:",
                f"{self.resistance['Electric']}",
                "Water:",
                f"{self.resistance['Water']}",
            ),
            "{:12}{:>6}  {:12}{:>6}".format(
                "Earth:", f"{self.resistance['Earth']}", "Wind:", f"{self.resistance['Wind']}"
            ),
            "{:12}{:>6}  {:12}{:>6}".format(
                "Shadow:", f"{self.resistance['Shadow']}", "Holy:", f"{self.resistance['Holy']}"
            ),
            "{:12}{:>6}  {:12}{:>6}".format(
                "Poison:",
                f"{self.resistance['Poison']}",
                "Physical:",
                f"{self.resistance['Physical']}",
            ),
        ]
        resist_str = "\n".join(resist_str)
        immunity_str = ", ".join(self.status_immunity) if self.status_immunity else "None"
        specials = list(self.spellbook["Spells"].keys()) + list(self.spellbook["Skills"].keys())
        specials = ", ".join(specials)
        specials = "\n".join(wrap(f"Specials: {specials}", 50, break_on_hyphens=False))
        text = (
            f"\nName: {self.name} Type: {self.enemy_typ}\n\n"
            f"Stats:\n"
            f"{stats_str}\n\n"
            f"Resistances:\n"
            f"{resist_str}\n\n"
            f"Immunities: {immunity_str}\n\n"
            f"{specials}"
        )
        return text

    def options(
        self, target: Character, action_list: list[str], tile: object
    ) -> tuple[str, str | None]:
        self.last_action_stack_entry = None
        for skill_name, skill in self.spellbook.get("Skills", {}).items():
            if getattr(skill, "charging", False):
                return "Use Skill", skill_name
        if self.status_effects["Berserk"].active:
            return "Attack", None
        if self.turtle or self.magic_effects["Ice Block"].active:
            return "Nothing", None

        # If action_stack is defined with priorities, use weighted selection
        if self.action_stack and any(
            isinstance(item, dict) and "priority" in item for item in self.action_stack
        ):
            return self._choose_action_by_priority(target, tile)

        # Legacy path: standard random action selection
        if self.name != "Test" and not self.tunnel:
            action_list = ["Attack"]
        else:
            action_list = []
        if not self.abilities_suppressed():
            spell_list = []
            for spell_name, spell in self.spellbook["Spells"].items():
                if (
                    spell_name in self.single_use_abilities
                    and spell_name in self._used_single_use_abilities
                ):
                    continue
                if self.spellbook["Spells"][spell_name].passive:
                    continue
                if self._should_skip_reapply_debuff(spell_name, target):
                    continue
                if self.tunnel:
                    if spell.subtyp not in ["Heal", "Support"]:
                        continue
                if self._should_skip_full_health_heal(spell):
                    continue
                if self.spellbook["Spells"][spell_name].cost <= self.mana.current:
                    spell_list.append(spell_name)
            if spell_list:
                action_list.append("Cast Spell")
            skill_list = []
            for skill_name, _ in self.spellbook["Skills"].items():
                if (
                    skill_name in self.single_use_abilities
                    and skill_name in self._used_single_use_abilities
                ):
                    continue
                if any(
                    [
                        self.spellbook["Skills"][skill_name].passive,
                        self.spellbook["Skills"][skill_name].name == "Backstab"
                        and not target.incapacitated(),
                        self.spellbook["Skills"][skill_name].name == "Disarm"
                        and not self._target_has_weapon(target),
                        self.spellbook["Skills"][skill_name].weapon and self.is_disarmed(),
                        self.spellbook["Skills"][skill_name].name == "Smoke Screen"
                        and self.health.current > self.health.max * ENEMY_LOW_HEALTH_THRESHOLD,
                        self.tunnel,
                    ]
                ):
                    continue
                if self._should_skip_reapply_debuff(skill_name, target):
                    continue
                if self.spellbook["Skills"][skill_name].cost <= self.mana.current:
                    skill_list.append(skill_name)
            if skill_list:
                action_list.append("Use Skill")
        item_list = self._combat_item_choices()
        if item_list:
            action_list.append("Use Item")
        if self.is_disarmed():
            action_list.append("Pickup Weapon")
        if self.tunnel:
            action_list.extend(["Surface", "Nothing"])
        if self._should_attempt_flee(target, tile):
            action_list.append("Flee")
        action = random.choice(action_list)
        if action == "Cast Spell":
            ability = random.choice(spell_list)
        elif action == "Use Skill":
            ability = random.choice(skill_list)
        elif action == "Use Item":
            ability = random.choice(item_list)
        else:
            ability = None
        if ability in self.single_use_abilities:
            self._used_single_use_abilities.add(ability)
        self._advance_debuff_failure_cooldowns()
        return action, ability

    def _choose_action_by_priority(self, target: Character, tile: object) -> tuple[str, str | None]:
        """
        Choose an action based on priority weights from action_stack.
        Priority weighting: HIGH=3, NORMAL=2, LOW=1
        Ensures enemies use abilities strategically, not just random selection.
        """
        # Build weighted pool of available actions from action_stack
        self.last_action_stack_entry = None
        weighted_actions = []
        if self._should_attempt_flee(target, tile):
            weighted_actions.extend(
                [
                    ("Flee", None, {"ability": "Flee", "reason": "outclassed"}),
                ]
                * self._priority_to_weight(ActionPriority.HIGH)
            )
        pickup_priority = self._pickup_weapon_priority()
        if pickup_priority != ActionPriority.SKIP:
            for _ in range(self._priority_to_weight(pickup_priority)):
                weighted_actions.append(
                    (
                        "Pickup Weapon",
                        None,
                        {
                            "ability": "Pickup Weapon",
                            "priority": pickup_priority,
                            "reason": "disarmed",
                        },
                    )
                )

        for action_entry in self.action_stack:
            if not isinstance(action_entry, dict):
                continue

            ability_name = action_entry.get("ability", "Attack")
            if (
                ability_name in self.single_use_abilities
                and ability_name in self._used_single_use_abilities
            ):
                continue
            priority = action_entry.get("priority", ActionPriority.NORMAL)
            priority_if = action_entry.get("priority_if")
            if priority_if:
                priority = self._resolve_priority_condition(priority_if, priority, target, tile)
            priority = self._resolve_ai_priority(priority, action_entry)
            if priority == ActionPriority.SKIP:
                continue

            # Determine action type and check availability
            item_list = self._combat_item_choices()
            if ability_name == "Use Item":
                if not item_list:
                    continue
                action_type = "Use Item"
                ability_name = item_list[0]
                usable = True
            elif isinstance(ability_name, str) and ability_name.startswith("Use Item:"):
                item_name = ability_name.split(":", 1)[1].strip()
                if item_name not in item_list:
                    continue
                action_type = "Use Item"
                ability_name = item_name
                usable = True
            elif ability_name == "Attack":
                action_type = "Attack"
                ability_name = None
                usable = not self.tunnel
            elif ability_name == "Pickup Weapon":
                action_type = "Pickup Weapon"
                ability_name = None
                usable = self.is_disarmed()
            elif ability_name in self.spellbook.get("Spells", {}):
                if self.abilities_suppressed():
                    continue
                if self._should_skip_reapply_debuff(ability_name, target):
                    continue
                spell = self.spellbook["Spells"][ability_name]
                # Skip passive spells and check mana
                if spell.passive or self.mana.current < spell.cost:
                    continue
                if self._should_skip_full_health_heal(spell):
                    continue
                if self._is_full_health() and self._is_regen_spell(spell):
                    priority = ActionPriority.LOW
                if self.tunnel and spell.subtyp not in ["Heal", "Support"]:
                    continue
                action_type = "Cast Spell"
                usable = True
            elif ability_name in self.spellbook.get("Skills", {}):
                if self.abilities_suppressed():
                    continue
                if self._should_skip_reapply_debuff(ability_name, target):
                    continue
                skill = self.spellbook["Skills"][ability_name]
                # Skip passive skills and check mana/target constraints
                if skill.passive or self.mana.current < skill.cost:
                    continue
                if self.tunnel and ability_name != "Surface":
                    continue
                if ability_name == "Backstab" and not target.incapacitated():
                    continue
                if skill.weapon and self.is_disarmed():
                    continue
                if ability_name == "Smoke Screen":
                    steal_ready = bool(
                        self.status_effects.get("Steal Success", StatusEffect()).active
                    )
                    if (
                        not steal_ready
                        and self.health.current > self.health.max * ENEMY_LOW_HEALTH_THRESHOLD
                    ):
                        continue
                if ability_name == "Tunnel" and (
                    self.health.current > self.health.max * ENEMY_LOW_HEALTH_THRESHOLD
                    or self.tunnel
                ):
                    # Don't use Tunnel if health is above 25% OR if already tunneled
                    continue
                if ability_name == "Disarm" and not self._target_has_weapon(target):
                    continue
                action_type = "Use Skill"
                usable = True
            else:
                usable = False

            if not usable:
                continue

            # Weight by priority: HIGH=3, NORMAL=2, LOW=1
            weight = self._priority_to_weight(priority)

            # Add action to weighted pool proportional to priority weight
            for _ in range(weight):
                resolved_entry = dict(action_entry)
                resolved_entry["priority"] = priority
                weighted_actions.append((action_type, ability_name, resolved_entry))

        # If no weighted actions available, fall back to standard options() logic
        if not weighted_actions:
            return self._fallback_action_selection(target, tile)

        # Choose from weighted pool (higher priority = more copies in pool = higher selection chance)
        action_type, ability_name, action_entry = random.choice(weighted_actions)
        self.last_action_stack_entry = action_entry
        if ability_name in self.single_use_abilities:
            self._used_single_use_abilities.add(ability_name)
        self._advance_debuff_failure_cooldowns()
        return action_type, ability_name

    def _is_full_health(self) -> bool:
        """Return whether an enemy has no missing health to restore."""
        return self.health.current >= self.health.max

    @staticmethod
    def _is_regen_spell(spell) -> bool:
        """Recognize the recurring self-heal that remains a low-priority setup."""
        return str(getattr(spell, "name", "")).strip().lower().startswith("regen")

    def _should_skip_full_health_heal(self, spell) -> bool:
        """Avoid spending a direct healing spell when it cannot restore health."""
        return (
            self._is_full_health()
            and getattr(spell, "subtyp", None) == "Heal"
            and not self._is_regen_spell(spell)
        )

    def _pickup_weapon_priority(self) -> ActionPriority:
        """Classify how urgently this enemy should recover from Disarm."""
        if not self.is_disarmed():
            return ActionPriority.SKIP

        skills = [
            skill
            for skill in self.spellbook.get("Skills", {}).values()
            if not getattr(skill, "passive", False)
        ]
        spells = [
            spell
            for spell in self.spellbook.get("Spells", {}).values()
            if not getattr(spell, "passive", False)
            and getattr(spell, "cost", 0) <= self.mana.current
        ]
        weapon_skills = [skill for skill in skills if getattr(skill, "weapon", False)]

        if weapon_skills or not spells:
            return ActionPriority.HIGH
        if len(spells) >= 2 and not weapon_skills:
            return ActionPriority.LOW
        return ActionPriority.NORMAL

    def _fallback_action_selection(self, target: Character, tile: object) -> tuple[str, str | None]:
        """Fallback to standard random action selection if action_stack can't be used."""
        self.last_action_stack_entry = None
        if self.name != "Test" and not self.tunnel:
            action_list = ["Attack"]
        else:
            action_list = []

        spell_list = []
        skill_list = []

        if not self.abilities_suppressed():
            for spell_name, spell in self.spellbook["Spells"].items():
                if (
                    spell_name in self.single_use_abilities
                    and spell_name in self._used_single_use_abilities
                ):
                    continue
                if self.spellbook["Spells"][spell_name].passive:
                    continue
                if self._should_skip_reapply_debuff(spell_name, target):
                    continue
                if self.tunnel:
                    if spell.subtyp not in ["Heal", "Support"]:
                        continue
                if self.spellbook["Spells"][spell_name].cost <= self.mana.current:
                    spell_list.append(spell_name)
            if spell_list:
                action_list.append("Cast Spell")

            for skill_name, _ in self.spellbook["Skills"].items():
                if (
                    skill_name in self.single_use_abilities
                    and skill_name in self._used_single_use_abilities
                ):
                    continue
                if any(
                    [
                        self.spellbook["Skills"][skill_name].passive,
                        self.spellbook["Skills"][skill_name].name == "Backstab"
                        and not target.incapacitated(),
                        self.spellbook["Skills"][skill_name].weapon and self.is_disarmed(),
                        self.spellbook["Skills"][skill_name].name == "Smoke Screen"
                        and self.health.current > self.health.max * ENEMY_LOW_HEALTH_THRESHOLD
                        and not self.status_effects.get("Steal Success", StatusEffect()).active,
                        self.tunnel,
                    ]
                ):
                    continue
                if self._should_skip_reapply_debuff(skill_name, target):
                    continue
                if self.spellbook["Skills"][skill_name].cost <= self.mana.current:
                    skill_list.append(skill_name)
            if skill_list:
                action_list.append("Use Skill")
        item_list = self._combat_item_choices()
        if item_list:
            action_list.append("Use Item")

        if self.is_disarmed():
            action_list.append("Pickup Weapon")
        if self.tunnel:
            action_list.extend(["Surface", "Nothing"])
        if self._should_attempt_flee(target, tile):
            action_list.append("Flee")

        action = random.choice(action_list) if action_list else "Attack"
        ability = None

        if action == "Cast Spell" and spell_list:
            ability = random.choice(spell_list)
        elif action == "Use Skill" and skill_list:
            ability = random.choice(skill_list)
        elif action == "Use Item" and item_list:
            ability = random.choice(item_list)
        if ability in self.single_use_abilities:
            self._used_single_use_abilities.add(ability)
        self._advance_debuff_failure_cooldowns()

        return action, ability

    def _should_attempt_flee(self, target: Character, tile: object) -> bool:
        """Return whether an ordinary enemy is frightened by a superior class."""
        if (
            target.level.pro_level * target.level.level < 10
            or target.level.pro_level <= self.level.pro_level
            or "Boss" in str(tile)
            or self.name == "Mimic"
            or getattr(self, "scripted_combat_enemy", False)
        ):
            return False
        difference = max(0, target.level.pro_level - self.level.pro_level)
        return bool(random.randint(0, difference))

    def _combat_item_choices(self) -> list[str]:
        """Return inventory item keys that are useful for this enemy in combat."""
        choices = []
        for item_name, entries in self.inventory.items():
            if not entries:
                continue
            item = entries[0]() if isinstance(entries[0], type) else entries[0]
            if not isinstance(item, items.Potion):
                continue
            if item.subtyp == "Health" and self.health.current < self.health.max:
                choices.append(item_name)
            elif item.subtyp == "Mana" and self.mana.current < self.mana.max:
                choices.append(item_name)
            elif item.subtyp in {"Elixir", "Both"} and (
                self.health.current < self.health.max or self.mana.current < self.mana.max
            ):
                choices.append(item_name)
        return choices

    def get_last_action_metadata(self) -> dict[str, object]:
        """Return metadata from the last selected action_stack entry."""
        entry = self.last_action_stack_entry or {}
        try:
            delay = max(0, int(entry.get("delay", 0) or 0))
        except (TypeError, ValueError):
            delay = 0
        return {
            "ability": entry.get("ability"),
            "priority": entry.get("priority"),
            "delay": delay,
            "telegraph": entry.get("telegraph"),
            "from_action_stack": bool(entry),
        }

    def _resolve_priority_condition(
        self, condition: dict, fallback_priority: ActionPriority, target: Character, tile: object
    ) -> ActionPriority:
        """
        Resolve action_stack priority conditions.

        Supports two formats:
        1) Dict format (legacy/new): {"target_has_weapon": True, "priority": HIGH, "else": SKIP}
        2) List format (newer): [{"condition": "self_hp_pct_lt", "value": 0.5, "priority": HIGH}, ...]
        """

        def _pct_threshold(val: object) -> float | None:
            """
            Convert a % or ratio threshold into a 0..1 float.

            Accepts:
            - 0.25, "0.25" (ratio)
            - 25, "25" (percent)
            """
            try:
                thr = float(val)
            except (TypeError, ValueError):
                return None
            if thr < 0:
                return None
            # Treat values > 1 as percentages (e.g., 50 => 0.5).
            if thr > 1.0:
                thr = thr / 100.0
            return thr

        def _effect_active(ch: Character, effect_name: str) -> tuple[bool, StatusEffect]:
            """
            Check for an effect name across all common effect dictionaries.

            This intentionally supports action_stack configs that refer to
            magic effects like "Regen" using "self_status"/"target_status".
            """
            for bucket_name in (
                "status_effects",
                "physical_effects",
                "magic_effects",
                "class_effects",
                "stat_effects",
            ):
                bucket = getattr(ch, bucket_name, None)
                if isinstance(bucket, dict) and effect_name in bucket:
                    eff = bucket.get(effect_name, StatusEffect())
                    return bool(getattr(eff, "active", False)), eff
            return False, StatusEffect()

        def _has_positive_stat_effect(ch: Character) -> bool:
            stat_effects = getattr(ch, "stat_effects", {})
            if not isinstance(stat_effects, dict):
                return False
            return any(
                bool(getattr(effect, "active", False)) and getattr(effect, "extra", 0) > 0
                for effect in stat_effects.values()
            )

        def _matches_list_rule(cond: str, value: object) -> bool:
            """
            Evaluate a single list-style rule ("condition"/"value").

            Conditions supported are the same set as the dict-style keys.
            """
            if cond == "tunneled":
                desired = bool(value)
                return bool(getattr(self, "tunnel", False)) == desired
            if cond == "target_status":
                active, _eff = _effect_active(target, str(value))
                return active
            if cond == "self_status":
                active, _eff = _effect_active(self, str(value))
                return active
            if cond == "target_incapacitated":
                desired = bool(value)
                return bool(target.incapacitated()) == desired
            if cond == "target_has_weapon":
                desired = bool(value)
                return bool(self._target_has_weapon(target)) == desired
            if cond == "target_has_mana":
                desired = bool(value)
                has_mana = hasattr(target, "mana") and target.mana.current > 0
                return bool(has_mana) == desired
            if cond == "target_has_positive_effects":
                desired = bool(value)
                stat_effects = getattr(target, "stat_effects", {})
                magic_effects = getattr(target, "magic_effects", {})
                has_pos = any(bool(effect.active) for effect in stat_effects.values()) or any(
                    bool(effect.active) for effect in magic_effects.values()
                )
                return bool(has_pos) == desired
            if cond == "target_has_positive_stat_effects":
                desired = bool(value)
                return _has_positive_stat_effect(target) == desired
            if cond == "self_hp_pct_lt":
                threshold = _pct_threshold(value)
                if threshold is None:
                    return False
                return bool(self.health.max) and (self.health.current / self.health.max) < threshold
            if cond == "self_mana_pct_lt":
                threshold = _pct_threshold(value)
                if threshold is None:
                    return False
                return (
                    bool(getattr(self, "mana", None) and self.mana.max)
                    and (self.mana.current / self.mana.max) < threshold
                )
            if cond == "self_stat":
                stat_effects = getattr(self, "stat_effects", {})
                return bool(stat_effects.get(str(value), StatusEffect()).active)
            if cond == "self_stat_any":
                stat_effects = getattr(self, "stat_effects", {})
                if not isinstance(value, (list, tuple)):
                    return False
                return any(
                    bool(stat_effects.get(str(stat_name), StatusEffect()).active)
                    for stat_name in value
                )
            return False

        if isinstance(condition, list):
            for rule in condition:
                if not isinstance(rule, dict):
                    continue
                cond = rule.get("condition")
                if not cond:
                    continue
                if _matches_list_rule(str(cond), rule.get("value")):
                    return rule.get("priority", fallback_priority)
                if "else" in rule:
                    return rule.get("else", fallback_priority)
            return fallback_priority

        if not isinstance(condition, dict):
            return fallback_priority

        if condition.get("tunneled") is not None:
            desired = bool(condition.get("tunneled"))
            is_tunneled = bool(getattr(self, "tunnel", False))
            if is_tunneled == desired:
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        target_status = condition.get("target_status")
        if target_status:
            is_active, _eff = _effect_active(target, str(target_status))
            if is_active:
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        if condition.get("target_incapacitated") is not None:
            is_incapacitated = target.incapacitated()
            if is_incapacitated:
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        if condition.get("target_has_weapon") is not None:
            has_weapon = self._target_has_weapon(target)
            if has_weapon:
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        if condition.get("target_has_mana") is not None:
            has_mana = hasattr(target, "mana") and target.mana.current > 0
            if has_mana:
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        if condition.get("target_has_positive_effects") is not None:
            # Check for active positive effects (stat buffs or magic buffs)
            stat_effects = getattr(target, "stat_effects", {})
            magic_effects = getattr(target, "magic_effects", {})
            has_positive_effects = any(
                bool(effect.active) for effect in stat_effects.values()
            ) or any(bool(effect.active) for effect in magic_effects.values())
            if has_positive_effects:
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        if condition.get("target_has_positive_stat_effects") is not None:
            has_positive_stat_effects = _has_positive_stat_effect(target)
            if has_positive_stat_effects:
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        self_hp_pct_lt = condition.get("self_hp_pct_lt")
        if self_hp_pct_lt is not None:
            threshold = _pct_threshold(self_hp_pct_lt)
            if threshold is None:
                return fallback_priority
            if self.health.max and (self.health.current / self.health.max) < threshold:
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        self_mana_pct_lt = condition.get("self_mana_pct_lt")
        if self_mana_pct_lt is not None:
            threshold = _pct_threshold(self_mana_pct_lt)
            if threshold is None:
                return fallback_priority
            if (
                hasattr(self, "mana")
                and self.mana.max
                and (self.mana.current / self.mana.max) < threshold
            ):
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        self_status = condition.get("self_status")
        if self_status:
            is_active, _eff = _effect_active(self, str(self_status))
            if is_active:
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        self_stat = condition.get("self_stat")
        if self_stat:
            stat_effects = getattr(self, "stat_effects", {})
            is_active = bool(stat_effects.get(self_stat, StatusEffect()).active)
            if is_active:
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        self_stat_any = condition.get("self_stat_any")
        if self_stat_any:
            stat_effects = getattr(self, "stat_effects", {})
            is_active = any(
                bool(stat_effects.get(stat_name, StatusEffect()).active)
                for stat_name in self_stat_any
            )
            if is_active:
                return condition.get("priority", fallback_priority)
            return condition.get("else", fallback_priority)

        return fallback_priority

    def _resolve_ai_priority(self, priority: ActionPriority, action_entry: dict) -> ActionPriority:
        """Resolve AI-only priority modes into selectable priority weights."""
        if priority != ActionPriority.LOW_HP_ONLY:
            return priority

        threshold = action_entry.get("hp_threshold", action_entry.get("self_hp_pct_lt", 0.5))
        try:
            threshold_value = float(threshold)
        except (TypeError, ValueError):
            threshold_value = 0.5
        if threshold_value > 1.0:
            threshold_value /= 100.0

        if self.health.max and (self.health.current / self.health.max) < threshold_value:
            return action_entry.get("low_hp_priority", ActionPriority.HIGH)
        return action_entry.get("else", ActionPriority.SKIP)

    def _should_skip_reapply_debuff(self, ability_name: str, target: Character | None) -> bool:
        if target is None:
            return False
        rule = self._DEBUFF_REAPPLY_RULES.get(ability_name)
        if not rule:
            return False
        if self._debuff_failure_cooldowns.get(ability_name, 0) > 0:
            return True

        status_name = rule.get("status")
        if status_name:
            status_effects = getattr(target, "status_effects", {})
            eff = status_effects.get(status_name, StatusEffect())
            # Special-case Stun: "extra" is used as a short post-stun immunity window.
            if status_name == "Stun":
                return bool(eff.active) or bool(getattr(eff, "extra", 0) > 0)
            return bool(eff.active)

        physical_name = rule.get("physical")
        if physical_name:
            physical_effects = getattr(target, "physical_effects", {})
            return bool(physical_effects.get(physical_name, StatusEffect()).active)

        stat_all = rule.get("stat_all")
        if stat_all:
            stat_effects = getattr(target, "stat_effects", {})
            return all(
                bool(stat_effects.get(stat_name, StatusEffect()).active) for stat_name in stat_all
            )

        return False

    def record_debuff_failure(self, ability_name: str, turns: int = 2) -> None:
        """Temporarily suppress a debuff that failed to affect its target."""
        if ability_name not in self._DEBUFF_REAPPLY_RULES:
            return
        self._debuff_failure_cooldowns[ability_name] = max(
            self._debuff_failure_cooldowns.get(ability_name, 0),
            max(0, int(turns)),
        )

    def _advance_debuff_failure_cooldowns(self) -> None:
        if not self._debuff_failure_cooldowns:
            return
        for ability_name in list(self._debuff_failure_cooldowns):
            remaining = self._debuff_failure_cooldowns[ability_name] - 1
            if remaining <= 0:
                del self._debuff_failure_cooldowns[ability_name]
            else:
                self._debuff_failure_cooldowns[ability_name] = remaining

    def _target_has_weapon(self, target: Character) -> bool:
        is_disarmed = getattr(target, "is_disarmed", None)
        if callable(is_disarmed) and is_disarmed():
            return False
        equipment = getattr(target, "equipment", {})
        weapon = equipment.get("Weapon") if isinstance(equipment, dict) else None
        if weapon is None:
            return False
        return not isinstance(weapon, items.NoWeapon)

    @staticmethod
    def _priority_to_weight(priority: ActionPriority) -> int:
        """Convert ActionPriority enum to selection weight (HIGH=3, NORMAL=2, LOW=1)."""
        if priority == ActionPriority.HIGH:
            return 3
        elif priority == ActionPriority.LOW:
            return 1
        elif priority == ActionPriority.SKIP:
            return 0
        else:  # NORMAL, VERY_HIGH, VERY_LOW, etc. default to 2
            return 2


class Misc(Enemy):
    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Misc"


class Slime(Enemy):
    """
    Slime type; resistance against all attack magic types; weak against physical damage
    """

    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Slime"
        self.resistance["Fire"] = 0.75
        self.resistance["Ice"] = 0.75
        self.resistance["Electric"] = 0.75
        self.resistance["Water"] = 0.75
        self.resistance["Earth"] = 0.75
        self.resistance["Wind"] = 0.75
        self.resistance["Shadow"] = 0.75
        self.resistance["Holy"] = 0.75
        self.resistance["Physical"] = -0.5
        self.picture = "slime.txt"


class Animal(Enemy):
    """
    Animal type; no special features
    """

    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Animal"
        self.inventory["Mystery Meat"] = [items.MysteryMeat]


class Humanoid(Enemy):
    """
    Humanoid type; no special features
    """

    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Humanoid"


class Fey(Enemy):
    """
    Fey type; resistance against shadow damage
    """

    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Fey"
        self.resistance["Shadow"] = 0.25


class Fiend(Enemy):
    """
    Fiend type; resistance against shadow damage and weak against holy; immune to death
    """

    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Fiend"
        self.resistance["Shadow"] = 0.25
        self.resistance["Holy"] = -0.25
        self.status_immunity = ["Death"]


class Undead(Enemy):
    """
    Undead type; resistance against shadow and poison and weak against fire; very weak against holy and immune to death
    """

    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Undead"
        self.resistance["Fire"] = -0.25
        self.resistance["Shadow"] = 0.5
        self.resistance["Holy"] = -0.75
        self.resistance["Poison"] = 0.5
        self.status_immunity = ["Death"]


class Elemental(Enemy):
    """
    Elemental type; high resistance against physical damage
    """

    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Elemental"
        self.resistance["Physical"] = 0.25


class Dragon(Enemy):
    """
    Dragon type; resistance against elemental and immune to death magic types; mild resistance against physical
    """

    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Dragon"
        self.resistance["Fire"] = 0.25
        self.resistance["Ice"] = 0.25
        self.resistance["Electric"] = 0.25
        self.resistance["Water"] = 0.25
        self.resistance["Earth"] = 0.25
        self.resistance["Wind"] = 0.25
        self.resistance["Physical"] = 0.1
        self.status_immunity = ["Death", "Stone"]
        self.inventory["Dragon's Tear"] = [items.DragonTear]


class Monster(Enemy):
    """
    Monster type; no special resistances
    """

    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Monster"


class Aberration(Enemy):
    """
    Aberration type; no special resistances
    """

    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Aberration"


class Construct(Enemy):
    """
    Construct type: immune to death, stone, and poison, strong against physical
    """

    def __init__(
        self,
        name,
        health,
        mana,
        strength,
        intel,
        wisdom,
        con,
        charisma,
        dex,
        attack,
        defense,
        magic,
        magic_def,
        exp,
    ):
        super().__init__(
            name,
            health,
            mana,
            strength,
            intel,
            wisdom,
            con,
            charisma,
            dex,
            attack,
            defense,
            magic,
            magic_def,
            exp,
        )
        self.enemy_typ = "Construct"
        self.resistance["Poison"] = 1.0
        self.resistance["Physical"] = 0.5
        self.status_immunity = ["Poison", "Death", "Stone"]
