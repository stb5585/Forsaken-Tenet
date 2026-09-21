"""Progression state synchronization, purchases, growth, and promotions."""

from __future__ import annotations

import copy
import math
from dataclasses import asdict, replace
from typing import Any

from src.core.randomness import gameplay_random as random

from .. import abilities
from ..constants import (
    LEVELUP_ATK_LUCK_FACTOR,
    LEVELUP_DEF_LUCK_FACTOR,
    LEVELUP_LUCK_DIVISOR_BASE,
    LEVELUP_LUCK_FACTOR_HP_MP,
    LEVELUP_MAG_LUCK_FACTOR,
    LEVELUP_MDEF_LUCK_FACTOR,
    LEVELUP_STAT_DIVISOR,
)
from ..progression_manifest import (
    ABILITY_ICON_KEYS,
    CATALOG_ONLY_PROMOTED_TREE_CLASSES,
    EXTERNAL_ACQUISITION_ABILITIES,
)
from .models import (
    MAX_PLAYER_LEVEL,
    PRIMARY_ATTRIBUTES,
    RATING_PAYLOADS,
    RESOURCE_NODE_AMOUNTS,
    AbilityTreeNode,
    GrowthResult,
    LevelUpResult,
    NodeKind,
    NodeState,
    NodeStatus,
    ProgressionState,
    PromotionPreview,
    PurchaseResult,
    attribute_points_through_level,
    class_tier,
    cumulative_experience_for_level,
    prerequisite_groups,
    progression_points_through_level,
)
from .trees import (
    ABILITY_TREES,
    CARRIED_NODE_IDS_BY_CLASS,
    CLASS_DETAILS,
    TALENT_NODES,
    TREE_NODES,
    _ability_entries,
    _tree_size_range,
    effective_node_level_requirement,
)


def progression_class_name(player: Any) -> str:
    """Return the permanent class whose progression tree should be displayed."""
    if getattr(player, "_transformed", False):
        permanent_name = getattr(player, "_normal_class_name", None)
        if permanent_name in ABILITY_TREES:
            return permanent_name
    return player.cls.name


def _is_carried_node(
    node: AbilityTreeNode,
    current_class: str,
    completed_tree_ids: set[str],
) -> bool:
    """Return whether a promoted class may edit a completed-tree node."""
    return node.tree_id in completed_tree_ids and node.id in CARRIED_NODE_IDS_BY_CLASS.get(
        current_class, ()
    )


def has_talent(player: Any, talent_key: str) -> bool:
    """Return whether a player permanently owns a named progression talent."""
    node = TALENT_NODES.get(str(talent_key))
    state = getattr(player, "progression", None)
    return bool(
        node is not None
        and isinstance(state, ProgressionState)
        and node.id in state.purchased_node_ids
    )


def validate_trees() -> tuple[str, ...]:
    """Validate all manifests and return errors without mutating state."""
    errors: list[str] = []
    seen: set[str] = set()
    known_classes = set(CLASS_DETAILS)
    known_ability_classes = {
        entry[3].__name__ for class_name in known_classes for entry in _ability_entries(class_name)
    }
    catalog_ability_classes = {
        ability_ctor.__name__
        for source in (abilities.spell_dict, abilities.skill_dict)
        for levels in source.values()
        for raw in levels.values()
        for ability_ctor in abilities.ability_classes_for(raw)
        if ability_ctor().name not in EXTERNAL_ACQUISITION_ABILITIES
    }
    manifested: set[str] = set()

    for tree in ABILITY_TREES.values():
        minimum, maximum = _tree_size_range(tree.class_name, tree.stage)
        development_node_count = sum(node.kind != NodeKind.PROMOTION for node in tree.nodes)
        if not minimum <= development_node_count <= maximum:
            errors.append(f"{tree.id}: invalid stage size")
        node_map = {node.id: node for node in tree.nodes}
        expected_tree_abilities = {entry[3].__name__ for entry in _ability_entries(tree.class_name)}
        manifested_tree_abilities = {
            node.payload["ability_class"].__name__
            for node in tree.nodes
            if (node.kind == NodeKind.ABILITY and node.tree_id == tree.class_name)
        }
        missing_tree_abilities = expected_tree_abilities - manifested_tree_abilities
        if missing_tree_abilities:
            errors.append(
                f"{tree.id}: catalog abilities missing from tree: {sorted(missing_tree_abilities)}"
            )
        extra_tree_abilities = manifested_tree_abilities - expected_tree_abilities
        if extra_tree_abilities:
            errors.append(
                f"{tree.id}: undeclared catalog abilities in tree: {sorted(extra_tree_abilities)}"
            )
        positions: set[tuple[float, int]] = set()
        for node in tree.nodes:
            if node.id in seen and node.tree_id == tree.class_name:
                errors.append(f"{tree.id}: duplicate node ID {node.id}")
            seen.add(node.id)
            node_stage = CLASS_DETAILS[node.tree_id][1]
            node_allowed_levels = {
                1: {0, 5, 10, 15, 20, 25},
                2: {35, 40, 45, 50, 55},
                3: {60, 65, 70, 75, 80, 85, 90, 95},
            }[node_stage]
            if node.lane not in tree.branches:
                errors.append(f"{node.id}: unknown branch")
            if node.position in positions:
                errors.append(f"{tree.id}: duplicate position {node.position}")
            positions.add(node.position)
            if node.icon_key not in ABILITY_ICON_KEYS:
                errors.append(f"{node.id}: unknown icon key {node.icon_key}")
            if node.cost < 1:
                errors.append(f"{node.id}: invalid point cost {node.cost}")
            for prerequisite in node.prerequisites:
                if prerequisite not in node_map:
                    errors.append(f"{node.id}: unknown prerequisite {prerequisite}")
            if node.kind == NodeKind.ABILITY:
                ability_class_name = node.payload["ability_class"].__name__
                manifested.add(ability_class_name)
                if ability_class_name not in known_ability_classes:
                    errors.append(f"{node.id}: unknown ability {node.name}")
                specialization = node.payload.get("weapon_specialization")
                if specialization is not None:
                    from ..classes import grandmaster

                    if (
                        not isinstance(specialization, tuple)
                        or len(specialization) != 2
                        or specialization[0] not in grandmaster.WEAPON_TYPES
                        or int(specialization[1]) < 1
                    ):
                        errors.append(f"{node.id}: invalid weapon specialization gate")
            prerequisite_mode = node.payload.get("prerequisite_mode", "all")
            if prerequisite_mode not in {"all", "any"}:
                errors.append(f"{node.id}: invalid prerequisite mode {prerequisite_mode}")
            if prerequisite_mode == "any" and len(node.prerequisites) < 2:
                errors.append(f"{node.id}: any-prerequisite node needs multiple choices")
            authored_groups = node.payload.get("prerequisite_groups")
            if authored_groups:
                groups = prerequisite_groups(node)
                if any(not group for group in groups):
                    errors.append(f"{node.id}: prerequisite group is empty")
                grouped_ids = {prerequisite for group in groups for prerequisite in group}
                if grouped_ids != set(node.prerequisites):
                    errors.append(f"{node.id}: prerequisite groups must cover every prerequisite")
            if node.kind == NodeKind.TALENT:
                talent_key = str(node.payload.get("talent_key", "")).strip()
                if not talent_key:
                    errors.append(f"{node.id}: talent has no stable key")
                elif TALENT_NODES.get(talent_key) is None or TALENT_NODES[talent_key].id != node.id:
                    errors.append(f"{node.id}: duplicate talent key {talent_key}")
                if not str(node.payload.get("description", "")).strip():
                    errors.append(f"{node.id}: talent has no description")
                kit_effect = node.payload.get("kit_effect")
                if kit_effect is not None and (
                    not isinstance(kit_effect, tuple)
                    or len(kit_effect) != 3
                    or kit_effect[0] not in {"meter_cap", "control_progress", "bond_power"}
                    or int(kit_effect[2]) <= 0
                ):
                    errors.append(f"{node.id}: invalid kit effect {kit_effect!r}")
            if node.kind == NodeKind.PROMOTION:
                expected_cost = 2 if tree.stage == 1 else 3
                if node.cost != expected_cost:
                    errors.append(f"{node.id}: promotion must cost {expected_cost} points")
                target = node.payload["target_class"]
                if target not in known_classes:
                    errors.append(f"{node.id}: unknown target class {target}")
                if not node.prerequisites and not node.payload.get("floating_promotion"):
                    errors.append(f"{node.id}: promotion has no completed path")
            if (
                node.kind == NodeKind.RATING
                and int(node.payload.get("amount", 0)) != node_stage * 10
            ):
                errors.append(f"{node.id}: rating node must grant {node_stage * 10}")
            if (
                node.kind == NodeKind.HEALTH
                and int(node.payload.get("amount", 0)) != RESOURCE_NODE_AMOUNTS[node_stage]
            ):
                errors.append(
                    f"{node.id}: health node must grant {RESOURCE_NODE_AMOUNTS[node_stage]}"
                )
            if (
                node.kind == NodeKind.MANA
                and int(node.payload.get("amount", 0)) != RESOURCE_NODE_AMOUNTS[node_stage]
            ):
                errors.append(
                    f"{node.id}: mana node must grant {RESOURCE_NODE_AMOUNTS[node_stage]}"
                )
            if node.kind != NodeKind.PROMOTION:
                required_level = int(node.payload.get("level_requirement", 0) or 0)
                level_optional = (
                    node.kind == NodeKind.RATING
                    or node.kind == NodeKind.HEALTH
                    or node.kind == NodeKind.MANA
                    or bool(node.payload.get("available_on_promotion"))
                    or bool(node.payload.get("owned_if_known"))
                    or bool(node.payload.get("weapon_specialization"))
                )
                if (
                    node.kind == NodeKind.RATING
                    and required_level
                    and not node.payload.get("level_band_gate")
                ):
                    errors.append(f"{node.id}: rating node must not have a level gate")
                elif not level_optional and required_level not in node_allowed_levels:
                    errors.append(
                        f"{node.id}: invalid stage-{node_stage} level gate {required_level}"
                    )
                if node_stage > 1 and not level_optional and required_level == 0:
                    errors.append(f"{node.id}: promoted-tree node has no level gate")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                errors.append(f"{tree.id}: prerequisite cycle at {node_id}")
                return
            if node_id in visited or node_id not in node_map:
                return
            visiting.add(node_id)
            for prerequisite in node_map[node_id].prerequisites:
                visit(prerequisite)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in node_map:
            visit(node_id)

        exclusive_groups: dict[str, list[AbilityTreeNode]] = {}
        for node in tree.nodes:
            group = node.payload.get("exclusive_group")
            if group:
                exclusive_groups.setdefault(str(group), []).append(node)
        for group, choices in exclusive_groups.items():
            if len(choices) < 2:
                errors.append(f"{tree.id}: exclusive group {group} has fewer than two choices")

        if tree.stage == 3 and tree.class_name not in CATALOG_ONLY_PROMOTED_TREE_CLASSES:
            roots = [node for node in tree.nodes if not node.prerequisites]
            if len(roots) < 2:
                errors.append(f"{tree.id}: terminal tree has fewer than two roots")
            if not any(node.kind in {NodeKind.ABILITY, NodeKind.TALENT} for node in tree.nodes):
                errors.append(f"{tree.id}: terminal tree has no class-specific choice")

    missing = catalog_ability_classes - manifested
    if missing:
        errors.append(f"ordinary catalog abilities missing from trees: {sorted(missing)}")

    from ..races import races_dict

    races = [race_ctor() for race_ctor in races_dict.values()]
    for class_name, (_ctor, stage, _parent) in CLASS_DETAILS.items():
        if stage != 2:
            continue
        if not any(class_name in getattr(race, "cls_res", {}).get("First", ()) for race in races):
            errors.append(f"{class_name}: no race can reach this promotion")
    return tuple(errors)


def ensure_progression(player: Any) -> ProgressionState:
    """Return the player's state, creating an unallocated state if needed."""
    current = getattr(player, "progression", None)
    if isinstance(current, ProgressionState):
        _adopt_known_ability_nodes(player, current)
        return current
    level = max(1, min(MAX_PLAYER_LEVEL, int(getattr(player.level, "level", 1))))
    total_xp = max(0, int(getattr(player.level, "exp", 0)))
    state = ProgressionState(
        level=level,
        total_xp=total_xp,
        unspent_points=progression_points_through_level(level),
        unspent_attribute_points=attribute_points_through_level(level),
    )
    player.progression = state
    _adopt_known_ability_nodes(player, state)
    _sync_level(player)
    return state


def _adopt_known_ability_nodes(player: Any, state: ProgressionState) -> None:
    """Mark explicitly inheritable abilities and Jump mods as pre-owned."""
    class_name = getattr(getattr(player, "cls", None), "name", None)
    if class_name == "Stalwart Defender":
        for ability_ctor in (
            abilities.CitadelAegis,
            abilities.IronwallReprisal,
            abilities.LastBastionSurge,
            abilities.Stronghold,
        ):
            ability = ability_ctor()
            player.spellbook.setdefault("Skills", {}).setdefault(
                ability.name,
                ability,
            )
    tree = ABILITY_TREES.get(class_name)
    if tree is None:
        return
    learned = {
        ability_name
        for book in getattr(player, "spellbook", {}).values()
        for ability_name in getattr(book, "keys", lambda: ())()
    }
    jump_skill = player.spellbook.get("Skills", {}).get("Jump")
    unlocked_jump_mods = set()
    if jump_skill is not None:
        unlocked_jump_mods = {
            name
            for name, unlocked in getattr(jump_skill, "unlocked_modifications", {}).items()
            if unlocked
        }

    def adopt_with_prerequisites(
        node: AbilityTreeNode,
        available_nodes: dict[str, AbilityTreeNode],
    ) -> None:
        state.purchased_node_ids.add(node.id)
        for prerequisite_id in node.prerequisites:
            prerequisite = available_nodes.get(prerequisite_id)
            if prerequisite is not None:
                adopt_with_prerequisites(prerequisite, available_nodes)

    for node in tree.nodes:
        if (
            node.kind == NodeKind.ABILITY
            and node.payload.get("owned_if_known")
            and node.name in learned
        ):
            state.purchased_node_ids.add(node.id)

    modifier_tree_names = ("Lancer", "Dragoon") if class_name == "Dragoon" else (class_name,)
    for modifier_tree_name in modifier_tree_names:
        modifier_tree = ABILITY_TREES.get(modifier_tree_name)
        if modifier_tree is None:
            continue
        modifier_node_map = {node.id: node for node in modifier_tree.nodes}
        for node in modifier_tree.nodes:
            jump_modification = node.payload.get("jump_modification")
            if jump_modification and jump_modification in unlocked_jump_mods:
                adopt_with_prerequisites(node, modifier_node_map)
    sync_jump_modification_nodes(player, state)


def sync_jump_modification_nodes(
    player: Any,
    state: ProgressionState | None = None,
) -> None:
    """Synchronize purchased Jump-mod nodes into the stateful Jump skill."""
    progression_state = state or getattr(player, "progression", None)
    if not isinstance(progression_state, ProgressionState):
        return
    jump_skill = player.spellbook.get("Skills", {}).get("Jump")
    if jump_skill is None or not hasattr(jump_skill, "unlock_modification"):
        return
    for node_id in progression_state.purchased_node_ids:
        node = TREE_NODES.get(node_id)
        if node is None:
            continue
        modification = node.payload.get("jump_modification")
        if modification:
            jump_skill.unlock_modification(str(modification))


def initialize_progression(player: Any) -> PurchaseResult:
    """Initialize a new player with one freely allocatable point."""
    player.progression = ProgressionState(
        level=1,
        total_xp=0,
        unspent_points=1,
        unspent_attribute_points=0,
    )
    _sync_level(player)
    return PurchaseResult(
        True,
        "Progression initialized with 1 unspent point.",
        points_remaining=1,
    )


def _sync_level(player: Any) -> None:
    state = player.progression
    player.level.level = state.level
    player.level.pro_level = class_tier(player)
    player.level.exp = state.total_xp
    player.level.exp_to_gain = (
        "MAX"
        if state.level >= MAX_PLAYER_LEVEL
        else cumulative_experience_for_level(state.level + 1) - state.total_xp
    )


def _roll_growth(player: Any, rng: random.Random) -> GrowthResult:
    form_snapshot = getattr(player, "_normal_form_snapshot", None)
    transformed = isinstance(form_snapshot, dict)
    active_class = player.cls
    active_stats = player.stats
    if transformed:
        player.cls = form_snapshot["cls"]
        player.stats = form_snapshot["stats"]
    luck = player.check_mod
    divisor = max(
        1,
        LEVELUP_LUCK_DIVISOR_BASE - luck("luck", luck_factor=LEVELUP_LUCK_FACTOR_HP_MP),
    )
    health = rng.randint(player.stats.con // divisor, player.stats.con)
    mana = rng.randint(player.stats.intel // divisor, player.stats.intel)
    attack = rng.randint(
        0,
        luck("luck", luck_factor=LEVELUP_ATK_LUCK_FACTOR)
        + (player.stats.strength // LEVELUP_STAT_DIVISOR)
        + max(1, player.cls.att_plus // 2),
    )
    defense = rng.randint(
        0,
        luck("luck", luck_factor=LEVELUP_DEF_LUCK_FACTOR)
        + (player.stats.con // LEVELUP_STAT_DIVISOR)
        + max(1, player.cls.def_plus // 2),
    )
    magic = rng.randint(
        0,
        luck("luck", luck_factor=LEVELUP_MAG_LUCK_FACTOR)
        + (player.stats.intel // LEVELUP_STAT_DIVISOR)
        + max(1, player.cls.int_plus // 2),
    )
    magic_defense = rng.randint(
        0,
        luck("luck", luck_factor=LEVELUP_MDEF_LUCK_FACTOR)
        + (player.stats.wisdom // LEVELUP_STAT_DIVISOR)
        + max(1, player.cls.wis_plus // 2),
    )
    if transformed:
        player.cls = active_class
        player.stats = active_stats
    normal_health = form_snapshot["health"] if transformed else player.health
    normal_mana = form_snapshot["mana"] if transformed else player.mana
    normal_health.max += health
    normal_mana.max += mana
    if transformed:
        player.health.max += health
        player.mana.max += mana
    player.combat.attack += attack
    player.combat.defense += defense
    player.combat.magic += magic
    player.combat.magic_def += magic_defense
    if player.in_town():
        player.health.current = player.health.max
        player.mana.current = player.mana.max
        if transformed:
            normal_health.current = normal_health.max
            normal_mana.current = normal_mana.max
    return GrowthResult(health, mana, attack, defense, magic, magic_defense)


def award_experience(
    player: Any,
    amount: int,
    rng: random.Random | None = None,
) -> LevelUpResult:
    """Award total XP, carry across levels, and stop at global level 100."""
    state = ensure_progression(player)
    requested = max(0, int(amount))
    old_level = state.level
    maximum_xp = cumulative_experience_for_level(MAX_PLAYER_LEVEL)
    awarded = min(requested, max(0, maximum_xp - state.total_xp))
    state.total_xp += awarded
    growth: list[GrowthResult] = []
    points_awarded = 0
    attribute_points_awarded = 0
    generator = rng or random

    while state.level < MAX_PLAYER_LEVEL and state.total_xp >= cumulative_experience_for_level(
        state.level + 1
    ):
        state.level += 1
        if state.level % 2 == 0:
            state.unspent_points += 1
            points_awarded += 1
        if state.level % 4 == 0:
            state.unspent_attribute_points += 1
            attribute_points_awarded += 1
        growth.append(_roll_growth(player, generator))
    _sync_level(player)
    if hasattr(player, "refresh_highest_level"):
        player.refresh_highest_level()
    return LevelUpResult(
        experience_awarded=awarded,
        old_level=old_level,
        new_level=state.level,
        points_awarded=points_awarded,
        growth=tuple(growth),
        reached_max_level=state.level == MAX_PLAYER_LEVEL,
        attribute_points_awarded=attribute_points_awarded,
    )


def _outside_combat(player: Any) -> bool:
    return not bool(
        getattr(player, "in_combat", False)
        or getattr(player, "combat_active", False)
        or getattr(player, "_active_combat", False)
    )


def increase_attribute(player: Any, stat_name: str) -> PurchaseResult:
    """Permanently increase one primary attribute for one point."""
    state = ensure_progression(player)
    normalized = stat_name.strip().lower().replace("intelligence", "intel")
    normalized = normalized.replace("constitution", "con").replace("dexterity", "dex")
    if not _outside_combat(player):
        return PurchaseResult(False, "Progression purchases are unavailable in combat.")
    if normalized not in PRIMARY_ATTRIBUTES:
        return PurchaseResult(False, f"Unknown primary attribute: {stat_name}.")
    if state.unspent_attribute_points < 1:
        return PurchaseResult(False, "No attribute points are available.")
    form_snapshot = getattr(player, "_normal_form_snapshot", None)
    if isinstance(form_snapshot, dict):
        normal_stats = form_snapshot["stats"]
        setattr(normal_stats, normalized, getattr(normal_stats, normalized) + 1)
    setattr(player.stats, normalized, getattr(player.stats, normalized) + 1)
    state.trained_attributes[normalized] = state.trained_attributes.get(normalized, 0) + 1
    state.unspent_attribute_points -= 1
    return PurchaseResult(
        True,
        f"{normalized.replace('intel', 'intelligence').title()} increased by 1.",
        points_remaining=state.unspent_points,
    )


def _race_allows(player: Any, target_class: str) -> bool:
    if class_tier(player) != 1:
        return True
    allowed = getattr(getattr(player, "race", None), "cls_res", {}).get("First", ())
    return not allowed or target_class in allowed


def _node_blockers(
    player: Any,
    node: AbilityTreeNode,
    *,
    purchased_node_ids: set[str] | None = None,
    remaining_points: int | None = None,
    planned_attributes: dict[str, int] | None = None,
) -> tuple[str, ...]:
    state = ensure_progression(player)
    purchased = state.purchased_node_ids if purchased_node_ids is None else purchased_node_ids
    points = state.unspent_points if remaining_points is None else remaining_points
    attribute_plan = planned_attributes or {}
    blockers: list[str] = []
    if points < node.cost:
        noun = "point" if node.cost == 1 else "points"
        blockers.append(f"Requires {node.cost} {noun}.")

    def prerequisite_path_satisfied(node_id: str, visiting: set[str]) -> bool:
        """Require an unbroken purchased path through inherited nodes."""
        if node_id not in purchased or node_id in visiting:
            return False
        prerequisite_node = TREE_NODES[node_id]
        if not prerequisite_node.prerequisites:
            return True
        next_visiting = {*visiting, node_id}
        return all(
            any(prerequisite_path_satisfied(prerequisite, next_visiting) for prerequisite in group)
            for group in prerequisite_groups(prerequisite_node)
        )

    for group in prerequisite_groups(node):
        if not any(prerequisite_path_satisfied(prerequisite, set()) for prerequisite in group):
            names = " or ".join(TREE_NODES[prerequisite].name for prerequisite in group)
            blockers.append(f"Requires {names}.")
    required_level = effective_node_level_requirement(
        node,
        progression_class_name(player),
    )
    if required_level and state.level < required_level:
        blockers.append(f"Requires level {required_level} (current {state.level}).")
    required_ability = str(node.payload.get("requires_known_ability", "") or "")
    if required_ability and not any(
        required_ability in player.spellbook.get(book, {}) for book in ("Spells", "Skills")
    ):
        blockers.append(f"Requires learned ability {required_ability}.")
    quest_unlock = str(node.payload.get("quest_unlock", "") or "")
    if quest_unlock:
        quest = (
            getattr(player, "quest_dict", {})
            .get("Side", {})
            .get(
                quest_unlock,
                {},
            )
        )
        if not bool(quest.get("Turned In")):
            blockers.append(f"Requires completing {quest_unlock}.")
    school_affinity = node.payload.get("school_affinity")
    if school_affinity:
        from ..classes import wizard

        school_name, required_affinity = school_affinity
        current_affinity = wizard.ensure_affinity(player).get(str(school_name), 0)
        if current_affinity < float(required_affinity):
            blockers.append(
                f"Requires {required_affinity:g} {school_name} affinity "
                f"(current {current_affinity:g})."
            )
    if node.kind == NodeKind.ABILITY:
        exclusive_group = node.payload.get("exclusive_group")
        if exclusive_group:
            selected = next(
                (
                    candidate
                    for candidate in TREE_NODES.values()
                    if candidate.id in purchased
                    and candidate.id != node.id
                    and candidate.payload.get("exclusive_group") == exclusive_group
                ),
                None,
            )
            if selected is not None:
                blockers.append(f"{selected.name} permanently closed this style path.")
        specialization = node.payload.get("weapon_specialization")
        if specialization:
            from ..classes import grandmaster

            weapon_type, required_rank = specialization
            current_rank = grandmaster.discipline_rank(player, weapon_type)
            if current_rank < int(required_rank):
                blockers.append(
                    f"Requires {weapon_type} specialization level "
                    f"{required_rank} (current {current_rank})."
                )
        ability_ctor = node.payload["ability_class"]
        from ..player.stats import _upgrade_source_name

        source_name = _upgrade_source_name(ability_ctor)
        planned_names = {
            TREE_NODES[node_id].name
            for node_id in purchased - state.purchased_node_ids
            if TREE_NODES[node_id].kind == NodeKind.ABILITY
        }
        if (
            source_name
            and not node.payload.get("upgrade_without_source")
            and source_name not in planned_names
            and not any(
                source_name in player.spellbook.get(book, {}) for book in ("Spells", "Skills")
            )
        ):
            blockers.append(f"Requires learned ability {source_name}.")
    if node.kind == NodeKind.PROMOTION:
        target_class = node.payload["target_class"]
        permanent_class = getattr(player, "transform_type", None)
        if (
            permanent_class is not None
            and getattr(permanent_class, "name", None) != player.cls.name
        ) or getattr(player, "state", "normal") != "normal":
            blockers.append("Return to your permanent form before promotion.")
        if not _race_allows(player, target_class):
            blockers.append(f"{player.race.name} cannot promote to {target_class}.")
        for stat_name, requirement in node.payload["requirements"].items():
            current = int(getattr(player.stats, stat_name))
            current += int(attribute_plan.get(stat_name, 0))
            if current < requirement:
                blockers.append(
                    f"Requires {stat_name.replace('intel', 'intelligence').title()} "
                    f"{requirement} (current {current})."
                )
    return tuple(blockers)


def available_nodes(
    player: Any,
    tree_id: str | None = None,
    *,
    planned_node_ids: tuple[str, ...] | list[str] | set[str] = (),
    planned_attributes: dict[str, int] | None = None,
) -> list[NodeStatus]:
    """Return owned, available, blocked, and closed nodes for one tree."""
    state = ensure_progression(player)
    selected_tree = tree_id or progression_class_name(player)
    tree = ABILITY_TREES[selected_tree]
    is_closed = selected_tree in state.completed_trees
    planned = {node_id for node_id in planned_node_ids if node_id in TREE_NODES}
    effective_purchased = state.purchased_node_ids | planned
    planned_cost = sum(TREE_NODES[node_id].cost for node_id in planned)
    remaining_points = state.unspent_points - planned_cost
    planned_promotions = {
        node_id for node_id in planned if TREE_NODES[node_id].kind == NodeKind.PROMOTION
    }
    selected_exclusive_nodes = {
        str(node.payload["exclusive_group"]): node.id
        for node in tree.nodes
        if node.id in effective_purchased and node.payload.get("exclusive_group")
    }
    choice_closed: dict[str, bool] = {}

    def is_choice_closed(node: AbilityTreeNode) -> bool:
        """Return whether a permanent exclusive choice made this node unreachable."""
        if node.id in choice_closed:
            return choice_closed[node.id]
        exclusive_group = node.payload.get("exclusive_group")
        selected = selected_exclusive_nodes.get(str(exclusive_group))
        if selected is not None and selected != node.id:
            choice_closed[node.id] = True
            return True
        groups = prerequisite_groups(node)
        closed = any(
            all(is_choice_closed(TREE_NODES[prerequisite]) for prerequisite in group)
            for group in groups
        )
        choice_closed[node.id] = closed
        return closed

    statuses: list[NodeStatus] = []
    learned_names = {
        name
        for book in getattr(player, "spellbook", {}).values()
        for name in getattr(book, "keys", lambda: ())()
    }
    for node in tree.nodes:
        hidden_until_known = str(node.payload.get("hidden_until_known", "") or "")
        if hidden_until_known and hidden_until_known not in learned_names:
            continue
        display_node = node
        revealed_name = str(node.payload.get("revealed_name", "") or "")
        if revealed_name and revealed_name in learned_names:
            display_node = replace(
                node,
                payload={**node.payload, "name": revealed_name},
            )
        if node.id in effective_purchased:
            statuses.append(NodeStatus(display_node, NodeState.OWNED))
        elif is_closed:
            statuses.append(
                NodeStatus(
                    display_node,
                    NodeState.CLOSED,
                    ("This completed branch is permanently closed.",),
                )
            )
        elif is_choice_closed(node):
            statuses.append(
                NodeStatus(
                    display_node,
                    NodeState.CLOSED,
                    ("The competing style path was chosen permanently.",),
                )
            )
        else:
            blockers = _node_blockers(
                player,
                node,
                purchased_node_ids=effective_purchased,
                remaining_points=remaining_points,
                planned_attributes=planned_attributes,
            )
            if (
                node.kind == NodeKind.PROMOTION
                and planned_promotions
                and node.id not in planned_promotions
            ):
                blockers = (
                    *blockers,
                    "Another promotion is already distributed.",
                )
            permanently_unavailable_promotion = node.kind == NodeKind.PROMOTION and (
                not _race_allows(
                    player,
                    node.payload["target_class"],
                )
                or (bool(planned_promotions) and node.id not in planned_promotions)
                or any(
                    node.payload["target_class"]
                    in TREE_NODES[purchased_id].payload.get(
                        "closes_promotions",
                        (),
                    )
                    for purchased_id in effective_purchased
                    if purchased_id in TREE_NODES
                )
            )
            statuses.append(
                NodeStatus(
                    display_node,
                    (
                        NodeState.CLOSED
                        if permanently_unavailable_promotion
                        else NodeState.BLOCKED if blockers else NodeState.AVAILABLE
                    ),
                    blockers,
                )
            )
    return statuses


def permanent_closures_for_plan(
    player: Any,
    tree_id: str,
    planned_node_ids: tuple[str, ...] | list[str] | set[str],
) -> tuple[str, ...]:
    """List currently open development nodes a staged choice will close forever."""
    planned = {
        node_id
        for node_id in planned_node_ids
        if node_id in TREE_NODES and TREE_NODES[node_id].kind != NodeKind.PROMOTION
    }
    if not planned:
        return ()
    before = {status.node.id: status for status in available_nodes(player, tree_id)}
    after = available_nodes(player, tree_id, planned_node_ids=planned)
    closures = {
        status.node.name
        for status in after
        if status.node.id not in planned
        and status.state == NodeState.CLOSED
        and before[status.node.id].state != NodeState.CLOSED
        and status.node.kind != NodeKind.PROMOTION
    }
    return tuple(sorted(closures))


def _grant_ability(player: Any, node: AbilityTreeNode) -> str:
    from ..classes import transformation

    ability_ctor = node.payload["ability_class"]
    ability = ability_ctor()
    book_name = node.payload["book"]
    snapshot = getattr(player, "_normal_form_snapshot", None)
    normal_spellbook = (
        snapshot["spellbook"]
        if transformation.is_transformed(player) and isinstance(snapshot, dict)
        else player.spellbook
    )
    book = normal_spellbook[book_name]
    if node.payload.get("stack_if_known") and ability.name in book:
        existing = book[ability.name]
        state = ensure_progression(player)
        existing.ranks = (
            max(
                1,
                int(state.ability_ranks.get(ability.name, 1) or 1),
            )
            + 1
        )
        state.ability_ranks[ability.name] = existing.ranks
        return f"{ability.name} {existing.ranks}"
    from ..player.stats import _upgrade_source_name

    old_name = _upgrade_source_name(ability_ctor)
    if old_name:
        for candidate_book in normal_spellbook.values():
            candidate_book.pop(old_name, None)
    if ability.name == "Health/Mana Drain":
        for old_name in ("Health Drain", "Mana Drain"):
            normal_spellbook["Skills"].pop(old_name, None)
    elif ability.name == "True Piercing Strike":
        for old_name in ("Piercing Strike", "True Strike"):
            normal_spellbook["Skills"].pop(old_name, None)
    elif ability.name == "Triple Strike":
        normal_spellbook["Skills"].pop("Double Strike", None)
    elif ability.name == "Flurry of Blades":
        normal_spellbook["Skills"].pop("Triple Strike", None)
    book[ability.name] = ability
    if ability.name == "Death Mark":
        deathblow = abilities.Deathblow()
        normal_spellbook["Skills"][deathblow.name] = deathblow
    if node.payload.get("stack_if_known"):
        ensure_progression(player).ability_ranks.setdefault(ability.name, 1)
    if transformation.is_transformed(player):
        transformation.mirror_learned_skill(player, ability.name, ability)
    if ability.name in ("Purity of Body", "Reveal"):
        ability.use(player)
    return ability.name


def _grant_talent(player: Any, node: AbilityTreeNode) -> None:
    """Apply the immediate permanent bonuses attached to a talent."""
    bonuses = node.payload.get("bonuses", {})
    for rating_name, amount in bonuses.get("ratings", {}).items():
        rating_attr = RATING_PAYLOADS[rating_name]
        setattr(
            player.combat,
            rating_attr,
            getattr(player.combat, rating_attr) + int(amount),
        )
    for rating_name, percentage in bonuses.get(
        "rating_percentages",
        {},
    ).items():
        rating_attr = RATING_PAYLOADS[rating_name]
        current = int(getattr(player.combat, rating_attr))
        amount = max(1, math.ceil(current * float(percentage)))
        setattr(player.combat, rating_attr, current + amount)
    for resource_name in ("health", "mana"):
        amount = int(bonuses.get(resource_name, 0) or 0)
        if not amount:
            continue
        resource = getattr(player, resource_name)
        resource.max += amount
        resource.current += amount
    for resource_name in ("health", "mana"):
        percentage = float(bonuses.get(f"{resource_name}_percentage", 0) or 0)
        if not percentage:
            continue
        resource = getattr(player, resource_name)
        amount = max(1, math.ceil(resource.max * percentage))
        resource.max += amount
        resource.current += amount
    jump_modification = node.payload.get("jump_modification")
    if jump_modification:
        jump_skill = player.spellbook.get("Skills", {}).get("Jump")
        if (
            jump_skill is None
            or not hasattr(jump_skill, "unlock_modification")
            or not jump_skill.unlock_modification(str(jump_modification))
        ):
            raise ValueError(f"Jump cannot unlock the {jump_modification} modification.")


def _equipment_conflicts(player: Any, target_class: Any) -> tuple[str, ...]:
    from ..classes import ability_mechanics

    conflicts: list[str] = []
    for slot in ("Weapon", "OffHand", "Armor", "Helmet"):
        item = getattr(player, "equipment", {}).get(slot)
        if item is None or getattr(item, "subtyp", None) == "None":
            continue
        try:
            legal = target_class.equip_check(item, slot)
            legal = legal or ability_mechanics.can_dual_wield_item(
                player,
                item,
                slot,
            )
        except (KeyError, TypeError, ValueError):
            legal = False
        if not legal:
            conflicts.append(f"{slot}: {getattr(item, 'name', item)}")
    return tuple(conflicts)


def promotion_combat_bonuses(target_class: Any) -> dict[str, int]:
    """Return one-time combat bonuses scaled by promotion depth."""
    scale = max(1, int(getattr(target_class, "pro_level", 1)))
    return {
        "attack": int(getattr(target_class, "att_plus", 0)) * scale,
        "defense": int(getattr(target_class, "def_plus", 0)) * scale,
        "magic": int(getattr(target_class, "magic_plus", 0)) * scale,
        "magic defense": (int(getattr(target_class, "magic_def_plus", 0)) * scale),
    }


def _promotion_closure_warning(source_class: str, target_class: str) -> str:
    """Describe which prior-tree development remains after promotion."""
    if (source_class, target_class) == ("Lancer", "Dragoon"):
        return (
            "All Lancer development nodes remain purchasable in the Dragoon tree after promotion."
        )
    if (source_class, target_class) == ("Mage", "Sorcerer"):
        return (
            "Unpurchased Mage nodes and competing promotions close permanently. "
            "Sorcerer tier-two spells unlock through matching School Affinity."
        )
    if (source_class, target_class) == ("Sorcerer", "Wizard"):
        return (
            "Unpurchased Sorcerer nodes close permanently. Learned spells and "
            "passives are retained in the Wizard spellbook."
        )
    if (source_class, target_class) == ("Conjurer", "Thaumaturgist"):
        return (
            "Conjure Animal and all six Conjurer Calling nodes appear in the "
            "Thaumaturgist tree. Other unpurchased Conjurer nodes close "
            "permanently; each Calling gains a permanent paired-Xenid choice."
        )
    return (
        f"Promoting permanently closes all unpurchased {source_class} nodes "
        "and competing promotions. Learned abilities are retained."
    )


def promotion_preview(player: Any, node_id: str) -> PromotionPreview:
    """Build the mandatory confirmation details for a promotion node."""
    node = TREE_NODES[node_id]
    if node.kind != NodeKind.PROMOTION:
        raise ValueError(f"{node_id} is not a promotion node")
    target = node.payload["target_class_ctor"]()
    combat_bonuses = promotion_combat_bonuses(target)
    bonuses = {
        "strength": target.str_plus,
        "intelligence": target.int_plus,
        "wisdom": target.wis_plus,
        "constitution": target.con_plus,
        "charisma": target.cha_plus,
        "dexterity": target.dex_plus,
        "health": target.con_plus * 2,
        "mana": target.int_plus * 2,
        **combat_bonuses,
    }
    return PromotionPreview(
        node_id=node.id,
        source_class=node.tree_id,
        target_class=target.name,
        level_requirement=int(node.payload["level_requirement"]),
        requirements=dict(node.payload["requirements"]),
        bonuses=bonuses,
        equipment_conflicts=_equipment_conflicts(player, target),
        warning=_promotion_closure_warning(node.tree_id, target.name),
    )


def _remove_illegal_gear(player: Any) -> tuple[str, ...]:
    from ..classes import ability_mechanics
    from ..items import remove_equipment

    removed: list[str] = []
    for slot in ("Weapon", "OffHand", "Armor", "Helmet"):
        item = player.equipment.get(slot)
        if item is None or getattr(item, "subtyp", None) == "None":
            continue
        try:
            legal = player.cls.equip_check(item, slot)
            legal = legal or ability_mechanics.can_dual_wield_item(
                player,
                item,
                slot,
            )
        except (KeyError, TypeError, ValueError):
            legal = False
        if legal:
            continue
        if hasattr(player, "modify_inventory"):
            player.modify_inventory(item, 1)
        player.equipment[slot] = remove_equipment(slot)
        removed.append(f"{slot}: {getattr(item, 'name', item)}")
    return tuple(removed)


def _apply_promotion(
    player: Any,
    node: AbilityTreeNode,
    choices: dict[str, Any] | None,
) -> tuple[str, ...]:
    choices = choices or {}
    new_class = node.payload["target_class_ctor"]()
    target_name = new_class.name
    if target_name == "Paladin" and not choices.get("vow"):
        raise ValueError("A Paladin vow must be selected before promotion.")
    if target_name == "Warlock" and not choices.get("familiar"):
        raise ValueError("A familiar must be selected before promotion.")

    retained_abilities = {
        book_name: dict(entries) for book_name, entries in player.spellbook.items()
    }
    old_class_name = player.cls.name
    permanent_class = getattr(player, "transform_type", None)
    player.cls = new_class
    if permanent_class is None or getattr(permanent_class, "name", None) == old_class_name:
        player.transform_type = new_class
    for stat_name, bonus_name in (
        ("strength", "str_plus"),
        ("intel", "int_plus"),
        ("wisdom", "wis_plus"),
        ("con", "con_plus"),
        ("charisma", "cha_plus"),
        ("dex", "dex_plus"),
    ):
        setattr(
            player.stats,
            stat_name,
            getattr(player.stats, stat_name) + getattr(new_class, bonus_name),
        )
    health_bonus = new_class.con_plus * 2
    mana_bonus = new_class.int_plus * 2
    player.health.max += health_bonus
    player.health.current = min(player.health.max, player.health.current + health_bonus)
    player.mana.max += mana_bonus
    player.mana.current = min(player.mana.max, player.mana.current + mana_bonus)
    combat_bonuses = promotion_combat_bonuses(new_class)
    player.combat.attack += combat_bonuses["attack"]
    player.combat.defense += combat_bonuses["defense"]
    player.combat.magic += combat_bonuses["magic"]
    player.combat.magic_def += combat_bonuses["magic defense"]
    removed = _remove_illegal_gear(player)

    if target_name == "Paladin":
        success, message = player.choose_paladin_vow(choices["vow"])
        if not success:
            raise ValueError(message)
    elif target_name == "Warlock":
        player.familiar = choices["familiar"]
        player.spellbook["Skills"].setdefault("Familiar", abilities.Familiar())
    elif target_name == "Demonologist":
        player.spellbook["Skills"].setdefault(
            "Call Contract",
            abilities.CallContract(),
        )
        player.ensure_demonologist_contracts()
    elif target_name == "Ranger":
        player.spellbook["Skills"].setdefault("Tame", abilities.Tame())
        player.ensure_tamed_companion()
    elif target_name == "Shaman":
        player.spellbook["Skills"].setdefault("Totem", abilities.Totem())
    elif target_name == "Stalwart Defender":
        for ability_ctor in (
            abilities.CitadelAegis,
            abilities.IronwallReprisal,
            abilities.LastBastionSurge,
            abilities.Stronghold,
        ):
            ability = ability_ctor()
            player.spellbook["Skills"].setdefault(ability.name, ability)
    if target_name in ("Seeker", "Wizard"):
        player.teleport = (player.location_x, player.location_y, player.location_z)

    # Promotion grants are additive. Restore the original objects as a final
    # invariant so class-specific initialization cannot revoke or replace an
    # ability the player already owned.
    for book_name, entries in retained_abilities.items():
        player.spellbook.setdefault(book_name, {}).update(entries)
    from ..classes import class_rings, promotion_kits

    promotion_kits.clear_combat_state(player)
    class_rings.reset_combat_flags(player)
    _adopt_known_ability_nodes(player, ensure_progression(player))
    return removed


def _purchase_snapshot(player: Any) -> dict[str, Any]:
    """Capture all state mutated by progression purchases."""
    return {
        "progression": copy.deepcopy(ensure_progression(player)),
        "cls": player.cls,
        "transform_type": getattr(player, "transform_type", None),
        "stats": copy.deepcopy(player.stats),
        "health": copy.deepcopy(player.health),
        "mana": copy.deepcopy(player.mana),
        "combat": copy.deepcopy(player.combat),
        "equipment": copy.deepcopy(getattr(player, "equipment", {})),
        "inventory": copy.deepcopy(getattr(player, "inventory", {})),
        "spellbook": copy.deepcopy(player.spellbook),
        "normal_form_snapshot": copy.deepcopy(getattr(player, "_normal_form_snapshot", None)),
        "transformation_state": copy.deepcopy(getattr(player, "transformation_state", None)),
        "familiar": getattr(player, "familiar", None),
        "summons": copy.deepcopy(getattr(player, "summons", {})),
        "special_fields": {
            field_name: copy.deepcopy(getattr(player, field_name, None))
            for field_name in (
                "paladin_vow",
                "demonologist_contracts",
                "promotion_kit_state",
                "teleport",
                "xenid_choices",
            )
        },
    }


def _restore_purchase_snapshot(player: Any, snapshot: dict[str, Any]) -> None:
    """Restore a progression purchase snapshot after an atomic failure."""
    player.progression = snapshot["progression"]
    player.cls = snapshot["cls"]
    player.transform_type = snapshot["transform_type"]
    player.stats = snapshot["stats"]
    player.health = snapshot["health"]
    player.mana = snapshot["mana"]
    player.combat = snapshot["combat"]
    player.equipment = snapshot["equipment"]
    player.inventory = snapshot["inventory"]
    player.spellbook = snapshot["spellbook"]
    player._normal_form_snapshot = snapshot["normal_form_snapshot"]
    player.transformation_state = snapshot["transformation_state"]
    player.familiar = snapshot["familiar"]
    player.summons = snapshot["summons"]
    for field_name, value in snapshot["special_fields"].items():
        setattr(player, field_name, value)
    _sync_level(player)


def purchase_node(
    player: Any,
    node_id: str,
    *,
    confirm_promotion: bool = False,
    promotion_choices: dict[str, Any] | None = None,
    node_choices: dict[str, Any] | None = None,
    allow_in_combat: bool = False,
) -> PurchaseResult:
    """Permanently purchase one node and atomically apply its payload."""
    state = ensure_progression(player)
    node = TREE_NODES.get(node_id)
    if node is None:
        return PurchaseResult(False, f"Unknown progression node: {node_id}.")
    if node.id in state.purchased_node_ids:
        return PurchaseResult(
            False, f"{node.name} is already owned.", node.id, state.unspent_points
        )
    if not allow_in_combat and not _outside_combat(player):
        return PurchaseResult(False, "Progression purchases are unavailable in combat.")
    from ..classes import transformation

    current_class = transformation.permanent_class_name(player)
    carried_node = _is_carried_node(
        node,
        current_class,
        state.completed_trees,
    )
    if node.tree_id != current_class and not carried_node:
        return PurchaseResult(False, "Only the current class tree can be edited.")
    if node.tree_id in state.completed_trees and not carried_node:
        return PurchaseResult(False, "That completed tree is permanently closed.")
    blockers = _node_blockers(player, node)
    if blockers:
        return PurchaseResult(False, " ".join(blockers), node.id, state.unspent_points)
    if node.kind == NodeKind.PROMOTION and not confirm_promotion:
        return PurchaseResult(
            False,
            "Promotion requires confirmation after reviewing its permanent effects.",
            node.id,
            state.unspent_points,
        )

    snapshot = _purchase_snapshot(player)
    try:
        promoted_to = None
        removed: tuple[str, ...] = ()
        if node.kind == NodeKind.ABILITY:
            learned = _grant_ability(player, node)
            message = f"Learned {learned}."
        elif node.kind == NodeKind.TALENT:
            category = node.payload.get("xenid_category")
            if category:
                from .. import companions

                selected = str((node_choices or {}).get("xenid", "") or "")
                success, choice_message = companions.choose_xenid(
                    player,
                    str(category),
                    selected,
                )
                if not success:
                    raise ValueError(choice_message)
            ultimate_category = node.payload.get("xenid_ultimate_category")
            if ultimate_category:
                from .. import companions

                success, choice_message = companions.unlock_xenid_ultimate(
                    player,
                    str(ultimate_category),
                )
                if not success:
                    raise ValueError(choice_message)
            _grant_talent(player, node)
            message = (
                choice_message if category or ultimate_category else f"Learned talent {node.name}."
            )
        elif node.kind == NodeKind.RATING:
            rating_attr = RATING_PAYLOADS[node.payload["rating"]]
            amount = int(node.payload["amount"])
            setattr(player.combat, rating_attr, getattr(player.combat, rating_attr) + amount)
            message = f"{node.payload['rating']} increased by {amount}."
        elif node.kind == NodeKind.HEALTH:
            amount = int(node.payload["amount"])
            snapshot = getattr(player, "_normal_form_snapshot", None)
            target = snapshot["health"] if isinstance(snapshot, dict) else player.health
            target.max += amount
            target.current = min(target.max, target.current + amount)
            if isinstance(snapshot, dict):
                player.health.max += amount
                player.health.current = min(player.health.max, player.health.current + amount)
            message = f"Maximum HP increased by {amount}."
        elif node.kind == NodeKind.MANA:
            amount = int(node.payload["amount"])
            snapshot = getattr(player, "_normal_form_snapshot", None)
            target = snapshot["mana"] if isinstance(snapshot, dict) else player.mana
            target.max += amount
            target.current = min(target.max, target.current + amount)
            if isinstance(snapshot, dict):
                player.mana.max += amount
                player.mana.current = min(player.mana.max, player.mana.current + amount)
            message = f"Maximum MP increased by {amount}."
        else:
            removed = _apply_promotion(player, node, promotion_choices)
            promoted_to = node.payload["target_class"]
            state.completed_trees.add(node.tree_id)
            state.chosen_promotions[node.tree_id] = promoted_to
            if (node.tree_id, promoted_to) == ("Lancer", "Dragoon"):
                message = (
                    "Promoted to Dragoon; remaining Lancer training is retained "
                    "in the Dragoon tree."
                )
            elif (node.tree_id, promoted_to) == ("Mage", "Sorcerer"):
                message = (
                    "Promoted to Sorcerer; remaining Mage elemental-school "
                    "training is retained through Wizard."
                )
            elif (node.tree_id, promoted_to) == ("Sorcerer", "Wizard"):
                message = (
                    "Promoted to Wizard; remaining Mage elemental-school training is retained."
                )
            else:
                message = (
                    f"Promoted to {promoted_to}; unpurchased {node.tree_id} nodes are now closed."
                )
        state.purchased_node_ids.add(node.id)
        state.unspent_points -= node.cost
        _sync_level(player)
        return PurchaseResult(
            True,
            message,
            node.id,
            state.unspent_points,
            promoted_to,
            removed,
        )
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        _restore_purchase_snapshot(player, snapshot)
        return PurchaseResult(False, f"Purchase failed: {exc}", node.id, state.unspent_points)


def apply_progression_plan(
    player: Any,
    node_ids: tuple[str, ...] | list[str],
    attribute_increases: dict[str, int],
    *,
    promotion_choices: dict[str, dict[str, Any]] | None = None,
    node_choices: dict[str, dict[str, Any]] | None = None,
) -> PurchaseResult:
    """Atomically commit a staged set of node and attribute purchases."""
    state = ensure_progression(player)
    nodes = list(dict.fromkeys(node_ids))
    attributes = {
        name: int(amount) for name, amount in attribute_increases.items() if int(amount) > 0
    }
    unknown_nodes = [node_id for node_id in nodes if node_id not in TREE_NODES]
    if unknown_nodes:
        return PurchaseResult(
            False,
            f"Unknown progression node: {unknown_nodes[0]}.",
            points_remaining=state.unspent_points,
        )
    unknown_attributes = [name for name in attributes if name not in PRIMARY_ATTRIBUTES]
    if unknown_attributes:
        return PurchaseResult(
            False,
            f"Unknown primary attribute: {unknown_attributes[0]}.",
            points_remaining=state.unspent_points,
        )
    node_cost = sum(TREE_NODES[node_id].cost for node_id in nodes)
    attribute_cost = sum(attributes.values())
    if node_cost + attribute_cost <= 0:
        return PurchaseResult(
            False,
            "No points have been distributed.",
            points_remaining=state.unspent_points,
        )
    if node_cost > state.unspent_points:
        return PurchaseResult(
            False,
            "The staged nodes exceed the available progression points.",
            points_remaining=state.unspent_points,
        )
    if attribute_cost > state.unspent_attribute_points:
        return PurchaseResult(
            False,
            "The staged attributes exceed the available attribute points.",
            points_remaining=state.unspent_points,
        )
    if not _outside_combat(player):
        return PurchaseResult(
            False,
            "Progression purchases are unavailable in combat.",
            points_remaining=state.unspent_points,
        )

    snapshot = _purchase_snapshot(player)
    try:
        for stat_name in PRIMARY_ATTRIBUTES:
            for _index in range(attributes.get(stat_name, 0)):
                result = increase_attribute(player, stat_name)
                if not result.success:
                    raise ValueError(result.message)

        ordinary_nodes = [
            node_id
            for node_id in nodes
            if TREE_NODES.get(node_id, None) and TREE_NODES[node_id].kind != NodeKind.PROMOTION
        ]
        promotion_nodes = [
            node_id
            for node_id in nodes
            if TREE_NODES.get(node_id, None) and TREE_NODES[node_id].kind == NodeKind.PROMOTION
        ]
        if len(promotion_nodes) > 1:
            raise ValueError("Only one promotion can be purchased at a time.")

        pending = ordinary_nodes[:]
        while pending:
            progressed = False
            for node_id in pending[:]:
                result = purchase_node(
                    player,
                    node_id,
                    node_choices=(node_choices or {}).get(node_id),
                )
                if not result.success:
                    continue
                pending.remove(node_id)
                progressed = True
            if not progressed:
                first = pending[0]
                failure = purchase_node(
                    player,
                    first,
                    node_choices=(node_choices or {}).get(first),
                )
                raise ValueError(failure.message)

        promoted_to = None
        promotion_message = ""
        removed_equipment: tuple[str, ...] = ()
        for node_id in promotion_nodes:
            result = purchase_node(
                player,
                node_id,
                confirm_promotion=True,
                promotion_choices=(promotion_choices or {}).get(node_id),
            )
            if not result.success:
                raise ValueError(result.message)
            promoted_to = result.promoted_to
            promotion_message = result.message
            removed_equipment = result.removed_equipment
        spent_parts = []
        if node_cost:
            spent_parts.append(f"{node_cost} progression point{'s' if node_cost != 1 else ''}")
        if attribute_cost:
            spent_parts.append(
                f"{attribute_cost} attribute point{'s' if attribute_cost != 1 else ''}"
            )
        message = f"Spent {' and '.join(spent_parts)}."
        if promotion_message:
            message = f"{message} {promotion_message}"
        return PurchaseResult(
            True,
            message,
            points_remaining=player.progression.unspent_points,
            promoted_to=promoted_to,
            removed_equipment=removed_equipment,
        )
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        _restore_purchase_snapshot(player, snapshot)
        return PurchaseResult(
            False,
            f"Purchase failed: {exc}",
            points_remaining=player.progression.unspent_points,
        )


def level_up_message(result: LevelUpResult) -> str:
    """Build a frontend-neutral level-up summary."""
    if result.new_level == result.old_level:
        return f"Gained {result.experience_awarded} experience."
    lines = [f"Reached global level {result.new_level}."]
    if result.points_awarded:
        lines.append(
            f"+{result.points_awarded} progression point"
            f"{'s' if result.points_awarded != 1 else ''}."
        )
    else:
        lines.append("No progression point awarded at this level.")
    if result.attribute_points_awarded:
        lines.append(
            f"+{result.attribute_points_awarded} attribute point"
            f"{'s' if result.attribute_points_awarded != 1 else ''}."
        )
    for index, growth in enumerate(result.growth, start=result.old_level + 1):
        values = asdict(growth)
        details = ", ".join(
            f"+{amount} {name.replace('_', ' ')}" for name, amount in values.items()
        )
        lines.append(f"Level {index}: {details}.")
    return "\n".join(lines)
