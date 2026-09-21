###########################################
"""companion manager"""

from __future__ import annotations

import hashlib

from src.core.randomness import gameplay_random as random

from . import abilities, items
from .character import Character, Combat, Resource, Stats
from .identity import COMPANION_TYPES

XENID_PAIRS = {
    "Animal": ("Hodag", "Caladrius"),
    "Humanoid": ("Patagon", "Kobalos"),
    "Monster": ("Dilong", "Cacus"),
    "Spirit": ("Agloolik", "Izulu"),
    "Fiend": ("Hala", "Lamashtu"),
    "Celestial": ("Seraphim", "Bardi"),
    "Dragon": ("Tiamat", "Zahhak"),
}
XENID_NAMES = tuple(name for pair in XENID_PAIRS.values() for name in pair)


# familiars
class Familiar(Character):
    """
    Base Familiar class
    """

    companion_id: str

    def __init_subclass__(cls, *, companion_id: str | None = None, **kwargs: object) -> None:
        """Register familiar types for strict persistence."""
        super().__init_subclass__(**kwargs)
        cls.companion_id = COMPANION_TYPES.register(cls, companion_id)

    def __init__(
        self, name: str, health: Resource, mana: Resource, stats: Stats, combat: Combat
    ) -> None:
        super().__init__(name=name, health=health, mana=mana, stats=stats, combat=combat)
        # Familiars grow twice. Their body is abstract: their Warlock supplies
        # attributes/resources whenever they act.
        self.level.exp_to_gain = 500

    def inspect(self) -> str:
        raise NotImplementedError

    def gain_action_experience(self, amount: int) -> str:
        """Award encounter experience only after this familiar took an action."""
        if self.level.pro_level >= 3:
            return ""
        gained = max(0, int(amount or 0))
        self.level.exp += gained
        self.level.exp_to_gain -= gained
        message = f"{self.name} gained {gained} familiar experience.\n"
        while self.level.exp_to_gain <= 0 and self.level.pro_level < 3:
            overflow = -self.level.exp_to_gain
            message += self.level_up()
            self.level.exp_to_gain = (1000 if self.level.pro_level == 2 else 0) - overflow
        return message


class TamedCompanion(Familiar):
    """A persistent animal companion created by the Ranger Tame skill."""

    def __init__(self, enemy) -> None:
        super().__init__(
            name=getattr(enemy, "name", "Tamed Companion"),
            health=Resource(
                max(1, int(getattr(enemy.health, "max", 20) * 0.75)),
                max(1, int(getattr(enemy.health, "max", 20) * 0.75)),
            ),
            mana=Resource(
                max(0, int(getattr(enemy.mana, "max", 0) * 0.5)),
                max(0, int(getattr(enemy.mana, "max", 0) * 0.5)),
            ),
            stats=Stats(
                strength=max(1, int(getattr(enemy.stats, "strength", 5) * 0.75)),
                intel=max(1, int(getattr(enemy.stats, "intel", 5) * 0.5)),
                wisdom=max(1, int(getattr(enemy.stats, "wisdom", 5) * 0.5)),
                con=max(1, int(getattr(enemy.stats, "con", 5) * 0.75)),
                charisma=max(1, int(getattr(enemy.stats, "charisma", 5) * 0.5)),
                dex=max(1, int(getattr(enemy.stats, "dex", 5) * 0.75)),
            ),
            combat=Combat(
                attack=max(1, int(getattr(enemy.combat, "attack", 5) * 0.75)),
                defense=max(1, int(getattr(enemy.combat, "defense", 5) * 0.75)),
                magic=max(1, int(getattr(enemy.combat, "magic", 5) * 0.5)),
                magic_def=max(1, int(getattr(enemy.combat, "magic_def", 5) * 0.5)),
            ),
        )
        self.race = getattr(enemy, "name", "Animal")
        self.enemy_class = enemy.__class__.__name__
        self.enemy_typ = getattr(enemy, "enemy_typ", "Animal")
        self.spec = "Tamed"
        self.cls = "Familiar"
        self.spellbook = {"Spells": {}, "Skills": {}}
        self.equipment = getattr(enemy, "equipment", self.equipment)

    def inspect(self) -> str:
        evolution = getattr(self, "evolution", "Wild Form")
        special = getattr(self, "special_ability", "Keen Scent")
        return f"{self.name} is a {evolution} tamed companion with {special}."


def tamed_companion_from_state(state):
    """Rebuild a tamed companion from compact save state."""
    from . import enemies
    from .classes import ability_mechanics

    normalized = ability_mechanics.normalize_tamed_companion(state)
    if not normalized["active"] or not normalized["enemy_class"]:
        return None
    enemy_cls = getattr(enemies, normalized["enemy_class"], None)
    if enemy_cls is None:
        return None
    seed_parts = (
        str(normalized.get("enemy_class") or ""),
        str(normalized.get("name") or ""),
        str(normalized.get("species") or ""),
        str(normalized.get("level") or 1),
    )
    seed = int(hashlib.sha256("|".join(seed_parts).encode("utf-8")).hexdigest()[:16], 16)
    random_state = random.getstate()
    try:
        random.seed(seed)
        try:
            enemy = enemy_cls()
        except TypeError:
            enemy = enemy_cls(normalized.get("level", 1))
    finally:
        random.setstate(random_state)
    companion = TamedCompanion(enemy)
    base = normalized.get("base")
    if isinstance(base, dict) and base:
        companion.health = Resource(
            max(1, int(base.get("health_max", companion.health.max) or companion.health.max)),
            max(1, int(base.get("health_max", companion.health.max) or companion.health.max)),
        )
        companion.mana = Resource(
            max(0, int(base.get("mana_max", companion.mana.max) or companion.mana.max)),
            max(0, int(base.get("mana_max", companion.mana.max) or companion.mana.max)),
        )
        stats = base.get("stats", {})
        if isinstance(stats, dict):
            companion.stats = Stats(
                strength=max(
                    1,
                    int(
                        stats.get("strength", companion.stats.strength) or companion.stats.strength
                    ),
                ),
                intel=max(
                    1, int(stats.get("intel", companion.stats.intel) or companion.stats.intel)
                ),
                wisdom=max(
                    1, int(stats.get("wisdom", companion.stats.wisdom) or companion.stats.wisdom)
                ),
                con=max(1, int(stats.get("con", companion.stats.con) or companion.stats.con)),
                charisma=max(
                    1,
                    int(
                        stats.get("charisma", companion.stats.charisma) or companion.stats.charisma
                    ),
                ),
                dex=max(1, int(stats.get("dex", companion.stats.dex) or companion.stats.dex)),
            )
        combat = base.get("combat", {})
        if isinstance(combat, dict):
            companion.combat = Combat(
                attack=max(
                    1, int(combat.get("attack", companion.combat.attack) or companion.combat.attack)
                ),
                defense=max(
                    1,
                    int(
                        combat.get("defense", companion.combat.defense) or companion.combat.defense
                    ),
                ),
                magic=max(
                    1, int(combat.get("magic", companion.combat.magic) or companion.combat.magic)
                ),
                magic_def=max(
                    1,
                    int(
                        combat.get("magic_def", companion.combat.magic_def)
                        or companion.combat.magic_def
                    ),
                ),
            )
    companion.name = ability_mechanics.tamed_companion_display_name(normalized)
    ability_mechanics.apply_tamed_companion_growth(companion, normalized)
    return companion


class Homunculus(Familiar):
    """
    Familiar - cast helpful defensive abilities; abilities upgrade when the familiar upgrades
    Level 1: Can use Disarm, Pocket Sand, and Stupefy
    Level 2: Gains Cover, Goad, and Slow and bonus to defense
    Level 3: Gains Resurrection
    """

    def __init__(self) -> None:
        super().__init__(
            name="", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.race = "Homunculus"
        self.name = self.race
        self.spellbook = {
            "Spells": {"Stupefy": abilities.Stupefy()},
            "Skills": {"Disarm": abilities.Disarm(), "Pocket Sand": abilities.PocketSand()},
        }
        self.spec = "Defense"
        self.cls = "Familiar"

    def inspect(self) -> str:
        return (
            f"A tiny construct that serves and protects its master from anything that challenges them, regardless"
            f" of the enemy's size or toughness. The {self.race} specializes in defensive abilities, either to "
            f"prevent direct damage or to limit the enemy's ability to deal damage. Choose this familiar if you "
            f"are a tad bit squishy, or your favorite movie is The Bodyguard."
        )

    def level_up(self) -> str:
        fam_level_str = f"{self.name} has leveled up!\n"
        if self.level.pro_level == 1:
            self.level.pro_level = 2
            skill_list = [abilities.Cover(), abilities.Goad(), abilities.Slow()]
            for skill in skill_list:
                self.spellbook["Skills"][skill.name] = skill
                fam_level_str += f"{self.name} has gain the ability {skill.name}.\n"
            fam_level_str += f"{self.name} also increases your defense.\n"
        else:
            self.level.pro_level = 3
            self.spellbook["Spells"]["Resurrection"] = abilities.Resurrection()
            fam_level_str += f"{self.name} has gain the ability Resurrection.\n"
        return fam_level_str


class Fairy(Familiar):
    """
    Familiar - cast helpful support abilities; abilities upgrade when the familiar upgrades
    Level 1: Can cast Heal, Regen, and Bless
    Level 2: Gains level 2 spells, Reflect, and will randomly restore percentage of mana
    Level 3: Gains level 3 spells and Cleanse
    """

    def __init__(self) -> None:
        super().__init__(
            name="", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.race = "Fairy"
        self.name = self.race
        self.spellbook = {
            "Spells": {
                "Heal": abilities.Heal(),
                "Regen": abilities.Regen(),
                "Bless": abilities.Bless(),
            },
            "Skills": {},
        }
        self.spec = "Support"
        self.cls = "Familiar"

    def inspect(self) -> str:
        return (
            f"These small, flying creatures hail from a parallel plane of existence and are typically associated"
            f" with a connection to nature. While the {self.race} is not known for its constitution, they more than"
            f" make up for it with support magics. If you hate having to stock up on potions, this familiar is the "
            f"one for you!"
        )

    def level_up(self) -> str:
        fam_level_str = f"{self.name} has leveled up!\n"
        if self.level.pro_level == 1:
            self.level.pro_level = 2
            spell_list = [abilities.Reflect(), abilities.Heal2(), abilities.Regen2()]
            for spell in spell_list:
                self.spellbook["Spells"][spell.name] = spell
                fam_level_str += f"{self.name} has gained the ability {spell.name}.\n"
        else:
            self.level.pro_level = 3
            spell_list = [
                abilities.Cleanse(),
                abilities.Heal3(),
                abilities.Regen3(),
                abilities.ExpelCurse(),
            ]
            for spell in spell_list:
                self.spellbook["Spells"][spell.name] = spell
                fam_level_str += f"{self.name} has gained the ability {spell.name}.\n"
        return fam_level_str


class Mephit(Familiar):
    """
    Familiar - cast helpful arcane abilities
    Level 1: Can cast Magic Missile and Silence
    Level 2: Gains level 2 spells, Boost, and sometimes provides elemental resistance
    Level 3: Gains level 3 spells
    """

    def __init__(self) -> None:
        super().__init__(
            name="", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.race = "Mephit"
        self.name = self.race
        self.spellbook = {
            "Spells": {"Magic Missile": abilities.MagicMissile(), "Silence": abilities.Silence()},
            "Skills": {},
        }
        self.spec = "Arcane"
        self.cls = "Familiar"

    def inspect(self) -> str:
        return (
            f"A {self.race} is similar to an imp, except this little guy can blast arcane spells. It also "
            f"gains some crowd control and support abilities. Who wouldn't want a their "
            f"very own pocket caster?"
        )

    def level_up(self) -> str:
        fam_level_str = f"{self.name} has leveled up!\n"
        if self.level.pro_level == 1:
            self.level.pro_level = 2
            spell_list = [
                abilities.Fireball(),
                abilities.Icicle(),
                abilities.Lightning(),
                abilities.Hurricane(),
                abilities.Aqualung(),
                abilities.Mudslide(),
                abilities.Boost(),
            ]
            for spell in spell_list:
                self.spellbook["Spells"][spell.name] = spell
                fam_level_str += f"{self.name} has gained the ability {spell.name}.\n"
            fam_level_str += f"{self.name} also increases your magic defense.\n"
        else:
            self.level.pro_level = 3
            spell_list = [
                abilities.Firestorm(),
                abilities.IceBlizzard(),
                abilities.Electrocution(),
                abilities.Tornado(),
                abilities.Tsunami(),
                abilities.Earthquake(),
                abilities.Invisibility(),
                abilities.Polymorph(),
            ]
            for spell in spell_list:
                self.spellbook["Spells"][spell.name] = spell
                fam_level_str += f"{self.name} has gained the ability {spell.name}.\n"
        return fam_level_str


class Jinkin(Familiar):
    """
    Familiar - cast (mostly) helpful luck abilities
    Level 1: Can cast Corruption and use Gold Toss (uses player_char gold) and Steal (items go to player_char inventory)
    Level 2: Gains Enfeeble and will unlock Treasure chests
    Level 3: Gains Slot Machine and Twist Fate and will randomly find items at the end of combat
    """

    def __init__(self) -> None:
        super().__init__(
            name="", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.race = "Jinkin"
        self.name = self.race
        self.spellbook = {
            "Spells": {"Corruption": abilities.Corruption()},
            "Skills": {"Gold Toss": abilities.GoldToss(), "Steal": abilities.Steal()},
        }
        self.spec = "Luck"
        self.cls = "Familiar"

    def inspect(self) -> str:
        return (
            f"{self.race}s are vindictive little tricksters. While they mostly rely on (their very good) luck, "
            f"Jinkins also enjoy the occasional curse to really add a thorn to your enemy's paw. You may not always"
            f" like what you get but you also may just love it! (low charisma characters should probably avoid this"
            f" familiar)..."
        )

    def level_up(self) -> str:
        fam_level_str = f"{self.name} has leveled up!\n"
        if self.level.pro_level == 1:
            self.level.pro_level = 2
            self.spellbook["Spells"]["Enfeeble"] = abilities.Enfeeble()
            fam_level_str += f"{self.name} has gained the ability Enfeeble.\n"
            self.spellbook["Skills"]["Lockpick"] = abilities.Lockpick()
            fam_level_str += f"{self.name} has gained the ability Lockpick.\n"
        else:
            self.level.pro_level = 3
            self.spellbook["Skills"]["Slot Machine"] = abilities.SlotMachine()
            fam_level_str += f"{self.name} has gained the ability Slot Machine.\n"
            self.spellbook["Spells"]["Twist Fate"] = abilities.TwistFate()
            fam_level_str += f"{self.name} has gained the ability Twist Fate.\n"
        return fam_level_str


# summons
class Summons(Character):
    """
    Base class for summon creature
    Odd number levels result in ability gain (except 10); even levels gain stat(s)
    """

    companion_id: str

    def __init_subclass__(cls, *, companion_id: str | None = None, **kwargs: object) -> None:
        """Register summon types for strict persistence."""
        super().__init_subclass__(**kwargs)
        cls.companion_id = COMPANION_TYPES.register(cls, companion_id)

    def __init__(
        self, name: str, health: Resource, mana: Resource, stats: Stats, combat: Combat
    ) -> None:
        super().__init__(name=name, health=health, mana=mana, stats=stats, combat=combat)
        self.start_stats: list[int] = [
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ]  # health, mana, str, intel, wis, con, cha, dex
        self.start_combat: list[int] = [0, 0, 0, 0]  # attack, defense, magic, magic_def
        self.cls = self
        self.exp_scale: int = 1000
        self.summon_mana_cost: int | None = None
        self.summon_gold_cost: int = 0
        self.description: str = ""

    def _starting_stat_values(self) -> list[int]:
        """Return health, mana, and six core stats from summon starting data."""
        return (list(self.start_stats[:8]) + [0] * 8)[:8]

    def _starting_combat_values(self) -> list[int]:
        """Return attack, defense, magic, and magic defense from starting data."""
        return (list(self.start_combat[:4]) + [0] * 4)[:4]

    def initialize_stats(self, player_char: Character) -> None:
        self.level.exp_to_gain = self.level.pro_level * self.exp_scale
        stat_scale = 25 - self.level.pro_level
        stat_adj = 1 + (
            (
                (player_char.stats.intel - random.randint(10, 20))
                + (player_char.stats.charisma - random.randint(10, 20))
            )
            / stat_scale
        )
        stats = [int(x * stat_adj) for x in self._starting_stat_values()]
        self.health = Resource(stats[0], stats[0])
        self.mana = Resource(stats[1], stats[1])
        self.stats = Stats(*stats[2:])
        combat_stats = [int(x * stat_adj) for x in self._starting_combat_values()]
        self.combat = Combat(*combat_stats)
        try:
            from .classes import class_rings, mage_mechanics

            ring_multiplier = class_rings.summon_multiplier(player_char)
            health_multiplier, damage_multiplier = mage_mechanics.permanent_summon_multipliers(
                player_char
            )
            if ring_multiplier != 1.0 or health_multiplier != 1.0:
                self.health.max = max(1, int(self.health.max * ring_multiplier * health_multiplier))
                self.health.current = self.health.max
            if ring_multiplier != 1.0 or damage_multiplier != 1.0:
                self.combat.attack = int(self.combat.attack * ring_multiplier * damage_multiplier)
                self.combat.magic = int(self.combat.magic * ring_multiplier * damage_multiplier)
        except Exception:
            pass
        self._conduit_base = {
            "health": self.health.max,
            "mana": self.mana.max,
            "stats": dict(self.stats.__dict__),
            "combat": dict(self.combat.__dict__),
        }
        sync_xenid_conduit(player_char, self.name)

    def level_up(self, player_char: Character) -> str:
        self.level.level += 1
        self.level.exp_to_gain += self.level.pro_level * self.exp_scale * self.level.level
        level_str = f"{self.name} gains a level and its power increases.\n"
        total_level = self.level.pro_level * (player_char.level.pro_level - 1)
        stat_scale = (100 - random.randint(0, 10)) // total_level
        stat_adj = 1 + (((player_char.stats.intel + player_char.stats.charisma) / stat_scale))
        self.health.max = int(self.health.max * stat_adj)
        self.mana.max = int(self.mana.max * stat_adj)
        new_combat = [int(x * stat_adj) for x in list(self.combat.__dict__.values())]
        self.combat = Combat(*new_combat)
        for typ in summon_abilities[self.name]:
            if str(self.level.level) in summon_abilities[self.name][typ]:
                ability = summon_abilities[self.name][typ][str(self.level.level)]()
                self.spellbook[typ][ability.name] = ability
                level_str += f"{self.name} gains the ability {ability.name}.\n"
        if self.level.level % 2 == 0:
            starting_stats = self._starting_stat_values()[2:]
            chances = [x / sum(starting_stats) for x in starting_stats]
            new_stats = list(self.stats.__dict__.values())
            for _ in range(total_level):
                ind = random.choices([0, 1, 2, 3, 4, 5], chances)[0]
                new_stats[ind] += 1
            self.stats = Stats(*new_stats)
        return level_str

    def options(self) -> list[str]:
        if getattr(self, "tunnel", False):
            action_list = []
            if not self.status_effects["Silence"].active and "Surface" in self.spellbook.get(
                "Skills", {}
            ):
                action_list.append("Use Skill")
            action_list.append("Support")
            return action_list

        action_list = ["Attack"]
        if not self.status_effects["Silence"].active:
            if self.spellbook["Skills"]:
                action_list.append("Use Skill")
            if self.spellbook["Spells"]:
                action_list.append("Cast Spell")
        action_list.append("Support")
        return action_list

    def inspect(self) -> str:
        inspect_str = f"{self.name} - Level {self.level.level}\n\n"
        inspect_str += self.description
        inspect_str += (
            f"{'Hit Points:':13}{' ':1}{self.health.current:3}/{self.health.max:>3}\n"
            f"{'Mana Points:':13}{' ':1}{self.mana.current:3}/{self.mana.max:>3}\n"
            f"{'Attack:':13}{' ':1}{self.combat.attack:>7}\n"
            f"{'Defense:':13}{' ':1}{self.combat.defense:>7}\n"
            f"{'Magic:':13}{' ':1}{self.combat.magic:>7}\n"
            f"{'Magic Defense:':13}{' ':1}{self.combat.magic_def:>7}\n"
        )
        return inspect_str


Xenid = Summons


def _conduit_level(conduit: int) -> int:
    """Map conduit strength to the legacy level slots used by ability tables."""
    conduit = max(0, min(100, int(conduit)))
    return (1, 3, 5, 7, 9, 10)[min(5, conduit // 20)]


def sync_xenid_conduit(
    player_char: Character,
    summon_name: str,
    conduit: int | None = None,
) -> None:
    """Apply conduit-driven stats and ability unlocks to one bound Xenid."""
    roster = getattr(player_char, "summons", {})
    xenid = roster.get(summon_name) if isinstance(roster, dict) else None
    if not isinstance(xenid, Summons):
        return
    if conduit is None:
        from .classes import promotion_kits

        conduit = promotion_kits.ensure_state(player_char)["summon_bonds"].get(
            summon_name,
            0,
        )
    conduit = max(0, min(100, int(conduit or 0)))
    base = getattr(xenid, "_conduit_base", None)
    if not isinstance(base, dict):
        base = {
            "health": xenid.health.max,
            "mana": xenid.mana.max,
            "stats": dict(xenid.stats.__dict__),
            "combat": dict(xenid.combat.__dict__),
        }
        xenid._conduit_base = base
    was_alive = xenid.health.current > 0
    health_ratio = xenid.health.current / xenid.health.max if xenid.health.max else 1.0
    mana_ratio = xenid.mana.current / xenid.mana.max if xenid.mana.max else 1.0
    resource_scale = 1.0 + 0.50 * conduit / 100
    rating_scale = 1.0 + 0.35 * conduit / 100
    xenid.health.max = max(1, int(base["health"] * resource_scale))
    xenid.health.current = (
        max(
            1,
            min(
                xenid.health.max,
                int(xenid.health.max * health_ratio),
            ),
        )
        if was_alive
        else 0
    )
    xenid.mana.max = max(0, int(base["mana"] * resource_scale))
    xenid.mana.current = max(
        0,
        min(
            xenid.mana.max,
            int(xenid.mana.max * mana_ratio),
        ),
    )
    xenid.stats = Stats(
        **{key: max(1, int(value * rating_scale)) for key, value in base["stats"].items()}
    )
    xenid.combat = Combat(
        **{key: max(1, int(value * rating_scale)) for key, value in base["combat"].items()}
    )
    xenid.level.level = _conduit_level(conduit)
    xenid.level.exp = 0
    xenid.level.exp_to_gain = 0
    ultimate_node = (
        f"thaumaturgist.talent."
        f"{next((category.lower() for category, names in XENID_PAIRS.items() if summon_name in names), '')}"
        "-ultimate"
    )
    purchased = getattr(
        getattr(player_char, "progression", None),
        "purchased_node_ids",
        set(),
    )
    for book, entries in summon_abilities.get(summon_name, {}).items():
        for level_text, ability_ctor in entries.items():
            level = int(level_text)
            if level > xenid.level.level or (level == 10 and ultimate_node not in purchased):
                continue
            ability = ability_ctor()
            xenid.spellbook[book][ability.name] = ability


def unlock_xenid_ultimate(
    player_char: Character,
    category: str,
) -> tuple[bool, str]:
    """Grant the selected Xenid's level-10 ultimate ability."""
    name = chosen_xenid(player_char, category)
    if not name:
        return False, f"Choose a {category.lower()} Xenid first."
    entries = summon_abilities.get(name, {})
    for book, abilities_by_level in entries.items():
        ability_ctor = abilities_by_level.get("10")
        if ability_ctor is None:
            continue
        ability = ability_ctor()
        player_char.summons[name].spellbook[book][ability.name] = ability
        return True, f"{name} unlocks its ultimate ability, {ability.name}."
    return False, f"{name} has no ultimate ability configured."


def chosen_xenid(player_char: Character, category: str) -> str | None:
    """Return the permanent Xenid choice for one Calling category."""
    choices = getattr(player_char, "xenid_choices", {})
    if not isinstance(choices, dict):
        return None
    choice = choices.get(category)
    if choice not in XENID_PAIRS.get(category, ()):
        return None
    return choice


def choose_xenid(player_char: Character, category: str, name: str) -> tuple[bool, str]:
    """Make one permanent paired Xenid choice and initialize its roster entry."""
    if name not in XENID_PAIRS.get(category, ()):
        return False, f"{name} is not a {category.lower()} Xenid."
    existing = chosen_xenid(player_char, category)
    if existing:
        if existing == name:
            return True, f"{name} is already the chosen {category.lower()} Xenid."
        return False, f"{existing} is already bound to the {category.lower()} Calling."

    xenid_type = globals().get(name)
    if xenid_type is None:
        return False, f"{name} is not available."
    xenid = xenid_type()
    xenid.initialize_stats(player_char)
    choices = getattr(player_char, "xenid_choices", None)
    if not isinstance(choices, dict):
        choices = {}
        player_char.xenid_choices = choices
    roster = getattr(player_char, "summons", None)
    if not isinstance(roster, dict):
        roster = {}
        player_char.summons = roster
    choices[category] = name
    roster[name] = xenid
    sync_xenid_conduit(player_char, name)
    return True, f"{name} is permanently bound to the {category.lower()} Calling."


class Hodag(Summons):
    """Bull-horned animal Xenid built for charging physical offense."""

    def __init__(self) -> None:
        super().__init__(
            name="Hodag",
            health=Resource(),
            mana=Resource(),
            stats=Stats(),
            combat=Combat(),
        )
        self.level.pro_level = 2
        self.start_stats = [245, 55, 27, 5, 10, 24, 8, 17]
        self.start_combat = [118, 82, 28, 58]
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Skills"]["Charge"] = abilities.Charge()
        self.spellbook["Skills"]["Crush"] = abilities.Crush()
        self.resistance["Physical"] = 0.25
        self.description = "A massive bull-horned carnivore protected by curved dorsal spines.\n\n"


class Caladrius(Summons):
    """Snow-white healing bird that draws sickness into itself."""

    def __init__(self) -> None:
        super().__init__(
            name="Caladrius",
            health=Resource(),
            mana=Resource(),
            stats=Stats(),
            combat=Combat(),
        )
        self.level.pro_level = 2
        self.start_stats = [175, 220, 10, 19, 27, 14, 19, 24]
        self.start_combat = [62, 70, 105, 112]
        self.equipment = {
            "Weapon": items.NoWeapon(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Spells"]["Heal"] = abilities.Heal2()
        self.spellbook["Spells"]["Cleanse"] = abilities.Cleanse()
        self.resistance["Holy"] = 0.75
        self.resistance["Poison"] = 0.75
        self.flying = True
        self.description = "A snow-white bird that absorbs sickness and disperses it in flight.\n\n"


class Patagon(Summons):
    """
    Level 1 Summon creature
    Giant mountain man with a giant club; one Humanoid Calling choice.

    Abilities:
    Level 1 (start)
    - Throw Rock
    - Charge
    Level 3
    - Piercing Strike
    Level 5
    - Stomp
    Level 7
    - Mortal Strike
    Level 9
    - Crush
    Level 10
    - Titanic Slam
    """

    def __init__(self) -> None:
        super().__init__(
            name="Patagon", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.level.pro_level = 1
        self.start_stats = [125, 85, 20, 5, 8, 15, 3, 14]
        self.start_combat = [75, 40, 15, 25]
        self.equipment = {
            "Weapon": items.GiantClub(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Skills"]["Throw Rock"] = abilities.ThrowRock()
        self.spellbook["Skills"]["Charge"] = abilities.Charge()
        self.resistance["Holy"] = -0.3
        self.resistance["Poison"] = 0.33
        self.resistance["Physical"] = 0.2
        self.description = "A giant mountain man that wields a giant club.\n\n"


class Dilong(Summons):
    """
    Summon creature
    Sandworm; unlocked by retrieving Chiryu Koma item from Xorn enemy and taking it to 1:I17

    Abilities:
    Level 1 (start)
    - Tremor
    - Tunnel
    Level 3
    - Slam
    Level 5
    - Mudslide
    Level 7
    - Consume Item
    Level 9
    - Earthquake
    Level 10
    - Devour
    """

    def __init__(self) -> None:
        super().__init__(
            name="Dilong", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.level.pro_level = 2
        self.start_stats = [225, 118, 24, 7, 12, 23, 4, 15]
        self.start_combat = [105, 80, 65, 55]
        self.equipment = {
            "Weapon": items.EarthMaw(),
            "Armor": items.SnakeScales2(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Spells"]["Tremor"] = abilities.Tremor()
        self.spellbook["Skills"]["Tunnel"] = abilities.Tunnel()
        self.spellbook["Skills"]["Surface"] = abilities.Surface()
        self.resistance["Water"] = -0.5
        self.resistance["Earth"] = 1.0
        self.status_immunity = ["Stone"]
        self.description = "A sandworm that can harness the power of the Earth.\n\n"


class Agloolik(Summons):
    """
    Summon creature
    Ice spirit; unlocked after defeating Wendigo

    Abilities:
    Level 1 (start)
    - Ice Lance
    - Piercing Strike
    Level 3
    - Ice Block
    Level 5
    - Icicle
    Level 7
    - True Piercing Strike
    Level 9
    - Blizzard
    Level 10
    - Absolute Zero
    """

    def __init__(self) -> None:
        super().__init__(
            name="Agloolik", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.level.pro_level = 2
        self.start_stats = [190, 168, 18, 15, 13, 12, 9, 18]
        self.start_combat = [80, 55, 88, 70]
        self.equipment = {
            "Weapon": items.IceShard(),
            "Armor": items.NoArmor(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Spells"]["Ice Lance"] = abilities.IceLance()
        self.spellbook["Skills"]["Piercing Strike"] = abilities.PiercingStrike()
        self.resistance["Fire"] = -0.5
        self.resistance["Ice"] = 1.25
        self.resistance["Physical"] = -0.2
        self.description = (
            "An ice spirit, said to provide aid to fishermen and hunters in the Inuit culture.\n\n"
        )


class Cacus(Summons):
    """
    Summon creature
    Fire breathing monster; unlocked by retrieving Vulcan's Hammer item from Griswold after obtaining the first 2
      relics and taking it to 2:F13

    Abilities:
    Level 1 (start)
    - Scorch
    - Mortal Strike
    Level 3
    - Vulcanize
    Level 5
    - Molten Rock
    Level 7
    - Mortal Strike 2
    Level 9
    - Volcano
    Level 10
    - Eruption
    """

    def __init__(self) -> None:
        super().__init__(
            name="Cacus", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.level.pro_level = 2
        self.start_stats = [215, 112, 25, 11, 13, 21, 7, 15]
        self.start_combat = [110, 60, 90, 65]
        self.equipment = {
            "Weapon": items.VulcansHammer(),
            "Armor": items.Splint(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Spells"]["Scorch"] = abilities.Scorch()
        self.spellbook["Skills"]["Mortal Strike"] = abilities.MortalStrike()
        self.resistance["Fire"] = 1.0
        self.resistance["Ice"] = -0.75
        self.resistance["Physical"] = 0.2
        self.description = "A fire-breathing monster and the son of the fire god Vulcan.\n\n"


class Izulu(Summons):
    """
    Summon creature
    Avian, vampiric lightning spirit

    Abilities:
    Level 1 (start)
    - Shock
    - True Strike
    Level 3
    - Berserk
    Level 5
    - Lightning
    Level 7
    - True Piercing Strike
    Level 9
    - Electrocution
    Level 10
    - Thunderstrike
    """

    def __init__(self) -> None:
        super().__init__(
            name="Izulu", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.level.pro_level = 2
        self.start_stats = [212, 123, 18, 11, 12, 14, 13, 22]
        self.start_combat = [85, 50, 86, 62]
        self.equipment = {
            "Weapon": items.VampireBite(),
            "Armor": items.NoArmor(),
            "OffHand": items.VampireBite(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Spells"]["Shock"] = abilities.Shock()
        self.spellbook["Skills"]["True Strike"] = abilities.TrueStrike()
        self.resistance["Electric"] = 1.0
        self.resistance["Water"] = -0.5
        self.resistance["Wind"] = -0.5
        self.resistance["Shadow"] = 0.5
        self.status_immunity = ["Death"]
        self.flying = True
        self.description = (
            "The lightning bird, a vampiric spirit with an insatiable lust for blood.\n\n"
        )


class Hala(Summons):
    """
    Summon creature
    Wind demon

    Abilities:
    Level 1 (start)
    - Parry
    - Gust
    Level 3
    - Double Strike
    Level 5
    - Hurricane
    Level 7
    - Wind Speed
    Level 9
    - Tornado
    Level 10
    - Wind Shrapnel
    """

    def __init__(self) -> None:
        super().__init__(
            name="Hala", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.level.pro_level = 2
        self.start_stats = [224, 109, 20, 12, 9, 15, 10, 24]
        self.start_combat = [105, 65, 72, 60]
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.DemonArmor(),
            "OffHand": items.DemonClaw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Skills"]["Parry"] = abilities.Parry()
        self.spellbook["Spells"]["Gust"] = abilities.Gust()
        self.resistance["Wind"] = 1.0
        self.resistance["Shadow"] = 0.5
        self.resistance["Holy"] = -1.0
        self.status_immunity = ["Death"]
        self.flying = True
        self.description = (
            "A female demon that can harness the power of the wind for devious purposes.\n\n"
        )


class Lamashtu(Summons):
    """Grotesque fiend Xenid specializing in curses and poison."""

    def __init__(self) -> None:
        super().__init__(
            name="Lamashtu",
            health=Resource(),
            mana=Resource(),
            stats=Stats(),
            combat=Combat(),
        )
        self.level.pro_level = 4
        self.start_stats = [330, 290, 24, 27, 20, 28, 22, 17]
        self.start_combat = [135, 85, 145, 110]
        self.equipment = {
            "Weapon": items.Claw2(),
            "Armor": items.DemonArmor2(),
            "OffHand": items.DemonClaw(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Spells"]["Corruption"] = abilities.Corruption()
        self.spellbook["Spells"]["Enfeeble"] = abilities.Enfeeble()
        self.spellbook["Skills"]["Screech"] = abilities.Screech()
        self.resistance["Shadow"] = 1.0
        self.resistance["Holy"] = -1.0
        self.resistance["Poison"] = 1.0
        self.status_immunity = ["Death", "Poison"]
        self.description = "A grotesque demoness who spreads disease, curses, and terror.\n\n"


class Seraphim(Summons):
    """
    Summon creature
    An angelic spirit known as the Watcher

    Abilities:
    Level 1 (start)
    - Smite 2
    - Holy 2
    - Shield Slam
    Level 3
    - Divine Protection
    Level 5
    - Regen 2
    Level 7
    - Holy 3
    Level 9
    - Resurrection
    Level 10
    - Divine Judgment
    """

    def __init__(self) -> None:
        super().__init__(
            name="Seraphim", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.level.pro_level = 3
        self.start_stats = [280, 205, 29, 12, 18, 30, 14, 12]
        self.start_combat = [130, 90, 115, 105]
        self.equipment = {
            "Weapon": items.Pernach(),
            "Armor": items.Breastplate(),
            "OffHand": items.KiteShield(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Spells"]["Smite"] = abilities.Smite2()
        self.spellbook["Spells"]["Holy"] = abilities.Holy2()
        self.spellbook["Skills"]["Shield Slam"] = abilities.ShieldSlam()
        self.resistance["Shadow"] = -0.25
        self.resistance["Holy"] = 1.25
        self.status_immunity = ["Death"]
        self.flying = True
        self.description = "A radiant high angel that serves Elysia without question.\n\n"


class Bardi(Summons):
    """
    Summon creature
    death spirit, perhaps modeled after Anima from FFX

    Abilities:
    Level 1 (start)
    - Battle Cry
    - Double Strike
    - Shadow Bolt 2
    - Blinding Fog
    Level 3
    - Corruption
    Level 5
    - Sleeping Powder
    Level 7
    - Ruin
    Level 9
    - Shadow Bolt 3
    Level 10
    - Oblivion
    """

    def __init__(self) -> None:
        super().__init__(
            name="Bardi", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.level.pro_level = 4
        self.start_stats = [321, 285, 32, 19, 22, 27, 19, 18]
        self.start_combat = [155, 80, 132, 95]
        self.equipment = {
            "Weapon": items.Scythe(),
            "Armor": items.DemonArmor2(),
            "OffHand": items.NoOffHand(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Skills"]["Battle Cry"] = abilities.BattleCry()
        self.spellbook["Skills"]["Double Strike"] = abilities.DoubleStrike()
        self.spellbook["Spells"]["Shadow Bolt"] = abilities.ShadowBolt2()
        self.spellbook["Spells"]["Blinding Fog"] = abilities.BlindingFog()
        self.resistance["Shadow"] = 0.25
        self.resistance["Holy"] = -0.5
        self.status_immunity = ["Death"]
        self.description = "An evil spirit, the bringer of Death and darkness.\n\n"


class Kobalos(Summons):
    """
    Summon creature
    Goblin thief/trickster; unlocked once Jester is defeated and Joker obtained
    Chance to turn on user, will either fight or steal and run

    Abilities:
    Level 1 (start)
    - Steal
    - Backstab
    - Pocket Sand
    - Gold Toss
    Level 3
    - Poison Strike
    Level 5
    - Mug
    Level 7
    - Sneak Attack
    Level 9
    - Slot Machine
    Level 10
    - Grand Heist
    """

    def __init__(self) -> None:
        super().__init__(
            name="Kobalos", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.level.pro_level = 4
        self.start_stats = [365, 305, 23, 14, 13, 19, 20, 25]
        self.start_combat = [130, 75, 55, 65]
        self.summon_gold_cost = 100
        self.equipment = {
            "Weapon": items.KoboldDagger(),
            "Armor": items.StuddedCuirboulli(),
            "OffHand": items.KoboldDagger(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Skills"]["Steal"] = abilities.Steal()
        self.spellbook["Skills"]["Backstab"] = abilities.Backstab()
        self.spellbook["Skills"]["Pocket Sand"] = abilities.PocketSand()
        self.spellbook["Skills"]["Gold Toss"] = abilities.GoldToss()
        self.resistance = {
            "Fire": 0.1,
            "Ice": 0.1,
            "Electric": 0.1,
            "Water": 0.1,
            "Earth": 0.1,
            "Wind": 0.1,
            "Shadow": 0.1,
            "Holy": 0.0,
            "Poison": 1.0,
            "Physical": 0.0,
        }
        self.status_immunity.append("Poison")
        self.invisible = True
        self.description = "A filthy little trickster. Watch your back with this guy around.\n\n"


class Tiamat(Summons):
    """Massive sea-dragon Xenid specializing in water magic."""

    def __init__(self) -> None:
        super().__init__(
            name="Tiamat",
            health=Resource(),
            mana=Resource(),
            stats=Stats(),
            combat=Combat(),
        )
        self.level.pro_level = 5
        self.start_stats = [485, 420, 35, 31, 30, 38, 24, 20]
        self.start_combat = [195, 125, 175, 145]
        self.equipment = {
            "Weapon": items.DragonClaw2(),
            "Armor": items.DragonScale(),
            "OffHand": items.DragonTail2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Spells"]["Water Jet"] = abilities.WaterJet()
        self.spellbook["Spells"]["Tsunami"] = abilities.Tsunami()
        self.spellbook["Skills"]["Slam"] = abilities.Slam()
        self.resistance["Water"] = 1.25
        self.resistance["Electric"] = -0.75
        self.resistance["Physical"] = 0.25
        self.status_immunity = ["Poison"]
        self.description = "A massive sea dragon whose coils churn entire oceans.\n\n"


class Zahhak(Summons):
    """
    Summon creature
    Non-elemental red dragon spirit; obtained by beating the Red Dragon
    Has special attack Breathe Fire

    Abilities:
    Level 1 (start)
    - Magic Missile 2
    - Mirror Image
    - Heal 3
    - Reflect
    Level 3
    - Magic Missile 3
    Level 5
    - Photon Sphere
    Level 7
    - Disintegrate
    Level 9
    - Meteor
    Level 10
    - Cataclysm
    """

    def __init__(self) -> None:
        super().__init__(
            name="Zahhak", health=Resource(), mana=Resource(), stats=Stats(), combat=Combat()
        )
        self.level.pro_level = 5
        self.start_stats = [455, 402, 32, 29, 31, 35, 23, 26]
        self.start_combat = [190, 100, 165, 130]
        self.equipment = {
            "Weapon": items.DragonClaw2(),
            "Armor": items.DragonScale(),
            "OffHand": items.DragonTail2(),
            "Ring": items.NoRing(),
            "Pendant": items.NoPendant(),
        }
        self.spellbook["Spells"]["Magic Missile"] = abilities.MagicMissile2()
        self.spellbook["Spells"]["Mirror Image"] = abilities.MirrorImage()
        self.spellbook["Spells"]["Heal"] = abilities.Heal3()
        self.spellbook["Spells"]["Reflect"] = abilities.Reflect()
        self.resistance = {
            "Fire": 0.25,
            "Ice": 0.25,
            "Electric": 0.25,
            "Water": 0.25,
            "Earth": 0.25,
            "Wind": 0.25,
            "Shadow": 0.25,
            "Holy": 0.25,
            "Poison": 1.0,
            "Physical": 0.25,
        }
        self.status_immunity.append("Poison")
        self.description = "A dragon ally whose elemental wards and spellcraft grow with level."

    def special_attack(self, target: Character) -> str:
        return abilities.BreatheFire().use(self, target=target)


summon_abilities = {
    "Hodag": {
        "Skills": {
            "3": abilities.MortalStrike,
            "5": abilities.Stomp,
            "7": abilities.MortalStrike2,
            "9": abilities.Crush,
            "10": abilities.TitanicSlam,
        },
        "Spells": {},
    },
    "Caladrius": {
        "Skills": {},
        "Spells": {
            "3": abilities.Reflect,
            "5": abilities.Heal3,
            "7": abilities.Regen3,
            "9": abilities.DivineProtection,
            "10": abilities.Resurrection,
        },
    },
    "Patagon": {
        "Skills": {
            "3": abilities.PiercingStrike,
            "5": abilities.Stomp,
            "7": abilities.MortalStrike,
            "9": abilities.Crush,
            "10": abilities.TitanicSlam,
        },
        "Spells": {},
    },
    "Dilong": {
        "Skills": {"3": abilities.Slam, "7": abilities.ConsumeItem, "10": abilities.Devour},
        "Spells": {"5": abilities.Mudslide, "9": abilities.Earthquake},
    },
    "Agloolik": {
        "Skills": {"7": abilities.TruePiercingStrike},
        "Spells": {
            "3": abilities.IceBlock,
            "5": abilities.Icicle,
            "9": abilities.IceBlizzard,
            "10": abilities.AbsoluteZero,
        },
    },
    "Cacus": {
        "Skills": {"7": abilities.MortalStrike2},
        "Spells": {
            "3": abilities.Vulcanize,
            "5": abilities.MoltenRock,
            "9": abilities.Volcano,
            "10": abilities.Eruption,
        },
    },
    "Izulu": {
        "Skills": {"7": abilities.TruePiercingStrike},
        "Spells": {
            "3": abilities.Berserk,
            "5": abilities.Lightning,
            "9": abilities.Electrocution,
            "10": abilities.Thunderstrike,
        },
    },
    "Hala": {
        "Skills": {"3": abilities.DoubleStrike},
        "Spells": {
            "5": abilities.Hurricane,
            "7": abilities.WindSpeed,
            "9": abilities.Tornado,
            "10": abilities.WindShrapnel,
        },
    },
    "Lamashtu": {
        "Skills": {},
        "Spells": {
            "3": abilities.Terrify,
            "5": abilities.PoisonBreath,
            "7": abilities.WeakenMind,
            "9": abilities.Corruption2,
            "10": abilities.Oblivion,
        },
    },
    "Seraphim": {
        "Skills": {},
        "Spells": {
            "3": abilities.DivineProtection,
            "5": abilities.Regen2,
            "7": abilities.Holy3,
            "9": abilities.Resurrection,
            "10": abilities.DivineJudgment,
        },
    },
    "Bardi": {
        "Skills": {"5": abilities.SleepingPowder},
        "Spells": {
            "3": abilities.Corruption,
            "7": abilities.Ruin,
            "9": abilities.ShadowBolt3,
            "10": abilities.Oblivion,
        },
    },
    "Kobalos": {
        "Skills": {
            "5": abilities.Mug,
            "7": abilities.SneakAttack,
            "9": abilities.SlotMachine,
            "10": abilities.GrandHeist,
        },
        "Spells": {"3": abilities.PoisonStrike},
    },
    "Tiamat": {
        "Skills": {"3": abilities.PiercingStrike, "7": abilities.TruePiercingStrike},
        "Spells": {
            "5": abilities.Hydration,
            "9": abilities.Tsunami,
            "10": abilities.MaelstromVortex,
        },
    },
    "Zahhak": {
        "Skills": {},
        "Spells": {
            "3": abilities.MagicMissile3,
            "5": abilities.PhotonSphere,
            "7": abilities.Disintegrate,
            "9": abilities.Meteor,
            "10": abilities.Cataclysm,
        },
    },
}
