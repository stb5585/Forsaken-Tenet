"""Advanced and bespoke ability effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Effect

if TYPE_CHECKING:
    from ..character import Character
    from ..combat.combat_result import CombatResult


class DoublecastEffect(Effect):
    """Cast multiple spells from the user's spellbook in a single turn.

    Used by Doublecast (cast_count=2) and Triplecast (cast_count=3).

    Parameters (YAML):
        cast_count (int): Number of spells to cast (default 2).
        exclude_spells (list[str]): Spell names to exclude (default ["Magic Missile"]).
        ability_cost (int): The parent ability's mana cost, used for refund logic
            when no affordable spells are available.

    The UI may pass a ``spell_selector`` callback via ``use_kwargs``.  When
    present it is called as ``spell_selector(user, spell_list, cast_index)``
    returning the chosen spell key.  Without it a random spell is picked.
    """

    def __init__(
        self, cast_count: int = 2, exclude_spells: list[str] | None = None, ability_cost: int = 0
    ):
        super().__init__()
        self.cast_count = cast_count
        self.exclude_spells = exclude_spells or ["Magic Missile"]
        self.ability_cost = ability_cost

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        use_kw = result.extra.get("use_kwargs", {})
        spell_selector = use_kw.get("spell_selector")
        cover = result.extra.get("cover", False)

        j = 0
        while j < self.cast_count:
            spell_list = []
            for entry in actor.spellbook.get("Spells", {}):
                spell_obj = actor.spellbook["Spells"][entry]
                if (
                    spell_obj.cost <= actor.mana.current
                    and spell_obj.name not in self.exclude_spells
                ):
                    if actor.cls != actor:
                        spell_list.append(f"{entry}  {spell_obj.cost}")
                    else:
                        spell_list.append(str(entry))
            if len(spell_list) == 0:
                messages.append(
                    f"{actor.name} does not have enough mana to cast any"
                    f" spells with {result.action}.\n"
                )
                actor.mana.current += self.ability_cost
                break
            # UI-agnostic spell selection
            if spell_selector is not None:
                spell_key = spell_selector(actor, spell_list, j)
                spell_key = spell_key.rsplit("  ", 1)[0]
            else:
                spell_key = _rng.choice([s.rsplit("  ", 1)[0] for s in spell_list])
            spell = actor.spellbook["Spells"][spell_key]
            cast_message = spell.cast(actor, target=target, cover=cover)
            messages.append(str(cast_message))
            j += 1
            if not target.is_alive():
                break


class ChooseFateEffect(Effect):
    """Let the player choose the Devil's action for the turn.

    Presents three options (Attack / Hellfire / Crush) via a
    ``selection_callback`` passed through ``use_kwargs``.

    - *Attack*: weapon damage with ``dmg_mod``, user's ``damage_mod`` increases.
    - *Hellfire*: user's ``spell_mod`` increases, casts Hellfire on target.
    - *Crush*: uses Crush on target, both mods decrease.

    Parameters (YAML):
        dmg_mod (float): Weapon damage multiplier for Attack (default 1.5).
    """

    def __init__(self, dmg_mod: float = 1.5):
        super().__init__()
        self.dmg_mod = dmg_mod

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        use_kw = result.extra.get("use_kwargs", {})
        selection_callback = use_kw.get("selection_callback")

        choose_message = "I'm bored, you choose."
        options = ["Attack", "Hellfire", "Crush"]
        if selection_callback is not None:
            option_index = selection_callback(choose_message, options)
        else:
            option_index = _rng.randint(0, len(options) - 1)

        mod_up = _rng.randint(10, 25)
        if options[option_index] == "Attack":
            wd_str, _, _ = actor.weapon_damage(target, dmg_mod=self.dmg_mod, use_offhand=False)
            messages.append(wd_str)
            actor.damage_mod += mod_up
            messages.append("Hahaha, my power increases!\n")
        elif options[option_index] == "Hellfire":
            from src.core.abilities import Hellfire

            actor.spell_mod += mod_up
            cast_msg = Hellfire().cast(actor, target=target)
            messages.append(str(cast_msg))
            messages.append("The devastation will only get worse from here.\n")
        elif options[option_index] == "Crush":
            from src.core.abilities import Crush

            use_msg = Crush().use(actor, target)
            messages.append(str(use_msg))
            mod_down = _rng.randint(0, 10)
            if actor.damage_mod > 0:
                actor.damage_mod -= mod_down
            if actor.spell_mod > 0:
                actor.spell_mod -= mod_down
            messages.append("Interesting choice...maybe I'll show pity.\n")


class VesperionChooseFateEffect(Effect):
    """Vesperion's phase-aware choice pressure.

    Unlike the legacy Devil version, this effect does not present a taunt or
    fixed attack menu. It asks the player to choose which consequence of
    Voluntas they will bear: pain, loss, or control.
    """

    PHASE_OPTIONS = {
        1: (
            ("Bear the Wound", "damage", 0.10, 0, 0, "Hexagonum"),
            ("Spend the Breath", "resource", 0, 0.22, 0, "Luna"),
            ("Accept Stillness", "control", 0, 0, 1, "Quadrata"),
        ),
        2: (
            ("Carry the Hurt", "damage", 0.16, 0, 0, "Infinitas"),
            ("Lose the Voice", "resource", 0, 0.34, 0, "Polaris"),
            ("Yield the Moment", "control", 0, 0, 2, "Quadrata"),
        ),
        3: (
            ("Suffer and Stand", "damage", 0.22, 0, 0, "Infinitas"),
            ("Empty the Self", "resource", 0, 0.46, 0, "Luna"),
            ("Be Written Over", "control", 0, 0, 3, "Triangulus"),
        ),
    }

    PHASE_MESSAGES = {
        1: "Choice made the wound. Choose which mercy remains.",
        2: "If Voluntas is sacred, choose the shape of its suffering.",
        3: "Choose, champion. Prove the will you would preserve.",
    }

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        messages = result.extra.setdefault("messages", [])
        use_kw = result.extra.get("use_kwargs", {})
        selection_callback = use_kw.get("selection_callback")
        phase = self._phase(actor)
        options = self.PHASE_OPTIONS[phase]
        labels = [option[0] for option in options]

        if selection_callback is not None:
            option_index = selection_callback(self.PHASE_MESSAGES[phase], labels)
        else:
            import random as _rng

            option_index = _rng.randint(0, len(options) - 1)
        option_index = max(0, min(int(option_index), len(options) - 1))

        label, consequence, damage_fraction, mana_fraction, control_duration, counter_guardian = (
            options[option_index]
        )
        counter_active = self._guardian_counter_active(target, counter_guardian)
        result.extra["vesperion_phase"] = phase
        result.extra["vesperion_choice"] = label
        result.extra["vesperion_consequence"] = consequence
        result.extra["vesperion_counter_guardian"] = counter_guardian
        result.extra["vesperion_counter_active"] = counter_active

        messages.append(f"Vesperion offers a terrible choice: {label}.\n")
        if counter_active:
            messages.append(
                f"{counter_guardian} answers the Evening Star and blunts the consequence.\n"
            )
        if consequence == "damage":
            effective_fraction = damage_fraction * (0.35 if counter_active else 1)
            damage = max(1, int(target.health.max * effective_fraction))
            target.health.current -= damage
            result.damage = (result.damage or 0) + damage
            messages.append(f"{target.name} bears {damage} radiant damage by choice.\n")
        elif consequence == "resource":
            effective_fraction = mana_fraction * (0.35 if counter_active else 1)
            mana_loss = max(0, min(target.mana.current, int(target.mana.max * effective_fraction)))
            target.mana.current -= mana_loss
            messages.append(f"{target.name}'s will burns away {mana_loss} MP.\n")
        elif consequence == "control":
            if counter_active:
                control_duration = 0
            effect = target.status_effects.get("Silence")
            if control_duration <= 0:
                messages.append(f"{target.name} keeps hold of choice through the silence.\n")
            elif effect is not None and "Silence" not in getattr(target, "status_immunity", []):
                effect.active = True
                effect.duration = max(getattr(effect, "duration", 0), control_duration)
                result.effects_applied["Status"].append("Silence")
                messages.append(f"{target.name}'s voice is sealed by twilight command.\n")
            else:
                messages.append(f"{target.name} resists the silence of the Evening Star.\n")

    @staticmethod
    def _guardian_counter_active(target: Character, guardian: str) -> bool:
        story_state = getattr(target, "main_story", {})
        completed = (
            story_state.get("guardian_trials_completed", {})
            if isinstance(story_state, dict)
            else {}
        )
        return isinstance(completed, dict) and bool(completed.get(guardian))

    def _phase(self, actor: Character) -> int:
        phase_getter = getattr(actor, "vesperion_phase", None)
        if callable(phase_getter):
            try:
                return max(1, min(int(phase_getter()), 3))
            except Exception:
                pass
        explicit_phase = getattr(actor, "phase", None)
        if explicit_phase is not None:
            try:
                return max(1, min(int(explicit_phase), 3))
            except Exception:
                pass
        if getattr(actor, "health", None) and actor.health.max:
            hp_pct = actor.health.current / actor.health.max
            if hp_pct <= 0.33:
                return 3
            if hp_pct <= 0.66:
                return 2
        return 1


class ShapeshiftEffect(Effect):
    """Transform the user into a random creature from their transform list.

    Copies all stats, equipment, spellbook, resistances, etc. from the
    chosen creature.  Re-adds Shapeshift to the new spellbook and applies
    a ``Shapeshifted`` status cooldown.

    This effect expects ``self_target: true`` in the YAML so that both
    *actor* and *target* refer to the shapeshifting entity.

    Parameters (YAML):
        status_name (str): Cooldown status to apply (default "Shapeshifted").
        status_duration (int): Duration of cooldown in turns (default 3).
    """

    def __init__(self, status_name: str = "Shapeshifted", status_duration: int = 3):
        super().__init__()
        self.status_name = status_name
        self.status_duration = status_duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        from src.core.enemies.identity import remember_defeat_identity

        # With self_target the effect_target == actor (the shapeshifter)
        user = target
        messages = result.extra.setdefault("messages", [])
        if getattr(user, "shapeshift_suppressed", False):
            messages.append(f"Moonlight prevents {user.name} from shapeshifting.\n")
            return
        remember_defeat_identity(user)

        if not isinstance(getattr(user, "_shapeshift_original_state", None), dict):
            user._shapeshift_original_state = {
                "cls": user.cls,
                "stats": user.stats,
                "equipment": user.equipment,
                "spellbook": user.spellbook,
                "resistance": user.resistance,
                "flying": user.flying,
                "invisible": user.invisible,
                "sight": user.sight,
                "name": user.name,
                "picture": getattr(user, "picture", None),
            }

        while True:
            s_creature = _rng.choice(user.transform)()
            if user.cls.name != s_creature.cls.name:
                break

        old_name = user.name
        user.cls = s_creature.cls
        user.stats = s_creature.stats
        user.equipment = s_creature.equipment
        user.spellbook = s_creature.spellbook
        user.resistance = s_creature.resistance
        user.flying = s_creature.flying
        user.invisible = s_creature.invisible
        user.sight = s_creature.sight
        user.name = s_creature.name
        user.picture = s_creature.picture

        # Re-add Shapeshift to new spellbook
        from src.core.abilities import Shapeshift as ShapeshiftAbility

        user.spellbook["Skills"]["Shapeshift"] = ShapeshiftAbility()

        # Apply cooldown status
        user.status_effects[self.status_name].active = True
        user.status_effects[self.status_name].duration = self.status_duration
        try:
            user._emit_status_event(
                user,
                self.status_name,
                applied=True,
                duration=self.status_duration,
                source="Shapeshift",
            )
        except Exception:
            pass

        messages.append(f"{old_name} changes shape, becoming a {s_creature.name}.\n")


class AstralJudgmentEffect(Effect):
    """Resolve the active Astromancer sign, apply its rider, then spin signs."""

    def __init__(self, damage_mod: float = 3.0, rider_duration: int = 2):
        super().__init__()
        self.damage_mod = damage_mod
        self.rider_duration = rider_duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        from src.core.classes import astromancer
        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])
        sign = astromancer.active_constellation(actor)
        element = astromancer.SIGN_TO_ELEMENT.get(sign, "Non-elemental")
        messages.append(f"{actor.name} calls {sign}'s Astral Judgment.\n")

        base = int(actor.stats.intel * self.damage_mod)
        variance = _rng.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        if sign == "Ember":
            floor = DAMAGE_VARIANCE_LOW + ((DAMAGE_VARIANCE_HIGH - DAMAGE_VARIANCE_LOW) * 0.75)
            variance = max(variance, floor)
        damage = int(base * variance)
        hit, def_msg, damage = target.handle_defenses(actor, damage, typ="Magic")
        if def_msg:
            messages.append(def_msg)
        if hit:
            _, red_msg, damage = target.damage_reduction(damage, actor, typ=element)
            if red_msg:
                messages.append(red_msg)
            if damage > 0:
                target.health.current -= damage
                result.damage = (result.damage or 0) + damage
                result.hit = True
                actor._emit_damage_event(target, damage, damage_type=element, is_critical=False)
                messages.append(f"{target.name} takes {damage} {element} damage.\n")
            else:
                messages.append("The judgment was ineffective and does no damage.\n")
        else:
            messages.append(f"The judgment misses {target.name}.\n")

        if sign == "Tide":
            heal = max(1, int(actor.health.max * 0.20))
            before = actor.health.current
            actor.health.current = min(actor.health.max, actor.health.current + heal)
            healed = actor.health.current - before
            actor.stat_effects["Magic Defense"].active = True
            actor.stat_effects["Magic Defense"].duration = max(
                self.rider_duration,
                actor.stat_effects["Magic Defense"].duration,
            )
            actor.stat_effects["Magic Defense"].extra = max(
                actor.stat_effects["Magic Defense"].extra,
                max(1, actor.stats.wisdom // 2),
            )
            messages.append(f"Tide wards {actor.name}, restoring {healed} health.\n")
        elif sign == "Gale":
            actor.stat_effects["Speed"].active = True
            actor.stat_effects["Speed"].duration = max(
                self.rider_duration,
                actor.stat_effects["Speed"].duration,
            )
            actor.stat_effects["Speed"].extra = max(
                actor.stat_effects["Speed"].extra,
                max(1, actor.stats.dex // 2),
            )
            messages.append(f"Gale bends the next exchanges around {actor.name}.\n")
        elif sign == "Stone":
            for stat_name in ("Defense", "Magic Defense"):
                target.stat_effects[stat_name].active = True
                target.stat_effects[stat_name].duration = max(
                    self.rider_duration,
                    target.stat_effects[stat_name].duration,
                )
                target.stat_effects[stat_name].extra = min(
                    target.stat_effects[stat_name].extra,
                    -max(1, actor.stats.intel // 3),
                )
            messages.append(f"Stone fractures {target.name}'s defenses.\n")

        next_sign = astromancer.spin_constellation(actor)
        messages.append(f"The constellation wheel turns to {next_sign}.\n")


class ConsumeItemEffect(Effect):
    """Steal a random item from the target and consume it for a status effect.

    Performs a speed+luck contest.  On success, steals a random inventory
    item, removes it, and applies an effect based on item type:
      Weapon → Attack buff, Armor → Defense buff, OffHand/Tome → Magic buff,
      OffHand/other → Magic Defense buff, Accessory/Ring → random Attack/Defense,
      Accessory/other → random Magic/MagicDefense, Potion → Regen or Poison,
      else → random status (Berserk/Blind/Doom/Silence/Sleep/Stun).
    If the target has no items, steal gold and heal the user instead.

    Parameters (YAML):  (none - behaviour is fully self-contained)
    """

    def __init__(self, **_kw):
        super().__init__()

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        if target is None:
            return
        if any([target.magic_effects["Ice Block"].active, getattr(target, "tunnel", False)]):
            messages.append("It has no effect.\n")
            return

        u_chance = actor.check_mod("luck", enemy=target, luck_factor=10)
        t_chance = target.check_mod("luck", enemy=actor, luck_factor=10)

        if (
            _rng.randint(0, actor.check_mod("speed", enemy=actor)) + u_chance
            > _rng.randint(0, target.check_mod("speed", enemy=actor)) + t_chance
        ):
            if len(target.inventory) != 0 and _rng.randint(0, u_chance):
                item_key = _rng.choice(list(target.inventory))
                item = target.inventory[item_key][0]
                target.modify_inventory(item, subtract=True)
                messages.append(
                    f"{actor.name} steals {item_key} from {target.name} and consumes it.\n"
                )
                duration = max(1, int(1 / item.rarity))
                amount = max(1, int(2 / item.rarity))

                if item.typ == "Weapon":
                    effect = "Attack"
                elif item.typ == "Armor":
                    effect = "Defense"
                elif item.typ == "OffHand":
                    effect = "Magic" if item.subtyp == "Tome" else "Magic Defense"
                elif item.typ == "Accessory":
                    effect = (
                        _rng.choice(["Attack", "Defense"])
                        if item.subtyp == "Ring"
                        else _rng.choice(["Magic", "Magic Defense"])
                    )
                elif item.typ == "Potion":
                    effect = "Regen" if item.subtyp != "Stat" else "Poison"
                else:
                    effect = _rng.choice(["Berserk", "Blind", "Doom", "Silence", "Sleep", "Stun"])

                # Immunity check
                status_effects = ["Berserk", "Blind", "Doom", "Poison", "Silence", "Sleep", "Stun"]
                if any(
                    [
                        effect in actor.status_immunity,
                        f"Status-{effect}" in actor.equipment["Pendant"].mod,
                        "Status-All" in actor.equipment["Pendant"].mod and effect in status_effects,
                    ]
                ):
                    messages.append(f"{actor.name} is immune to {effect.lower()}.\n")
                else:
                    messages.append(f"{actor.name} is affected by {effect.lower()}.\n")
                    effect_dict = actor.effect_handler(effect)
                    effect_dict[effect].active = True
                    if effect in ["Blind", "Disarm", "Silence"]:
                        effect_dict[effect].duration = -1
                    else:
                        effect_dict[effect].duration = max(duration, effect_dict[effect].duration)
                    if effect in ["Poison", "Regen"]:
                        amount = int((actor.health.max * 0.01) * amount)
                        effect_dict[effect].extra = amount
                    if effect in actor.stat_effects:
                        combat_effect = "magic_def" if effect == "Magic Defense" else effect.lower()
                        amount *= actor.combat.__dict__[combat_effect] // 10
                        effect_dict[effect].extra = amount
                        messages.append(
                            f"{actor.name}'s {effect.lower()} is temporarily "
                            f"increased by {amount}.\n"
                        )
            else:
                gold = _rng.randint(target.gold // 100, target.gold // 50) * u_chance
                regen = gold // 10
                messages.append(
                    f"{actor.name} steals {gold} gold from {target.name} " f"and consumes it.\n"
                )
                messages.append(f"{actor.name} regains {regen} health and mana.\n")
                actor.health.current = min(actor.health.current + regen, actor.health.max)
                actor.mana.current = min(actor.mana.current + regen, actor.mana.max)
        else:
            messages.append(f"{actor.name} can't steal anything.\n")


class DestroyMetalEffect(Effect):
    """Target metal items in the enemy's inventory/equipment and destroy them.

    Searches inventory first, then equipment, for items with metal subtypes.
    Uses a luck-based chance to destroy the selected item.

    Parameters (YAML):
        metal_subtypes (list[str]): Subtypes considered "metal".
    """

    METAL_SUBTYPES_DEFAULT = [
        "Fist",
        "Dagger",
        "Club",
        "Sword",
        "Ninja Blade",
        "Longsword",
        "Battle Axe",
        "Polearm",
        "Shield",
        "Heavy",
        "Ring",
        "Pendant",
        "Key",
    ]

    def __init__(self, metal_subtypes: list[str] | None = None, **_kw):
        super().__init__()
        self.metal_subtypes = metal_subtypes or self.METAL_SUBTYPES_DEFAULT

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        if target is None:
            return

        from src.core.items import remove_equipment

        metal_items = self.metal_subtypes
        destroy_list: list = []
        destroy_loc = "inv"
        for item in [target.inventory[x][0] for x in target.inventory]:
            if item.subtyp in metal_items and not item.ultimate and item.rarity > 0:
                destroy_list.append(item)
        if len(destroy_list) == 0:
            destroy_loc = "equip"
            for item in target.equipment.values():
                if item.subtyp in metal_items and not item.ultimate and item.rarity > 0:
                    destroy_list.append(item)
        try:
            destroy_item = _rng.choice(destroy_list)
            t_chance = target.check_mod("luck", enemy=actor, luck_factor=5)
            if not _rng.randint(0, int(2 / destroy_item.rarity) + t_chance):
                if destroy_loc == "inv":
                    messages.append(
                        f"{actor.name} destroys a {destroy_item.name} out of "
                        f"{target.name}'s inventory.\n"
                    )
                    target.modify_inventory(destroy_item, subtract=True)
                elif destroy_loc == "equip":
                    if destroy_item.typ not in ["Weapon", "Accessory"]:
                        messages.append(
                            f"{actor.name} destroys {target.name}'s " f"{destroy_item.typ}.\n"
                        )
                        target.equipment[destroy_item.typ] = remove_equipment(destroy_item.typ)
                    elif destroy_item.typ == "Accessory":
                        messages.append(
                            f"{actor.name} destroys {target.name}'s " f"{destroy_item.subtyp}.\n"
                        )
                        target.equipment[destroy_item.subtyp] = remove_equipment(
                            destroy_item.subtyp
                        )
                    else:
                        if target.equipment["OffHand"] == destroy_item:
                            target.equipment["OffHand"] = remove_equipment("OffHand")
                            messages.append(
                                f"{actor.name} destroys {target.name}'s " f"offhand weapon.\n"
                            )
                        else:
                            target.equipment[destroy_item.typ] = remove_equipment(destroy_item.typ)
                            messages.append(
                                f"{actor.name} destroys {target.name}'s " f"{destroy_item.typ}.\n"
                            )
                else:
                    raise AssertionError("You shouldn't reach here.")
            else:
                messages.append(f"{actor.name} fails to destroy any items.\n")
        except IndexError:
            messages.append(f"{target.name} isn't carrying any metal items.\n")


class SlotMachineEffect(Effect):
    """Slot Machine: deal 3 cards and resolve poker-style outcomes.

    The UI may pass a ``slot_machine_callback`` via ``use_kwargs``.

    Modern outcomes: Straight Flush, Three of a Kind, Straight, Flush, Pair,
    Chance. Legacy 3-digit spins are still accepted for older callers/tests.

    Parameters (YAML):  (none - behaviour is self-contained)
    """

    HANDS = {
        "Death": ["666", "999"],
        "Trips": ["000", "111", "222", "333", "444", "555", "777", "888"],
        "Straight": [
            "012",
            "123",
            "234",
            "345",
            "456",
            "567",
            "678",
            "789",
        ],
        "Palindrome": [f"{a}{b}{a}" for a in range(10) for b in range(10) if a != b],
    }
    CARD_RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
    CARD_SUITS = ("S", "H", "D", "C")
    CARD_VALUES = {
        "A": 14,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 11,
        "Q": 12,
        "K": 13,
    }

    def __init__(self, **_kw):
        super().__init__()

    @classmethod
    def deal_card_spin(cls, rng) -> str:
        """Return a comma-separated 3-card hand from a 52-card deck."""
        deck = [f"{rank}{suit}" for suit in cls.CARD_SUITS for rank in cls.CARD_RANKS]
        return ",".join(rng.sample(deck, 3))

    @classmethod
    def parse_card_spin(cls, spin: object) -> list[tuple[str, str]] | None:
        """Parse a card spin such as ``AS,10H,QD``."""
        if not isinstance(spin, str) or "," not in spin:
            return None
        cards: list[tuple[str, str]] = []
        for raw_card in spin.split(","):
            card = raw_card.strip().upper()
            if len(card) < 2:
                return None
            rank = card[:-1]
            suit = card[-1]
            if rank not in cls.CARD_VALUES or suit not in cls.CARD_SUITS:
                return None
            cards.append((rank, suit))
        if len(cards) != 3 or len(set(cards)) != 3:
            return None
        return cards

    @classmethod
    def card_hand_label(cls, cards: list[tuple[str, str]]) -> str:
        """Return the visible poker outcome label for a 3-card Slot Machine hand."""
        ranks = [rank for rank, _suit in cards]
        suits = [suit for _rank, suit in cards]
        values = sorted(cls.CARD_VALUES[rank] for rank in ranks)
        low_ace_values = sorted(1 if rank == "A" else cls.CARD_VALUES[rank] for rank in ranks)
        flush = len(set(suits)) == 1
        straight = (
            values[1] == values[0] + 1 and values[2] == values[1] + 1
        ) or low_ace_values == [1, 2, 3]
        if flush and straight:
            return "Straight Flush"
        if len(set(ranks)) == 1:
            return "3 of a Kind"
        if straight:
            return "Straight"
        if flush:
            return "Flush"
        if len(set(ranks)) == 2:
            return "Pair"
        return "Chance"

    @classmethod
    def _card_hand_score(cls, cards: list[tuple[str, str]]) -> int:
        return sum(cls.CARD_VALUES[rank] for rank, _suit in cards)

    @staticmethod
    def _restore_health_and_mana(target: Character, messages: list[str]) -> None:
        target.health.current = target.health.max
        target.mana.current = target.mana.max
        messages.append(f"{target.name} has been revitalized! " f"Health and mana are restored.\n")
        from src.core import abilities as _abilities

        cleanse_result = _abilities.Cleanse().cast(target, special=True)
        messages.append(
            str(cleanse_result) if not isinstance(cleanse_result, str) else cleanse_result
        )

    @staticmethod
    def _record_slot_pair_effect(
        result: CombatResult, target: Character, effect: str, effect_dict
    ) -> None:
        if effect in target.status_effects:
            result.effects_applied.setdefault("Status", []).append(effect)
            result.extra["status_effect"] = effect
        elif effect in target.physical_effects:
            result.effects_applied.setdefault("Physical", []).append(effect)
        elif effect in target.stat_effects:
            result.effects_applied.setdefault("Stat", []).append(effect)
        elif effect in target.magic_effects:
            result.effects_applied.setdefault("Magic", []).append(effect)
        if effect == "DOT":
            effect_dict[effect].source = "Slot Machine"

    @classmethod
    def _apply_random_pair_effect(
        cls,
        target: Character,
        duration: int,
        amount: int,
        rng,
        messages: list[str],
        result: CombatResult,
    ) -> None:
        effects = [
            "Berserk",
            "Blind",
            "Doom",
            "Poison",
            "Silence",
            "Sleep",
            "Stun",
            "Bleed",
            "Disarm",
            "Prone",
            "Attack",
            "Defense",
            "Magic",
            "Magic Defense",
            "Speed",
            "DOT",
            "Reflect",
            "Regen",
        ]
        effect = rng.choice(effects)
        status_effects = [
            "Berserk",
            "Blind",
            "Doom",
            "Poison",
            "Silence",
            "Sleep",
            "Stun",
        ]
        if any(
            [
                effect in target.status_immunity,
                f"Status-{effect}" in target.equipment["Pendant"].mod,
                "Status-All" in target.equipment["Pendant"].mod and effect in status_effects,
            ]
        ):
            messages.append(f"{target.name} is immune to {effect.lower()}.\n")
            return
        if any([target.magic_effects["Ice Block"].active, getattr(target, "tunnel", False)]):
            messages.append("It has no effect.\n")
            return

        messages.append(f"{effect} has been randomly selected to affect " f"{target.name}.\n")
        effect_dict = target.effect_handler(effect)
        effect_dict[effect].active = True
        if effect in ["Blind", "Disarm", "Silence"]:
            effect_dict[effect].duration = -1
        else:
            effect_dict[effect].duration = max(duration, effect_dict[effect].duration)
        if effect in ["Poison", "Bleed", "DOT"]:
            amount *= int(target.health.max * 0.01)
            effect_dict[effect].extra = amount
            if effect == "DOT":
                effect_dict[effect].source = "Slot Machine"
        if effect in target.stat_effects:
            combat_effect = "magic_def" if effect == "Magic Defense" else effect.lower()
            amount *= target.combat.__dict__[combat_effect] // 10
            messages.append(
                f"{target.name}'s {effect.lower()} is " f"temporarily increased by {amount}.\n"
            )
            effect_dict[effect].extra = amount
        cls._record_slot_pair_effect(result, target, effect, effect_dict)

    def _apply_card_spin(
        self,
        spin: str,
        cards: list[tuple[str, str]],
        actor: Character,
        target: Character,
        user_chance: int,
        target_chance: int,
        rng,
        messages: list[str],
        result: CombatResult,
    ) -> None:
        label = self.card_hand_label(cards)
        score = self._card_hand_score(cards)
        try:
            from src.core.classes import promotion_kits

            severity = promotion_kits.misfortune_severity_multiplier(actor)
        except Exception:
            severity = 1.0
        result.extra["luck_success"] = False
        result.extra["slot_outcome"] = label
        messages.append(f"{label}!\n")
        messages.append(f"Cards: {spin}\n")

        if target_chance > user_chance + 1 and label in {"Straight Flush", "Straight"}:
            target = actor

        if label == "Straight Flush":
            result.extra["luck_success"] = target is not actor
            if any([target.magic_effects["Ice Block"].active, getattr(target, "tunnel", False)]):
                messages.append("It has no effect.\n")
                return
            damage = max(1, int(score * 4 * severity))
            mana_drain = min(target.mana.current, max(1, int((score // 2) * severity)))
            target.health.current -= damage
            target.mana.current -= mana_drain
            actor.mana.current = min(actor.mana.max, actor.mana.current + mana_drain)
            messages.append(f"{target.name} takes {damage} damage and loses {mana_drain} mana.\n")
            return

        if label == "3 of a Kind":
            if any([target.magic_effects["Ice Block"].active, rng.randint(0, max(1, user_chance))]):
                target = actor
            result.extra["luck_success"] = target is actor
            self._restore_health_and_mana(target, messages)
            return

        if label == "Straight":
            result.extra["luck_success"] = target is not actor
            if target.magic_effects["Ice Block"].active:
                messages.append("It has no effect.\n")
            else:
                damage = max(1, int(score * 2 * severity))
                target.health.current -= damage
                messages.append(f"{target.name} takes {damage} damage.\n")
            return

        if label == "Flush":
            if any(
                [
                    target.magic_effects["Ice Block"].active,
                    getattr(target, "tunnel", False),
                    target_chance > user_chance + 1,
                ]
            ):
                target = actor
            result.extra["luck_success"] = target is not actor
            gold_drain = min(
                getattr(target, "gold", 0),
                int(score * 25 * severity),
            )
            mana_drain = min(
                target.mana.current,
                max(1, int((score // 3) * severity)),
            )
            target.gold -= gold_drain
            actor.gold += gold_drain
            target.mana.current -= mana_drain
            actor.mana.current = min(actor.mana.max, actor.mana.current + mana_drain)
            messages.append(
                f"{target.name} is flushed for {gold_drain} gold and {mana_drain} mana.\n"
            )
            return

        if label == "Pair":
            paired_rank = max(
                {rank for rank, _suit in cards},
                key=lambda rank: [card_rank for card_rank, _suit in cards].count(rank),
            )
            amount = max(1, int((self.CARD_VALUES[paired_rank] // 2) * severity))
            duration = max(1, min(10, amount))
            if not rng.randint(0, 1):
                target = actor
            result.extra["luck_success"] = target is not actor
            self._apply_random_pair_effect(target, duration, amount**2, rng, messages, result)
            return

        mod = max(1, score // 3) / 10
        messages.append(f"{actor.name} gains {int(mod * 100)}% to attack.\n")
        wd_str, hit, _ = actor.weapon_damage(target, dmg_mod=1 + mod, use_offhand=False)
        result.extra["luck_success"] = bool(hit)
        messages.append(wd_str)

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random as _rng

        messages = result.extra.setdefault("messages", [])
        if target is None:
            return

        use_kw = result.extra.get("use_kwargs", {})
        slot_machine_callback = use_kw.get("slot_machine_callback")

        user_chance = actor.check_mod("luck", enemy=target, luck_factor=10)
        target_chance = target.check_mod("luck", enemy=actor, luck_factor=10)
        fortune_bonus = max(0.0, float(result.extra.get("fortune_bonus", 0.0) or 0.0))
        user_chance += max(0, int(max(1, user_chance) * fortune_bonus))

        hands = self.HANDS
        success = False
        retries = 0

        while not success:
            if slot_machine_callback is not None:
                spin = slot_machine_callback(actor, target)
            else:
                spin = self.deal_card_spin(_rng)

            card_hand = self.parse_card_spin(spin)
            if card_hand is not None:
                self._apply_card_spin(
                    spin,
                    card_hand,
                    actor,
                    target,
                    user_chance,
                    target_chance,
                    _rng,
                    messages,
                    result,
                )
                success = True
                continue

            if spin in hands["Death"]:
                messages.append("The mark of the beast!\n")
                success = True
                if target_chance > user_chance + 1:
                    target = actor
                if any(
                    [target.magic_effects["Ice Block"].active, getattr(target, "tunnel", False)]
                ):
                    messages.append("It has no effect.\n")
                elif "Death" not in target.status_immunity:
                    target.health.current = 0
                    messages.append(f"Death has come for {target.name}!\n")
                else:
                    messages.append(f"{target.name} is immune to death spells.\n")

            elif spin in hands["Trips"]:
                messages.append("3 of a Kind!\n")
                success = True
                if any(
                    [target.magic_effects["Ice Block"].active, _rng.randint(0, max(1, user_chance))]
                ):
                    target = actor
                target.health.current = target.health.max
                target.mana.current = target.mana.max
                messages.append(
                    f"{target.name} has been revitalized! " f"Health and mana are restored.\n"
                )
                from src.core import abilities as _abilities

                cleanse_result = _abilities.Cleanse().cast(target, special=True)
                messages.append(
                    str(cleanse_result) if not isinstance(cleanse_result, str) else cleanse_result
                )

            elif "".join(sorted(spin)) in hands["Straight"]:
                messages.append("Straight!\n")
                success = True
                if target_chance > user_chance + 1:
                    target = actor
                ints = [int(x) for x in list(spin)]
                damage = 1
                for i in ints:
                    damage *= i
                if target.magic_effects["Ice Block"].active:
                    messages.append("It has no effect.\n")
                else:
                    target.health.current -= damage
                    messages.append(f"{target.name} takes {damage} damage.\n")

            elif spin in hands["Palindrome"]:
                messages.append("Palindrome!\n")
                success = True
                if target_chance > user_chance + 1:
                    target = actor
                from src.core import abilities as _abilities

                spell_list = [
                    _abilities.MagicMissile3(),
                    _abilities.Firestorm(),
                    _abilities.IceBlizzard(),
                    _abilities.Electrocution(),
                    _abilities.Tsunami(),
                    _abilities.Earthquake(),
                    _abilities.Tornado(),
                    _abilities.ShadowBolt3(),
                    _abilities.Holy3(),
                    _abilities.PhotonSphere(),
                ]
                spell = spell_list[int(spin[1])]
                messages.append(f"{spell.name} is cast!\n")
                if any(
                    [target.magic_effects["Ice Block"].active, getattr(target, "tunnel", False)]
                ):
                    messages.append("It has no effect.\n")
                else:
                    cast_result = spell.cast(actor, target=target, special=True)
                    messages.append(
                        str(cast_result) if not isinstance(cast_result, str) else cast_result
                    )

            elif len(set(spin)) == 2:
                messages.append("Pairs!\n")
                success = True
                duration = int(min(set(list(spin)), key=list(spin).count))
                if duration == 0:
                    duration = 10
                amount = int(max(set(list(spin)), key=list(spin).count))
                if amount == 0:
                    amount = 10
                amount **= 2
                effects = [
                    "Berserk",
                    "Blind",
                    "Doom",
                    "Poison",
                    "Silence",
                    "Sleep",
                    "Stun",
                    "Bleed",
                    "Disarm",
                    "Prone",
                    "Attack",
                    "Defense",
                    "Magic",
                    "Magic Defense",
                    "Speed",
                    "DOT",
                    "Reflect",
                    "Regen",
                ]
                if not _rng.randint(0, 1):
                    target = actor
                effect = _rng.choice(effects)
                status_effects = [
                    "Berserk",
                    "Blind",
                    "Doom",
                    "Poison",
                    "Silence",
                    "Sleep",
                    "Stun",
                ]
                if any(
                    [
                        effect in target.status_immunity,
                        f"Status-{effect}" in target.equipment["Pendant"].mod,
                        "Status-All" in target.equipment["Pendant"].mod
                        and effect in status_effects,
                    ]
                ):
                    messages.append(f"{target.name} is immune to {effect.lower()}.\n")
                elif any(
                    [target.magic_effects["Ice Block"].active, getattr(target, "tunnel", False)]
                ):
                    messages.append("It has no effect.\n")
                else:
                    messages.append(
                        f"{effect} has been randomly selected to affect " f"{target.name}.\n"
                    )
                    effect_dict = target.effect_handler(effect)
                    effect_dict[effect].active = True
                    if effect in ["Blind", "Disarm", "Silence"]:
                        effect_dict[effect].duration = -1
                    else:
                        effect_dict[effect].duration = max(duration, effect_dict[effect].duration)
                    if effect in ["Poison", "Bleed", "DOT"]:
                        amount *= int(target.health.max * 0.01)
                        effect_dict[effect].extra = amount
                        if effect == "DOT":
                            effect_dict[effect].source = "Slot Machine"
                    if effect in target.stat_effects:
                        combat_effect = "magic_def" if effect == "Magic Defense" else effect.lower()
                        amount *= target.combat.__dict__[combat_effect] // 10
                        messages.append(
                            f"{target.name}'s {effect.lower()} is "
                            f"temporarily increased by {amount}.\n"
                        )
                        effect_dict[effect].extra = amount
                    self._record_slot_pair_effect(result, target, effect, effect_dict)

            elif all(int(x) % 2 == 0 for x in list(spin)):
                messages.append("Evens!\n")
                success = True
                if any(
                    [
                        target.magic_effects["Ice Block"].active,
                        getattr(target, "tunnel", False),
                        user_chance + 1 >= target_chance,
                    ]
                ):
                    target = actor
                target.gold += int(spin) * 10
                messages.append(f"{target.name} gains {int(spin)} gold!\n")

            elif all(int(x) % 2 == 1 for x in list(spin)):
                messages.append("Odds!\n")
                success = True
                level = min(list(spin))
                if any(
                    [
                        user_chance + 1 >= target_chance,
                        target.magic_effects["Ice Block"].active,
                        getattr(target, "tunnel", False),
                    ]
                ):
                    target = actor
                from src.core import items as _items

                item_cls = _items.random_item(int(level))
                item = item_cls() if isinstance(item_cls, type) else item_cls
                try:
                    target.modify_inventory(item)
                except AttributeError:
                    pass
                messages.append(f"{target.name} gains {item.name}.\n")

            elif _rng.randint(0, user_chance):
                messages.append("Chance!\n")
                success = True
                mod = int(_rng.choice(list(spin))) / 10
                messages.append(f"{actor.name} gains {int(mod * 100)}% to attack.\n")
                wd_str, _, _ = actor.weapon_damage(target, dmg_mod=1 + mod, use_offhand=False)
                messages.append(wd_str)

            else:
                if _rng.randint(0, user_chance) and retries < 2:
                    retries += 1
                else:
                    success = True
                    messages.append("Nothing happens.\n")


class TotemEffect(Effect):
    """Activate a totem magic effect with the selected sacred aspect.

    The active aspect is passed via ``use_kwargs["active_aspect"]``.
    Falls back to ``"Earth"`` if not provided.

    Stores aspect data in ``user.magic_effects["Totem"].extra`` for the
    combat engine to reference (bonuses, secondary effects).

    Parameters (YAML):
        aspects (dict): Aspect definitions keyed by name.
        unlock_requirements (dict): Level requirements per aspect.
        duration_base (int): Base totem duration in turns.
    """

    DEFAULT_ASPECTS = {
        "Earth": {
            "cost": 12,
            "attack_bonus": 0.0,
            "defense_bonus": 0.20,
            "secondary": "reflect",
            "description": "+20% Defense. Reflects 25% of damage back at attackers.",
        },
        "Water": {
            "cost": 14,
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "magic_defense_bonus": 0.20,
            "absorb_fraction": 0.25,
            "secondary": "water_ward",
            "description": "+50% healing effectiveness. Cleanses negative status effects and wards against spell damage.",
        },
        "Fire": {
            "cost": 16,
            "attack_bonus": 0.25,
            "defense_bonus": 0.0,
            "secondary": "elemental",
            "description": "+25% Attack damage. Adds elemental fire damage to your attacks.",
        },
        "Wind": {
            "cost": 15,
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "secondary": "speed",
            "description": "+15% Dodge chance and +10% Critical strike chance. Enhanced precision and evasion.",
        },
        "Soul": {
            "cost": 18,
            "attack_bonus": 0.20,
            "defense_bonus": 0.0,
            "secondary": "crit_damage",
            "description": "+20% Weapon damage and +20% Critical damage. Embodies the essence of conquered foes.",
        },
    }

    DEFAULT_UNLOCK_REQUIREMENTS = {
        "Earth": 1,
        "Water": 10,
        "Fire": 20,
        "Wind": 30,
        "Soul": 999,
    }

    def __init__(
        self,
        aspects: dict | None = None,
        unlock_requirements: dict | None = None,
        duration_base: int = 5,
        **_kw,
    ):
        super().__init__()
        self.aspects = aspects or dict(self.DEFAULT_ASPECTS)
        self.unlock_requirements = unlock_requirements or dict(self.DEFAULT_UNLOCK_REQUIREMENTS)
        self.duration_base = duration_base

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        messages = result.extra.setdefault("messages", [])
        use_kw = result.extra.get("use_kwargs", {})
        active_aspect = use_kw.get("active_aspect", "Earth")

        if active_aspect not in self.aspects:
            messages.append(f"Unknown aspect: {active_aspect}\n")
            return

        aspect = self.aspects[active_aspect]
        duration = self.duration_base + (actor.stats.wisdom // 10)

        # Activate the Totem magic effect
        actor.magic_effects["Totem"].active = True
        actor.magic_effects["Totem"].duration = duration
        actor.magic_effects["Totem"].extra = {
            "aspect": active_aspect,
            "attack_bonus": aspect["attack_bonus"],
            "defense_bonus": aspect["defense_bonus"],
            "secondary": aspect["secondary"],
            "magic_defense_bonus": aspect.get("magic_defense_bonus", 0.0),
            "absorb_fraction": aspect.get("absorb_fraction", 0.0),
        }

        messages.append(
            f"{actor.name} drives a {active_aspect.lower()} totem into " f"the ground!\n"
        )
        messages.append(f"{aspect['description']}\n")

        if aspect["attack_bonus"] > 0:
            messages.append(f"Attack increased by " f"{int(aspect['attack_bonus'] * 100)}%.\n")
        if aspect["defense_bonus"] > 0:
            messages.append(f"Defense increased by " f"{int(aspect['defense_bonus'] * 100)}%.\n")

        secondary_descriptions = {
            "reflect": "Attacks against you are reflected back at the attacker.\n",
            "healing": "Healing spells and effects are significantly more effective.\n",
            "water_ward": "Healing is strengthened and hostile spellwork flows into restoration.\n",
            "elemental": "Your attacks burn with primal fire.\n",
            "speed": "Your reflexes and precision are heightened, granting increased dodge and critical strike chance.\n",
            "crit_damage": "The captured essence of fallen foes empowers your weapon with devastating critical strikes.\n",
        }
        desc = secondary_descriptions.get(aspect["secondary"])
        if desc:
            messages.append(desc)

        messages.append(f"The totem emanates power for {duration} turns.\n")

        # Emit status event
        try:
            actor._emit_status_event(
                actor,
                "Totem",
                applied=True,
                duration=duration,
                source=f"{active_aspect} Totem",
            )
        except (AttributeError, Exception):
            pass


class SoulDrainEffect(Effect):
    """Deal nonlethal current-HP percentage damage."""

    def __init__(self, fraction: float = 0.10, **_kw):
        super().__init__()
        self.fraction = fraction

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        messages = result.extra.setdefault("messages", [])
        if target is None or not target.is_alive():
            return
        potency = 1.0
        try:
            potency = max(0.0, float(getattr(actor, "_totem_pulse_potency", 1.0)))
        except (TypeError, ValueError):
            pass
        if hasattr(actor, "_totem_pulse_potency"):
            try:
                from ..classes import class_rings

                potency *= 1.0 + class_rings.soul_aspect_bonus(actor)
                potency *= max(0.0, float(getattr(actor, "_totem_surge_output", 1.0)))
            except Exception:
                pass
        if target.health.current <= 1:
            messages.append(f"{target.name}'s soul clings to a final thread.\n")
            return
        damage = max(1, int(target.health.current * self.fraction * potency))
        damage = min(damage, target.health.current - 1)
        target.health.current -= damage
        result.damage = damage
        result.hit = True
        try:
            actor._emit_damage_event(
                target,
                damage,
                damage_type="Soul",
                is_critical=False,
                source="spell",
                attack_source="spell",
                ability_name="Soul Drain",
            )
        except Exception:
            pass
        messages.append(f"{actor.name} drains {damage} hit points from {target.name}'s soul.\n")


class ChargeEffect(Effect):
    """
    Charge execute phase: str-vs-con stun check BEFORE weapon damage.

    Stun is blocked by: status immunity, Pendant of Stun/All, tunnel,
    Mana Shield, already stunned.
    """

    def __init__(self, dmg_mod: float = 1.25, stun_duration: int = 1):
        self.dmg_mod = dmg_mod
        self.stun_duration = stun_duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        messages = result.extra.setdefault("messages", [])
        cover = result.extra.get("cover", False)

        # ── Stun check BEFORE damage ────────────────────────────────
        if not any(
            [
                "Stun" in target.status_immunity,
                "Status-Stun" in target.equipment["Pendant"].mod,
                "Status-All" in target.equipment["Pendant"].mod,
                target.tunnel,
            ]
        ):
            if not target.magic_effects["Mana Shield"].active and target.stun_contest_success(
                actor,
                random.randint(actor.stats.strength // 2, actor.stats.strength),
                random.randint(target.stats.con // 2, target.stats.con),
            ):
                if target.apply_stun(self.stun_duration, source="Head Butt", applier=actor):
                    messages.append(f"{actor.name} stunned {target.name}.\n")

        # ── Weapon damage ───────────────────────────────────────────
        wd_str, hit, crit = actor.weapon_damage(
            target,
            cover=cover,
            dmg_mod=self.dmg_mod,
            use_offhand=False,
        )
        messages.append(wd_str)
        result.hit = hit
        result.crit = crit if crit > 1 else None


class CrushingBlowEffect(Effect):
    """
    Crushing Blow execute phase: weapon damage (3x, crit 2) then
    50 % chance to stun for 2 turns.
    """

    def __init__(
        self,
        dmg_mod: float = 3.0,
        crit_override: int = 2,
        stun_chance: float = 0.5,
        stun_duration: int = 2,
    ):
        self.dmg_mod = dmg_mod
        self.crit_override = crit_override
        self.stun_chance = stun_chance
        self.stun_duration = stun_duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        messages = result.extra.setdefault("messages", [])
        cover = result.extra.get("cover", False)

        # ── Weapon damage ───────────────────────────────────────────
        wd_str, hit, crit = actor.weapon_damage(
            target,
            cover=cover,
            dmg_mod=self.dmg_mod,
            crit=self.crit_override,
            use_offhand=False,
        )
        messages.append(wd_str)
        result.hit = hit
        result.crit = crit if crit > 1 else None

        # ── Post-hit stun check ─────────────────────────────────────
        if hit and target.is_alive():
            if not any(
                [
                    "Stun" in target.status_immunity,
                    "Status-Stun" in target.equipment["Pendant"].mod,
                    "Status-All" in target.equipment["Pendant"].mod,
                ]
            ):
                if random.random() < self.stun_chance:
                    if target.apply_stun(self.stun_duration, source="Crushing Blow", applier=actor):
                        messages.append(f"{target.name} is stunned!\n")


class ArcaneBlastEffect(Effect):
    """
    Arcane Blast execute phase: use all mana as magic damage via
    handle_defenses / damage_reduction, drain to 0, then queue
    Power Up for mana regen over N turns if the target survives.
    """

    def __init__(self, regen_turns: int = 4, regen_fraction: float = 0.1):
        self.regen_turns = regen_turns
        self.regen_fraction = regen_fraction

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])
        cover = result.extra.get("cover", False)
        charge_ctx = result.extra.get("charge_context", {})

        mana_spent = charge_ctx.get("mana", actor.mana.current)

        hit, message, damage = target.handle_defenses(
            actor,
            mana_spent,
            cover,
            typ="Magic",
        )
        messages.append(message)
        hit, message, damage = target.damage_reduction(
            damage,
            actor,
            typ="Arcane",
        )
        messages.append(message)
        actor.mana.current = 0

        if hit:
            variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
            damage = int(damage * variance)
            if damage > 0:
                target.health.current -= damage
                messages.append(
                    f"{actor.name} blasts {target.name} for {damage} damage, "
                    f"draining all remaining mana.\n"
                )
            result.hit = True
            result.damage = damage

        # Power Up for mana regen if target survived
        if target.is_alive():
            if hasattr(actor, "class_effects") and "Power Up" in actor.class_effects:
                actor.power_up = True
                actor.class_effects["Power Up"].active = True
                actor.class_effects["Power Up"].duration = self.regen_turns
                actor.class_effects["Power Up"].extra = max(
                    1,
                    int(actor.mana.max * self.regen_fraction),
                )


class JumpEffect(Effect):
    """
    Jump execute phase: weapon damage with modification-dependent
    dmg_mod/crit, then apply active modification combat effects
    (Quake, Rend, Dragon's Fury, Skyfall, Thrust, Recover).

    Reads modification state from ``result.extra["modifications"]``.
    Reads retribution bonus from ``result.extra["retribution_damage"]``.
    """

    def __init__(self, base_dmg_mod: float = 2.0):
        self.base_dmg_mod = base_dmg_mod

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:

        messages = result.extra.setdefault("messages", [])
        cover = result.extra.get("cover", False)
        mods = result.extra.get("modifications", {})
        retribution_damage = result.extra.get("retribution_damage", 0)

        # ── Calculate dmg_mod / crit from active modifications ──────
        dmg_mod = self.base_dmg_mod
        crit = 1

        if mods.get("Crit"):
            dmg_mod = 1.5
            crit = 2

        if mods.get("Quick Dive"):
            dmg_mod = 1.25

        # Soaring Strike overrides Crit
        if mods.get("Soaring Strike"):
            dmg_mod = 3.0
            crit = 3

        # Retribution bonus
        if mods.get("Retribution") and retribution_damage > 0:
            dmg_mod += retribution_damage / 100
            messages.append(f"{actor.name}'s fury from taking damage empowers the strike!\n")

        messages.append(f"{actor.name} descends from the air, weapon aimed at " f"{target.name}!\n")

        # ── Main weapon damage ──────────────────────────────────────
        target_hp_before = target.health.current
        wd_str, hit, actual_crit = actor.weapon_damage(
            target,
            cover=cover,
            dmg_mod=dmg_mod,
            crit=crit,
            use_offhand=False,
        )
        messages.append(wd_str)
        result.hit = hit
        result.crit = actual_crit if actual_crit > 1 else None
        jump_damage = max(0, target_hp_before - target.health.current)
        try:
            from ..classes import promotion_kits

            landing_message = promotion_kits.record_clean_jump_landing(
                actor,
                jump_damage,
                mods,
            )
            if landing_message:
                messages.append(landing_message)
        except Exception:
            pass

        if hit and target.is_alive():
            # ── Quake (stun chance) ─────────────────────────────────
            if mods.get("Quake"):
                self._apply_quake(actor, target, messages)

            # ── Rend (bleed) ────────────────────────────────────────
            if mods.get("Rend"):
                self._apply_rend(actor, target, messages)

            # ── Dragon's Fury (elemental damage) ────────────────────
            if mods.get("Dragon's Fury"):
                self._apply_dragons_fury(actor, target, messages)

            # ── Skyfall (multi-hit debris) ──────────────────────────
            if mods.get("Skyfall"):
                self._apply_skyfall(actor, target, messages)

            # ── Thrust (follow-up weapon hit) ───────────────────────
            if mods.get("Thrust") and target.is_alive():
                self._apply_thrust(actor, target, cover, messages)

        # ── Recover (heal on landing, regardless of hit) ────────────
        if mods.get("Recover"):
            self._apply_recover(actor, messages)
            from src.core.classes import dragoon

            dragoon.try_restore_kaelenon(actor, target, mods, messages)

    # ------------------------------------------------------------------
    # Modification sub-effects
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_quake(actor: Character, target: Character, messages: list[str]) -> None:
        import random

        if any(
            [
                "Stun" in target.status_immunity,
                "Status-Stun" in target.equipment["Pendant"].mod,
                "Status-All" in target.equipment["Pendant"].mod,
            ]
        ):
            return
        att_roll = random.randint(actor.stats.strength // 2, actor.stats.strength)
        def_roll = random.randint(target.stats.con // 2, target.stats.con)
        if target.stun_contest_success(actor, att_roll, def_roll):
            if target.apply_stun(1, source="Jump (Quake)", applier=actor):
                messages.append(f"The impact stuns {target.name}!\n")

    @staticmethod
    def _apply_rend(actor: Character, target: Character, messages: list[str]) -> None:
        import random

        if target.physical_effects["Bleed"].active:
            return
        if random.randint(0, 100) < 40:  # 40% chance
            bleed_dmg = int(actor.stats.strength * 1.0)
            target.physical_effects["Bleed"].active = True
            target.physical_effects["Bleed"].duration = 2
            target.physical_effects["Bleed"].extra = bleed_dmg
            try:
                actor._emit_status_event(
                    target,
                    "Bleed",
                    applied=True,
                    duration=2,
                    source="Jump (Rend)",
                )
            except (AttributeError, Exception):
                pass
            messages.append(f"{target.name} is bleeding from the vicious strike!\n")

    @staticmethod
    def _apply_dragons_fury(actor: Character, target: Character, messages: list[str]) -> None:
        import random

        elements = ["Fire", "Ice", "Lightning"]
        element = random.choice(elements)
        elem_damage = int(actor.stats.intel * random.uniform(0.5, 1.0))
        elem_damage = max(1, elem_damage)

        resistance = target.check_mod(
            mod="resist",
            typ=f"{element}",
            enemy=actor,
        )
        elem_damage = max(1, elem_damage - resistance)

        target.health.current -= elem_damage
        messages.append(f"Draconic {element.lower()} energy erupts for " f"{elem_damage} damage!\n")

    @staticmethod
    def _apply_skyfall(actor: Character, target: Character, messages: list[str]) -> None:
        import random

        num_hits = random.randint(2, 4)
        messages.append(f"Debris rains down on {target.name}!\n")
        for i in range(num_hits):
            if target.is_alive():
                sky_dmg = int(actor.stats.strength * random.uniform(0.2, 0.4))
                sky_dmg = max(1, sky_dmg)
                target.health.current -= sky_dmg
                messages.append(f"  Impact {i + 1}: {sky_dmg} damage!\n")

    @staticmethod
    def _apply_thrust(
        actor: Character, target: Character, cover: bool, messages: list[str]
    ) -> None:
        messages.append(f"{actor.name} thrusts their weapon forward!\n")
        thrust_str, _, _ = actor.weapon_damage(
            target,
            cover=cover,
            dmg_mod=0.75,
            use_offhand=False,
        )
        messages.append(thrust_str)

    @staticmethod
    def _apply_recover(actor: Character, messages: list[str]) -> None:
        from src.core.classes import dragoon

        hp_recover, mp_recover = dragoon.recover_amounts(actor)
        actor.health.current = min(
            actor.health.max,
            actor.health.current + hp_recover,
        )
        actor.mana.current = min(
            actor.mana.max,
            actor.mana.current + mp_recover,
        )
        messages.append(f"{actor.name} recovers {hp_recover} HP and " f"{mp_recover} MP!\n")


class ShadowStrikeEffect(Effect):
    """
    Shadow Strike execute phase: guaranteed-critical weapon damage
    followed by a chance to blind the target.

    Blind is blocked by: status immunity, Pendant of Blind/All,
    Mana Shield, already blinded.
    """

    def __init__(
        self,
        dmg_mod: float = 2.0,
        blind_chance: float = 0.6,
        blind_duration: int = 2,
    ):
        self.dmg_mod = dmg_mod
        self.blind_chance = blind_chance
        self.blind_duration = blind_duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        messages = result.extra.setdefault("messages", [])
        cover = result.extra.get("cover", False)

        # ── Guaranteed-crit weapon damage ───────────────────────────
        messages.append(f"{actor.name} strikes from the shadows!\n")
        wd_str, hit, crit = actor.weapon_damage(
            target,
            cover=cover,
            dmg_mod=self.dmg_mod,
            crit=2,
            use_offhand=False,
        )
        messages.append(wd_str)
        result.hit = hit
        result.crit = crit if crit > 1 else None

        # ── Post-hit blind check ────────────────────────────────────
        if hit and target.is_alive():
            if not any(
                [
                    "Blind" in target.status_immunity,
                    "Status-Blind" in target.equipment["Pendant"].mod,
                    "Status-All" in target.equipment["Pendant"].mod,
                ]
            ):
                if (
                    random.random() < self.blind_chance
                    and not target.status_effects["Blind"].active
                    and not target.magic_effects["Mana Shield"].active
                ):
                    target.status_effects["Blind"].active = True
                    target.status_effects["Blind"].duration = self.blind_duration
                    try:
                        actor._emit_status_event(
                            target,
                            "Blind",
                            applied=True,
                            duration=self.blind_duration,
                            source="Shadow Strike",
                        )
                    except (AttributeError, Exception):
                        pass
                    messages.append(f"{target.name} is blinded by the attack!\n")
