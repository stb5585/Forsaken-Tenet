"""Player state serialization and restoration."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from .. import main_story, quest_progress, thieves_guild
from .. import town as town_core
from ..character import Combat, Level, Resource, Stats
from ..classes import bard, promotion_kits, transformation
from ..contracts import ActionReference
from ..identity import CLASS_TYPES, RACE_TYPES
from .errors import SaveValidationError
from .item_serialization import AbilitySerializer, ItemSerializer
from .models import SAVE_SCHEMA_VERSION, CombatData, LevelData, ResourceData, StatsData
from .quests import QuestDataSerializer
from .summons import SummonSerializer
from .tiles import TileStateSerializer

if TYPE_CHECKING:
    from typing import Any


class PlayerDataSerializer:
    """Serializes/deserializes player character."""

    @staticmethod
    def _is_jump_skill(skill) -> bool:
        return bool(
            skill
            and getattr(skill, "name", "") == "Jump"
            and hasattr(skill, "modifications")
            and hasattr(skill, "unlocked_modifications")
        )

    @staticmethod
    def _is_totem_skill(skill) -> bool:
        return bool(
            skill and getattr(skill, "name", "") == "Totem" and hasattr(skill, "unlocked_aspects")
        )

    @staticmethod
    def _portrait_variant(value) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _serialize_action_bar(player) -> list[dict[str, str] | None]:
        """Return exactly six typed action-reference save slots."""
        raw_assignments = list(getattr(player, "action_bar_assignments", ()) or ())[:6]
        raw_assignments.extend([None] * (6 - len(raw_assignments)))
        serialized: list[dict[str, str] | None] = []
        for assignment in raw_assignments:
            if assignment is None:
                serialized.append(None)
            elif isinstance(assignment, ActionReference):
                serialized.append(assignment.to_dict())
            elif isinstance(assignment, dict):
                serialized.append(ActionReference.from_dict(assignment).to_dict())
            else:
                raise TypeError("action bar entries must be ActionReference, mapping, or None")
        return serialized

    @staticmethod
    def _deserialize_action_bar(payload: object) -> tuple[ActionReference | None, ...]:
        """Parse and normalize exactly six canonical shortcut slots."""
        if payload is None:
            entries: list[object] = []
        elif isinstance(payload, list):
            entries = list(payload[:6])
        else:
            raise TypeError("action_bar_assignments must be a list")
        entries.extend([None] * (6 - len(entries)))
        assignments: list[ActionReference | None] = []
        for entry in entries:
            if entry is None:
                assignments.append(None)
            elif isinstance(entry, dict):
                assignments.append(ActionReference.from_dict(entry))
            else:
                raise TypeError("action bar entries must be mappings or null")
        return tuple(assignments)

    @staticmethod
    def _serialize_transformation_state(player) -> dict[str, Any] | None:
        state = getattr(player, "transformation_state", None)
        if not transformation.is_transformed(player) or not isinstance(state, dict):
            return None
        overlay = state.get("overlay")
        if not isinstance(overlay, dict):
            return None
        return {
            "active_form": state.get("active_form"),
            "overlay": {
                "health_bonus": int(overlay.get("health_bonus", 0) or 0),
                "mana_bonus": int(overlay.get("mana_bonus", 0) or 0),
                "stats": dict(overlay.get("stats", {})),
                "equipment": {
                    slot: ItemSerializer.serialize(item)
                    for slot, item in overlay.get("equipment", {}).items()
                },
                "spellbook": {
                    book: {
                        name: AbilitySerializer.serialize(ability)
                        for name, ability in entries.items()
                    }
                    for book, entries in overlay.get("spellbook", {}).items()
                },
                "resistance": dict(overlay.get("resistance", {})),
            },
        }

    @staticmethod
    def _deserialize_transformation_state(data: Any) -> tuple[str, dict[str, Any]] | None:
        if not isinstance(data, dict) or not data.get("active_form"):
            return None
        overlay = data.get("overlay")
        if not isinstance(overlay, dict):
            return None
        return str(data["active_form"]), {
            "health_bonus": int(overlay.get("health_bonus", 0) or 0),
            "mana_bonus": int(overlay.get("mana_bonus", 0) or 0),
            "stats": dict(overlay.get("stats", {})),
            "equipment": {
                slot: ItemSerializer.deserialize(item)
                for slot, item in overlay.get("equipment", {}).items()
            },
            "spellbook": {
                book: {
                    name: AbilitySerializer.deserialize(ability)
                    for name, ability in entries.items()
                }
                for book, entries in overlay.get("spellbook", {}).items()
            },
            "resistance": dict(overlay.get("resistance", {})),
        }

    @staticmethod
    def serialize(player) -> dict[str, Any]:
        """Convert player object to data dictionary."""
        from ..player import normalize_gameplay_stats

        canonical = transformation.canonical_view(player)

        # Basic attributes
        data = {
            "schema_version": SAVE_SCHEMA_VERSION,
            "name": player.name,
            "location": (player.location_x, player.location_y, player.location_z),
            "facing": player.facing,
            "health": asdict(ResourceData(canonical["health"].max, canonical["health"].current)),
            "mana": asdict(ResourceData(canonical["mana"].max, canonical["mana"].current)),
            "stats": asdict(
                StatsData(
                    canonical["stats"].strength,
                    canonical["stats"].intel,
                    canonical["stats"].wisdom,
                    canonical["stats"].con,
                    canonical["stats"].charisma,
                    canonical["stats"].dex,
                )
            ),
            "combat": asdict(
                CombatData(
                    player.combat.attack,
                    player.combat.defense,
                    player.combat.magic,
                    player.combat.magic_def,
                )
            ),
            "level": asdict(
                LevelData(
                    player.level.level,
                    player.level.pro_level,
                    player.level.exp,
                    player.level.exp_to_gain,
                )
            ),
            "progression": player.progression.to_dict(),
            "gold": player.gold,
            "resistance": dict(canonical["resistance"]),
            # Equipment
            "equipment": {
                slot: ItemSerializer.serialize(item)
                for slot, item in canonical["equipment"].items()
            },
            # Inventory
            "inventory": {
                item_name: [ItemSerializer.serialize(item) for item in item_list]
                for item_name, item_list in player.inventory.items()
            },
            "special_inventory": {
                item_name: [ItemSerializer.serialize(item) for item in item_list]
                for item_name, item_list in player.special_inventory.items()
            },
            "storage": {
                item_name: [ItemSerializer.serialize(item) for item in item_list]
                for item_name, item_list in player.storage.items()
            },
            # Spellbook
            "spellbook": {
                "Spells": {
                    name: AbilitySerializer.serialize(spell)
                    for name, spell in canonical["spellbook"]["Spells"].items()
                },
                "Skills": {
                    name: AbilitySerializer.serialize(skill)
                    for name, skill in canonical["spellbook"]["Skills"].items()
                },
            },
            "spellbook_state": {
                "Skills": {},
            },
            "action_bar_assignments": PlayerDataSerializer._serialize_action_bar(player),
            "action_bar_autofill_complete": bool(
                getattr(player, "action_bar_autofill_complete", False)
            ),
            # Character attributes
            "class_id": CLASS_TYPES.id_for(canonical["cls"]) if canonical["cls"] else None,
            "race_id": RACE_TYPES.id_for(player.race) if player.race else None,
            "sex": getattr(player, "sex", "Male"),
            "portrait_variant": PlayerDataSerializer._portrait_variant(
                getattr(player, "portrait_variant", 0)
            ),
            "invisible": player.invisible,
            "flying": player.flying,
            "sight": player.sight,
            "power_up": player.power_up,
            "encumbered": player.encumbered,
            "state": player.state,
            "warp_point": player.warp_point,
            "intro_shown": getattr(player, "intro_shown", False),
            "inventory_sort_mode": getattr(player, "inventory_sort_mode", "Name"),
            # Derived data - serialize quest_dict properly
            "quest_dict": QuestDataSerializer.serialize_quest_dict(player.quest_dict),
            "bounty_board_state": town_core.normalize_bounty_board_state(
                getattr(player, "bounty_board_state", None)
            ),
            "kill_dict": player.kill_dict,
            "last_defeated_enemy": getattr(player, "last_defeated_enemy", None),
            "transient_companion": getattr(player, "transient_companion", None),
            "conjure_potion_cooldown": int(getattr(player, "conjure_potion_cooldown", 0) or 0),
            "conjure_elixir_cooldown": int(getattr(player, "conjure_elixir_cooldown", 0) or 0),
            "torchlight_steps": int(getattr(player, "torchlight_steps", 0) or 0),
            "xenid_choices": dict(getattr(player, "xenid_choices", {}) or {}),
            "bestiary": getattr(player, "bestiary", {}),
            "absorb_essence_state": getattr(player, "absorb_essence_state", {}),
            "spirit_animal": getattr(player, "spirit_animal", "Bear"),
            "grandmaster_discipline": getattr(player, "grandmaster_discipline", None),
            "demonologist_contracts": getattr(player, "demonologist_contracts", None),
            "persistent_curses": getattr(player, "persistent_curses", {}),
            "fractures": getattr(player, "fractures", {}),
            "archdruid_attunement": getattr(player, "archdruid_attunement", None),
            "class_ring_awakening": getattr(player, "class_ring_awakening", None),
            "promotion_kit_state": promotion_kits.normalize_state(
                getattr(player, "promotion_kit_state", None)
            ),
            "astromancer_state": getattr(player, "astromancer_state", None),
            "paladin_vow": getattr(player, "paladin_vow", None),
            "dragoon_dragon_quest": getattr(player, "dragoon_dragon_quest", None),
            "bard_song": getattr(player, "bard_song", None),
            "bard_exploration_song": getattr(
                player,
                "bard_exploration_song",
                None,
            ),
            "summons": SummonSerializer.serialize_summons(getattr(player, "summons", {})),
            "tamed_companion": getattr(player, "tamed_companion", None),
            "familiar_state": (
                {
                    "race": getattr(player.familiar, "race", ""),
                    "name": getattr(player.familiar, "name", ""),
                    "pro_level": getattr(player.familiar.level, "pro_level", 1),
                    "exp": getattr(player.familiar.level, "exp", 0),
                    "exp_to_gain": getattr(player.familiar.level, "exp_to_gain", 500),
                }
                if getattr(player, "familiar", None) is not None
                and getattr(player.familiar, "spec", "") != "Tamed"
                else None
            ),
            "temporary_exploration_effects": getattr(player, "temporary_exploration_effects", None),
            "lycan_state": getattr(player, "lycan_state", None),
            "transformation_state": PlayerDataSerializer._serialize_transformation_state(player),
            "wizard_affinity": getattr(player, "wizard_affinity", None),
            "wizard_affinity_version": getattr(player, "wizard_affinity_version", 1),
            "main_story": main_story.normalize_state(getattr(player, "main_story", None)),
            "thieves_guild": thieves_guild.normalize_state(getattr(player, "thieves_guild", None)),
            "liminal_gap_return": getattr(player, "liminal_gap_return", None),
            "dungeon_trap_seed": int(getattr(player, "dungeon_trap_seed", 0) or 0),
            "resist_death_steps": int(getattr(player, "resist_death_steps", 0) or 0),
            "applied_toxin": getattr(player, "_applied_toxin", None),
            "selected_crossbow_bolts": getattr(player, "selected_crossbow_bolts", ""),
            "gameplay_stats": normalize_gameplay_stats(
                getattr(player, "gameplay_stats", None),
                current_level=(
                    player.player_level()
                    if hasattr(player, "player_level")
                    else getattr(getattr(player, "level", None), "level", 1)
                ),
            ),
            # World state (tile visited flags, defeated enemies, open doors, etc.)
            "world_state": (
                TileStateSerializer.serialize_tile_state(player.world_dict)
                if player.world_dict
                else {}
            ),
        }

        # Persist stateful skill data (e.g., Jump modifications, Totem aspects)
        for name, skill in canonical["spellbook"].get("Skills", {}).items():
            if not skill:
                continue
            if PlayerDataSerializer._is_jump_skill(skill):
                data["spellbook_state"]["Skills"][name] = {
                    "modifications": getattr(skill, "modifications", None),
                    "unlocked_modifications": getattr(skill, "unlocked_modifications", None),
                }
            elif PlayerDataSerializer._is_totem_skill(skill):
                data["spellbook_state"]["Skills"][name] = {
                    "unlocked_aspects": getattr(skill, "unlocked_aspects", None),
                    "active_aspect": getattr(skill, "active_aspect", None),
                }

        return data

    @staticmethod
    def deserialize(data: dict[str, Any], skip_tiles=False):
        """Reconstruct player from data dictionary.

        Args:
            data: Serialized player data dictionary
            skip_tiles: If True, skip loading world tiles (for transform feature)
        """
        from ..player import Player, normalize_gameplay_stats
        from ..progression import ProgressionState, award_experience

        if not isinstance(data, dict):
            raise SaveValidationError("save", "expected an object")
        class_id = data.get("class_id")
        race_id = data.get("race_id")
        if not isinstance(class_id, str) or not class_id:
            raise SaveValidationError("class_id", "expected a non-empty string")
        if not isinstance(race_id, str) or not race_id:
            raise SaveValidationError("race_id", "expected a non-empty string")
        try:
            class_type = CLASS_TYPES.resolve(class_id)
        except KeyError as exc:
            raise SaveValidationError("class_id", str(exc)) from exc
        try:
            race_type = RACE_TYPES.resolve(race_id)
        except KeyError as exc:
            raise SaveValidationError("race_id", str(exc)) from exc
        try:
            restored_class = class_type()
            restored_race = race_type()
        except (TypeError, ValueError) as exc:
            raise SaveValidationError(
                "identity", f"could not construct character identity: {exc}"
            ) from exc

        # Create fresh character
        health = Resource(data["health"]["max"], data["health"]["current"])
        mana = Resource(data["mana"]["max"], data["mana"]["current"])

        stats_d = data["stats"]
        stats = Stats(
            strength=stats_d["strength"],
            intel=stats_d["intel"],
            wisdom=stats_d["wisdom"],
            con=stats_d["con"],
            charisma=stats_d["charisma"],
            dex=stats_d["dex"],
        )

        combat_d = data["combat"]
        combat = Combat(
            attack=combat_d["attack"],
            defense=combat_d["defense"],
            magic=combat_d["magic"],
            magic_def=combat_d["magic_def"],
        )

        level_d = data["level"]
        level = Level(
            level=level_d["level"],
            pro_level=level_d["pro_level"],
            exp=level_d["exp"],
            exp_to_gain=level_d["exp_to_gain"],
        )

        # Create player
        player = Player(
            data["location"][0],
            data["location"][1],
            data["location"][2],
            level,
            health,
            mana,
            stats,
            combat,
            data["gold"],
            data["resistance"],
        )

        # Restore basic attributes
        player.name = data["name"]
        player.sex = data.get("sex", "Male")
        player.portrait_variant = PlayerDataSerializer._portrait_variant(
            data.get("portrait_variant", 0)
        )
        player.invisible = data["invisible"]
        player.flying = data["flying"]
        player.sight = data["sight"]
        player.power_up = data["power_up"]
        player.state = data["state"]
        player.warp_point = data["warp_point"]
        player.facing = data["facing"]
        player.inventory_sort_mode = data.get("inventory_sort_mode", "Name")
        player.action_bar_assignments = PlayerDataSerializer._deserialize_action_bar(
            data.get("action_bar_assignments")
        )
        player.action_bar_autofill_complete = bool(data.get("action_bar_autofill_complete", False))

        # Restore the identity only after every persisted ID has been validated.
        player.cls = restored_class
        player.race = restored_race

        player.transform_type = player.cls
        player.progression = ProgressionState.from_dict(data["progression"])
        award_experience(player, 0)

        # Restore equipment
        required_slots = {"Weapon", "OffHand", "Armor", "Helmet", "Ring", "Pendant"}
        equipment_data = data["equipment"]
        missing_slots = required_slots.difference(equipment_data)
        if missing_slots:
            raise SaveValidationError(
                "equipment", f"missing required slots: {', '.join(sorted(missing_slots))}"
            )
        for slot, item_data in equipment_data.items():
            player.equipment[slot] = ItemSerializer.deserialize(item_data, path=f"equipment.{slot}")

        # Restore inventory
        for item_name, item_list in data["inventory"].items():
            player.inventory[item_name] = [
                ItemSerializer.deserialize(item_data) for item_data in item_list
            ]

        for item_name, item_list in data["special_inventory"].items():
            player.special_inventory[item_name] = [
                ItemSerializer.deserialize(item_data) for item_data in item_list
            ]

        # Migrate legacy quest-key items that used to be stored in the main inventory.
        legacy_jester_tokens = player.inventory.pop("Jester Token", [])
        if legacy_jester_tokens:
            player.special_inventory.setdefault("Jester Token", []).extend(legacy_jester_tokens)

        for item_name, item_list in data["storage"].items():
            player.storage[item_name] = [
                ItemSerializer.deserialize(item_data) for item_data in item_list
            ]

        # Restore spellbook
        player.spellbook["Spells"] = {
            name: AbilitySerializer.deserialize(ability_name)
            for name, ability_name in data["spellbook"]["Spells"].items()
        }
        player.spellbook["Skills"] = {
            name: AbilitySerializer.deserialize(ability_name)
            for name, ability_name in data["spellbook"]["Skills"].items()
        }
        for name, rank in player.progression.ability_ranks.items():
            ability = player.spellbook["Skills"].get(name)
            if ability is not None:
                ability.ranks = rank

        # Restore stateful skill data (e.g., Jump modifications, Totem aspects)
        spellbook_state = data.get("spellbook_state", {})
        skill_state = spellbook_state.get("Skills", {})
        if skill_state:
            for name, state in skill_state.items():
                skill = player.spellbook["Skills"].get(name)
                if PlayerDataSerializer._is_jump_skill(skill):
                    if "modifications" in state and state["modifications"] is not None:
                        skill.modifications = state["modifications"]
                    if (
                        "unlocked_modifications" in state
                        and state["unlocked_modifications"] is not None
                    ):
                        skill.unlocked_modifications = state["unlocked_modifications"]
                elif PlayerDataSerializer._is_totem_skill(skill):
                    if "unlocked_aspects" in state and state["unlocked_aspects"] is not None:
                        skill.unlocked_aspects = state["unlocked_aspects"]
                    if "active_aspect" in state and state["active_aspect"] is not None:
                        skill.active_aspect = state["active_aspect"]
        from ..progression import ensure_progression

        ensure_progression(player)

        # Restore quest/kill dicts
        player.quest_dict = QuestDataSerializer.deserialize_quest_dict(
            data.get("quest_dict", {"Bounty": {}, "Main": {}, "Side": {}})
        )
        quest_progress.migrate_relic_story_quests(player)
        player.bounty_board_state = town_core.normalize_bounty_board_state(
            data.get("bounty_board_state")
        )
        player.kill_dict = data.get("kill_dict", {})
        player.last_defeated_enemy = data.get("last_defeated_enemy")
        player.transient_companion = data.get("transient_companion")
        player.conjure_potion_cooldown = max(0, int(data.get("conjure_potion_cooldown", 0) or 0))
        player.conjure_elixir_cooldown = max(0, int(data.get("conjure_elixir_cooldown", 0) or 0))
        player.torchlight_steps = max(0, int(data.get("torchlight_steps", 0) or 0))
        player.xenid_choices = dict(data.get("xenid_choices", {}) or {})
        player.bestiary = data.get("bestiary", {})
        player.absorb_essence_state = data.get(
            "absorb_essence_state", getattr(player, "absorb_essence_state", {})
        )
        spirit_animal = str(data.get("spirit_animal", "Bear"))
        player.spirit_animal = (
            spirit_animal
            if spirit_animal
            in (
                "Bear",
                "Wolf",
                "Owl",
                "Panther",
                "Eagle",
                "Turtle",
                "Toad",
                "Snake",
            )
            else "Bear"
        )
        player.grandmaster_discipline = data.get(
            "grandmaster_discipline", getattr(player, "grandmaster_discipline", None)
        )
        if hasattr(player, "ensure_grandmaster_discipline"):
            player.ensure_grandmaster_discipline()
        player.demonologist_contracts = data.get(
            "demonologist_contracts",
            getattr(player, "demonologist_contracts", None),
        )
        if hasattr(player, "ensure_demonologist_contracts"):
            player.ensure_demonologist_contracts()
        from .. import persistent_afflictions as afflictions

        player.persistent_curses = data.get("persistent_curses", {})
        afflictions.ensure_curses(player)
        player.fractures = dict(data.get("fractures", {}) or {})
        familiar_state = data.get("familiar_state")
        if isinstance(familiar_state, dict):
            from .. import companions

            familiar_ctor = getattr(companions, str(familiar_state.get("race", "")), None)
            if callable(familiar_ctor):
                player.familiar = familiar_ctor()
                player.familiar.name = str(familiar_state.get("name") or player.familiar.race)
                target_level = max(1, min(3, int(familiar_state.get("pro_level", 1) or 1)))
                while player.familiar.level.pro_level < target_level:
                    player.familiar.level_up()
                player.familiar.level.exp = max(0, int(familiar_state.get("exp", 0) or 0))
                player.familiar.level.exp_to_gain = max(
                    0, int(familiar_state.get("exp_to_gain", 0) or 0)
                )
        player.archdruid_attunement = data.get(
            "archdruid_attunement",
            getattr(player, "archdruid_attunement", None),
        )
        if hasattr(player, "ensure_archdruid_attunement"):
            player.ensure_archdruid_attunement()
        player.class_ring_awakening = data.get(
            "class_ring_awakening",
            getattr(player, "class_ring_awakening", None),
        )
        if hasattr(player, "ensure_class_ring_awakening"):
            player.ensure_class_ring_awakening()
        player.promotion_kit_state = data.get(
            "promotion_kit_state",
            getattr(player, "promotion_kit_state", None),
        )
        if hasattr(player, "ensure_promotion_kit_state"):
            player.ensure_promotion_kit_state()
        promotion_kits.sync_xenid_invocations(player)
        promotion_kits.clear_combat_state(player)
        from ..classes import class_rings

        class_rings.reset_combat_flags(player)
        player.astromancer_state = data.get(
            "astromancer_state",
            getattr(player, "astromancer_state", None),
        )
        if hasattr(player, "ensure_astromancer_state"):
            player.ensure_astromancer_state()
        player.paladin_vow = data.get(
            "paladin_vow",
            getattr(player, "paladin_vow", None),
        )
        if hasattr(player, "ensure_paladin_vow"):
            player.ensure_paladin_vow()
        player.dragoon_dragon_quest = data.get(
            "dragoon_dragon_quest",
            getattr(player, "dragoon_dragon_quest", None),
        )
        if hasattr(player, "ensure_dragoon_dragon_quest"):
            player.ensure_dragoon_dragon_quest()
        player.bard_song = data.get("bard_song", getattr(player, "bard_song", None))
        if hasattr(player, "ensure_bard_song"):
            player.ensure_bard_song()
        player.bard_exploration_song = bard.normalize_exploration_song_state(
            data.get(
                "bard_exploration_song",
                getattr(player, "bard_exploration_song", None),
            )
        )
        player.summons = SummonSerializer.deserialize_summons(data.get("summons", {}))
        player.tamed_companion = data.get(
            "tamed_companion", getattr(player, "tamed_companion", None)
        )
        if hasattr(player, "ensure_tamed_companion"):
            player.ensure_tamed_companion()
        player.temporary_exploration_effects = data.get(
            "temporary_exploration_effects",
            getattr(player, "temporary_exploration_effects", None),
        )
        if hasattr(player, "ensure_temporary_exploration_effects"):
            player.ensure_temporary_exploration_effects()
        player.lycan_state = data.get("lycan_state", getattr(player, "lycan_state", None))
        if hasattr(player, "ensure_lycan_state"):
            player.ensure_lycan_state()
        legacy_dragon_essence = bool(
            isinstance(player.lycan_state, dict) and player.lycan_state.get("dragon_essence", False)
        )
        if legacy_dragon_essence:
            promotion_kits.lycan_control_state(player)["dragon_essence"] = True
        player.wizard_affinity = data.get(
            "wizard_affinity", getattr(player, "wizard_affinity", None)
        )
        player.wizard_affinity_version = data.get(
            "wizard_affinity_version",
            getattr(player, "wizard_affinity_version", 1),
        )
        if hasattr(player, "ensure_wizard_affinity"):
            player.ensure_wizard_affinity()
        player.main_story = data.get("main_story", getattr(player, "main_story", None))
        if hasattr(player, "ensure_main_story_state"):
            player.ensure_main_story_state()
        player.thieves_guild = data.get("thieves_guild", getattr(player, "thieves_guild", None))
        if hasattr(player, "ensure_thieves_guild_state"):
            player.ensure_thieves_guild_state()
        liminal_gap_return = data.get(
            "liminal_gap_return", getattr(player, "liminal_gap_return", None)
        )
        if isinstance(liminal_gap_return, (list, tuple)) and len(liminal_gap_return) >= 4:
            liminal_gap_return = tuple(liminal_gap_return[:4])
        else:
            liminal_gap_return = None
        player.liminal_gap_return = liminal_gap_return
        player.dungeon_trap_seed = int(
            data.get("dungeon_trap_seed", getattr(player, "dungeon_trap_seed", 0)) or 0
        )
        player.resist_death_steps = int(data.get("resist_death_steps", 0) or 0)
        applied_toxin = data.get("applied_toxin")
        player._applied_toxin = applied_toxin if isinstance(applied_toxin, dict) else None
        player.selected_crossbow_bolts = str(data.get("selected_crossbow_bolts", "") or "")
        player.gameplay_stats = normalize_gameplay_stats(
            data.get("gameplay_stats"),
            current_level=(
                player.player_level() if hasattr(player, "player_level") else player.level.level
            ),
        )
        player.intro_shown = data.get("intro_shown", False)

        saved_form = PlayerDataSerializer._deserialize_transformation_state(
            data.get("transformation_state")
        )
        if saved_form is not None:
            form_name, overlay = saved_form
            transformation.apply_form(player, form_name, overlay=overlay, force=True)

        # Load world tiles and restore saved world state (unless skipped for transform)
        if not skip_tiles:
            player.load_tiles()
            if "world_state" in data:
                TileStateSerializer.restore_tile_state(player.world_dict, data["world_state"])

            # Fallback: if legacy saves lack tile state, mark boss rooms defeated
            # when the player already has boss kills recorded.
            if player.world_dict:
                killed_names = set()
                for _typ, name_counts in (player.kill_dict or {}).items():
                    for name, count in name_counts.items():
                        if count:
                            killed_names.add(name)

                if killed_names:
                    for tile in player.world_dict.values():
                        if hasattr(tile, "defeated") and not getattr(tile, "defeated", False):
                            enemy = getattr(tile, "enemy", None)
                            enemy_name = None
                            if isinstance(enemy, type):
                                enemy_name = enemy.__name__
                            elif hasattr(enemy, "name"):
                                enemy_name = enemy.name

                            if enemy_name and enemy_name in killed_names:
                                tile.defeated = True
                                tile.enemy = None

                from .. import map_tiles

                if map_tiles.jester_defeated(player):
                    for tile in player.world_dict.values():
                        if type(tile).__name__ == "FunhouseTeleporter" and hasattr(tile, "active"):
                            tile.active = False
                map_tiles.sync_rookie_body_drop_marker(player)

        return player
