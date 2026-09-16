#!/usr/bin/env python3
"""Focused regression coverage for the UI-agnostic battle engine."""

from __future__ import annotations

from types import SimpleNamespace

from src.core import abilities, items
from src.core.classes import class_rings, promotion_kits
from src.core.combat.battle_engine import STOLEN_SCROLL_CHOICE_PREFIX, BattleEngine
from src.core.combat.targeting import TargetScope
from src.core.data.data_driven_abilities import DataDrivenSpell
from src.core.enemies import Barghest, Goblin, GuildArcaneBoss
from src.core.player import REALM_OF_CAMBION_LEVEL
from tests.test_framework import TestGameState


class DummyCombatTile:
    def available_actions(self, _player):
        return ["Attack"]


def _make_engine_with_player_attacking():
    player = TestGameState.create_player(name="TestHero", class_name="Warrior", race_name="Human")
    enemy = Goblin()
    engine = BattleEngine(player, enemy, DummyCombatTile())
    engine.attacker = player
    engine.defender = enemy
    return engine, player


def test_pre_start_action_scope_uses_player_ability_owner():
    """Interface projections may query ability scope before initiative starts."""
    player = TestGameState.create_player(name="TestHero", class_name="Wizard", race_name="Human")
    player.spellbook["Spells"]["Firebolt"] = abilities.Firebolt()
    engine = BattleEngine(player, Goblin(), DummyCombatTile())

    assert engine.attacker is None
    assert engine.target_scope_for_action("Cast Spell", "Firebolt") is TargetScope.SINGLE_ENEMY


def test_start_battle_clears_stale_cambion_anti_magic_outside_realm():
    player = TestGameState.create_player(name="TestHero", class_name="Warrior", race_name="Human")
    player.location_z = 1
    player.anti_magic_active = True

    BattleEngine(player, Goblin(), DummyCombatTile()).start_battle()

    assert player.anti_magic_active is False


def test_cambion_anti_magic_suppresses_player_and_enemy_abilities():
    player = TestGameState.create_player(name="TestHero", class_name="Warrior", race_name="Human")
    player.location_z = REALM_OF_CAMBION_LEVEL
    player.anti_magic_active = True
    player.spellbook["Skills"]["Rally"] = abilities.Rally()
    enemy = Goblin()
    enemy.spellbook["Spells"]["Firebolt"] = abilities.Firebolt()
    engine = BattleEngine(player, enemy, DummyCombatTile())

    engine.start_battle()

    assert player.anti_magic_active is True
    assert enemy.anti_magic_active is True
    engine.attacker = player
    engine.defender = enemy
    assert "anti-magic field" in engine._execute_skill("Rally").lower()
    engine.attacker = enemy
    engine.defender = player
    assert "anti-magic field" in engine._execute_spell("Firebolt").lower()


def test_start_battle_encumbered_player_loses_initiative():
    """Encumbrance must override virtual-readiness initiative jitter."""
    player = TestGameState.create_player(name="TestHero", class_name="Warrior", race_name="Human")
    player.encumbered = True
    enemy = Goblin()

    first, second = BattleEngine(player, enemy, DummyCombatTile()).start_battle()

    assert first is enemy
    assert second is player


def test_enemy_sleeping_powder_bypasses_required_monocane_inventory():
    player = TestGameState.create_player(name="TestHero", class_name="Warrior", race_name="Human")
    enemy = Goblin()
    enemy.mana.current = 100
    enemy.spellbook["Skills"]["Sleeping Powder"] = abilities.SleepingPowder()
    engine = BattleEngine(player, enemy, DummyCombatTile())
    engine.attacker = enemy
    engine.defender = player

    result = engine.execute_action("Use Skill", "Sleeping Powder")

    assert "does not have a Monocane" not in result.message
    assert "uses Sleeping Powder" in result.message


def test_player_sleeping_powder_still_requires_monocane_inventory():
    player = TestGameState.create_player(name="TestHero", class_name="Warrior", race_name="Human")
    player.mana.current = 100
    player.spellbook["Skills"]["Sleeping Powder"] = abilities.SleepingPowder()
    enemy = Goblin()
    engine = BattleEngine(player, enemy, DummyCombatTile())
    engine.attacker = player
    engine.defender = enemy

    result = engine.execute_action("Use Skill", "Sleeping Powder")

    assert "Monocane is required." in result.message


def test_familiar_sleeping_powder_bypasses_required_monocane_inventory():
    player = TestGameState.create_player(name="TestHero", class_name="Warrior", race_name="Human")
    target = Goblin()
    skill = abilities.SleepingPowder()

    message = skill.use(player, target=target, fam=True)

    assert "does not have a Monocane" not in message


class FakeJumpSkill:
    name = "Jump"
    cost = 0

    def __init__(self, *, unstoppable: bool = False):
        self.charging = True
        self.modifications = {"Unstoppable": unstoppable}
        self.use_calls = 0

    def get_charge_time(self):
        return 1

    def use(self, _user, target=None):
        self.use_calls += 1
        self.charging = False
        return f"Jump hits {target.name}.\n"

    def cancel_charge(self, _user):
        self.charging = False
        return "Jump was cancelled.\n"


class FakeChargingJumpSkill(FakeJumpSkill):
    def __init__(self):
        super().__init__()
        self.charging = False

    def use(self, _user, target=None):
        self.use_calls += 1
        self.charging = True
        return "TestHero is coiling their legs, preparing to leap into the air!\n"


class FakeContinuingJumpSkill(FakeJumpSkill):
    def __init__(self):
        super().__init__()
        self.charge_turns = 2

    def get_charge_time(self):
        return 2

    def use(self, _user, target=None):
        self.use_calls += 1
        self.charge_turns -= 1
        return "TestHero continues to gather power... (1 turn remaining)\n"


def test_pre_turn_duration_one_stun_still_skips_current_turn():
    engine, player = _make_engine_with_player_attacking()
    player.status_effects["Stun"].active = True
    player.status_effects["Stun"].duration = 1

    result = engine.pre_turn()

    assert result.can_act is False
    assert result.inactive_reason == ""
    assert "no longer stunned" in result.effects_text
    assert player.status_effects["Stun"].active is False


def test_resolve_skill_ignores_silence_and_spends_resolve():
    engine, player = _make_engine_with_player_attacking()
    player.cls = SimpleNamespace(name="Sentinel")
    player.equipment["OffHand"] = SimpleNamespace(subtyp="Shield")
    player.spellbook["Skills"]["Brace Wall"] = abilities.BraceWall()
    class_rings.ensure_state(player)["data"]["Stalwart Defender"]["guard_meter"] = 15
    player.abilities_suppressed = lambda: True

    result = engine.execute_action("Use Skill", "Brace Wall")

    assert "cannot use skills because of silence" not in result.message
    assert "uses Brace Wall" in result.message
    assert "spends 15 Resolve on Brace Wall" in result.message
    assert promotion_kits.current_resolve(player) == 0


def test_zero_mana_skill_ignores_silence_but_mana_skill_does_not():
    engine, player = _make_engine_with_player_attacking()
    player.status_effects["Silence"].active = True
    player.spellbook["Skills"]["Free Technique"] = SimpleNamespace(
        name="Free Technique",
        cost=0,
        passive=False,
        use=lambda _user, target=None: f"{target.name} is pressured.\n",
    )
    player.spellbook["Skills"]["Mana Technique"] = SimpleNamespace(
        name="Mana Technique",
        cost=3,
        passive=False,
        use=lambda _user, target=None: f"{target.name} is struck.\n",
    )

    free_result = engine.execute_action("Use Skill", "Free Technique")
    mana_result = engine.execute_action("Use Skill", "Mana Technique")

    assert "uses Free Technique" in free_result.message
    assert "Goblin is pressured" in free_result.message
    assert "cannot use skills because of silence" in mana_result.message


def test_pre_turn_duration_one_sleep_still_skips_current_turn():
    engine, player = _make_engine_with_player_attacking()
    player.status_effects["Sleep"].active = True
    player.status_effects["Sleep"].duration = 1

    result = engine.pre_turn()

    assert result.can_act is False
    assert result.inactive_reason == ""
    assert "no longer asleep" in result.effects_text
    assert player.status_effects["Sleep"].active is False


def test_pre_turn_prone_recovery_still_skips_current_turn(monkeypatch):
    engine, player = _make_engine_with_player_attacking()
    player.physical_effects["Prone"].active = True
    player.physical_effects["Prone"].duration = 1
    monkeypatch.setattr("src.core.character.random.randint", lambda *_args: 0)

    result = engine.pre_turn()

    assert result.can_act is False
    assert result.inactive_reason == ""
    assert "no longer prone" in result.effects_text
    assert player.physical_effects["Prone"].active is False


def test_pre_turn_stun_cancels_pending_jump():
    engine, player = _make_engine_with_player_attacking()
    jump = FakeJumpSkill()
    player.spellbook["Skills"] = {"Jump": jump}
    player.class_effects["Jump"].active = True
    player.status_effects["Stun"].active = True
    player.status_effects["Stun"].duration = 2

    result = engine.pre_turn()

    assert result.can_act is False
    assert "Jump" in result.effects_text
    assert jump.charging is False
    assert player.class_effects["Jump"].active is False
    assert "stunned" in result.inactive_reason


def test_start_battle_clears_stale_saved_jump_charge():
    engine, player = _make_engine_with_player_attacking()
    jump = FakeContinuingJumpSkill()
    player.spellbook["Skills"] = {"Jump": jump}
    player.class_effects["Jump"].active = True

    engine.start_battle()

    assert jump.charging is False
    assert jump.charge_turns == 0
    assert player.class_effects["Jump"].active is False


def test_start_battle_records_bestiary_encounter():
    engine, player = _make_engine_with_player_attacking()

    engine.start_battle()

    record = player.bestiary["Goblin"]
    assert record["name"] == "Goblin"
    assert record["type"] == "Humanoid"
    assert record["seen_count"] == 1
    assert record["details_unlocked"] is False
    assert "resistances" not in record


def test_shapeshifted_barghest_victory_credits_original_enemy(monkeypatch):
    player = TestGameState.create_player(
        name="Kongol", class_name="Warrior", race_name="Half Giant"
    )
    enemy = Barghest()
    engine = BattleEngine(player, enemy, DummyCombatTile())
    player.quest_dict = {
        "Bounty": {},
        "Main": {
            "Cry Havoc!": {
                "Type": "Defeat",
                "What": "Barghest",
                "Total": 1,
                "Completed": False,
            }
        },
        "Side": {},
    }
    monkeypatch.setattr(
        player, "loot", lambda defeated_enemy, _tile: f"{defeated_enemy.name} dropped loot.\n"
    )

    engine.start_battle()
    enemy.name = "Direwolf"
    enemy.enemy_typ = "Animal"

    msg = engine._process_victory()

    assert player.bestiary["Barghest"]["seen_count"] == 1
    assert player.kill_dict["Fiend"]["Barghest"] == 1
    assert "Direwolf" not in player.kill_dict.get("Animal", {})
    assert player.quest_dict["Main"]["Cry Havoc!"]["Completed"] is True
    assert "Barghest dropped loot" in msg


def test_thieves_guild_trial_victory_uses_guild_wording_and_awards_signet():
    player = TestGameState.create_player(
        name="Shade", class_name="Spell Stealer", race_name="Human"
    )
    enemy = GuildArcaneBoss()
    engine = BattleEngine(player, enemy, DummyCombatTile())

    outcome = engine.end_battle()

    assert outcome.result == "victory"
    assert "Class Ring" not in outcome.message
    assert "Spell-Sealed Cutpurse" in outcome.message
    assert "Thieves Guild Signet" in outcome.message
    assert "Thieves Guild Signet" in player.special_inventory


def test_boss_battle_blocks_enemy_detail_vision():
    engine, player = _make_engine_with_player_attacking()
    player.cls.name = "Seeker"
    engine.boss = True

    assert engine.player_has_sight() is True
    assert engine.show_enemy_details() is False


def test_initial_jump_charge_omits_generic_uses_line():
    engine, player = _make_engine_with_player_attacking()
    jump = FakeChargingJumpSkill()
    player.spellbook["Skills"] = {"Jump": jump}

    result = engine.execute_action("Use Skill", "Jump")

    assert "uses Jump" not in result.message
    assert "coiling their legs" in result.message
    assert jump.charging is True


def test_continuing_jump_charge_omits_generic_uses_line():
    engine, player = _make_engine_with_player_attacking()
    jump = FakeContinuingJumpSkill()
    player.spellbook["Skills"] = {"Jump": jump}
    player.class_effects["Jump"].active = True

    result = engine.execute_action("Use Skill", "Jump")

    assert "uses Jump" not in result.message
    assert "continues to gather power" in result.message
    assert jump.charging is True


def test_charging_skill_forced_action_takes_priority_over_berserk():
    engine, player = _make_engine_with_player_attacking()
    charge = FakeJumpSkill()
    charge.name = "Dragon Breath (Fire)"
    player.spellbook["Skills"] = {"Dragon Breath (Fire)": charge}
    player.status_effects["Berserk"].active = True

    forced = engine.get_forced_action()

    assert forced is not None
    assert forced.action == "Use Skill"
    assert forced.choice == "Dragon Breath (Fire)"


def test_forced_berserk_action_cannot_be_bypassed_by_a_direct_intent():
    engine, player = _make_engine_with_player_attacking()
    player.status_effects["Berserk"].active = True

    blocked = engine.execute_action("Defend")

    assert blocked.committed is False
    assert blocked.validation_code.name == "FORCED_ACTION_REQUIRED"
    assert "forced action: Attack" in blocked.message


def test_forced_jump_cannot_be_bypassed_by_a_direct_intent():
    engine, player = _make_engine_with_player_attacking()
    jump = FakeJumpSkill()
    player.spellbook["Skills"] = {"Jump": jump}
    player.class_effects["Jump"].active = True

    blocked = engine.execute_action("Attack")
    resolved = engine.execute_action("Use Skill", "Jump")

    assert blocked.committed is False
    assert blocked.validation_code.name == "FORCED_ACTION_REQUIRED"
    assert "Jump hits" in resolved.message


def test_forced_cancellation_remains_enforceable_after_its_charge_is_cleared():
    engine, player = _make_engine_with_player_attacking()
    jump = FakeJumpSkill()
    player.spellbook["Skills"] = {"Jump": jump}
    player.class_effects["Jump"].active = True
    player.incapacitated = lambda: True

    blocked = engine.execute_action("Attack")
    cancelled = engine.execute_action("Cancelled")

    assert blocked.committed is False
    assert blocked.validation_code.name == "FORCED_ACTION_REQUIRED"
    assert jump.charging is False
    assert cancelled.committed is True


def test_resolved_jump_clears_forced_action_and_returns_control():
    engine, player = _make_engine_with_player_attacking()
    jump = FakeJumpSkill()
    player.spellbook["Skills"] = {"Jump": jump}
    player.class_effects["Jump"].active = True

    forced = engine.get_forced_action()
    assert forced is not None
    assert forced.action == "Use Skill"
    assert forced.choice == "Jump"

    result = engine.execute_action(forced.action, forced.choice)

    assert "Jump hits" in result.message
    assert jump.use_calls == 1
    assert jump.charging is False
    assert player.class_effects["Jump"].active is False
    assert engine.get_forced_action() is None


def test_unstoppable_jump_resolves_before_berserk_forced_attack():
    engine, player = _make_engine_with_player_attacking()
    jump = FakeJumpSkill(unstoppable=True)
    player.spellbook["Skills"] = {"Jump": jump}
    player.class_effects["Jump"].active = True
    player.status_effects["Berserk"].active = True
    player.status_effects["Berserk"].duration = 2

    forced = engine.get_forced_action()

    assert forced is not None
    assert forced.action == "Use Skill"
    assert forced.choice == "Jump"


def test_execute_spell_accepts_data_driven_spell_with_engine_context():
    engine, player = _make_engine_with_player_attacking()
    spell = DataDrivenSpell(
        name="Test Flame",
        description="A regression spell.",
        cost=0,
        dmg_mod=1,
        crit=999,
        subtyp="Fire",
    )
    player.spellbook["Spells"] = {"Test Flame": spell}

    result = engine.execute_action("Cast Spell", "Test Flame")

    assert "TestHero casts Test Flame" in result.message


def test_natural_damaging_spell_releases_stolen_charge_once_per_action():
    player = TestGameState.create_player(
        name="TestHero",
        class_name="Spell Stealer",
        race_name="Human",
    )
    enemy = Goblin()
    enemy.health.current = enemy.health.max = 500
    engine = BattleEngine(player, enemy, DummyCombatTile())
    engine.attacker = player
    engine.defender = enemy
    spell = DataDrivenSpell(
        name="Certain Flame",
        description="A stolen-magic integration test.",
        cost=0,
        dmg_mod=1,
        crit=999,
        subtyp="Fire",
    )
    player.spellbook["Spells"] = {spell.name: spell}
    promotion_kits.combat_state(player)["stolen_charge"] = 2
    enemy.status_effects["Sleep"].active = True

    result = engine.execute_action("Cast Spell", spell.name)

    assert result.message.count("commits 2 Stolen Charge") == 1
    assert result.message.count("Stolen Charge releases") == 1
    assert promotion_kits.combat_state(player)["stolen_charge"] == 0


def test_steal_as_well_stolen_scroll_cast_grants_charge_but_item_theft_does_not():
    player = TestGameState.create_player(
        name="TestHero",
        class_name="Spell Stealer",
        race_name="Human",
    )
    enemy = Goblin()
    enemy.health.current = enemy.health.max = 500
    engine = BattleEngine(player, enemy, DummyCombatTile())
    engine.attacker = player
    engine.defender = enemy
    scroll = items.InscribedSpellScroll("Firebolt", charges=2)
    player.inventory[scroll.name] = [scroll]

    result = engine.execute_action("Steal As Well", scroll.name)

    assert "gains 1 Stolen Charge from stolen spell scroll" in result.message
    assert promotion_kits.combat_state(player)["stolen_charge"] == 1


def test_execute_spell_accepts_stolen_scroll_choice_token():
    player = TestGameState.create_player(
        name="TestHero", class_name="Spell Stealer", race_name="Human"
    )
    enemy = Goblin()
    engine = BattleEngine(player, enemy, DummyCombatTile())
    engine.attacker = player
    engine.defender = enemy
    scroll = items.InscribedSpellScroll("Firebolt", charges=2)
    player.inventory[scroll.name] = [scroll]

    result = engine.execute_action("Cast Spell", f"{STOLEN_SCROLL_CHOICE_PREFIX}{scroll.name}")

    assert f"TestHero uses {scroll.name}" in result.message
    assert "Stolen Charge" in result.message
    assert scroll.charges == 1


def test_execute_spell_consumes_stolen_scroll_when_charges_run_out():
    player = TestGameState.create_player(
        name="TestHero", class_name="Spell Stealer", race_name="Human"
    )
    enemy = Goblin()
    engine = BattleEngine(player, enemy, DummyCombatTile())
    engine.attacker = player
    engine.defender = enemy
    scroll = items.InscribedSpellScroll("Firebolt", charges=1)
    player.inventory[scroll.name] = [scroll]

    result = engine.execute_action("Cast Spell", f"{STOLEN_SCROLL_CHOICE_PREFIX}{scroll.name}")

    assert "crumbles to dust" in result.message
    assert scroll.name not in player.inventory


def test_execute_spell_rejects_non_stolen_scroll_choice_token():
    engine, player = _make_engine_with_player_attacking()
    player.inventory["Potion"] = [SimpleNamespace(name="Potion")]

    result = engine.execute_action("Cast Spell", f"{STOLEN_SCROLL_CHOICE_PREFIX}Potion")

    assert result.message == "Potion is not a stolen spell scroll.\n"


def test_execute_spell_still_casts_learned_spell_with_matching_scroll_inventory():
    engine, player = _make_engine_with_player_attacking()
    spell = abilities.Firebolt()
    player.spellbook["Spells"] = {"Firebolt": spell}
    player.inventory["Stolen Firebolt Scroll"] = [items.InscribedSpellScroll("Firebolt", charges=2)]

    result = engine.execute_action("Cast Spell", "Firebolt")

    assert "TestHero casts Firebolt" in result.message
    assert player.inventory["Stolen Firebolt Scroll"][0].charges == 2


def test_smoke_screen_requires_and_consumes_smoke_bomb():
    engine, player = _make_engine_with_player_attacking()
    player.spellbook["Skills"] = {"Smoke Screen": abilities.SmokeScreen()}
    player.flee = lambda _enemy, smoke=False: (True, "TestHero vanishes into smoke.\n")

    missing_result = engine.execute_action("Use Skill", "Smoke Screen")

    assert missing_result.message == "Smoke Screen requires a Smoke Bomb.\n"
    assert missing_result.fled is False

    player.inventory["Smoke Bomb"] = [items.SmokeBomb()]
    result = engine.execute_action("Use Skill", "Smoke Screen")

    assert "TestHero uses Smoke Screen." in result.message
    assert "A Smoke Bomb bursts open." in result.message
    assert "TestHero vanishes into smoke." in result.message
    assert "Smoke Bomb" not in player.inventory
    assert result.fled is True


def test_take_it_on_the_run_attempts_theft_after_smoke_escape(monkeypatch):
    engine, player = _make_engine_with_player_attacking()
    player.spellbook["Skills"] = {
        "Smoke Screen": abilities.SmokeScreen(),
        "Take It On the Run": abilities.TakeItOnTheRun(),
    }
    player.inventory["Smoke Bomb"] = [items.SmokeBomb()]
    player.flee = lambda _enemy, smoke=False: (True, "TestHero escapes.\n")
    engine.defender.sight = False

    class FakeSteal:
        def use(self, _user, _target):
            return SimpleNamespace(
                message="Take It On the Run steals 7 gold.\n",
                extra={"stolen_gold": 7},
            )

    monkeypatch.setattr("src.core.abilities.utility.Steal", FakeSteal)

    result = engine.execute_action("Use Skill", "Smoke Screen")

    assert result.fled is True
    assert "Take It On the Run steals 7 gold" in result.message
