#!/usr/bin/env python3
"""Additional focused coverage for character helper behavior."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.core import abilities, items
from src.core.constants import (
    BASE_CRIT_PER_POINT,
    ELF_HEALING_RECEIVED_MULTIPLIER,
    HALF_ELF_HEALING_RECEIVED_MULTIPLIER,
    MAX_CRIT_CHANCE,
)
from tests.test_framework import TestGameState


def _fixed_randint(_low, high):
    return high


class TestCharacterHelpers:
    def test_abilities_suppressed_checks_silence_and_anti_magic(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")

        assert player.abilities_suppressed() is False

        player.status_effects["Silence"].active = True
        assert player.abilities_suppressed() is True

        player.status_effects["Silence"].active = False
        player.anti_magic_active = True
        assert player.abilities_suppressed() is True

    def test_defensive_stance_sets_status_and_caps_total_reduction(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")

        result = player.enter_defensive_stance(duration=2, reduction=0.65, source="Defend")
        assert "defensive stance" in result
        assert player.status_effects["Defend"].active is True
        assert player.status_effects["Defend"].duration == 2
        assert player.status_effects["Defend"].extra == 0.65
        assert player.get_defensive_reduction() == pytest.approx(0.65)

        player.jump_defend_active = True
        assert player.get_defensive_reduction() == pytest.approx(0.75)

    def test_healing_received_multiplier_accounts_for_race_and_poison(self):
        elf = TestGameState.create_player(class_name="Warrior", race_name="Elf")
        half_elf = TestGameState.create_player(class_name="Warrior", race_name="Half Elf")
        human = TestGameState.create_player(class_name="Warrior", race_name="Human")

        elf.status_effects["Poison"].active = True
        half_elf.status_effects["Poison"].active = True

        assert elf.healing_received_multiplier() == pytest.approx(
            0.70 * ELF_HEALING_RECEIVED_MULTIPLIER
        )
        assert half_elf.healing_received_multiplier() == pytest.approx(
            0.70 * HALF_ELF_HEALING_RECEIVED_MULTIPLIER
        )
        assert human.healing_received_multiplier() == pytest.approx(1.0)

    def test_bleed_tick_uses_bleeding_message(self, monkeypatch):
        player = TestGameState.create_player(name="Kain", class_name="Warrior", race_name="Human")
        player.physical_effects["Bleed"].active = True
        player.physical_effects["Bleed"].duration = 2
        player.physical_effects["Bleed"].extra = 8
        monkeypatch.setattr("src.core.character.random.randint", lambda *_args: 0)

        text = player.effects()

        assert "Kain bleeds for" in text
        assert "The magic damages" not in text

    def test_shop_helpers_apply_gnome_charisma_bonus(self):
        human = TestGameState.create_player(class_name="Warrior", race_name="Human")
        gnome = TestGameState.create_player(class_name="Warrior", race_name="Gnome")
        human.stats.charisma = 20
        gnome.stats.charisma = 20

        assert gnome.shop_price_scale() < human.shop_price_scale()
        assert gnome.shop_sell_price_multiplier() > human.shop_sell_price_multiplier()

    def test_effect_handler_and_disarm_helpers_cover_common_branches(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")

        assert player.effect_handler("Poison") is player.status_effects
        assert player.can_be_disarmed() is True

        player.physical_effects["Disarm"].active = True
        assert player.is_disarmed() is True

        player.status_immunity.append("Disarm")
        assert player.can_be_disarmed() is False
        assert player.is_disarmed() is False
        player.status_immunity.remove("Disarm")

        player.equipment["Weapon"] = items.Claw()
        assert player.can_be_disarmed() is False
        assert player.is_disarmed() is False

        with pytest.raises(NotImplementedError):
            player.effect_handler("Unknown Effect")

    def test_monk_cannot_be_disarmed_from_unarmed_training(self):
        monk = TestGameState.create_player(class_name="Monk", race_name="Human")
        monk.physical_effects["Disarm"].active = True

        assert monk.can_be_disarmed() is False
        assert monk.is_disarmed() is False

    def test_druid_can_choose_panther_and_later_direbear_forms(self):
        druid = TestGameState.create_player(class_name="Druid", race_name="Human")
        druid.level.pro_level = 1
        druid.progression.purchased_node_ids.add("druid.ability.transform")

        assert druid.available_transform_forms() == ("Panther",)
        assert druid.select_transform_form("Direbear") is False
        assert druid.select_transform_form("Panther") is True
        assert druid._selected_transform_form == "Panther"

        druid.level.pro_level = 15
        druid.progression.purchased_node_ids.add("druid.ability.transform2")
        assert druid.available_transform_forms() == ("Panther", "Direbear")
        assert druid.select_transform_form("Direbear") is True
        assert druid._selected_transform_form == "Direbear"

    def test_transformation_save_load_preserves_overlay_and_normal_deficits(self):
        from src.core.save_system.player import PlayerDataSerializer

        druid = TestGameState.create_player(class_name="Druid", race_name="Human")
        druid.progression.purchased_node_ids.add("druid.ability.transform")
        normal_health_max = druid.health.max
        normal_mana_max = druid.mana.max
        assert druid.select_transform_form("Panther")
        druid.transform()
        overlay = druid.transformation_state["overlay"]
        druid.health.current -= 7
        druid.mana.current -= 3

        saved = PlayerDataSerializer.serialize(druid)
        restored = PlayerDataSerializer.deserialize(saved, skip_tiles=True)

        assert saved["class_id"] == "druid"
        assert saved["health"]["max"] == normal_health_max
        assert saved["mana"]["max"] == normal_mana_max
        assert restored.cls.name == "Panther"
        assert restored.transformation_state["active_form"] == "Panther"
        assert restored.transformation_state["overlay"]["stats"] == overlay["stats"]
        assert restored.health.max - restored.health.current == 7
        assert restored.mana.max - restored.mana.current == 3
        restored.transform(back=True)
        assert restored.cls.name == "Druid"
        assert restored.health.max == normal_health_max
        assert restored.health.max - restored.health.current == 7

    def test_shifted_character_blocks_equipment_and_promotion_but_mirrors_skills(self):
        from src.core.progression import purchase_node

        lycan = TestGameState.create_player(
            class_name="Lycan",
            race_name="Human",
            level=100,
        )
        lycan.progression.unspent_points = 10
        lycan.progression.purchased_node_ids.update(
            {
                "lycan.ability.transform3",
                "lycan.ability.charge",
                "lycan.ability.battlecry",
            }
        )
        lycan.spellbook["Skills"]["Battle Cry"] = abilities.BattleCry()
        lycan.transform()

        assert lycan.equip("Weapon", items.IronshodStaff()) is False
        learned = purchase_node(lycan, "lycan.ability.wingedpounce")

        assert learned.success is True
        assert "Winged Pounce" in lycan.spellbook["Skills"]
        assert "Winged Pounce" in lycan._normal_form_snapshot["spellbook"]["Skills"]

        druid = TestGameState.create_player(
            class_name="Druid",
            race_name="Human",
            level=100,
        )
        druid.progression.purchased_node_ids.update(
            {
                "druid.ability.transform",
                "druid.talent.druid-grove-shelter.rank-2",
            }
        )
        druid.progression.unspent_points = 10
        druid.transform()
        promoted = purchase_node(
            druid,
            "druid.promotion.lycan",
            confirm_promotion=True,
        )

        assert promoted.success is False
        assert "permanent form" in promoted.message

    def test_hit_chance_reacts_to_accuracy_penalties_and_bonuses(self, monkeypatch):
        attacker = TestGameState.create_player(class_name="Warrior", race_name="Human")
        defender = TestGameState.create_player(class_name="Warrior", race_name="Human")
        monkeypatch.setattr("src.core.character.random.randint", _fixed_randint)

        base = attacker.hit_chance(defender)

        attacker.equipment["Ring"] = items.AccuracyRing()
        with_accuracy = attacker.hit_chance(defender)

        attacker.status_effects["Blind"].active = True
        defender.flying = True
        defender.invisible = True
        attacker.encumbered = True
        penalized = attacker.hit_chance(defender)

        assert with_accuracy > base
        assert penalized < with_accuracy

    def test_dodge_chance_covers_quickstep_magic_pendant_and_penalties(self, monkeypatch):
        attacker = TestGameState.create_player(class_name="Warrior", race_name="Human")
        defender = TestGameState.create_player(class_name="Warrior", race_name="Human")
        monkeypatch.setattr("src.core.character.random.randint", _fixed_randint)

        base_weapon_dodge = defender.dodge_chance(attacker, spell=False)
        base_spell_dodge = defender.dodge_chance(attacker, spell=True)

        defender.spellbook["Skills"]["Quickstep"] = SimpleNamespace(name="Quickstep")
        defender.equipment["Pendant"] = items.MagicPendant()
        boosted_weapon_dodge = defender.dodge_chance(attacker, spell=False)
        boosted_spell_dodge = defender.dodge_chance(attacker, spell=True)

        defender.status_effects["Hangover"].active = True
        defender.encumbered = True
        penalized_weapon_dodge = defender.dodge_chance(attacker, spell=False)

        assert boosted_weapon_dodge > base_weapon_dodge
        assert boosted_spell_dodge > base_spell_dodge
        assert penalized_weapon_dodge < boosted_weapon_dodge

    def test_critical_chance_includes_class_weapon_and_maelstrom_bonus(self):
        seeker = TestGameState.create_player(class_name="Seeker", race_name="Human")
        seeker.power_up = True
        base = seeker.critical_chance("Weapon")

        seeker.spellbook["Skills"]["Maelstrom Weapon"] = SimpleNamespace(name="Maelstrom Weapon")
        seeker.maelstrom_hits = 3
        boosted = seeker.critical_chance("Weapon")

        assert boosted > base

        seeker.stats.dex = 999
        seeker.stats.charisma = 999
        seeker.stats.wisdom = 999
        assert seeker.critical_chance("Weapon") == MAX_CRIT_CHANCE

    def test_third_eye_adds_intelligence_to_critical_and_both_dodge_calculations(
        self,
        monkeypatch,
    ):
        knight = TestGameState.create_player(
            class_name="Knight Enchanter",
            race_name="Human",
        )
        attacker = TestGameState.create_player(class_name="Warrior", race_name="Human")
        knight.stats.intel = 20
        attacker.stats.dex = 1
        attacker.stats.intel = 1
        monkeypatch.setattr("src.core.character.random.randint", _fixed_randint)

        base_crit = knight.critical_chance("Weapon")
        base_weapon_dodge = knight.dodge_chance(attacker, spell=False)
        base_spell_dodge = knight.dodge_chance(attacker, spell=True)
        knight.spellbook["Skills"]["Third Eye"] = abilities.ThirdEye()

        assert knight.critical_chance("Weapon") == pytest.approx(
            base_crit + 20 * BASE_CRIT_PER_POINT
        )
        assert knight.dodge_chance(attacker, spell=False) > base_weapon_dodge
        assert knight.dodge_chance(attacker, spell=True) > base_spell_dodge

    def test_handle_duplicates_consumes_last_duplicate(self, monkeypatch):
        attacker = TestGameState.create_player(class_name="Warrior", race_name="Human")
        defender = TestGameState.create_player(class_name="Warrior", race_name="Human")
        defender.magic_effects["Duplicates"].active = True
        defender.magic_effects["Duplicates"].duration = 1

        monkeypatch.setattr("src.core.character.random.randint", lambda _a, _b: 1)
        attacker.check_mod = lambda *_args, **_kwargs: 0

        still_hits, message = attacker._handle_duplicates(defender, "attacks")

        assert still_hits is False
        assert "mirror image" in message
        assert defender.magic_effects["Duplicates"].active is False
        assert defender.magic_effects["Duplicates"].duration == 0

    def test_mirror_images_remain_hittable_after_first_duplicate(self, monkeypatch):
        attacker = TestGameState.create_player(class_name="Warrior", race_name="Human")
        defender = TestGameState.create_player(class_name="Warrior", race_name="Human")
        defender.magic_effects["Duplicates"].active = True
        defender.magic_effects["Duplicates"].duration = 4

        monkeypatch.setattr("src.core.character.random.randint", lambda _a, _b: 1)
        attacker.check_mod = lambda *_args, **_kwargs: 99

        first_hit, first_message = attacker._handle_duplicates(defender, "attacks")
        second_hit, second_message = attacker._handle_duplicates(defender, "attacks")

        assert first_hit is False
        assert second_hit is False
        assert first_message.count("mirror image") == 1
        assert second_message.count("mirror image") == 1
        assert defender.magic_effects["Duplicates"].active is True
        assert defender.magic_effects["Duplicates"].duration == 2

    def test_handle_defenses_and_damage_reduction_cover_shields_and_magic_defense(self):
        defender = TestGameState.create_player(class_name="Warrior", race_name="Human")
        attacker = TestGameState.create_player(class_name="Warrior", race_name="Human")
        status_events = []
        attacker._emit_status_event = lambda *args, **kwargs: status_events.append((args, kwargs))

        defender.magic_effects["Mana Shield"].active = True
        defender.magic_effects["Mana Shield"].duration = 25
        defender.mana.current = 5

        hit, message, damage = defender.handle_defenses(
            attacker,
            damage=8,
            typ="Physical",
        )
        assert hit is True
        assert "redirects 2 physical damage" in message
        assert damage == 6
        assert defender.mana.current == 3

        defender.magic_effects["Mana Shield"].active = True
        defender.magic_effects["Mana Shield"].duration = 25
        defender.mana.current = 2

        hit, message, damage = defender.handle_defenses(
            attacker,
            damage=10,
            typ="Physical",
        )
        assert hit is True
        assert "redirects 2 physical damage" in message
        assert "mana shield dissolves" in message
        assert damage == 8
        assert defender.mana.current == 0
        assert defender.magic_effects["Mana Shield"].active is False
        assert status_events[-1][1]["source"] == "Mana Depleted"

        defender.magic_effects["Mana Shield"].active = True
        defender.magic_effects["Mana Shield"].duration = 25
        defender.mana.current = -4

        hit, message, damage = defender.handle_defenses(
            attacker,
            damage=8,
            typ="Physical",
        )
        assert hit is True
        assert "absorbs -" not in message
        assert "mana shield dissolves" in message
        assert damage == 8
        assert defender.magic_effects["Mana Shield"].active is False

        defender.resistance["Fire"] = 0.25
        defender.check_mod = lambda mod, enemy=None, typ=None, **_kwargs: (
            50 if mod == "magic def" else defender.resistance.get(typ, 0)
        )
        hit, message, damage = defender.damage_reduction(100, attacker, typ="Fire")

        assert hit is True
        assert "reduces damage" in message
        assert 0 < damage < 75

    def test_flee_covers_smoke_and_standard_success_paths(self, monkeypatch):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        enemy = TestGameState.create_player(name="Enemy", class_name="Warrior", race_name="Human")
        enemy.sight = False

        success, message = player.flee(enemy, smoke=True)
        assert success is True
        assert "cloud of smoke" in message

        player.state = "fight"
        enemy.sight = True
        enemy.status_effects["Blind"].active = True
        success, message = player.flee(enemy, smoke=False)
        assert success is True
        assert "flees from the Enemy" in message

        enemy.status_effects["Blind"].active = False
        enemy.incapacitated = lambda: False
        player.check_mod = lambda mod, enemy=None, luck_factor=None: 0 if mod == "luck" else 1
        enemy.check_mod = lambda mod, enemy=None: 99 if mod == "speed" else 0
        monkeypatch.setattr("src.core.character.random.random", lambda: 0.99)
        success, message = player.flee(enemy, smoke=False)
        assert success is False
        assert "couldn't escape" in message

    def test_modify_inventory_supports_storage_subtract_and_quest_callbacks(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        item = items.Antidote()
        calls = []
        player.quests = lambda item=None: calls.append(item.name)
        player.storage = {"Antidote": [items.Antidote()]}

        player.modify_inventory(item, num=1, quest=True, storage=True)
        assert "Antidote" in player.inventory
        assert player.storage == {}
        assert calls == ["Antidote"]

        player.modify_inventory(item, num=1, subtract=True, storage=True)
        assert "Antidote" not in player.inventory
        assert len(player.storage["Antidote"]) == 1

    def test_effects_cover_end_of_combat_and_common_duration_expiry(self, monkeypatch):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        emitted = []
        monkeypatch.setattr(
            player,
            "_emit_status_event",
            lambda *args, **kwargs: emitted.append(
                kwargs.get("source", args[-1] if args else None)
            ),
        )

        player.status_effects["Blind"].active = True
        player.status_effects["Blind"].duration = 1
        player.status_effects["Defend"].active = True
        player.status_effects["Defend"].duration = 1
        player.magic_effects["Reflect"].active = True
        player.magic_effects["Reflect"].duration = 1
        player.magic_effects["Totem"].active = True
        player.magic_effects["Totem"].duration = 1

        text = player.effects()

        assert "no longer blind" in text
        assert "lowers their guard" in text
        assert "no longer reflecting magic" in text
        assert "totem crumbles" in text

        player.status_effects["Blind"].active = True
        player.magic_effects["Regen"].active = True
        player.magic_effects["Regen"].duration = 2
        player.magic_effects["Regen"].extra = 5
        player.effects(end=True)

        assert player.status_effects["Blind"].active is False
        assert player.magic_effects["Regen"].active is False
        assert emitted

        jump = SimpleNamespace(
            charging=True,
            charge_turns=2,
            charge_target=object(),
            cancel_charge=lambda _user: setattr(jump, "charging", False),
        )
        player.spellbook["Skills"]["Jump"] = jump
        player.class_effects["Jump"].active = True
        player.effects(end=True)

        assert jump.charging is False
        assert player.class_effects["Jump"].active is False

    def test_effects_cover_doom_ice_block_and_dot_cleanup(self, monkeypatch):
        player = TestGameState.create_player(class_name="Knight Enchanter", race_name="Human")
        player.health.current = 20
        player.health.max = 100
        player.mana.current = 10
        player.mana.max = 100

        player.magic_effects["Ice Block"].active = True
        player.magic_effects["Ice Block"].duration = 1
        ice_text = player.effects()
        assert "regens" in ice_text
        assert "melts" in ice_text

        player.magic_effects["DOT"].active = True
        player.magic_effects["DOT"].duration = 1
        player.magic_effects["DOT"].extra = 0
        player.effects()
        assert player.magic_effects["DOT"].active is False

        player.magic_effects["DOT"].active = True
        player.magic_effects["DOT"].duration = 1
        player.magic_effects["DOT"].extra = 5
        player.magic_effects["DOT"].source = "Burn"
        monkeypatch.setattr("src.core.character.random.randint", lambda *_args: 0)
        burn_text = player.effects()
        assert "burns for" in burn_text
        assert "flames around" in burn_text

        player.status_effects["Doom"].active = True
        player.status_effects["Doom"].duration = 1
        doom_text = player.effects()
        assert "Doom countdown has expired" in doom_text
        assert player.health.current == 0

    def test_effects_cover_regen_and_power_up_regeneration(self):
        archbishop = TestGameState.create_player(class_name="Archbishop", race_name="Human")
        archbishop.power_up = True
        archbishop.health.current = 50
        archbishop.mana.current = 20
        archbishop.magic_effects["Regen"].active = True
        archbishop.magic_effects["Regen"].duration = 1
        archbishop.magic_effects["Regen"].extra = 8
        archbishop.class_effects["Power Up"].active = True
        archbishop.class_effects["Power Up"].duration = 1

        text = archbishop.effects()

        assert "health has regenerated" in text
        assert "regens" in text
        assert archbishop.magic_effects["Regen"].active is False
        assert archbishop.class_effects["Power Up"].active is False
