#!/usr/bin/env python3
"""
Character and Combat System Tests

Tests core character functionality, combat mechanics, and API contracts.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2]))

import pytest

from src.core import abilities, companions, enemies, items
from src.core.enemies import Goblin
from src.core.save_system import (
    PlayerDataSerializer,
    QuestDataSerializer,
    SaveValidationError,
    TileStateSerializer,
)
from tests.test_framework import TestGameState


class TestCharacterCreation:
    """Test basic character creation and initialization."""

    def test_create_basic_character(self):
        """Test creating a basic character."""
        char = TestGameState.create_player(name="TestHero", class_name="Warrior", race_name="Human")
        assert char.name == "TestHero"
        assert char.race.name == "Human"
        assert char.cls.name == "Warrior"
        assert char.is_alive()

    def test_character_has_required_attributes(self):
        """Verify character has all required attributes for combat."""
        char = TestGameState.create_player(name="Test", class_name="Warrior", race_name="Human")

        # Core attributes
        assert hasattr(char, "name")
        assert hasattr(char, "health")
        assert hasattr(char, "mana")
        assert hasattr(char, "stats")
        assert hasattr(char, "combat")
        assert hasattr(char, "equipment")

        # Combat attributes
        assert hasattr(char, "magic_effects")
        assert hasattr(char, "status_effects")
        assert hasattr(char, "physical_effects")
        assert hasattr(char, "stat_effects")

        # Methods
        assert hasattr(char, "is_alive")
        assert hasattr(char, "weapon_damage")
        assert hasattr(char, "hit_chance")
        assert hasattr(char, "dodge_chance")

    def test_resource_current_cannot_go_negative(self):
        """Resource pools should floor at zero when costs overrun."""
        from src.core.character import Resource

        resource = Resource(max=30, current=5)
        resource.current -= 12

        assert resource.current == 0


class TestCharacterMethods:
    """Test character methods exist and have correct signatures."""

    def test_check_active_method(self):
        """Test default active-state behavior."""
        char = TestGameState.create_player(name="Test", class_name="Warrior", race_name="Human")
        active, message = char.check_active()
        assert active is True
        assert message == ""

    @pytest.mark.parametrize("physical_resistance", [-0.4, 0.0, 0.75])
    def test_ultimate_physical_damage_ignores_player_resistance(self, physical_resistance):
        """Ultimate Physical hits are neutral at the resistance layer."""
        char = TestGameState.create_player(name="Test", class_name="Warrior", race_name="Human")
        char.resistance["Physical"] = physical_resistance

        assert char.check_mod("resist", typ="Physical") == pytest.approx(physical_resistance)
        assert char.check_mod("resist", typ="Physical", ultimate=True) == 0.0

    def test_incapacitated_method(self):
        """Test incapacitated method."""
        char = TestGameState.create_player(name="Test", class_name="Warrior", race_name="Human")
        assert hasattr(char, "incapacitated")
        result = char.incapacitated()
        assert isinstance(result, bool)

    def test_weapon_damage_signature(self):
        """Verify weapon_damage has the expected signature."""
        char = TestGameState.create_player(name="Attacker", class_name="Warrior", race_name="Human")
        target = Goblin()

        # Should accept target as first positional argument
        # Should return tuple of (str, bool, int)
        result = char.weapon_damage(target)
        assert isinstance(result, tuple)
        assert len(result) == 3
        result_str, hit, crit = result
        assert isinstance(result_str, str)
        assert isinstance(hit, bool)
        assert isinstance(crit, (int, float))

    def test_disarm_reduces_enemy_weapon_mod_total(self):
        """Disarm should reduce total weapon attack output, not only base weapon damage."""
        enemy = Goblin()
        enemy.status_effects["Berserk"].active = False
        enemy.magic_effects["Totem"].active = False
        enemy.stat_effects["Attack"].active = False

        enemy.physical_effects["Disarm"].active = False
        armed_mod = enemy.check_mod("weapon")

        enemy.physical_effects["Disarm"].active = True
        disarmed_mod = enemy.check_mod("weapon")

        expected_armed = enemy.combat.attack + enemy.equipment["Weapon"].damage
        expected_disarmed = int(enemy.combat.attack * 0.5)

        assert armed_mod == expected_armed
        assert disarmed_mod == expected_disarmed
        assert disarmed_mod < armed_mod

    def test_disarm_reduces_player_weapon_mod_total(self):
        """Player check_mod override should apply the same disarm weapon penalty."""
        player = TestGameState.create_player(name="Test", class_name="Warrior", race_name="Human")
        player.status_effects["Berserk"].active = False
        player.stat_effects["Attack"].active = False

        player.physical_effects["Disarm"].active = False
        armed_mod = player.check_mod("weapon")

        player.physical_effects["Disarm"].active = True
        disarmed_mod = player.check_mod("weapon")

        expected_armed = player.combat.attack + player.equipment["Weapon"].damage
        expected_disarmed = int(player.combat.attack * 0.5)

        assert armed_mod == expected_armed
        assert disarmed_mod == expected_disarmed
        assert disarmed_mod < armed_mod

    def test_fist_weapon_not_penalized_by_disarm(self):
        """Fist weapons are not disarmable and should not lose attack from disarm state."""
        player = TestGameState.create_player(name="Test", class_name="Warrior", race_name="Human")
        player.equipment["Weapon"] = items.BrassKnuckles()
        player.status_effects["Berserk"].active = False
        player.stat_effects["Attack"].active = False

        assert player.can_be_disarmed() is False

        player.physical_effects["Disarm"].active = False
        armed_mod = player.check_mod("weapon")

        player.physical_effects["Disarm"].active = True
        disarmed_mod = player.check_mod("weapon")

        assert disarmed_mod == armed_mod

    def test_magic_pendant_increases_spell_dodge(self, monkeypatch):
        attacker = TestGameState.create_player(name="Mage", class_name="Wizard", race_name="Human")
        defender = TestGameState.create_player(
            name="Target", class_name="Warrior", race_name="Human"
        )

        defender.equipment["Pendant"] = items.NoPendant()
        monkeypatch.setattr("src.core.character.random.randint", lambda lo, hi: (lo + hi) // 2)
        base_spell_dodge = defender.dodge_chance(attacker, spell=True)

        defender.equipment["Pendant"] = items.MagicPendant()
        pendant_spell_dodge = defender.dodge_chance(attacker, spell=True)

        assert pendant_spell_dodge > base_spell_dodge


class TestCombatAPIContract:
    """Test the API contract between combat systems and character."""

    def test_enemy_has_combat_attributes(self):
        """Verify enemies have all required combat attributes."""
        from src.core.enemies import Goblin

        enemy = Goblin()
        assert hasattr(enemy, "name")
        assert hasattr(enemy, "health")
        assert hasattr(enemy, "magic_effects")
        assert hasattr(enemy, "status_effects")
        assert hasattr(enemy, "tunnel")
        assert hasattr(enemy, "is_alive")
        assert hasattr(enemy, "weapon_damage")
        assert hasattr(enemy, "dodge_chance")

    def test_player_has_combat_attributes(self):
        """Verify player has all required combat attributes."""
        # Use TestGameState to properly create a player
        player = TestGameState.create_player(
            name="TestPlayer", class_name="Warrior", race_name="Human"
        )

        # Basic attributes
        assert hasattr(player, "name")
        assert hasattr(player, "health")
        assert hasattr(player, "cls")

        # Combat methods
        assert hasattr(player, "weapon_damage")
        assert hasattr(player, "is_alive")


class TestEnhancedCombatRequirements:
    """Test requirements for enhanced combat system."""

    def test_character_needs_check_active(self):
        """check_active should report incapacitated actors correctly."""
        char = TestGameState.create_player(name="Test", class_name="Warrior", race_name="Human")
        char.status_effects["Stun"].active = True

        active, msg = char.check_active()

        assert active is False
        assert "stunned" in msg.lower()

    def test_check_active_reports_ice_block(self):
        char = TestGameState.create_player(name="Frozen", class_name="Warrior", race_name="Human")
        char.magic_effects["Ice Block"].active = True

        active, msg = char.check_active()

        assert active is False
        assert "encased in ice" in msg.lower()

    def test_character_has_speed_stat(self):
        """Verify characters have speed/dex stat for turn order."""
        char = TestGameState.create_player(name="Test", class_name="Warrior", race_name="Human")

        # Check for speed or dexterity stat
        assert hasattr(char, "stats")
        assert hasattr(char.stats, "dex") or hasattr(char.stats, "speed")


class TestStatusEffectImprovements:
    def test_poison_reduces_healing_received(self, monkeypatch):
        import src.core.data.data_driven_abilities as dda
        from src.core.abilities import Heal
        from src.core.character import POISON_HEALING_MULTIPLIER

        monkeypatch.setattr(dda.random, "randint", lambda _a, _b: 1)  # avoid crit heals

        normal = TestGameState.create_player(
            name="Normal",
            class_name="Warrior",
            race_name="Human",
            level=10,
            health=(200, 50),
            mana=(200, 200),
        )
        poisoned = TestGameState.create_player(
            name="Poisoned",
            class_name="Warrior",
            race_name="Human",
            level=10,
            health=(200, 50),
            mana=(200, 200),
        )
        poisoned.status_effects["Poison"].active = True
        poisoned.status_effects["Poison"].duration = 2

        heal_spell = Heal()

        before = normal.health.current
        heal_spell.cast_out(normal)
        normal_healed = normal.health.current - before

        before = poisoned.health.current
        heal_spell.cast_out(poisoned)
        poisoned_healed = poisoned.health.current - before

        assert poisoned_healed <= int(normal_healed * POISON_HEALING_MULTIPLIER) + 1

    def test_bleed_increases_melee_damage_taken(self, monkeypatch):
        import src.core.character as character_mod

        attacker = TestGameState.create_player(
            name="Attacker", class_name="Warrior", race_name="Human"
        )
        defender = TestGameState.create_player(
            name="Defender", class_name="Warrior", race_name="Human"
        )

        monkeypatch.setattr(
            character_mod.random, "uniform", lambda _a, _b: 1.0
        )  # deterministic variance
        monkeypatch.setattr(
            character_mod.random, "random", lambda: 1.0
        )  # avoid block/dodge randomness
        monkeypatch.setattr(attacker, "critical_chance", lambda _att: 0.0)  # no crits

        defender.health.current = defender.health.max
        defender.physical_effects["Bleed"].active = False
        _msg, _hit, _crit = attacker.weapon_damage(defender, hit=True, use_offhand=False)
        base_damage = defender.health.max - defender.health.current

        defender.health.current = defender.health.max
        defender.physical_effects["Bleed"].active = True
        defender.physical_effects["Bleed"].duration = 2
        defender.physical_effects["Bleed"].extra = 5
        _msg, _hit, _crit = attacker.weapon_damage(defender, hit=True, use_offhand=False)
        bleed_damage = defender.health.max - defender.health.current

        assert bleed_damage > base_damage

    def test_dilong_earth_maw_damages_electric_bat(self, monkeypatch):
        import src.core.character as character_mod

        dilong = companions.Dilong()
        bat = enemies.ElectricBat()
        bat.health.max = 999
        bat.health.current = 999

        monkeypatch.setattr(character_mod.random, "uniform", lambda _a, _b: 1.0)
        monkeypatch.setattr(dilong, "critical_chance", lambda _att: 0.0)

        assert bat.flying is True
        assert bat.check_mod("resist", enemy=dilong, typ="Earth") == 0

        message, hit, _crit = dilong.weapon_damage(bat, hit=True, use_offhand=False)

        assert hit is True
        assert bat.health.current < 999
        assert "bites Electric Bat" in message

    def test_equip_diff_pendant_preview_does_not_leak_vision_buff(self):
        player = TestGameState.create_player(
            name="PendantHero", class_name="Warrior", race_name="Human"
        )
        player.equipment["Pendant"] = items.VisionPendant()
        player.sight = True

        diff = player.equip_diff(items.AntidotePendant(), "Pendant")

        assert "Buffs" in diff
        assert "Status-Poison, Vision" not in diff
        assert "Status-Poison" in diff
        assert player.equipment["Pendant"].name == "Pendant of Vision"
        assert player.sight is True

    def test_magic_pendant_reports_magic_dodge_buff(self):
        player = TestGameState.create_player(
            name="PendantHero", class_name="Warrior", race_name="Human"
        )
        player.equipment["Pendant"] = items.MagicPendant()

        assert "Magic Dodge" in player.buff_str()

    def test_active_resist_effects_are_reported_as_buffs(self):
        player = TestGameState.create_player(
            name="WardHero", class_name="Warrior", race_name="Human"
        )
        player.magic_effects["Resist Fire"].active = True
        player.magic_effects["Resist Holy"].active = True

        buffs = player.buff_str()

        assert "Resist Fire" in buffs
        assert "Resist Holy" in buffs


class TestGameplayStatistics:
    def test_player_initializes_gameplay_stats_defaults(self):
        player = TestGameState.create_player(
            name="StatsHero",
            class_name="Warrior",
            race_name="Human",
            level=12,
        )

        assert player.gameplay_stats["steps_taken"] == 0
        assert player.gameplay_stats["stairs_used"] == 0
        assert player.gameplay_stats["enemies_defeated"] == 0
        assert player.gameplay_stats["deaths"] == 0
        assert player.gameplay_stats["flees"] == 0
        assert player.gameplay_stats["highest_level_reached"] == 12
        assert player.gameplay_stats["highest_damage_dealt"] == 0
        assert player.gameplay_stats["highest_damage_taken"] == 0

    def test_promoted_player_initializes_highest_level_with_global_level(self):
        player = TestGameState.create_player(
            name="PromotedStatsHero",
            class_name="Warrior",
            race_name="Human",
            level=15,
            pro_level=2,
        )

        assert player.player_level() == 15
        assert player.gameplay_stats["highest_level_reached"] == 15

    def test_player_move_and_stairs_update_gameplay_stats(self):
        player = TestGameState.create_player(
            name="Walker",
            class_name="Warrior",
            race_name="Human",
            level=8,
        )
        player.world_dict[(6, 10, 0)] = type("Tile", (), {"enter": True})()

        player.move(1, 0)
        player.stairs_down()

        assert player.gameplay_stats["steps_taken"] == 1
        assert player.gameplay_stats["stairs_used"] == 1

    def test_player_data_serializer_round_trips_gameplay_stats(self):
        player = TestGameState.create_player(
            name="Saver",
            class_name="Warrior",
            race_name="Human",
            level=15,
        )
        player.gameplay_stats.update(
            {
                "steps_taken": 42,
                "stairs_used": 7,
                "enemies_defeated": 11,
                "deaths": 2,
                "flees": 3,
                "highest_level_reached": 16,
                "highest_damage_dealt": 88,
                "highest_damage_taken": 34,
            }
        )
        player.inventory_sort_mode = "Combat"

        serialized = PlayerDataSerializer.serialize(player)
        restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

        assert restored.gameplay_stats == player.gameplay_stats
        assert restored.inventory_sort_mode == "Combat"

    def test_player_data_serializer_backfills_missing_gameplay_stats(self):
        player = TestGameState.create_player(
            name="Legacy",
            class_name="Warrior",
            race_name="Human",
            level=9,
            pro_level=2,
        )

        serialized = PlayerDataSerializer.serialize(player)
        serialized.pop("gameplay_stats", None)

        restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

        assert restored.gameplay_stats["highest_level_reached"] == 9
        assert restored.gameplay_stats["steps_taken"] == 0

    def test_player_data_serializer_round_trips_bounty_board_state(self):
        player = TestGameState.create_player(
            name="BountySaver",
            class_name="Warrior",
            race_name="Human",
            level=11,
        )
        player.bounty_board_state = {
            "initialized": True,
            "last_restock_level": 11,
            "last_restock_steps": 210,
            "last_restock_enemies_defeated": 9,
        }

        serialized = PlayerDataSerializer.serialize(player)
        restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

        assert serialized["bounty_board_state"] == player.bounty_board_state
        assert restored.bounty_board_state == player.bounty_board_state

    def test_player_data_serializer_backfills_missing_bounty_board_state(self):
        from src.core import town

        player = TestGameState.create_player(
            name="LegacyBounty",
            class_name="Warrior",
            race_name="Human",
            level=5,
        )

        serialized = PlayerDataSerializer.serialize(player)
        serialized.pop("bounty_board_state", None)
        legacy_restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

        assert legacy_restored.bounty_board_state == town.default_bounty_board_state()

        serialized["bounty_board_state"] = {
            "initialized": True,
            "last_restock_level": "bad",
            "last_restock_steps": -3,
            "last_restock_enemies_defeated": "7",
        }
        malformed_restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

        assert malformed_restored.bounty_board_state == {
            "initialized": True,
            "last_restock_level": 0,
            "last_restock_steps": 0,
            "last_restock_enemies_defeated": 7,
        }

    def test_player_data_serializer_persists_portrait_choice_and_backfills_legacy_saves(self):
        player = TestGameState.create_player(
            name="PortraitHero",
            class_name="Warrior",
            race_name="Human",
            level=5,
        )
        player.sex = "Female"
        player.portrait_variant = 3

        serialized = PlayerDataSerializer.serialize(player)
        restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

        assert serialized["sex"] == "Female"
        assert serialized["portrait_variant"] == 3
        assert restored.sex == "Female"
        assert restored.portrait_variant == 3

        serialized.pop("sex", None)
        serialized.pop("portrait_variant", None)
        legacy_restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

        assert legacy_restored.sex == "Male"
        assert legacy_restored.portrait_variant == 0

        serialized["portrait_variant"] = "bad"
        malformed_restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

        assert malformed_restored.portrait_variant == 0

    def test_damage_event_updates_high_water_marks(self):
        from src.core.events.event_bus import EventType, get_event_bus, reset_event_bus

        attacker = TestGameState.create_player(
            name="Attacker",
            class_name="Warrior",
            race_name="Human",
            level=9,
        )
        defender = TestGameState.create_player(
            name="Defender",
            class_name="Warrior",
            race_name="Human",
            level=9,
        )
        reset_event_bus()
        captured = []
        get_event_bus().subscribe(EventType.DAMAGE_DEALT, lambda event: captured.append(event))

        attacker._emit_damage_event(defender, 37, damage_type="Physical", is_critical=False)

        assert attacker.gameplay_stats["highest_damage_dealt"] == 37
        assert defender.gameplay_stats["highest_damage_taken"] == 37
        assert captured[-1].data["source"] == "Unknown"
        assert captured[-1].data["crit"] is False

    def test_weapon_damage_events_include_audio_routing_metadata(self, monkeypatch):
        import src.core.character as character_mod
        from src.core import items
        from src.core.events.event_bus import EventType, get_event_bus, reset_event_bus

        attacker = TestGameState.create_player(
            name="LaserBot",
            class_name="Warrior",
            race_name="Human",
            level=9,
        )
        defender = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=9,
        )
        attacker.equipment["Weapon"] = items.Laser()
        defender.equipment["OffHand"] = items.NoOffHand()
        monkeypatch.setattr(character_mod.random, "uniform", lambda _a, _b: 1.0)
        monkeypatch.setattr(character_mod.random, "random", lambda: 1.0)
        monkeypatch.setattr(attacker, "critical_chance", lambda _att: 0.0)
        reset_event_bus()
        captured = []
        get_event_bus().subscribe(EventType.DAMAGE_DEALT, lambda event: captured.append(event))

        attacker.weapon_damage(defender, hit=True, use_offhand=False)

        payload = captured[-1].data
        assert payload["source"] == "weapon_damage"
        assert payload["attack_source"] == "natural_weapon"
        assert payload["weapon_name"] == "Laser"
        assert payload["weapon_slot"] == "Weapon"
        assert payload["weapon_type"] == "Natural"


class TestPlayerUtilityBehaviors:
    def test_record_helpers_ignore_negative_inputs_and_refresh_highest_level(self):
        player = TestGameState.create_player(
            name="Recorder",
            class_name="Warrior",
            race_name="Human",
            level=12,
        )

        player.record_step(-5)
        player.record_stairs_used(-1)
        player.record_enemy_defeat(-2)
        player.record_flee(-3)
        player.record_death(-4)
        player.record_damage_dealt(None)
        player.record_damage_taken(None)

        assert player.gameplay_stats["steps_taken"] == 0
        assert player.gameplay_stats["stairs_used"] == 0
        assert player.gameplay_stats["enemies_defeated"] == 0
        assert player.gameplay_stats["flees"] == 0
        assert player.gameplay_stats["deaths"] == 0

        player.record_damage_dealt(55)
        player.record_damage_taken(22)
        player.level.level = 18
        player.level.pro_level = 2
        player.refresh_highest_level()

        assert player.gameplay_stats["highest_damage_dealt"] == 55
        assert player.gameplay_stats["highest_damage_taken"] == 22
        assert player.gameplay_stats["highest_level_reached"] == 18

    def test_exp_gain_multiplier_matches_race(self):
        from src.core.constants import HALF_GIANT_EXP_MULTIPLIER, HUMAN_EXP_MULTIPLIER

        human = TestGameState.create_player(class_name="Warrior", race_name="Human")
        half_giant = TestGameState.create_player(class_name="Warrior", race_name="Half Giant")
        other = TestGameState.create_player(class_name="Warrior", race_name="Elf")

        assert human.exp_gain_multiplier() == HUMAN_EXP_MULTIPLIER
        assert half_giant.exp_gain_multiplier() == HALF_GIANT_EXP_MULTIPLIER
        assert other.exp_gain_multiplier() == 1.0

    def test_player_level_and_max_level_use_flat_global_level(self):
        base = TestGameState.create_player(level=20, pro_level=1)
        promoted = TestGameState.create_player(level=15, pro_level=2)
        final = TestGameState.create_player(level=7, pro_level=3)

        assert base.player_level() == 20
        assert promoted.player_level() == 15
        assert final.player_level() == 7

        assert TestGameState.create_player(level=100, pro_level=1).max_level() is True
        assert TestGameState.create_player(level=100, pro_level=2).max_level() is True
        assert TestGameState.create_player(level=50, pro_level=3).max_level() is False
        assert TestGameState.create_player(level=99, pro_level=1).max_level() is False

    def test_town_and_realm_location_helpers(self):
        from src.core.player import REALM_OF_CAMBION_LEVEL, TOWN_LOCATION

        player = TestGameState.create_player(
            name="Traveler",
            class_name="Warrior",
            race_name="Human",
            level=12,
        )
        player.change_location(1, 2, 3)
        assert player.in_town() is False

        player.to_town()
        assert (player.location_x, player.location_y, player.location_z) == TOWN_LOCATION
        assert player.in_town() is True

        player.change_location(7, 8, 1)
        player.facing = "north"
        player.enter_realm_of_cambion(4, 5, REALM_OF_CAMBION_LEVEL, facing="south")
        assert player.in_realm_of_cambion() is True
        assert player.anti_magic_active is True
        assert player.cambion_return == (7, 8, 1, "north")

        player.exit_realm_of_cambion()
        assert (player.location_x, player.location_y, player.location_z) == (7, 8, 1)
        assert player.facing == "north"
        assert player.anti_magic_active is False

    def test_exit_funhouse_restores_saved_location_or_falls_back_to_town(self):
        from src.core.player import TOWN_LOCATION

        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        player.funhouse_return = (9, 8, 7, "west")

        player.exit_funhouse()
        assert (player.location_x, player.location_y, player.location_z) == (9, 8, 7)
        assert player.facing == "west"
        assert player.funhouse_return is None

        player.change_location(1, 1, 1)
        player.exit_funhouse()
        assert (player.location_x, player.location_y, player.location_z) == TOWN_LOCATION

    def test_town_heal_restores_player_and_summons(self):
        from src.core.companions import Patagon

        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        summon = Patagon()
        summon.health.max = 40
        summon.health.current = 5
        summon.mana.max = 20
        summon.mana.current = 3
        player.summons["Patagon"] = summon
        player.state = "fight"
        player.health.current = 7
        player.mana.current = 2

        player.town_heal()

        assert player.state == "normal"
        assert player.health.current == player.health.max
        assert player.mana.current == player.mana.max
        assert summon.health.current == summon.health.max
        assert summon.mana.current == summon.mana.max

    def test_usable_item_respects_town_rules(self):
        from types import SimpleNamespace

        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        stat_item = SimpleNamespace(subtyp="Stat", name="Stat Tonic")

        player.to_town()
        assert player.usable_item(stat_item) is True
        assert player.usable_item(items.HealthPotion()) is False

        player.change_location(1, 1, 1)
        assert player.usable_item(items.HealthPotion()) is True
        assert player.usable_item(items.ManaPotion()) is True
        assert player.usable_item(items.SanctuaryScroll()) is True

    def test_usable_abilities_handles_suppression_equipment_checks_and_wizard_power_up(self):
        player = TestGameState.create_player(class_name="Wizard", race_name="Human")
        player.abilities_suppressed = lambda: False

        player.spellbook["Spells"].clear()
        player.spellbook["Spells"]["Heal"] = abilities.Heal()
        player.mana.current = 0
        player.power_up = True

        assert player.usable_abilities("Spells") is True
        assert player.class_effects["Power Up"].active is True
        assert player.class_effects["Power Up"].duration == 4

        player.cls.name = "Warrior"
        player.power_up = False
        player.abilities_suppressed = lambda: True
        assert player.usable_abilities("Spells") is False

        player.abilities_suppressed = lambda: False
        player.spellbook["Skills"].clear()
        player.spellbook["Skills"]["Shield Slam"] = abilities.ShieldSlam()
        player.equipment["OffHand"] = items.NoOffHand()
        player.mana.current = 999
        assert player.usable_abilities("Skills") is False

    def test_weight_helpers_and_additional_actions(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human", pro_level=2)
        player.equipment["Weapon"] = items.Falchion()
        player.equipment["Armor"] = items.PlateMail()
        player.inventory = {"Antidote": [items.Antidote(), items.Antidote()]}
        player.special_inventory = {"Old Key": [items.OldKey()]}

        assert player.max_weight() == player.stats.strength * 20
        assert player.current_weight() > 0

        player.physical_effects["Disarm"].active = True
        player.cls.name = "Thaumaturgist"
        alive_summon = TestGameState.create_player(
            name="Summon", class_name="Warrior", race_name="Human"
        )
        player.summons["Summon"] = alive_summon
        player.abilities_suppressed = lambda: False
        actions = player.additional_actions(["Attack", "Use Item", "Flee"])

        assert "Pickup Weapon" in actions
        assert "Summon" in actions

        actions = player.additional_actions(["Attack", "Pickup Weapon", "Use Item", "Flee"])
        assert actions.count("Pickup Weapon") == 1

    def test_move_blocked_tile_does_not_advance_and_turn_helpers_rotate(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        player.world_dict[(6, 10, 0)] = type("Tile", (), {"enter": False})()
        player.facing = "north"
        player.dwarf_hangover_steps = 2

        player.move(1, 0)
        assert (player.location_x, player.location_y) == (5, 10)
        assert player.gameplay_stats["steps_taken"] == 0
        assert player.dwarf_hangover_steps == 2

        player.turn_right()
        assert player.facing == "east"
        player.turn_left()
        assert player.facing == "north"
        player.turn_around()
        assert player.facing == "south"

    def test_death_moves_player_to_town_and_can_apply_penalty(self, monkeypatch):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human", level=15)
        player.gold = 1000
        player.location_z = 2
        player.stats.charisma = 0

        rolls = iter([750, 0, 0])  # cost, complication trigger, strength penalty
        monkeypatch.setattr("src.core.player.random.randint", lambda _a, _b: next(rolls))
        monkeypatch.setattr(player, "effects", lambda end=False: "")

        player.death()

        assert player.gold == 250
        assert player.stats.strength == 19
        assert player.in_town() is True
        assert player.gameplay_stats["deaths"] == 1

    def test_familiar_turn_support_familiar_can_restore_mana(self, monkeypatch):
        from src.core.companions import Fairy

        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        enemy = TestGameState.create_player(name="Enemy", class_name="Warrior", race_name="Human")
        familiar = Fairy()
        familiar.name = "Pixie"
        player.familiar = familiar
        player.mana.max = 200
        player.mana.current = 150

        rolls = iter([0, 0])
        monkeypatch.setattr("src.core.player.random.randint", lambda _a, _b: next(rolls))

        result = player.familiar_turn(enemy)

        assert "Pixie restores" in result
        assert player.mana.current == 160

    def test_familiar_turn_arcane_boost_targets_player(self, monkeypatch):
        from src.core.companions import Mephit

        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        enemy = TestGameState.create_player(name="Enemy", class_name="Warrior", race_name="Human")
        familiar = Mephit()
        familiar.name = "Spark"
        familiar.spellbook["Spells"] = {
            "Boost": SimpleNamespace(
                name="Boost",
                typ="Spell",
                cast=lambda user, target=None, fam=False: f"Boosted {target.name}.\n",
            )
        }
        player.familiar = familiar
        player.stat_effects["Magic"].active = False

        rolls = iter([0, 0])
        monkeypatch.setattr("src.core.player.random.randint", lambda _a, _b: next(rolls))
        monkeypatch.setattr("src.core.player.random.choice", lambda seq: "Boost")

        result = player.familiar_turn(enemy)

        assert "Spark casts Boost" in result
        assert "Boosted TestPlayer" in result

    def test_familiar_turn_luck_familiar_skips_lockpick(self, monkeypatch):
        from src.core.companions import Jinkin

        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        enemy = TestGameState.create_player(name="Enemy", class_name="Warrior", race_name="Human")
        familiar = Jinkin()
        familiar.name = "Gremlin"
        familiar.spellbook["Skills"] = {
            "Lockpick": SimpleNamespace(
                name="Lockpick", typ="Skill", use=lambda *_args, **_kwargs: "noop"
            ),
            "Steal": SimpleNamespace(
                name="Steal", typ="Skill", use=lambda *_args, **_kwargs: "Stolen!\n"
            ),
        }
        player.familiar = familiar

        rolls = iter([0, 1])  # trigger familiar, choose skills branch
        choices = iter(["Lockpick", "Steal"])
        monkeypatch.setattr("src.core.player.random.randint", lambda _a, _b: next(rolls))
        monkeypatch.setattr("src.core.player.random.choice", lambda seq: next(choices))

        result = player.familiar_turn(enemy)

        assert "Gremlin uses Steal" in result
        assert "Stolen!" in result

    def test_transform_forward_and_back_restore_state(self, monkeypatch):
        player = TestGameState.create_player(class_name="Lycan", race_name="Human")
        player.progression.purchased_node_ids.add("lycan.ability.transform3")
        original_cls = player.cls
        original_health_max = player.health.max
        original_mana_max = player.mana.max
        original_strength = player.stats.strength
        forward = player.transform()

        assert "transforms into a Werewolf" in forward
        assert player.cls.name == "Werewolf"
        assert player.transform_type == original_cls
        assert player.health.max > original_health_max
        assert player.mana.max >= original_mana_max
        assert player.stats.strength > original_strength
        assert player._transformed is True

        backward = player.transform(back=True)

        assert "transforms back into their normal self" in backward
        assert player.cls == original_cls
        assert player.health.max == original_health_max
        assert player.mana.max == original_mana_max
        assert player._transformed is False

    def test_transform_back_returns_empty_when_no_saved_form(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")

        assert player.transform(back=True) == ""

    def test_class_upgrades_soulcatcher_stat_and_gold_rewards(self, monkeypatch):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        player.cls.name = "Soulcatcher"
        player.location_z = 2
        player.gold = 100
        player.check_mod = lambda *args, **kwargs: 99
        monkeypatch.setattr("src.core.player.random.randint", lambda _a, _b: 0)

        lich = SimpleNamespace(name="Lich")
        lich_msg = player.class_upgrades(game=None, enemy=lich)
        assert "absorb part of the Lich's soul" in lich_msg
        assert "Gain 1 intelligence" in lich_msg

        dragon = SimpleNamespace(name="Red Dragon")
        dragon_msg = player.class_upgrades(game=None, enemy=dragon)
        assert "doubling your current stash" in dragon_msg
        assert player.gold == 200

    def test_class_upgrades_lycan_unlocks_dragon_essence_on_red_dragon(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        player.cls.name = "Lycan"

        msg = player.class_upgrades(game=None, enemy=SimpleNamespace(name="Red Dragon"))

        assert "Dragon Essence" in msg
        assert player.promotion_kit_state["lycan_control"]["dragon_essence"] is True
        assert "Transform" not in player.spellbook["Skills"]


class TestSaveSystemQuestCompatibility:
    def test_collect_quest_legacy_name_is_rejected(self):
        quest_dict = {
            "Bounty": {},
            "Main": {},
            "Side": {
                "Rat Trap": {
                    "Type": "Collect",
                    "What": "RatTail",
                    "Total": 6,
                    "Completed": False,
                }
            },
        }

        with pytest.raises(SaveValidationError, match="unknown quest id"):
            QuestDataSerializer.deserialize_quest_dict(quest_dict)

    def test_collect_quest_serialized_item_round_trips(self):
        quest_dict = {
            "Bounty": {},
            "Main": {},
            "Side": {
                "Ticket to Ride": {
                    "Type": "Collect",
                    "What": items.TicketPiece(),
                    "Total": 3,
                    "Completed": False,
                }
            },
        }

        serialized = QuestDataSerializer.serialize_quest_dict(quest_dict)
        restored = QuestDataSerializer.deserialize_quest_dict(serialized)

        assert restored["Side"]["Ticket to Ride"]["What"].name == "Ticket Piece"


class TestSaveSystemRoundTrips:
    def test_player_data_serializer_round_trips_equipment_and_inventories(self):
        player = TestGameState.create_player(
            name="Packrat",
            class_name="Warrior",
            race_name="Human",
            level=12,
        )
        player.equipment["Weapon"] = items.Falchion()
        player.equipment["Helmet"] = items.IronHelm()
        player.equipment["Ring"] = items.PowerRing()
        player.inventory = {
            "Antidote": [items.Antidote(), items.Antidote()],
            "Old Key": [items.OldKey()],
        }
        player.special_inventory = {
            "Ticket Piece": [items.TicketPiece(), items.TicketPiece()],
        }
        player.storage = {
            "Remedy": [items.Remedy()],
        }

        serialized = PlayerDataSerializer.serialize(player)
        restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

        assert restored.equipment["Weapon"].name == "Falchion"
        assert restored.equipment["Helmet"].name == "Iron Helm"
        assert restored.equipment["Ring"].name == "Power Ring"
        assert len(restored.inventory["Antidote"]) == 2
        assert restored.inventory["Old Key"][0].name == "Old Key"
        assert len(restored.special_inventory["Ticket Piece"]) == 2
        assert restored.storage["Remedy"][0].name == "Remedy"

        serialized["equipment"].pop("Helmet")
        with pytest.raises(SaveValidationError, match="missing required slots: Helmet"):
            PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

    def test_quest_serializer_round_trips_rewards_and_bounty_enemy_state(self):
        quest_dict = {
            "Bounty": {
                "Goblin": [
                    {
                        "enemy": enemies.Goblin(),
                        "reward": items.Antidote,
                        "num": 2,
                    },
                    1,
                    False,
                ]
            },
            "Main": {},
            "Side": {
                "Where's the Beef?": {
                    "Type": "Collect",
                    "What": items.MysteryMeat(),
                    "Reward": [items.GreatHealthPotion, "Gold"],
                    "Completed": False,
                    "Total": 12,
                }
            },
            "Milestone Storage Rewards": {
                "Rookie Mistake": True,
            },
        }

        serialized = QuestDataSerializer.serialize_quest_dict(quest_dict)
        restored = QuestDataSerializer.deserialize_quest_dict(serialized)

        bounty = restored["Bounty"]["Goblin"][0]
        assert bounty["enemy"].name == "Goblin"
        assert bounty["reward"] == items.Antidote
        assert restored["Milestone Storage Rewards"]["Rookie Mistake"] is True

        side_quest = restored["Side"]["Where's the Beef?"]
        assert side_quest["What"].name == "Mystery Meat"
        assert side_quest["Reward"][0].name == "Great Health Potion"
        assert side_quest["Reward"][1] == "Gold"

    def test_tile_state_serializer_restores_mutable_tile_fields(self):
        class DummyTile:
            def __init__(self, enemy=None, defeated=False):
                self.visited = False
                self.near = False
                self.open = False
                self.read = False
                self.blocked = None
                self.warped = False
                self.active = True
                self.enemy = enemy
                self.defeated = defeated
                self.drink = False
                self.nimue = False
                self.nimue_met_before = False

        alive_enemy = enemies.Goblin()
        alive_enemy.health.current = 7
        world = {
            (1, 2, 3): DummyTile(enemy=alive_enemy, defeated=False),
            (4, 5, 6): DummyTile(enemy=enemies.Goblin, defeated=True),
        }
        world[(1, 2, 3)].visited = True
        world[(1, 2, 3)].near = True
        world[(1, 2, 3)].open = True
        world[(1, 2, 3)].read = True
        world[(1, 2, 3)].blocked = "north"
        world[(1, 2, 3)].warped = True
        world[(1, 2, 3)].active = False
        world[(1, 2, 3)].drink = True
        world[(1, 2, 3)].nimue = True
        world[(1, 2, 3)].nimue_met_before = True

        tile_states = TileStateSerializer.serialize_tile_state(world)

        fresh_world = {
            (1, 2, 3): DummyTile(enemy=None, defeated=False),
            (4, 5, 6): DummyTile(enemy=enemies.Goblin(), defeated=False),
        }
        TileStateSerializer.restore_tile_state(fresh_world, tile_states)

        restored = fresh_world[(1, 2, 3)]
        assert restored.visited is True
        assert restored.near is True
        assert restored.open is True
        assert restored.read is True
        assert restored.blocked == "north"
        assert restored.warped is True
        assert restored.active is False
        assert restored.drink is True
        assert restored.nimue is True
        assert restored.nimue_met_before is True
        assert restored.enemy.name == "Goblin"
        assert restored.enemy.health.current == 7

        defeated_tile = fresh_world[(4, 5, 6)]
        assert defeated_tile.defeated is True
        assert defeated_tile.enemy is None

    def test_player_data_serializer_round_trips_jump_modifications(self):
        player = TestGameState.create_player(
            name="Dragoon",
            class_name="Dragoon",
            race_name="Human",
            level=35,
        )
        jump = abilities.Jump()
        jump.unlocked_modifications["Quick Dive"] = True
        jump.unlocked_modifications["Retribution"] = True
        jump.modifications["Crit"] = False
        jump.modifications["Quick Dive"] = True
        jump.modifications["Retribution"] = True
        player.spellbook["Skills"]["Jump"] = jump

        serialized = PlayerDataSerializer.serialize(player)
        restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)
        restored_jump = restored.spellbook["Skills"]["Jump"]

        assert restored_jump.modifications["Crit"] is False
        assert restored_jump.modifications["Quick Dive"] is True
        assert restored_jump.modifications["Retribution"] is True
        assert restored_jump.unlocked_modifications["Quick Dive"] is True
        assert restored_jump.unlocked_modifications["Retribution"] is True

    def test_stun_has_post_expiry_immunity_window(self):
        attacker = TestGameState.create_player(
            name="Attacker", class_name="Warrior", race_name="Human"
        )
        target = TestGameState.create_player(name="Target", class_name="Warrior", race_name="Human")

        assert target.apply_stun(1, source="Test", applier=attacker) is True
        assert target.status_effects["Stun"].active is True

        # Tick effects: stun expires and grants a short immunity window.
        target.effects()
        assert target.status_effects["Stun"].active is False
        assert target.status_effects["Stun"].duration == 0
        assert target.status_effects["Stun"].extra > 0

        assert target.apply_stun(1, source="Test", applier=attacker) is False

        # Next turn start: immunity ticks down.
        target.effects()
        assert target.status_effects["Stun"].extra == 0
        assert target.apply_stun(1, source="Test", applier=attacker) is True

    def test_stun_contest_is_biased_by_level_difference(self):
        high = TestGameState.create_player(
            name="High", class_name="Warrior", race_name="Human", level=20
        )
        low = TestGameState.create_player(
            name="Low", class_name="Warrior", race_name="Human", level=1
        )
        target = TestGameState.create_player(
            name="Target", class_name="Warrior", race_name="Human", level=10
        )

        attacker_roll = 10
        defender_roll = 11

        assert target.stun_contest_success(high, attacker_roll, defender_roll) is True
        assert target.stun_contest_success(low, attacker_roll, defender_roll) is False


def run_tests():
    """Run all tests and report results."""
    print("=" * 70)
    print("CHARACTER AND COMBAT SYSTEM TESTS")
    print("=" * 70)
    print()

    # Run pytest with verbose output
    import pytest

    exit_code = pytest.main([__file__, "-v", "--tb=short", "--color=yes"])

    return exit_code


if __name__ == "__main__":
    sys.exit(run_tests())
