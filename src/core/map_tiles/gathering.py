"""Specialist gathering-node rules for persistent dungeon resources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.randomness import gameplay_random as random

from .. import items

GATHERING_NODE_CHANCE = 0.03
GATHERING_ELIGIBLE_TILE_TYPES = frozenset({"EmptyCavePath", "CavePath0", "CavePath1", "CavePath2"})
GATHERING_STANDARD_DEPTHS = frozenset(range(0, 7))


@dataclass(frozen=True)
class GatheringNodeDefinition:
    """Describe one harvestable dungeon resource and its specialist knowledge."""

    resource_id: str
    item_class: type
    specialist_classes: frozenset[str]
    overlay_key: str


GATHERING_NODES = {
    "acorn": GatheringNodeDefinition(
        "acorn", items.Acorn, frozenset({"Druid", "Archdruid"}), "root_growth_sparse"
    ),
    "vine_seed": GatheringNodeDefinition(
        "vine_seed", items.VineSeed, frozenset({"Druid", "Archdruid"}), "root_growth"
    ),
    "fungus_spore": GatheringNodeDefinition(
        "fungus_spore", items.FungusSpore, frozenset({"Druid", "Archdruid"}), "fungus_patch_sparse"
    ),
    "hemlock_root": GatheringNodeDefinition(
        "hemlock_root", items.HemlockRoot, frozenset({"Druid", "Archdruid"}), "root_growth_dense"
    ),
    "deathcap_mushroom": GatheringNodeDefinition(
        "deathcap_mushroom",
        items.DeathcapMushroom,
        frozenset({"Assassin"}),
        "fungus_patch_dense",
    ),
}

_RESOURCE_WEIGHTS_BY_DEPTH = {
    range(0, 3): (("acorn", 40), ("vine_seed", 35), ("fungus_spore", 25)),
    range(3, 5): (
        ("vine_seed", 20),
        ("fungus_spore", 30),
        ("hemlock_root", 35),
        ("deathcap_mushroom", 15),
    ),
    range(5, 7): (("fungus_spore", 20), ("hemlock_root", 35), ("deathcap_mushroom", 45)),
}


def definition_for_tile(tile: object) -> GatheringNodeDefinition | None:
    """Return the active gathering definition for a tile, if it has one."""
    if not getattr(tile, "gathering_available", False) or getattr(
        tile, "gathering_harvested", False
    ):
        return None
    resource_id = getattr(tile, "gathering_resource", None)
    return GATHERING_NODES.get(resource_id)


def can_identify_gathering_node(player_char: object, tile: object) -> bool:
    """Return whether the character knows how to identify and harvest this node."""
    definition = definition_for_tile(tile)
    class_name = getattr(getattr(player_char, "cls", None), "name", "")
    return definition is not None and class_name in definition.specialist_classes


def gathering_hint(player_char: object, tile: object, *, current_tile: bool) -> str:
    """Return contextual discovery text for a visible gathering node."""
    definition = definition_for_tile(tile)
    if definition is None:
        return ""
    location = "here" if current_tile else "ahead"
    if can_identify_gathering_node(player_char, tile):
        action = " Press O to harvest." if current_tile else ""
        return f"You recognize {definition.item_class().name} growing {location}.{action}"
    return f"You notice unfamiliar growth {location}, but lack the knowledge to harvest it."


def harvest_gathering_node(player_char: object, tile: object):
    """Harvest one recognized gathering node, returning its item or ``None``."""
    if not can_identify_gathering_node(player_char, tile):
        return None
    definition = definition_for_tile(tile)
    if definition is None:
        return None
    item = definition.item_class()
    player_char.modify_inventory(item)
    tile.gathering_harvested = True
    tile.gathering_available = False
    return item


def _resource_weights(depth: int) -> tuple[tuple[str, int], ...]:
    for depth_range, weights in _RESOURCE_WEIGHTS_BY_DEPTH.items():
        if depth in depth_range:
            return weights
    return ()


def assign_dungeon_gathering_nodes(world_dict: dict, *, rng: Any | None = None) -> int:
    """Assign deterministic, sparse specialist resource nodes to ordinary cave paths."""
    rng = rng or random.Random(0x6A7E1)
    assigned = 0
    for position, tile in sorted(world_dict.items()):
        depth = int(getattr(tile, "z", position[2]) or 0)
        eligible = (
            type(tile).__name__ in GATHERING_ELIGIBLE_TILE_TYPES
            and depth in GATHERING_STANDARD_DEPTHS
        )
        tile.gathering_resource = None
        tile.gathering_available = False
        tile.gathering_harvested = False
        if not eligible or rng.random() >= GATHERING_NODE_CHANCE:
            continue
        weighted_resources = _resource_weights(depth)
        if not weighted_resources:
            continue
        resource_ids, weights = zip(*weighted_resources, strict=True)
        tile.gathering_resource = rng.choices(resource_ids, weights=weights, k=1)[0]
        tile.gathering_available = True
        assigned += 1
    return assigned
