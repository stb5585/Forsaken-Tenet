"""Render reviewable CSV snapshots of the authoritative game catalogs."""

from __future__ import annotations

import csv
import inspect
import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

from src.core.randomness import gameplay_random as random

from . import abilities, companions, enemies, items
from .classes.astromancer import LEARNABLE_SPELL_RANKS
from .data.data_loader import load_json_data
from .enemies.catalog import (
    FIXED_LOCATION_HINTS,
    FUNHOUSE_ENEMY_SPECS,
    RANDOM_ENEMY_SPECS,
    is_boss_enemy,
)
from .progression import (
    ABILITY_TREES,
    CLASS_CHILDREN,
    CLASS_DETAILS,
    NodeKind,
    effective_node_level_requirement,
)
from .progression_manifest import EXTERNAL_ACQUISITION_ABILITIES
from .races import races_dict

OUTPUT_DIRECTORY = Path(__file__).parents[2] / "docs" / "spreadsheets"
RESISTANCE_TYPES = (
    "Fire",
    "Ice",
    "Electric",
    "Water",
    "Earth",
    "Wind",
    "Shadow",
    "Holy",
    "Poison",
    "Physical",
)
STAT_FIELDS = (
    ("Strength", "strength"),
    ("Intelligence", "intel"),
    ("Wisdom", "wisdom"),
    ("Constitution", "con"),
    ("Charisma", "charisma"),
    ("Dexterity", "dex"),
)
COMBAT_FIELDS = (
    ("Attack", "attack"),
    ("Defense", "defense"),
    ("Magic", "magic"),
    ("Magic Defense", "magic_def"),
)


def _clean(value: Any) -> str:
    """Return compact single-line spreadsheet text."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _csv_text(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_clean(value) for value in row])
    return output.getvalue()


def _base_class(class_name: str) -> str:
    current = class_name
    while CLASS_DETAILS[current][2] is not None:
        current = str(CLASS_DETAILS[current][2])
    return current


def _stage_name(stage: int) -> str:
    return {1: "Base", 2: "First Promotion", 3: "Second Promotion"}[stage]


def _power_up_names() -> dict[str, str]:
    from .player.combat import _SPECIAL_POWER_ABILITIES

    return {
        class_name: constructor().name
        for class_name, constructor in _SPECIAL_POWER_ABILITIES.items()
    }


def _render_character_exports() -> dict[Path, str]:
    exports: dict[Path, str] = {}
    powers = _power_up_names()
    class_headers = [
        "Name",
        "Stage",
        "Parent",
        "Base Class",
        "Promotions",
        "Power Core Ability",
        *(name for name, _attribute in STAT_FIELDS),
        *(name for name, _attribute in COMBAT_FIELDS),
        "Weapons",
        "Off Hands",
        "Armor",
        "Helmets",
        "Starting Equipment",
        "Description",
    ]
    class_rows = []
    for class_name, (constructor, stage, parent) in sorted(
        CLASS_DETAILS.items(),
        key=lambda entry: (_base_class(entry[0]), entry[1][1], entry[0]),
    ):
        job = constructor()
        restrictions = job.restrictions
        class_rows.append(
            (
                class_name,
                _stage_name(stage),
                parent or "",
                _base_class(class_name),
                "; ".join(CLASS_CHILDREN.get(class_name, ())),
                powers.get(class_name, ""),
                *(
                    getattr(job, attribute)
                    for _name, attribute in (
                        ("Strength", "str_plus"),
                        ("Intelligence", "int_plus"),
                        ("Wisdom", "wis_plus"),
                        ("Constitution", "con_plus"),
                        ("Charisma", "cha_plus"),
                        ("Dexterity", "dex_plus"),
                    )
                ),
                *(
                    getattr(job, attribute)
                    for _name, attribute in (
                        ("Attack", "att_plus"),
                        ("Defense", "def_plus"),
                        ("Magic", "magic_plus"),
                        ("Magic Defense", "magic_def_plus"),
                    )
                ),
                "; ".join(restrictions.get("Weapon", ())),
                "; ".join(restrictions.get("OffHand", ())),
                "; ".join(restrictions.get("Armor", ())),
                "; ".join(restrictions.get("Helmet", ())),
                "; ".join(
                    f"{slot}: {equipment.name}"
                    for slot, equipment in job.equipment.items()
                    if not getattr(equipment, "unequip", False)
                ),
                job.description,
            )
        )
    exports[Path("characters/classes.csv")] = _csv_text(class_headers, class_rows)

    restriction_headers = ["Class", "Stage", "Weapon", "OffHand", "Armor", "Helmet"]
    restriction_rows = []
    for class_name, (constructor, stage, _parent) in sorted(CLASS_DETAILS.items()):
        restrictions = constructor().restrictions
        restriction_rows.append(
            (
                class_name,
                _stage_name(stage),
                "; ".join(restrictions.get("Weapon", ())),
                "; ".join(restrictions.get("OffHand", ())),
                "; ".join(restrictions.get("Armor", ())),
                "; ".join(restrictions.get("Helmet", ())),
            )
        )
    exports[Path("characters/equipment-restrictions.csv")] = _csv_text(
        restriction_headers,
        restriction_rows,
    )

    node_headers = [
        "Class",
        "Stage",
        "Parent",
        "Power Core Ability",
        *(f"{name} Bonus" for name, _attribute in STAT_FIELDS),
        *(f"{name} Bonus" for name, _attribute in COMBAT_FIELDS),
        "Weapons",
        "Off Hands",
        "Armor",
        "Helmets",
        "Class Description",
        "Node ID",
        "Lane",
        "Column",
        "Row",
        "Kind",
        "Name",
        "Cost",
        "Level",
        "Prerequisites",
        "Node Description",
    ]
    for class_name, tree in sorted(ABILITY_TREES.items()):
        constructor, stage, parent = CLASS_DETAILS[class_name]
        job = constructor()
        restrictions = job.restrictions
        class_prefix = (
            class_name,
            _stage_name(stage),
            parent or "",
            powers.get(class_name, ""),
            job.str_plus,
            job.int_plus,
            job.wis_plus,
            job.con_plus,
            job.cha_plus,
            job.dex_plus,
            job.att_plus,
            job.def_plus,
            job.magic_plus,
            job.magic_def_plus,
            "; ".join(restrictions.get("Weapon", ())),
            "; ".join(restrictions.get("OffHand", ())),
            "; ".join(restrictions.get("Armor", ())),
            "; ".join(restrictions.get("Helmet", ())),
            job.description,
        )
        node_rows = []
        for node in sorted(tree.nodes, key=lambda entry: (entry.position[0], entry.position[1])):
            node_rows.append(
                (
                    *class_prefix,
                    node.id,
                    node.lane,
                    node.position[0],
                    node.position[1],
                    node.kind.value,
                    node.name,
                    node.cost,
                    effective_node_level_requirement(node, class_name) or "",
                    "; ".join(node.prerequisites),
                    node.payload.get("description", ""),
                )
            )
        exports[Path(f"characters/classes/{_slug(class_name)}.csv")] = _csv_text(
            node_headers,
            node_rows,
        )

    race_headers = [
        "Race",
        *(name for name, _attribute in STAT_FIELDS),
        "Base Attack",
        "Base Defense",
        "Base Magic",
        "Base Magic Defense",
        *(f"{name} Resistance" for name in RESISTANCE_TYPES),
        "Virtue",
        "Virtue Effect",
        "Sin",
        "Sin Effect",
        "Description",
    ]
    race_rows = []
    for race_name, constructor in races_dict.items():
        race = constructor()
        race_rows.append(
            (
                race_name,
                *(getattr(race, attribute) for _name, attribute in STAT_FIELDS),
                race.base_attack,
                race.base_defense,
                race.base_magic,
                race.base_magic_def,
                *(race.resistance.get(name, 0) for name in RESISTANCE_TYPES),
                race.virtue.name,
                race.virtue.description,
                race.sin.name,
                race.sin.description,
                race.description,
            )
        )
        race_prefix = (
            race_name,
            *(getattr(race, attribute) for _name, attribute in STAT_FIELDS),
            race.base_attack,
            race.base_defense,
            race.base_magic,
            race.base_magic_def,
            *(race.resistance.get(name, 0) for name in RESISTANCE_TYPES),
            race.virtue.name,
            race.virtue.description,
            race.sin.name,
            race.sin.description,
            race.description,
        )
        class_rows_for_race = []
        for stage in ("Base", "First", "Second"):
            for available_class in race.cls_res.get(stage, ()):
                class_rows_for_race.append((*race_prefix, stage, available_class))
        exports[Path(f"characters/races/{_slug(race_name)}.csv")] = _csv_text(
            (*race_headers, "Stage", "Available Class"),
            class_rows_for_race,
        )
    exports[Path("characters/races.csv")] = _csv_text(race_headers, race_rows)

    companion_rows = []
    for name, constructor in inspect.getmembers(companions, inspect.isclass):
        if name.startswith("_") or constructor in {companions.Familiar, companions.Summons}:
            continue
        if not issubclass(constructor, companions.Familiar):
            continue
        try:
            companion = constructor()
        except TypeError:
            continue
        category = "Xenid" if isinstance(companion, companions.Summons) else "Familiar"
        specials = [
            *companion.spellbook.get("Spells", {}).keys(),
            *companion.spellbook.get("Skills", {}).keys(),
        ]
        companion_rows.append(
            (
                companion.name,
                name,
                category,
                getattr(companion, "spec", ""),
                companion.health.max,
                companion.mana.max,
                "; ".join(specials),
                getattr(companion, "description", ""),
            )
        )
    exports[Path("characters/companions.csv")] = _csv_text(
        ("Name", "Class ID", "Category", "Specialization", "HP", "MP", "Specials", "Description"),
        sorted(companion_rows),
    )
    return exports


def _zero_argument_instances(module: Any, base_class: type) -> list[tuple[str, Any, type]]:
    instances = []
    seen: set[type] = set()
    for name, constructor in inspect.getmembers(module, inspect.isclass):
        if name.startswith("_") or constructor in seen:
            continue
        if constructor is base_class or not issubclass(constructor, base_class):
            continue
        seen.add(constructor)
        try:
            instance = constructor()
        except TypeError:
            continue
        instances.append((name, instance, constructor))
    return instances


def _item_rows() -> list[tuple[Any, ...]]:
    rows = []
    random_state = random.getstate()
    random.seed(0)
    try:
        instances = _zero_argument_instances(items, items.Item)
    finally:
        random.setstate(random_state)
    for class_id, item, _constructor in instances:
        rows.append(
            (
                item.name,
                class_id,
                getattr(item, "typ", ""),
                item.subtyp,
                item.value,
                item.rarity,
                item.weight,
                getattr(item, "damage", ""),
                getattr(item, "crit_chance", ""),
                getattr(item, "handed", ""),
                getattr(item, "off", ""),
                getattr(item, "armor", ""),
                getattr(item, "mod", ""),
                getattr(item, "element", ""),
                "; ".join(getattr(item, "restriction", ())),
                "; ".join(getattr(item, "restricted_against", ())),
                getattr(item, "ultimate", False),
                getattr(item, "random_drop", True),
                getattr(item, "unequip", False),
                item.description,
            )
        )
    return sorted(rows, key=lambda row: (str(row[2]), str(row[3]), str(row[0]), str(row[1])))


def _render_item_exports() -> dict[Path, str]:
    headers = (
        "Name",
        "Class ID",
        "Type",
        "Subtype",
        "Value",
        "Rarity",
        "Weight",
        "Damage",
        "Critical Chance",
        "Hands",
        "Offhand Eligible",
        "Armor",
        "Modifier",
        "Element",
        "Restricted To",
        "Restricted Against",
        "Ultimate",
        "Random Drop",
        "Unequipped",
        "Description",
    )
    rows = _item_rows()
    categories = {
        "weapons.csv": lambda row: row[2] == "Weapon" and row[3] != "Natural",
        "natural-equipment.csv": lambda row: row[3] == "Natural",
        "off-hands.csv": lambda row: row[2] == "OffHand",
        "armor.csv": lambda row: row[2] == "Armor" and row[3] != "Natural",
        "helmets.csv": lambda row: row[2] == "Helmet",
        "accessories.csv": lambda row: row[2] == "Accessory",
        "potions.csv": lambda row: row[2] == "Potion",
        "misc.csv": lambda row: row[2] == "Misc",
    }
    exports = {Path("items/all-items.csv"): _csv_text(headers, rows)}
    for filename, predicate in categories.items():
        exports[Path(f"items/{filename}")] = _csv_text(
            headers,
            (row for row in rows if predicate(row)),
        )
    return exports


def _catalog_ability_sources() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    class_sources: dict[str, set[str]] = defaultdict(set)
    books: dict[str, set[str]] = defaultdict(set)
    for class_name, tree in ABILITY_TREES.items():
        for node in tree.nodes:
            if node.kind != NodeKind.ABILITY:
                continue
            constructor = node.payload.get("ability_class")
            if constructor is None:
                continue
            class_id = constructor.__name__
            class_sources[class_id].add(class_name)
            books[class_id].add(str(node.payload.get("book", "")))
    for book, catalog in (("Spells", abilities.spell_dict), ("Skills", abilities.skill_dict)):
        for class_name, levels in catalog.items():
            for constructors in levels.values():
                for constructor in abilities.ability_classes_for(constructors):
                    class_sources[constructor.__name__].add(class_name)
                    books[constructor.__name__].add(book)
    return class_sources, books


def _ability_instances() -> list[tuple[str, Any, type]]:
    """Instantiate public ability constructors, including YAML proxy classes."""
    instances = []
    seen: set[type] = set()
    random_state = random.getstate()
    random.seed(0)
    try:
        for class_id, constructor in inspect.getmembers(abilities, inspect.isclass):
            if class_id.startswith("_") or constructor in seen:
                continue
            if not constructor.__module__.startswith("src.core"):
                continue
            seen.add(constructor)
            try:
                ability = constructor()
            except TypeError:
                continue
            if not isinstance(ability, abilities.Ability) or not getattr(ability, "name", ""):
                continue
            instances.append((class_id, ability, constructor))
    finally:
        random.setstate(random_state)
    return instances


def _enemy_constructors() -> dict[str, Callable[[], Any]]:
    constructors: dict[str, Callable[[], Any]] = {}
    for specs in (*RANDOM_ENEMY_SPECS.values(), FUNHOUSE_ENEMY_SPECS):
        for _display_name, class_id in specs:
            constructor = getattr(enemies, class_id)
            constructors[class_id] = constructor
    random_state = random.getstate()
    random.seed(0)
    try:
        public_enemies = _zero_argument_instances(enemies, enemies.Enemy)
    finally:
        random.setstate(random_state)
    for class_id, _instance, constructor in public_enemies:
        constructors[class_id] = constructor
    return constructors


def _extreme_enemy(constructor: Callable[[], Any], *, high: bool) -> Any:
    def randint(low: int, upper: int) -> int:
        return upper if high else low

    def uniform(low: float, upper: float) -> float:
        return upper if high else low

    def choice(values: Sequence[Any]) -> Any:
        return values[-1] if high else values[0]

    def choices(values: Sequence[Any], **_kwargs: Any) -> list[Any]:
        return [choice(values)]

    def shuffle(values: list[Any]) -> None:
        if high:
            values.reverse()

    def random_value() -> float:
        return 1.0 if high else 0.0

    with (
        patch.object(random, "randint", randint),
        patch.object(random, "uniform", uniform),
        patch.object(random, "choice", choice),
        patch.object(random, "choices", choices),
        patch.object(random, "shuffle", shuffle),
        patch.object(random, "random", random_value),
    ):
        return constructor()


def _enemy_records() -> list[dict[str, Any]]:
    floors: dict[str, set[str]] = defaultdict(set)
    for floor, specs in RANDOM_ENEMY_SPECS.items():
        for _display_name, class_id in specs:
            floors[class_id].add(floor)
    funhouse_ids = {class_id for _display_name, class_id in FUNHOUSE_ENEMY_SPECS}
    records = []
    for class_id, constructor in sorted(_enemy_constructors().items()):
        try:
            low = _extreme_enemy(constructor, high=False)
            high = _extreme_enemy(constructor, high=True)
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            continue
        spell_names = tuple(
            sorted(
                {
                    *low.spellbook.get("Spells", {}).keys(),
                    *high.spellbook.get("Spells", {}).keys(),
                }
            )
        )
        skill_names = tuple(
            sorted(
                {
                    *low.spellbook.get("Skills", {}).keys(),
                    *high.spellbook.get("Skills", {}).keys(),
                }
            )
        )
        record = {
            "Name": low.name,
            "Class ID": class_id,
            "Type": low.enemy_typ,
            "Floors": "; ".join(sorted(floors.get(class_id, ()), key=int)),
            "Locations": "; ".join(FIXED_LOCATION_HINTS.get(low.name, ())),
            "Funhouse": class_id in funhouse_ids,
            "Boss": is_boss_enemy(low),
            "HP Min": min(low.health.max, high.health.max),
            "HP Max": max(low.health.max, high.health.max),
            "MP Min": min(low.mana.max, high.mana.max),
            "MP Max": max(low.mana.max, high.mana.max),
            "Experience Min": min(low.experience, high.experience),
            "Experience Max": max(low.experience, high.experience),
            "Promotion Level": getattr(low.level, "pro_level", ""),
            "Spells": "; ".join(spell_names),
            "Skills": "; ".join(skill_names),
            "Equipment": "; ".join(
                f"{slot}: {equipment.name}"
                for slot, equipment in low.equipment.items()
                if not getattr(equipment, "unequip", False)
            ),
            "Drops": "; ".join(low.inventory.keys()),
            "Status Immunities": "; ".join(low.status_immunity),
        }
        for label, attribute in STAT_FIELDS:
            record[f"{label} Min"] = min(
                getattr(low.stats, attribute),
                getattr(high.stats, attribute),
            )
            record[f"{label} Max"] = max(
                getattr(low.stats, attribute),
                getattr(high.stats, attribute),
            )
        for label, attribute in COMBAT_FIELDS:
            record[f"{label} Min"] = min(
                getattr(low.combat, attribute),
                getattr(high.combat, attribute),
            )
            record[f"{label} Max"] = max(
                getattr(low.combat, attribute),
                getattr(high.combat, attribute),
            )
        for resistance in RESISTANCE_TYPES:
            record[f"{resistance} Resistance"] = low.resistance.get(resistance, 0)
        records.append(record)
    return sorted(records, key=lambda record: (record["Name"], record["Class ID"]))


def _render_enemy_exports() -> dict[Path, str]:
    records = _enemy_records()
    headers = (
        "Name",
        "Class ID",
        "Type",
        "Floors",
        "Locations",
        "Funhouse",
        "Boss",
        "HP Min",
        "HP Max",
        "MP Min",
        "MP Max",
        "Experience Min",
        "Experience Max",
        *(field for label, _attribute in STAT_FIELDS for field in (f"{label} Min", f"{label} Max")),
        *(
            field
            for label, _attribute in COMBAT_FIELDS
            for field in (f"{label} Min", f"{label} Max")
        ),
        "Promotion Level",
        "Spells",
        "Skills",
        "Equipment",
        "Drops",
        "Status Immunities",
        *(f"{name} Resistance" for name in RESISTANCE_TYPES),
    )

    def rows(selected: Iterable[dict[str, Any]]) -> Iterable[tuple[Any, ...]]:
        return (tuple(record.get(header, "") for header in headers) for record in selected)

    exports = {Path("enemies/all-enemies.csv"): _csv_text(headers, rows(records))}
    for floor in sorted(RANDOM_ENEMY_SPECS, key=int):
        exports[Path(f"enemies/floor-{floor}.csv")] = _csv_text(
            headers,
            rows(record for record in records if floor in record["Floors"].split("; ")),
        )
    exports[Path("enemies/jester-funhouse.csv")] = _csv_text(
        headers,
        rows(record for record in records if record["Funhouse"] or record["Name"] == "Jester"),
    )
    exports[Path("enemies/realm-of-cambion.csv")] = _csv_text(
        headers,
        rows(
            record
            for record in records
            if "Realm of Cambion" in record["Locations"]
            or record["Name"] in {"Cambion Acolyte", "Devil", "Cerberus", "Incubus", "Merzhin"}
        ),
    )
    natural_rows = [
        row
        for row in _item_rows()
        if row[2] in {"Weapon", "Armor", "OffHand"} and row[3] == "Natural"
    ]
    exports[Path("enemies/natural-equipment.csv")] = _csv_text(
        (
            "Name",
            "Class ID",
            "Type",
            "Subtype",
            "Value",
            "Rarity",
            "Weight",
            "Damage",
            "Critical Chance",
            "Hands",
            "Offhand Eligible",
            "Armor",
            "Modifier",
            "Element",
            "Restricted To",
            "Restricted Against",
            "Ultimate",
            "Random Drop",
            "Unequipped",
            "Description",
        ),
        natural_rows,
    )
    return exports


def _enemy_ability_sources() -> dict[str, set[str]]:
    sources: dict[str, set[str]] = defaultdict(set)
    for record in _enemy_records():
        for name in (*record["Spells"].split("; "), *record["Skills"].split("; ")):
            if name:
                sources[name].add(record["Name"])
    return sources


def _render_special_exports() -> dict[Path, str]:
    class_sources, books = _catalog_ability_sources()
    enemy_sources = _enemy_ability_sources()
    headers = (
        "Name",
        "Class ID",
        "Book",
        "Type",
        "Subtype",
        "School",
        "Cost",
        "Resource",
        "Damage Modifier",
        "Critical Chance",
        "Target Scope",
        "Passive",
        "Combat Only",
        "Rank",
        "Class Sources",
        "Enemy Sources",
        "External Acquisition",
        "Modifies",
        "Description",
    )
    rows_by_book: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    for class_id, ability, _constructor in _ability_instances():
        inferred_book = "Spells" if isinstance(ability, abilities.Spell) else "Skills"
        declared_books = books.get(class_id, set())
        book = sorted(declared_books)[0] if len(declared_books) == 1 else inferred_book
        row = (
            ability.name,
            class_id,
            book,
            getattr(ability, "typ", ""),
            getattr(ability, "subtyp", ""),
            getattr(ability, "school", ""),
            getattr(ability, "cost", 0),
            getattr(ability, "resource_type", "Mana" if getattr(ability, "cost", 0) else ""),
            getattr(ability, "dmg_mod", ""),
            getattr(ability, "crit", ""),
            getattr(
                getattr(ability, "target_scope", ""),
                "value",
                getattr(ability, "target_scope", ""),
            ),
            getattr(ability, "passive", False),
            getattr(ability, "combat", True),
            getattr(ability, "rank", ""),
            "; ".join(sorted(class_sources.get(class_id, ()))),
            "; ".join(sorted(enemy_sources.get(ability.name, ()))),
            ability.name in EXTERNAL_ACQUISITION_ABILITIES or ability.name in LEARNABLE_SPELL_RANKS,
            "; ".join(getattr(ability, "modifies", ())),
            ability.description,
        )
        rows_by_book[book].append(row)
    return {
        Path("specials/spells.csv"): _csv_text(
            headers,
            sorted(rows_by_book["Spells"], key=lambda row: (row[0], row[1])),
        ),
        Path("specials/skills.csv"): _csv_text(
            headers,
            sorted(rows_by_book["Skills"], key=lambda row: (row[0], row[1])),
        ),
    }


def _render_quest_exports() -> dict[Path, str]:
    quest_data = load_json_data("quests.json")
    headers = (
        "Quest",
        "Story",
        "Level",
        "Giver",
        "Type",
        "Objective",
        "Total",
        "Rewards",
        "Reward Amount",
        "Experience",
        "Start Text",
        "Help Text",
        "End Text",
    )
    rows = []
    for giver, story_types in quest_data.items():
        for story_type, levels in story_types.items():
            for level, quests in levels.items():
                for quest_name, quest in quests.items():
                    rows.append(
                        (
                            quest_name,
                            story_type,
                            level,
                            giver,
                            quest.get("Type", ""),
                            quest.get("What", ""),
                            quest.get("Total", ""),
                            "; ".join(
                                reward if isinstance(reward, str) else reward.__name__
                                for reward in quest.get("Reward", ())
                            ),
                            quest.get("Reward Number", ""),
                            quest.get("Experience", ""),
                            quest.get("Start Text", ""),
                            quest.get("Help Text", ""),
                            quest.get("End Text", ""),
                        )
                    )
    rows.sort(key=lambda row: (int(row[2]), row[1], row[3], row[0]))
    return {Path("quests/quests.csv"): _csv_text(headers, rows)}


def render_all() -> dict[Path, str]:
    """Return every generated spreadsheet path and its canonical CSV text."""
    exports = {}
    exports.update(_render_character_exports())
    exports.update(_render_item_exports())
    exports.update(_render_enemy_exports())
    exports.update(_render_special_exports())
    exports.update(_render_quest_exports())
    return exports


def write_all(output_directory: Path = OUTPUT_DIRECTORY) -> None:
    """Write all current catalog snapshots below ``output_directory``."""
    rendered = render_all()
    expected_paths = set(rendered)
    managed_directories = ("characters", "items", "enemies", "quests", "specials")
    for directory_name in managed_directories:
        directory = output_directory / directory_name
        if not directory.exists():
            continue
        for existing_path in directory.rglob("*.csv"):
            if existing_path.relative_to(output_directory) not in expected_paths:
                existing_path.unlink()

    for relative_path, content in rendered.items():
        destination = output_directory / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
