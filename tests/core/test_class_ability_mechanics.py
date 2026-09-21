from types import SimpleNamespace

from src.core import abilities, companions, enemies, items, map_tiles
from src.core.classes import ability_mechanics, promotion_kits
from src.core.combat.battle_engine import BattleEngine
from src.core.save_system import PlayerDataSerializer
from tests.test_framework import TestGameState


class _Tile:
    enemy = None

    def available_actions(self, player):
        return player.additional_actions(["Attack", "Cast Spell", "Use Skill", "Use Item", "Flee"])

    def __str__(self):
        return "TestTile"


def test_monkey_grip_keeps_two_handed_weapon_and_offhand_weapon():
    player = TestGameState.create_player(class_name="Berserker", level=1)
    player.equipment["Weapon"] = items.Parashu()
    player.equipment["OffHand"] = items.Changdao()
    player.modify_inventory(items.Greataxe())

    assert player.equip("Weapon", items.Greataxe()) is True
    assert player.equipment["Weapon"].name == "Greataxe"
    assert player.equipment["OffHand"].name == "Changdao"

    base_main = player.check_mod("weapon")
    base_offhand = player.check_mod("offhand")
    player.spellbook["Skills"]["Monkey Grip"] = abilities.MonkeyGrip()
    assert player.check_mod("weapon") > base_main
    assert player.check_mod("offhand") > base_offhand

    stabilized_main = player.check_mod("weapon")
    stabilized_offhand = player.check_mod("offhand")
    player.spellbook["Skills"]["Monkey Grip 2"] = abilities.MonkeyGrip2()
    assert player.check_mod("weapon") == stabilized_main
    assert player.check_mod("offhand") > stabilized_offhand
    assert player.check_mod("offhand") < player.equipment["OffHand"].damage + player.combat.attack


def test_polearm_one_hand_progression_penalty_and_bonus():
    player = TestGameState.create_player(class_name="Lancer", level=1)
    player.equipment["Weapon"] = items.Halberd()
    player.equipment["OffHand"] = items.Glagwa()

    unrestricted = player.check_mod("weapon")
    player.spellbook["Skills"]["Polearm Proficiency"] = abilities.PolearmProficiency()
    penalized = player.check_mod("weapon")

    player.spellbook["Skills"].pop("Polearm Proficiency")
    player.spellbook["Skills"]["Polearm Excellence"] = abilities.PolearmExcellence()
    neutral = player.check_mod("weapon")

    player.spellbook["Skills"].pop("Polearm Excellence")
    player.spellbook["Skills"]["Polearm Mastery"] = abilities.PolearmMastery()
    mastered = player.check_mod("weapon")

    assert penalized < unrestricted
    assert neutral == unrestricted
    assert mastered > neutral


def test_tame_is_animal_only_and_round_trips_save(monkeypatch):
    player = TestGameState.create_player(class_name="Ranger", level=10, stats={"charisma": 40})
    rat = enemies.GiantRat()
    rat.health.current = 1

    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 0.0)
    message = abilities.Tame().use(player, rat)

    assert "tames" in message
    assert "bond is 5/100" not in message
    assert "begins watching for your signals" in message
    assert "Tamed companions held: 1/6" in message
    assert "Pounce" in message
    assert rat.tamed_by_player is True
    assert rat.no_victory_rewards is True
    assert player.tamed_companion["enemy_class"] == "GiantRat"
    assert player.tamed_companion["bond"] == ability_mechanics.TAMED_COMPANION_START_BOND
    assert player.tamed_companion["species"] == "Rat"
    assert player.tamed_companion["evolution"] == "Skittish Rat"
    assert player.tamed_companion["special_ability"] == "Pounce"
    assert len(player.tamed_companion["companions"]) == 1
    assert player.familiar is not None
    assert player.familiar.evolution == "Skittish Rat"
    assert player.familiar.special_ability == "Pounce"

    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(player), skip_tiles=True
    )
    assert restored.tamed_companion["enemy_class"] == "GiantRat"
    assert restored.tamed_companion["bond"] == ability_mechanics.TAMED_COMPANION_START_BOND
    assert restored.tamed_companion["special_ability"] == "Pounce"
    assert len(restored.tamed_companion["companions"]) == 1
    assert restored.familiar.name == "Giant Rat"
    assert restored.familiar.evolution == "Skittish Rat"
    assert "is not tamable" in abilities.Tame().use(player, enemies.Owlbear())


def test_tame_failed_attempt_and_invalid_target_messages_are_distinct(monkeypatch):
    player = TestGameState.create_player(class_name="Ranger", level=10, stats={"charisma": 0})
    rat = enemies.GiantRat()
    rat.health.current = rat.health.max
    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 1.0)

    failed = abilities.Tame().use(player, rat)
    invalid = abilities.Tame().use(player, enemies.Owlbear())

    assert "fails to tame Giant Rat" in failed
    assert "refuses the signal" in failed
    assert "is not tamable" in invalid
    assert "fails to tame" not in invalid


def test_tame_victory_grants_no_exp_gold_loot_or_extra_bond(monkeypatch):
    player = TestGameState.create_player(class_name="Ranger", level=10, stats={"charisma": 40})
    rat = enemies.GiantRat()
    rat.health.current = 1
    rat.gold = 999
    rat.experience = 999

    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 0.0)
    message = abilities.Tame().use(player, rat)
    assert "tames" in message

    loot_calls = []
    quest_calls = []
    monkeypatch.setattr(
        player, "loot", lambda *_args, **_kwargs: loot_calls.append(True) or "loot called\n"
    )
    monkeypatch.setattr(
        player, "quests", lambda *_args, **_kwargs: quest_calls.append(True) or "quest called\n"
    )

    before_exp = player.level.exp
    before_exp_to_gain = player.level.exp_to_gain
    before_gold = player.gold
    before_kills = {key: dict(value) for key, value in player.kill_dict.items()}

    engine = BattleEngine(player, rat, _Tile())
    victory_message = engine._process_victory()

    assert "leaves the fight as a companion" in victory_message
    assert "gained 999 experience" not in victory_message
    assert "loot called" not in victory_message
    assert "quest called" not in victory_message
    assert loot_calls == []
    assert quest_calls == []
    assert player.level.exp == before_exp
    assert player.level.exp_to_gain == before_exp_to_gain
    assert player.gold == before_gold
    assert player.kill_dict == before_kills
    assert player.tamed_companion["bond"] == ability_mechanics.TAMED_COMPANION_START_BOND


def test_companion_turn_skips_dead_or_tamed_defender(monkeypatch):
    player = TestGameState.create_player(class_name="Ranger", level=10, stats={"charisma": 40})
    rat = enemies.GiantRat()
    rat.health.current = 1
    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 0.0)
    abilities.Tame().use(player, rat)
    enemy = enemies.Goblin()
    engine = BattleEngine(player, enemy, _Tile())
    engine.attacker = player
    engine.defender = rat

    assert engine.companion_turn() == ""
    assert rat.health.current == 0
    assert rat.tamed_by_player is True

    enemy.health.current = 0
    engine.defender = enemy
    assert engine.companion_turn() == ""


def test_tamed_companion_auto_turn_can_attack_without_player_class_object(monkeypatch):
    player = TestGameState.create_player(class_name="Ranger", level=10, stats={"charisma": 40})
    rat = enemies.GiantRat()
    rat.health.current = 1

    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 0.0)
    abilities.Tame().use(player, rat)
    enemy = enemies.Goblin()

    message = player.familiar_turn(enemy)

    assert "Giant Rat attacks Goblin" in message


def test_tamed_companion_auto_chance_scales_by_bond(monkeypatch):
    player = TestGameState.create_player(class_name="Ranger", level=10, stats={"charisma": 40})
    rat = enemies.GiantRat()
    rat.health.current = 1
    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 0.0)
    abilities.Tame().use(player, rat)
    enemy = enemies.Goblin()

    player.tamed_companion["bond"] = 5
    player.familiar.bond = 5
    assert ability_mechanics.tamed_auto_action_chance(player) < 0.15
    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 0.99)
    assert player.familiar_turn(enemy) == ""

    player.tamed_companion["bond"] = 100
    player.familiar.bond = 100
    assert ability_mechanics.tamed_auto_action_chance(player) > 0.35
    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 0.0)
    assert "Giant Rat attacks Goblin" in player.familiar_turn(enemy)


def test_beast_master_companion_action_gates_and_command_resolution(monkeypatch):
    beast = TestGameState.create_player(class_name="Beast Master", level=30, stats={"charisma": 40})
    for command_cls in (
        abilities.PackStrike,
        abilities.GuardPartner,
        abilities.HarryPrey,
        abilities.MendWounds,
    ):
        command = command_cls()
        beast.spellbook["Skills"][command.name] = command
    rat = enemies.GiantRat()
    rat.health.current = 1
    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 0.0)
    abilities.Tame().use(beast, rat)
    enemy = enemies.Goblin()
    engine = BattleEngine(beast, enemy, _Tile())
    engine.attacker = beast
    engine.defender = enemy

    assert "Companion" in engine._available_actions()
    assert "Tame" not in engine._available_actions()

    ranger = TestGameState.create_player(class_name="Ranger", level=30, stats={"charisma": 40})
    rat2 = enemies.GiantRat()
    rat2.health.current = 1
    abilities.Tame().use(ranger, rat2)
    ranger_engine = BattleEngine(ranger, enemies.Goblin(), _Tile())
    ranger_engine.attacker = ranger
    ranger_engine.defender = ranger_engine.encounter.primary_enemy
    assert "Companion" not in ranger_engine._available_actions()
    assert "Tame" not in ranger_engine._available_actions()

    empty_beast = TestGameState.create_player(class_name="Beast Master", level=30)
    empty_beast.spellbook["Skills"]["Tame"] = abilities.Tame()
    empty_engine = BattleEngine(empty_beast, enemies.Goblin(), _Tile())
    empty_engine.attacker = empty_beast
    empty_engine.defender = empty_engine.encounter.primary_enemy
    assert "Companion" not in empty_engine._available_actions()
    assert "Tame" in empty_engine._available_actions()

    result = engine.execute_intent(engine.prepare_intent("Companion", "Pack Strike"))
    assert "orders their companion: Pack Strike" in result.message
    assert ability_mechanics.pending_companion_command(beast) == "Pack Strike"

    hp_before = enemy.health.current
    command_message = beast.familiar_turn(enemy)
    assert "follows Pack Strike" in command_message
    assert enemy.health.current < hp_before
    assert ability_mechanics.pending_companion_command(beast) is None


def test_beast_master_commands_always_do_something_and_scale_by_bond(monkeypatch):
    beast = TestGameState.create_player(class_name="Beast Master", level=30, stats={"charisma": 40})
    for command_cls in (
        abilities.PackStrike,
        abilities.GuardPartner,
        abilities.HarryPrey,
        abilities.MendWounds,
    ):
        command = command_cls()
        beast.spellbook["Skills"][command.name] = command
    rat = enemies.GiantRat()
    rat.health.current = 1
    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 0.0)
    abilities.Tame().use(beast, rat)
    enemy = enemies.Goblin()

    for command in ("Guard Partner", "Harry Prey", "Mend Wounds"):
        ability_mechanics.set_pending_companion_command(beast, command)
        message = ability_mechanics.resolve_tamed_companion_command(beast, enemy)
        assert message
        assert ability_mechanics.pending_companion_command(beast) is None

    beast.health.current = beast.health.max - 50
    beast.tamed_companion["bond"] = 5
    beast.familiar.bond = 5
    ability_mechanics.set_pending_companion_command(beast, "Mend Wounds")
    low_before = beast.health.current
    ability_mechanics.resolve_tamed_companion_command(beast, enemy)
    low_heal = beast.health.current - low_before

    beast.health.current = beast.health.max - 50
    beast.tamed_companion["bond"] = 100
    beast.familiar.bond = 100
    ability_mechanics.set_pending_companion_command(beast, "Mend Wounds")
    high_before = beast.health.current
    ability_mechanics.resolve_tamed_companion_command(beast, enemy)
    high_heal = beast.health.current - high_before

    assert high_heal > low_heal > 0


def test_tame_keeps_bounded_roster_and_requires_release_when_full(monkeypatch):
    player = TestGameState.create_player(class_name="Ranger", level=10, stats={"charisma": 40})
    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 0.0)

    for enemy_factory in (
        enemies.GiantRat,
        enemies.GiantCentipede,
        enemies.GiantHornet,
        enemies.ElectricBat,
        enemies.GiantSpider,
        enemies.Panther,
    ):
        target = enemy_factory()
        target.health.current = 1
        assert "Tamed companions held:" in abilities.Tame().use(player, target)

    assert (
        len(player.tamed_companion["companions"]) == ability_mechanics.TAMED_COMPANION_ROSTER_LIMIT
    )
    assert [entry["enemy_class"] for entry in player.tamed_companion["companions"]][0] == "GiantRat"
    assert player.tamed_companion["enemy_class"] == "Panther"

    direwolf = enemies.Direwolf()
    direwolf.health.current = 1
    message = abilities.Tame().use(player, direwolf)
    assert "cannot keep another tamed companion" in message
    assert "Release one from the Companion & Hunt tab" in message
    assert (
        len(player.tamed_companion["companions"]) == ability_mechanics.TAMED_COMPANION_ROSTER_LIMIT
    )

    release_message = ability_mechanics.release_tamed_companion(player, 0)
    assert "returns to the wild" in release_message
    direwolf.health.current = 1
    assert "tames Direwolf" in abilities.Tame().use(player, direwolf)
    assert player.tamed_companion["enemy_class"] == "Direwolf"
    assert (
        len(player.tamed_companion["companions"]) == ability_mechanics.TAMED_COMPANION_ROSTER_LIMIT
    )


def test_tamed_companion_rebuild_keeps_random_animal_stats_stable(monkeypatch):
    player = TestGameState.create_player(class_name="Ranger", level=10, stats={"charisma": 40})
    hornet = enemies.GiantHornet()
    hornet.health.max = 9
    hornet.health.current = 1

    monkeypatch.setattr("src.core.classes.ability_mechanics.random.random", lambda: 0.0)
    message = abilities.Tame().use(player, hornet)

    assert "tames Giant Hornet" in message
    assert player.tamed_companion["base"]["health_max"] == 6
    first = player.familiar
    rebuilt = companions.tamed_companion_from_state(player.tamed_companion)
    rebuilt_again = companions.tamed_companion_from_state(player.tamed_companion)
    assert (rebuilt.health.max, rebuilt.mana.max, rebuilt.combat.attack) == (
        first.health.max,
        first.mana.max,
        first.combat.attack,
    )
    assert (rebuilt_again.health.max, rebuilt_again.mana.max, rebuilt_again.combat.attack) == (
        rebuilt.health.max,
        rebuilt.mana.max,
        rebuilt.combat.attack,
    )


def test_legacy_tamed_companion_rebuild_is_deterministic_without_base_snapshot():
    legacy_state = {
        "active": True,
        "enemy_class": "GiantHornet",
        "name": "Giant Hornet",
        "bond": 25,
        "species": "Hornet",
        "special_ability": "Wingbeat",
    }

    rebuilt = companions.tamed_companion_from_state(legacy_state)
    rebuilt_again = companions.tamed_companion_from_state(legacy_state)

    assert rebuilt is not None
    assert rebuilt_again is not None
    assert (rebuilt.health.max, rebuilt.mana.max, rebuilt.combat.attack) == (
        rebuilt_again.health.max,
        rebuilt_again.mana.max,
        rebuilt_again.combat.attack,
    )


def test_tamed_companion_bond_growth_evolves_and_syncs_familiar():
    player = TestGameState.create_player(class_name="Ranger", level=10)
    player.tamed_companion = {
        "active": True,
        "enemy_class": "GiantRat",
        "name": "Giant Rat",
        "bond": 24,
        "special_ability": "Pounce",
    }
    player.ensure_tamed_companion()

    message = promotion_kits.gain_companion_bond(
        player, 1, "new trail", rng=SimpleNamespace(random=lambda: 0.0)
    )

    assert "bond increased" in message
    assert "bond grows by" not in message
    assert "/100" not in message
    assert "evolves into Tunnel Rat" in message
    assert player.tamed_companion["bond"] == 25
    assert player.tamed_companion["evolution"] == "Tunnel Rat"
    assert player.familiar.bond == 25
    assert player.familiar.evolution == "Tunnel Rat"


def test_tamed_companion_rename_keeps_species_visible():
    player = TestGameState.create_player(class_name="Ranger", level=10)
    player.tamed_companion = {
        "active": True,
        "name": "Giant Hornet",
        "enemy_class": "GiantHornet",
        "bond": 5,
        "companions": [
            {
                "active": True,
                "name": "Giant Hornet",
                "enemy_class": "GiantHornet",
                "bond": 5,
            }
        ],
        "active_index": 0,
    }

    ability_mechanics.rename_tamed_companion(player, "Needle")

    assert player.tamed_companion["custom_name"] == "Needle"
    assert player.tamed_companion["companions"][0]["custom_name"] == "Needle"
    assert (
        ability_mechanics.tamed_companion_display_name(player.tamed_companion)
        == "Needle (Giant Hornet)"
    )
    assert player.familiar.name == "Needle (Giant Hornet)"


def test_tamed_companion_special_ability_triggers_after_bonded_hit():
    player = TestGameState.create_player(class_name="Ranger", level=10)
    target = enemies.Goblin()
    player.tamed_companion = {
        "active": True,
        "enemy_class": "GiantRat",
        "name": "Giant Rat",
        "bond": 25,
        "special_ability": "Pounce",
    }
    player.ensure_tamed_companion()
    before = target.health.current

    message = ability_mechanics.tamed_companion_special_turn(player, target, hit=True, crit=False)

    assert "Pounce follows through" in message
    assert target.health.current < before


def test_tamed_guard_hide_uses_companion_sourced_nature_shield():
    player = TestGameState.create_player(class_name="Ranger", level=10)
    target = enemies.Goblin()
    player.tamed_companion = {
        "active": True,
        "enemy_class": "BattleToad",
        "name": "Battle Toad",
        "bond": 25,
        "special_ability": "Guard Hide",
    }
    player.ensure_tamed_companion()

    message = ability_mechanics.tamed_companion_special_turn(player, target, hit=False, crit=False)

    assert "Guard Hide braces" in message
    shield = player.magic_effects["Nature Shield"]
    assert shield.active is True
    assert shield.source == "Guard Hide"


def test_favored_enemy_marks_current_type_persists_and_rewards_discipline():
    player = TestGameState.create_player(class_name="Ranger", level=10)
    player.spellbook["Skills"]["Favored Enemy"] = abilities.FavoredEnemy()
    goblin = enemies.Goblin()
    rat = enemies.GiantRat()

    mark_message = abilities.FavoredEnemy().use(player, goblin)
    assert "marks" in mark_message
    assert ability_mechanics.favorite_enemy_type(player) == goblin.enemy_typ
    assert ability_mechanics.favored_enemy_bonus(player, goblin) == 1
    assert ability_mechanics.favored_enemy_bonus(player, rat) == 0

    repeat_message = abilities.FavoredEnemy().use(player, goblin)
    assert "studies" in repeat_message
    assert "practice" not in repeat_message
    assert ability_mechanics.favored_enemy_state(player)["practice"] == 2

    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(player), skip_tiles=True
    )
    assert ability_mechanics.favorite_enemy_type(restored) == goblin.enemy_typ
    assert ability_mechanics.favored_enemy_state(restored)["practice"] == 2

    switch_message = abilities.FavoredEnemy().use(restored, rat)
    assert "changes quarry" in switch_message
    assert "tracking mastery" not in switch_message
    assert "practice" not in switch_message
    assert ability_mechanics.favorite_enemy_type(restored) == rat.enemy_typ
    assert ability_mechanics.favored_enemy_state(restored)["practice"] == 0
    assert ability_mechanics.favored_enemy_state(restored)["switches"] == 1


def test_favored_enemy_does_not_fall_back_to_kill_history():
    player = TestGameState.create_player(class_name="Ranger", level=10)
    player.spellbook["Skills"]["Favored Enemy"] = abilities.FavoredEnemy()
    player.kill_dict = {"Animal": {"Giant Rat": 12}}
    rat = enemies.GiantRat()

    assert ability_mechanics.favorite_enemy_type(player) is None
    assert ability_mechanics.favored_enemy_label(player) == "None"
    assert ability_mechanics.favored_enemy_bonus(player, rat) == 0


def test_tamed_companion_bond_gain_slows_as_bond_rises():
    assert (
        promotion_kits.companion_bond_gain_roll(5, 4, rng=SimpleNamespace(random=lambda: 0.0)) == 4
    )
    assert (
        promotion_kits.companion_bond_gain_roll(50, 4, rng=SimpleNamespace(random=lambda: 0.0)) == 2
    )
    assert (
        promotion_kits.companion_bond_gain_roll(90, 4, rng=SimpleNamespace(random=lambda: 0.0)) == 1
    )
    assert (
        promotion_kits.companion_bond_gain_roll(90, 4, rng=SimpleNamespace(random=lambda: 0.5)) == 0
    )


def test_favored_enemy_practice_grows_on_marked_victories(monkeypatch):
    player = TestGameState.create_player(class_name="Ranger", level=10)
    player.spellbook["Skills"]["Favored Enemy"] = abilities.FavoredEnemy()
    rat = enemies.GiantRat()
    abilities.FavoredEnemy().use(player, rat)
    player.promotion_kit_state["favored_enemy"]["practice"] = 9
    monkeypatch.setattr("src.core.classes.promotion_kits.random.random", lambda: 0.0)

    message = promotion_kits.end_combat(player, victory=True, enemy=rat, exp_gain=10)

    assert "tracking mastery improves" not in message
    assert "practice" not in message
    assert ability_mechanics.favored_enemy_state(player)["practice"] == 10
    assert ability_mechanics.favored_enemy_bonus(player, rat) == 3


def test_companion_victory_and_favored_enemy_bond_use_one_message(monkeypatch):
    player = TestGameState.create_player(class_name="Ranger", level=10)
    player.spellbook["Skills"]["Favored Enemy"] = abilities.FavoredEnemy()
    rat = enemies.GiantRat()
    abilities.Tame().use(player, rat, rng=SimpleNamespace(random=lambda: 0.0))
    player.tamed_companion["bond"] = 5
    abilities.FavoredEnemy().use(player, rat)
    monkeypatch.setattr("src.core.classes.promotion_kits.random.random", lambda: 0.0)

    message = promotion_kits.end_combat(player, victory=True, enemy=rat, exp_gain=10)

    assert message.count("Giant Rat bond increased.") == 1
    assert "victory" not in message
    assert "Favored Enemy hunt" not in message
    assert player.tamed_companion["bond"] > 5


def test_victory_completion_popup_suppresses_progress_messages(monkeypatch):
    player = TestGameState.create_player(class_name="Ranger", level=10)
    player.spellbook["Skills"]["Favored Enemy"] = abilities.FavoredEnemy()
    rat = enemies.GiantRat()
    abilities.FavoredEnemy().use(player, rat)
    player.promotion_kit_state["favored_enemy"]["practice"] = 9
    rat.experience = 0
    monkeypatch.setattr("src.core.classes.promotion_kits.random.random", lambda: 0.0)
    engine = BattleEngine(player, rat, _Tile())

    message = engine._process_victory()

    assert "tracking mastery improves" not in message
    assert "practice" not in message
    assert "Case Journal records" not in message
    assert ability_mechanics.favored_enemy_state(player)["practice"] == 10


def test_favored_enemy_skill_marks_enemy_type_through_battle_engine():
    player = TestGameState.create_player(class_name="Ranger", level=10)
    player.spellbook["Skills"]["Favored Enemy"] = abilities.FavoredEnemy()
    enemy = enemies.Goblin()
    engine = BattleEngine(player, enemy, _Tile())
    engine.attacker = player
    engine.defender = enemy

    result = engine.execute_intent(engine.prepare_intent("Use Skill", "Favored Enemy"))

    assert "marks" in result.message
    assert ability_mechanics.favorite_enemy_type(player) == enemy.enemy_typ


def test_reagent_spells_consume_required_items_and_apply_effects(monkeypatch):
    player = TestGameState.create_player(class_name="Archdruid", level=30)
    target = enemies.Goblin()
    target.health.current = target.health.max = 500
    target.dodge_chance = lambda *_args, **_kwargs: 0.0
    monkeypatch.setattr("src.core.abilities.random.random", lambda: 1.0)
    monkeypatch.setattr("src.core.abilities.random.uniform", lambda _lo, _hi: 1.0)
    player.modify_inventory(items.Acorn())
    player.modify_inventory(items.VineSeed())
    player.modify_inventory(items.FungusSpore())
    player.modify_inventory(items.HemlockRoot())
    player.modify_inventory(items.FungusSpore())

    plant = abilities.PlantSeeds()
    assert "mighty oak" in plant.cast(player, target=target, reagent="Acorn").lower()
    assert "Acorn" not in player.inventory
    assert target.status_effects["Stun"].active is True
    target.status_effects["Stun"].active = False

    assert "vines" in plant.cast(player, target=target, reagent="Vine Seed")
    assert "Vine Seed" not in player.inventory
    assert target.physical_effects["Prone"].active is True

    assert "mushroom" in plant.cast(player, target=target, reagent="Fungus Spore")
    assert target.status_effects["Poison"].active is True

    vile = abilities.VilePotion()
    monkeypatch.setattr("src.core.abilities.random.random", lambda: 0.0)
    assert "poison" in vile.cast(player, target=target).lower()
    assert "Hemlock Root" not in player.inventory
    assert "Fungus Spore" not in player.inventory


def test_tree_of_life_is_growth_mastery_oak_form():
    from src.core.classes import archdruid

    player = TestGameState.create_player(
        class_name="Archdruid", level=30, health=(300, 100), mana=(200, 200)
    )
    state = archdruid.default_state()
    state["aspects"]["Growth"] = True
    state["attunement"]["Growth"] = archdruid.MASTERY_THRESHOLD
    player.archdruid_attunement = state

    archdruid.apply_mastery_perks(player)

    assert "Tree of Life" in player.spellbook["Spells"]
    before_armor = player.check_mod("armor")
    before_mdef = player.check_mod("magic def")
    assert "giant oak" in abilities.TreeOfLife().cast(player)
    assert player.magic_effects["Tree of Life"].active is True
    assert player.check_mod("armor") > before_armor
    assert player.check_mod("magic def") > before_mdef
    assert player.has_status_protection("Stun") is True

    enemy = enemies.Goblin()
    tile = _Tile()
    tile.enemy = enemy
    engine = BattleEngine(player, enemy, tile)
    engine.attacker = player
    engine.defender = enemy
    assert "cannot attack" in engine.execute_intent(engine.prepare_intent("Attack")).message

    message = player.effects()
    assert "Tree of Life restores" in message
    assert player.health.current == 199


def test_ball_lightning_is_multihit_without_stun(monkeypatch):
    caster = TestGameState.create_player(class_name="Archdruid", level=30, mana=(200, 200))
    target = enemies.Goblin()
    target.health.current = target.health.max = 500
    target.dodge_chance = lambda *_args, **_kwargs: 0.0
    monkeypatch.setattr("src.core.abilities.random.random", lambda: 1.0)
    monkeypatch.setattr("src.core.abilities.random.uniform", lambda _lo, _hi: 1.0)

    message = abilities.BallLightning().cast(caster, target=target)

    assert message.count("damages") == 3
    assert target.status_effects["Stun"].active is False


def test_calming_breeze_blocks_berserk_but_cannot_be_cast_while_berserk():
    player = TestGameState.create_player(class_name="Druid", level=20, mana=(200, 200))
    player.status_effects["Berserk"].active = True
    player.status_effects["Berserk"].duration = 2

    message = abilities.CalmingBreeze().cast(player, player)

    assert "too berserk" in message
    assert player.status_effects["Peaceful"].active is False

    player.status_effects["Berserk"].active = False
    assert "steadies" in abilities.CalmingBreeze().cast(player, player)
    abilities.Berserk().cast(player, target=player)
    assert player.status_effects["Berserk"].active is False


def test_defensive_regen_heals_while_defending():
    player = TestGameState.create_player(class_name="Priest", level=20, health=(100, 50))
    player.spellbook["Skills"]["Defensive Regen"] = abilities.DefensiveRegen()
    player.enter_defensive_stance(duration=2)

    message = player.effects()

    assert "defensive focus restores" in message
    assert player.health.current > 50


def test_foretell_and_rewind_restore_combat_snapshot():
    from src.core.classes import ability_mechanics

    player = TestGameState.create_player(class_name="Astromancer", level=30)
    enemy = enemies.Goblin()
    enemy.action_stack = [{"ability": "Stab", "weight": 100}]
    tile = _Tile()
    tile.enemy = enemy
    engine = BattleEngine(player, enemy, tile)
    engine.attacker = player
    engine.defender = enemy

    assert "next action: Stab" in abilities.Foretell().cast(
        player, target=enemy, battle_engine=engine
    )
    ability_mechanics.store_rewind_snapshot(engine)
    player.health.current -= 50
    enemy.health.current = 1

    assert "previous choice point" in abilities.Rewind().cast(
        player, target=enemy, battle_engine=engine
    )
    assert player.health.current == player.health.max
    assert enemy.health.current == enemy.health.max


def test_exploration_spells_affect_fire_path_and_wall_movement():
    player = TestGameState.create_player(class_name="Seeker", level=20)
    game = SimpleNamespace(player_char=player, _random_combat=False)
    player.location_x = 0
    player.location_y = 0
    player.location_z = 0
    player.world_dict = {
        (0, 0, 0): map_tiles.CavePath(0, 0, 0),
        (1, 0, 0): map_tiles.Wall(1, 0, 0),
    }

    assert "rises" in abilities.Volitation().cast_out(player)
    health = player.health.current
    map_tiles.FirePath(0, 0, 0).modify_player(game)
    assert player.health.current == health

    assert "stone" in abilities.EnterWall().cast_out(player)
    assert player.move(1, 0) is True
    assert (player.location_x, player.location_y) == (1, 0)


def test_steal_spell_2_learns_spell_without_scroll(monkeypatch):
    player = TestGameState.create_player(class_name="Arcane Trickster", level=20)
    target = enemies.Goblin()
    target.spellbook["Spells"]["Firebolt"] = abilities.Firebolt()

    monkeypatch.setattr("src.core.abilities.random.random", lambda: 0.0)
    monkeypatch.setattr("src.core.abilities.random.choice", lambda values: values[0])

    message = abilities.StealSpell2().use(player, target)

    assert "permanently learns" in message
    assert "Firebolt" in [
        getattr(spell, "_class_name", spell.__class__.__name__)
        for spell in player.spellbook["Spells"].values()
    ]
    assert "Stolen Firebolt Scroll" not in player.inventory


def test_sheet_music_composes_and_performs_one_use_song():
    from src.core.classes import bard

    player = TestGameState.create_player(class_name="Bard", level=20)
    player.equipment["OffHand"] = items.Lute()

    success, message = bard.compose_sheet_music(player, "Battle Hymn")
    assert success is True
    assert "Sheet Music: Battle Hymn" in player.inventory
    sheet = player.inventory["Sheet Music: Battle Hymn"][0]

    use_message = sheet.use(player)

    assert "Song of Battle Hymn" in use_message
    assert "Sheet Music: Battle Hymn" not in player.inventory
    assert player.bard_song["active"] == "Battle Hymn"


def test_mastered_repertoire_is_available_through_the_combat_action():
    from src.core.classes import bard

    player = TestGameState.create_player(class_name="Troubadour", level=30)
    player.equipment["OffHand"] = items.Lute()
    promotion_kits.ensure_state(player)["bard_repertoire"]["Battle Hymn"]["known"] = True
    enemy = enemies.Goblin()
    tile = _Tile()
    tile.enemy = enemy
    engine = BattleEngine(player, enemy, tile)
    engine.attacker = player
    engine.defender = enemy

    assert "Repertoire" in engine._available_actions()
    result = engine.execute_intent(engine.prepare_intent("Repertoire", "Battle Hymn"))

    assert "spends 14 MP from mastered repertoire" in result.message
    assert player.mana.current == player.mana.max - 14
    assert bard.ensure_song_state(player)["active"] == "Battle Hymn"


def test_composable_song_effects_apply_in_combat_and_exploration(monkeypatch):
    from src.core.classes import bard

    player = TestGameState.create_player(class_name="Troubadour", level=30)
    player.equipment["OffHand"] = items.Lute()
    enemy = enemies.Goblin()
    tile = _Tile()
    tile.enemy = enemy
    engine = BattleEngine(player, enemy, tile)

    battle_hymn = items.BattleHymnSheet()
    player.modify_inventory(battle_hymn)
    assert "battle frenzy" in battle_hymn.use(player, target=enemy)
    assert player.status_effects["Berserk"].active is True
    assert enemy.status_effects["Berserk"].active is True

    player.status_effects["Berserk"].active = False
    ramparts = items.RampartsOdeSheet()
    player.modify_inventory(ramparts)
    message = ramparts.use(player, target=enemy)
    assert "raises" in message
    assert player.stat_effects["Defense"].active is True
    assert player.stat_effects["Magic Defense"].active is True

    symphony = items.DysfunctionSymphonySheet()
    player.modify_inventory(symphony)
    assert symphony.use(player, target=enemy)
    assert bard.active_exploration_effect(player) == "enemy_attack_down"
    engine.start_battle()
    assert enemy.stat_effects["Attack"].active is True
    assert enemy.stat_effects["Magic"].active is True

    player.bard_song = {"active": "Chorus Time", "turns": 3, "encore": None}
    engine.attacker = enemy
    engine.defender = player
    rolls = iter([100, 1])
    monkeypatch.setattr(
        "src.core.combat.battle_engine.random.randint", lambda _lo, _hi: next(rolls)
    )
    pre = engine.pre_turn()
    assert pre.can_act is False
    assert "Chorus Time" in pre.effects_text


def test_composition_requires_matching_instrument():
    from src.core.classes import bard

    player = TestGameState.create_player(class_name="Bard", level=20)
    player.equipment["OffHand"] = items.Lute()

    success, message = bard.compose_sheet_music(player, "Chorus Time")

    assert success is False
    assert "GrandPiano" in message
    assert "Sheet Music: Chorus Time" not in player.inventory


def test_class_power_ups_have_runtime_effects():
    from src.core.classes import grandmaster

    trickster = TestGameState.create_player(class_name="Arcane Trickster", level=30)
    trickster.spellbook["Skills"]["Trickster's Gambit"] = abilities.TrickstersGambit()
    trickster.class_effects["Power Up"].active = True
    trickster.class_effects["Power Up"].duration = 3
    trickster.power_up = True
    assert trickster.check_mod("magic") > TestGameState.create_player(
        class_name="Arcane Trickster", level=30
    ).check_mod("magic")
    assert trickster.critical_chance("Weapon") > 0

    archdruid = TestGameState.create_player(class_name="Archdruid", level=30)
    archdruid.spellbook["Skills"]["Primal Ascendance"] = abilities.PrimalAscendance()
    archdruid.class_effects["Power Up"].active = True
    archdruid.class_effects["Power Up"].duration = 3
    archdruid.power_up = True
    base_heal = TestGameState.create_player(class_name="Archdruid", level=30).check_mod("heal")
    assert archdruid.check_mod("heal") > base_heal

    demonologist = TestGameState.create_player(class_name="Demonologist", level=30)
    demonologist.spellbook["Skills"]["Abyssal Covenant"] = abilities.AbyssalCovenant()
    demonologist.class_effects["Power Up"].active = True
    demonologist.class_effects["Power Up"].duration = 3
    demonologist.power_up = True
    assert demonologist.check_mod("magic") > TestGameState.create_player(
        class_name="Demonologist", level=30
    ).check_mod("magic")

    grandmaster_pc = TestGameState.create_player(class_name="Grandmaster of Arms", level=30)
    grandmaster_pc.spellbook["Skills"]["Arsenal Mastery"] = abilities.ArsenalMastery()
    grandmaster_pc.power_up = True
    grandmaster_pc.class_effects["Power Up"].active = True
    grandmaster_pc.class_effects["Power Up"].duration = 3
    state = grandmaster.default_state()
    state["disciplines"]["Sword"]["xp"] = 500
    state["disciplines"]["Sword"]["rank"] = 10
    grandmaster_pc.grandmaster_discipline = state
    assert grandmaster_pc.check_mod("weapon") > TestGameState.create_player(
        class_name="Grandmaster of Arms", level=30
    ).check_mod("weapon")

    hierophant = TestGameState.create_player(class_name="Hierophant", level=30)
    hierophant.equipment["Weapon"] = items.Quarterstaff()
    hierophant.spellbook["Skills"]["Sacred Overchannel"] = abilities.SacredOverchannel()
    hierophant.power_up = True
    hierophant.class_effects["Power Up"].active = True
    hierophant.class_effects["Power Up"].duration = 3
    base_hierophant = TestGameState.create_player(class_name="Hierophant", level=30)
    base_hierophant.equipment["Weapon"] = items.Quarterstaff()
    assert hierophant.check_mod("magic") > base_hierophant.check_mod("magic")
    assert hierophant.check_mod("heal") > base_hierophant.check_mod("heal")


def test_hierophant_power_core_grants_sacred_overchannel():
    player = TestGameState.create_player(class_name="Hierophant", level=30)
    events = []

    message = player.special_power(
        SimpleNamespace(special_event=lambda event: events.append(event))
    )

    assert events == ["Power Up"]
    assert "Sacred Overchannel" in player.spellbook["Skills"]
    assert player.power_up is True
    assert "Sacred Overchannel" in message


def test_every_terminal_class_can_claim_its_power_core_reward_without_game_adapter():
    expected_powers = {
        "Berserker": "Blood Rage",
        "Grandmaster of Arms": "Arsenal Mastery",
        "Crusader": "Divine Aegis",
        "Dragoon": "Draconic Onslaught",
        "Stalwart Defender": "Shield Mastery",
        "Wizard": "Spell Mastery",
        "Shadowcaster": "Shade of Ahool",
        "Demonologist": "Abyssal Covenant",
        "Knight Enchanter": "Arcane Blast",
        "Thaumaturgist": "Eternal Conduit",
        "Rogue": "Stroke of Luck",
        "Seeker": "Eyes of the Unseen",
        "Ninja": "Blade of Fatalities",
        "Arcane Trickster": "Trickster's Gambit",
        "Hierophant": "Sacred Overchannel",
        "Templar": "Holy Retribution",
        "Archbishop": "Great Gospel",
        "Master Monk": "Dim Mak",
        "Troubadour": "Melody of Inspiration",
        "Archdruid": "Primal Ascendance",
        "Lycan": "Lunar Frenzy",
        "Astromancer": "Astral Judgment",
        "Soulcatcher": "Soul Harvest",
        "Beast Master": "Pack Bond",
    }

    for class_name, ability_name in expected_powers.items():
        player = TestGameState.create_player(class_name=class_name, level=60)

        message = player.special_power()

        assert message == f"You gain the skill {ability_name}.\n", class_name
        assert ability_name in player.spellbook["Skills"], class_name
        assert player.power_up is True, class_name


def test_passive_power_ups_support_defender_troubadour_and_beast_master():
    defender = TestGameState.create_player(class_name="Stalwart Defender", level=30)
    defender.spellbook["Skills"]["Shield Mastery"] = abilities.ShieldMastery()
    defender.power_up = True
    assert defender.check_mod("shield") >= 25

    troubadour = TestGameState.create_player(class_name="Troubadour", level=30, stats={"dex": 40})
    troubadour.spellbook["Skills"]["Melody of Inspiration"] = abilities.MelodyInspiration()
    troubadour.power_up = True
    base_speed = TestGameState.create_player(
        class_name="Troubadour", level=30, stats={"dex": 40}
    ).check_mod("speed")
    assert troubadour.check_mod("speed") > base_speed

    beast = TestGameState.create_player(class_name="Beast Master", level=30)
    beast.spellbook["Skills"]["Pack Bond"] = abilities.PackBond()
    beast.power_up = True
    beast.familiar = SimpleNamespace(
        is_alive=lambda: True, health=SimpleNamespace(current=10, max=20)
    )
    base_weapon = TestGameState.create_player(class_name="Beast Master", level=30).check_mod(
        "weapon"
    )
    assert beast.check_mod("weapon") > base_weapon


def test_bad_breath_applies_enemy_only_status_package():
    user = enemies.Basilisk()
    target = TestGameState.create_player(class_name="Warrior", level=10)

    message = abilities.BadBreath().use(user, target)

    assert "poison" in message.lower()
    assert target.status_effects["Poison"].active is True
    assert target.status_effects["Blind"].active is True
    assert target.status_effects["Silence"].active is True
