#!/usr/bin/env python3
"""Focused coverage for player helper, quest, and menu behavior."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[2]))

import pytest

from src.core import items
from src.core.constants import BASE_CRIT_PER_POINT
from src.core.player import Player
from tests.test_framework import TestGameState


class TestPlayerHelperCoverage:
    def test_bestiary_observation_records_stable_enemy_details_and_abilities(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        enemy = SimpleNamespace(
            name="Wraith",
            enemy_typ="Undead",
            level=SimpleNamespace(level=7, pro_level=2),
            resistance={"Fire": 0.25, "Holy": -0.5, "Ice": 0.0},
            flying=True,
            sight=True,
            invisible=False,
            tunnel=False,
            boss=False,
            status_immunity=["Death", "Stone"],
            status_effects={"Blind": SimpleNamespace(active=True)},
            physical_effects={},
            magic_effects={"Regen": SimpleNamespace(active=False)},
        )

        player.record_bestiary_encounter(enemy)
        player.record_bestiary_encounter(enemy)
        seen_record = player.bestiary["Wraith"]
        assert seen_record["seen_count"] == 2
        assert seen_record["details_unlocked"] is False
        assert "resistances" not in seen_record

        player.record_bestiary_enemy(enemy)
        player.record_bestiary_ability(enemy, "Attack")
        player.record_bestiary_ability(enemy, "Soul Drain")

        record = player.bestiary["Wraith"]
        assert record["type"] == "Undead"
        assert record["seen_count"] == 2
        assert record["details_unlocked"] is True
        assert record["difficulty_level"] == 2
        assert record["resistances"] == {"Fire": 0.25, "Holy": -0.5}
        assert record["known_abilities"] == ["Soul Drain"]
        assert "Flying" in record["features"]
        assert "Sight" in record["features"]
        assert "Blind" in record["features"]
        assert record["immunities"] == ["Death", "Stone"]

        enemy.status_effects["Blind"].active = False
        player.record_bestiary_enemy(enemy)
        assert player.bestiary["Wraith"]["seen_count"] == 2
        assert "Blind" in player.bestiary["Wraith"]["features"]

    def test_quests_tracks_bounty_and_named_enemy_completion(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        player.quest_dict = {
            "Bounty": {"Goblin": [{"num": 2}, 1, False]},
            "Main": {"Clear the Cave": {"What": "Orc", "Completed": False}},
            "Side": {
                "Ogre Trouble": {"Type": "Defeat", "What": "Orc", "Completed": False},
                "Something to Cry About": {"Completed": False},
            },
        }

        bounty_message = player.quests(enemy=SimpleNamespace(name="Goblin"))
        named_enemy_message = player.quests(enemy=SimpleNamespace(name="Orc"))
        waitress_message = player.quests(enemy=SimpleNamespace(name="Waitress"))

        assert bounty_message == ""
        assert player.quest_dict["Bounty"]["Goblin"][1] == 2
        assert player.quest_dict["Bounty"]["Goblin"][2] is True
        assert "Clear the Cave" in named_enemy_message
        assert "Ogre Trouble" in named_enemy_message
        assert player.quest_dict["Main"]["Clear the Cave"]["Completed"] is True
        assert player.quest_dict["Side"]["Ogre Trouble"]["Completed"] is True
        assert "Something to Cry About" in waitress_message
        assert player.quest_dict["Side"]["Something to Cry About"]["Completed"] is True

    def test_quests_tracks_item_collection_and_holy_relics(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        rat_tail = items.RatTail()
        player.special_inventory = {
            rat_tail.name: [items.RatTail(), items.RatTail()],
        }
        player.quest_dict = {
            "Bounty": {},
            "Main": {"The Holy Relics": {"Completed": False}},
            "Side": {
                "Rat Trap": {"What": "RatTail", "Total": 2, "Completed": False},
            },
        }
        player.has_relics = lambda: True

        item_message = player.quests(item=rat_tail)
        relic_message = player.quests()

        assert "Rat Trap" in item_message
        assert player.quest_dict["Side"]["Rat Trap"]["Completed"] is True
        assert "The Holy Relics" in relic_message
        assert player.quest_dict["Main"]["The Holy Relics"]["Completed"] is True

    def test_quests_item_collection_requires_total_and_does_not_repeat_completion(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        mystery_meat = items.MysteryMeat()
        player.special_inventory = {mystery_meat.name: [items.MysteryMeat()]}
        player.quest_dict = {
            "Bounty": {},
            "Main": {},
            "Side": {
                "Where's the Beef?": {
                    "What": mystery_meat,
                    "Total": 2,
                    "Completed": False,
                },
            },
        }

        partial_message = player.quests(item=mystery_meat)
        player.special_inventory[mystery_meat.name].append(items.MysteryMeat())
        complete_message = player.quests(item=mystery_meat)
        repeated_message = player.quests(item=mystery_meat)

        assert partial_message == ""
        assert "Where's the Beef?" in complete_message
        assert repeated_message == ""
        assert player.quest_dict["Side"]["Where's the Beef?"]["Completed"] is True

    def test_check_mod_support_branches_cover_shield_magic_heal_and_magic_defense(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human", pro_level=3)
        player.equipment["OffHand"] = items.Buckler()
        player.equipment["Ring"] = items.BarrierRing()
        assert player.check_mod("shield") == 30

        player.equipment["OffHand"] = SimpleNamespace(
            subtyp="Tome", mod=6, damage=0, name="Prayer Tome", weight=0
        )
        player.stat_effects["Magic"].active = True
        player.stat_effects["Magic"].extra = 3
        assert player.check_mod("heal") == 84

        player.equipment["Pendant"] = items.RubyLocket()
        player.stat_effects["Magic Defense"].active = True
        player.stat_effects["Magic Defense"].extra = 4
        assert player.check_mod("magic def") == 105

        shadowcaster = TestGameState.create_player(class_name="Shadowcaster", race_name="Human")
        shadowcaster.power_up = True
        shadowcaster.class_effects["Power Up"].active = True
        shadowcaster.equipment["Weapon"] = SimpleNamespace(
            name="Void Staff",
            subtyp="Staff",
            damage=20,
            crit=0.1,
            typ="Weapon",
            weight=0,
        )
        shadowcaster.equipment["OffHand"] = SimpleNamespace(
            name="Hex Tome",
            subtyp="Tome",
            mod=7,
            damage=0,
            typ="OffHand",
            weight=0,
        )
        shadowcaster.equipment["Pendant"] = items.PlatinumNecklace()
        shadowcaster.equipment["Armor"] = items.NoArmor()
        shadowcaster.stat_effects["Magic"].active = True
        shadowcaster.stat_effects["Magic"].extra = 3

        assert shadowcaster.check_mod("magic") == 201

        shadowcaster.equipment["Armor"] = items.WizardRobe()
        assert shadowcaster.check_mod("magic") == 211

        shadowcaster.equipment["Armor"] = SimpleNamespace(subtyp="Cloth", armor=20, spell_mod=9)
        assert shadowcaster.check_mod("magic") == 219

    def test_check_mod_support_branches_cover_luck_speed_and_armor_variants(self, monkeypatch):
        rogue = TestGameState.create_player(class_name="Rogue", race_name="Human")
        rogue.power_up = True
        assert rogue.check_mod("luck", luck_factor=6) == 23

        rogue.stat_effects["Speed"].active = True
        rogue.stat_effects["Speed"].extra = 5
        assert rogue.check_mod("speed") == 23

        dragoon = TestGameState.create_player(class_name="Dragoon", race_name="Human")
        dragoon.power_up = True
        dragoon.class_effects["Power Up"].active = True
        dragoon.class_effects["Power Up"].duration = 2
        dragoon.equipment["Armor"] = SimpleNamespace(armor=10, name="Dragon Plate", weight=0)
        dragoon.equipment["Ring"] = items.SteelRing()
        dragoon.stat_effects["Defense"].active = True
        dragoon.stat_effects["Defense"].extra = 3

        assert dragoon.check_mod("armor") == 53
        assert dragoon.check_mod("armor", ignore=True) == 30

        warlock = TestGameState.create_player(class_name="Warlock", race_name="Human")
        warlock.equipment["Armor"] = SimpleNamespace(armor=5, name="Night Robe", weight=0)
        warlock.equipment["Ring"] = items.NoRing()
        warlock.familiar = SimpleNamespace(spec="Homunculus", level=SimpleNamespace(pro_level=2))
        familiar_rolls = iter([1, 2])
        monkeypatch.setattr("src.core.player.random.randint", lambda _a, _b: next(familiar_rolls))

        assert warlock.check_mod("armor") == 19

    def test_check_mod_resist_applies_flying_equipment_familiar_and_class_bonuses(
        self, monkeypatch
    ):
        geomancer = TestGameState.create_player(class_name="Astromancer", race_name="Human")
        geomancer.power_up = True
        geomancer.class_effects["Power Up"].active = True
        geomancer.resistance["Fire"] = 0.1
        geomancer.equipment["Pendant"] = items.FireChain()
        geomancer.equipment["OffHand"] = items.Svalinn()
        geomancer.equipment["Armor"] = items.DragonHide()

        assert geomancer.check_mod("resist", typ="Fire") == pytest.approx(1.6)

        geomancer.flying = True
        assert geomancer.check_mod("resist", typ="Earth") == pytest.approx(0.5)
        assert geomancer.check_mod("resist", typ="Wind") == pytest.approx(0.25)

        shadowcaster = TestGameState.create_player(class_name="Shadowcaster", race_name="Human")
        shadowcaster.stats.charisma = 20
        shadowcaster.familiar = SimpleNamespace(spec="Mephit", level=SimpleNamespace(pro_level=2))
        shadowcaster.equipment["Pendant"] = items.ElementalChain()
        familiar_rolls = iter([1, 2])
        monkeypatch.setattr("src.core.player.random.randint", lambda _a, _b: next(familiar_rolls))

        assert shadowcaster.check_mod("resist", typ="Fire") == pytest.approx(1.0)

        archbishop = TestGameState.create_player(class_name="Archbishop", race_name="Human")
        archbishop.class_effects["Power Up"].active = True

        assert archbishop.check_mod("resist", typ="Holy") == pytest.approx(0.25)

    def test_special_power_grants_shadowcaster_transformation(self):
        player = TestGameState.create_player(class_name="Shadowcaster", race_name="Human")
        events = []
        game = SimpleNamespace(special_event=lambda name: events.append(name))

        result = player.special_power(game)

        assert result == "You gain the skill Shade of Ahool.\n"
        assert events == ["Power Up"]
        assert player.power_up is True
        assert player.invisible is False
        assert "Shade of Ahool" in player.spellbook["Skills"]

    def test_status_string_includes_racial_traits(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")

        status_message = player.status_str()

        assert "Hit Points:" in status_message
        assert "Virtue:" in status_message
        assert "Diligence" in status_message
        assert "Sin:" in status_message
        assert "Lust" in status_message

    def test_combat_equipment_and_resist_strings_render_expected_sections(self):
        player = TestGameState.create_player(class_name="Warrior", race_name="Human")
        player.equipment["Weapon"] = SimpleNamespace(
            name="Falchion",
            crit=0.1,
            damage=12,
            subtyp="Sword",
            typ="Weapon",
            weight=0,
        )
        player.equipment["OffHand"] = SimpleNamespace(
            name="Parrying Dagger",
            crit=0.05,
            damage=5,
            mod=0,
            subtyp="Dagger",
            typ="Weapon",
            weight=0,
        )
        player.equipment["Armor"] = items.PlateMail()
        player.equipment["Ring"] = items.PowerRing()
        player.equipment["Pendant"] = items.FireChain()
        player.buff_str = lambda: "Blessed"

        resist_values = {
            "Fire": 1.5,
            "Electric": 0.5,
            "Earth": 0.0,
            "Shadow": -0.25,
            "Poison": 0.0,
            "Ice": 0.5,
            "Water": 0.0,
            "Wind": -0.1,
            "Holy": 0.25,
            "Physical": 0.1,
        }
        stat_values = {
            "weapon": 11,
            "speed": 4,
            "offhand": 7,
            "armor": 9,
            "shield": 12,
            "magic def": 13,
            "magic": 14,
            "heal": 15,
        }

        def fake_check_mod(mod, enemy=None, typ=None, **_kwargs):
            if mod == "resist":
                return resist_values[typ]
            return stat_values[mod]

        player.check_mod = fake_check_mod

        combat_message = player.combat_str()
        equipment_message = player.equipment_str()
        resist_message = player.resist_str()

        main_crit = int(
            (player.equipment["Weapon"].crit + (BASE_CRIT_PER_POINT * stat_values["speed"])) * 100
        )
        off_crit = int(
            (player.equipment["OffHand"].crit + (BASE_CRIT_PER_POINT * stat_values["speed"])) * 100
        )

        assert "Attack:" in combat_message
        assert "11/  7" in combat_message
        assert f"{main_crit}%/{off_crit:>2}%" in combat_message
        assert "Falchion" in equipment_message
        assert "Parrying Dagger" in equipment_message
        assert "Blessed" in equipment_message
        assert "Fire:" in resist_message
        assert "Physical:" in resist_message
