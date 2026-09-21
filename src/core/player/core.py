"""Concrete Player class composed from focused behavior mixins."""

from src.core.randomness import gameplay_random as random

from .. import main_story, thieves_guild, town
from ..character import Character
from ..classes import (
    ability_mechanics,
    archdruid,
    astromancer,
    bard,
    class_rings,
    demonologist,
    dragoon,
    grandmaster,
    lycan,
    paladin,
    promotion_kits,
    wizard,
)
from ..constants import EXP_SCALE_BASE, TOWN_LOCATION
from ..progression import (
    ProgressionState,
    attribute_points_through_level,
    progression_points_through_level,
)
from .combat import PlayerCombatMixin
from .exploration import PlayerExplorationMixin
from .inventory import PlayerInventoryMixin
from .presentation import PlayerPresentationMixin
from .progression import PlayerProgressionMixin
from .state import PlayerStateMixin
from .stats import normalize_gameplay_stats


class Player(
    PlayerStateMixin,
    PlayerExplorationMixin,
    PlayerPresentationMixin,
    PlayerInventoryMixin,
    PlayerProgressionMixin,
    PlayerCombatMixin,
    Character,
):
    """
    Player character class
    Health is defined based on initial value and is modified by the constitution stat
    Mana is defined based on the initial value and is modified by the intelligence stat

    encumbered(bool): signifies whether player is over carry weight
    power_up(bool): switch for power-up for retrieving Power Core
    """

    ABSORB_ESSENCE_MAX_PROCS_PER_FLOOR = 3
    ABSORB_ESSENCE_MAX_PROCS_PER_ENEMY_PER_FLOOR = 1
    ABSORB_ESSENCE_MAX_STAT_GAINS = 12
    ABSORB_ESSENCE_MAX_HEALTH_GAINS = 60
    ABSORB_ESSENCE_MAX_MANA_GAINS = 60
    ABSORB_ESSENCE_MAX_LEVEL_GAINS = 3

    def __init__(
        self,
        location_x,
        location_y,
        location_z,
        level,
        health,
        mana,
        stats,
        combat,
        gold,
        resistance,
    ):
        super().__init__(name="", health=health, mana=mana, stats=stats, combat=combat)
        self.location_x = location_x
        self.location_y = location_y
        self.location_z = location_z
        self.facing = "east"
        self.previous_location = TOWN_LOCATION  # starts at town location
        self.state = "normal"
        self.exp_scale = EXP_SCALE_BASE
        self.gold = gold
        self.level = level
        self.progression = ProgressionState(
            level=max(1, min(100, int(level.level))),
            total_xp=max(0, int(level.exp)),
            unspent_points=progression_points_through_level(level.level),
            unspent_attribute_points=attribute_points_through_level(
                level.level,
            ),
        )
        self.resistance = resistance
        self.sex = "Male"
        self.portrait_variant = 0
        self.inventory = {}
        self.action_bar_assignments = ()
        self.action_bar_autofill_complete = False
        self.special_inventory = {}
        self.world_dict = {}
        self.dungeon_trap_seed = random.SystemRandom().randrange(2**32)
        self.quest_dict = {"Bounty": {}, "Main": {}, "Side": {}}
        self.bounty_board_state = town.default_bounty_board_state()
        self.kill_dict = {}
        self.last_defeated_enemy = None
        self.transient_companion = None
        self.conjure_potion_cooldown = 0
        self.conjure_elixir_cooldown = 0
        self.torchlight_steps = 0
        self.xenid_choices = {}
        self.bestiary = {}
        self.storage = {}
        self.grandmaster_discipline = grandmaster.default_state()
        self._grandmaster_battle_hit_types = set()
        self.demonologist_contracts = demonologist.default_state()
        self.archdruid_attunement = archdruid.default_state()
        self.class_ring_awakening = class_rings.default_state()
        self.promotion_kit_state = promotion_kits.default_state()
        self.astromancer_state = astromancer.default_state()
        self.paladin_vow = paladin.default_state()
        self.dragoon_dragon_quest = dragoon.default_state()
        self.bard_song = bard.default_song_state()
        self.tamed_companion = ability_mechanics.default_tamed_companion()
        self.temporary_exploration_effects = ability_mechanics.default_exploration_effects()
        self.lycan_state = lycan.default_state()
        self.wizard_affinity = wizard.default_affinity()
        self.wizard_affinity_version = 2
        self.main_story = main_story.default_state()
        self.thieves_guild = thieves_guild.default_state()
        self.warp_point = False
        self.quit = False
        self.teleport = None
        self.familiar = None
        self.summons = {}
        self.transform_type = self.cls
        self._transformed = False
        self._normal_form_snapshot = None
        self._normal_class_name = ""
        self._selected_transform_form = ""
        self.transformation_state = {"active_form": None, "overlay": None}
        self.encumbered = False
        self.power_up = False
        self.inventory_sort_mode = "Name"
        self.gameplay_stats = normalize_gameplay_stats(current_level=self.player_level())
        # Dwarf Gluttony (racial sin): out-of-combat hangover that can affect initiative
        # for a number of steps after using combat consumables.
        self.dwarf_hangover_steps = 0
        self.absorb_essence_state = {
            "floor": self.location_z,
            "procs_this_floor": 0,
            "procs_by_enemy": {},
            "stat_gains": {
                "strength": 0,
                "intel": 0,
                "wisdom": 0,
                "con": 0,
                "charisma": 0,
                "dex": 0,
            },
            "health_gains": 0,
            "mana_gains": 0,
            "level_gains": 0,
            "dragon_gold_claimed": False,
        }

    def __str__(self):
        return (
            f"{self.name} | "
            f"Health: {self.health.current}/{self.health.max} | "
            f"Mana: {self.mana.current}/{self.mana.max}"
        )
