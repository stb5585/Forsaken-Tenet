"""Focused coverage for Thaumaturgist invocations and Conduit Command."""

from types import SimpleNamespace

import pytest

from src.core import abilities, companions, enemies, items
from src.core.classes import class_rings, promotion_kits
from src.core.combat.battle_engine import BattleEngine
from src.core.save_system import PlayerDataSerializer
from tests.test_framework import TestGameState


class _CombatTile:
    def available_actions(self, _player):
        return ["Attack", "Defend", "Recall", "Use Skill"]


def _thaumaturgist(*, health=(1000, 500), mana=(1000, 1000)):
    return TestGameState.create_player(
        name="Invoker",
        class_name="Thaumaturgist",
        race_name="Human",
        level=90,
        health=health,
        mana=mana,
    )


@pytest.mark.parametrize(
    ("summon_name", "expected_type", "rider_text"),
    (
        ("Hodag", "Physical", "strengthens Invoker's Attack"),
        ("Caladrius", "Holy", "restores"),
        ("Patagon", "Physical/Earth", "suppresses Goblin's Attack"),
        ("Dilong", "Earth", "erodes Goblin's Defense"),
        ("Agloolik", "Ice", "strengthens Invoker's Defense"),
        ("Cacus", "Fire", "burning pressure"),
        ("Izulu", "Electric", "siphons"),
        ("Hala", "Wind", "Invoker's Speed"),
        ("Lamashtu", "Shadow", "Curse of Umbra"),
        ("Seraphim", "Holy", "restores"),
        ("Bardi", "Shadow", "blinds Goblin"),
        ("Kobalos", "Physical/Poison", "Invoker's evasion"),
        ("Tiamat", "Water", "erodes Goblin's Defense"),
        ("Zahhak", "Arcane", "Magic Defense"),
    ),
)
def test_all_fourteen_invocations_use_authored_types_and_riders(
    monkeypatch,
    summon_name,
    expected_type,
    rider_text,
):
    player = _thaumaturgist()
    target = enemies.Goblin()
    target.health.max = 100_000
    target.health.current = target.health.max
    promotion_kits.ensure_state(player)["summon_bonds"][summon_name] = 50
    monkeypatch.setattr(
        "src.core.classes.promotion_kits.companions.random.random",
        lambda: 0.0,
    )

    message = promotion_kits.invoke_summon(player, target, summon_name)

    assert f"invokes {summon_name}" in message
    assert expected_type in message
    assert rider_text in message
    assert target.health.current < target.health.max


def test_invocations_include_hodag_and_caladrius_in_the_class_catalog():
    from src.core.abilities.catalog import skill_dict

    names = {ability().name for ability in skill_dict["Thaumaturgist"]["1"]}

    assert "Invoke Hodag" in names
    assert "Invoke Caladrius" in names
    assert len({name for name in names if name.startswith("Invoke ")}) == 14


def test_invocation_requires_conduit_target_and_mp():
    player = _thaumaturgist(mana=(20, 0))
    target = enemies.Goblin()

    assert "has not entrusted" in promotion_kits.invoke_summon(
        player,
        target,
        "Hodag",
    )
    promotion_kits.ensure_state(player)["summon_bonds"]["Hodag"] = 50
    assert "no invocation target" in promotion_kits.invoke_summon(player, None, "Hodag")
    assert "Not enough MP" in promotion_kits.invoke_summon(player, target, "Hodag")


def test_conduit_milestone_grants_the_matching_owner_invocation():
    player = _thaumaturgist()

    promotion_kits.gain_summon_bond(player, "Hodag", 49, "test")
    assert "Invoke Hodag" not in player.spellbook["Skills"]
    promotion_kits.gain_summon_bond(player, "Hodag", 1, "test")

    assert isinstance(player.spellbook["Skills"]["Invoke Hodag"], abilities.InvokeHodag)


def test_load_repairs_an_invocation_earned_by_persistent_conduit_progress():
    player = _thaumaturgist()
    promotion_kits.ensure_state(player)["summon_bonds"]["Caladrius"] = 50
    player.spellbook["Skills"].pop("Invoke Caladrius", None)

    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(player),
        skip_tiles=True,
    )

    assert isinstance(
        restored.spellbook["Skills"]["Invoke Caladrius"],
        abilities.InvokeCaladrius,
    )


def test_invocation_damage_uses_typed_resistance():
    player = _thaumaturgist()
    promotion_kits.ensure_state(player)["summon_bonds"]["Dilong"] = 50
    unresisted = enemies.Goblin()
    resisted = enemies.Goblin()
    for target in (unresisted, resisted):
        target.health.max = 100_000
        target.health.current = target.health.max
    unresisted.resistance["Earth"] = 0.0
    resisted.resistance["Earth"] = 0.75

    promotion_kits.invoke_summon(player, unresisted, "Dilong")
    promotion_kits.invoke_summon(player, resisted, "Dilong")

    normal_damage = unresisted.health.max - unresisted.health.current
    resisted_damage = resisted.health.max - resisted.health.current
    assert 0 < resisted_damage < normal_damage


def test_caladrius_invocation_cleanses_one_ordinary_status():
    player = _thaumaturgist()
    target = enemies.Goblin()
    target.health.max = 100_000
    target.health.current = target.health.max
    poison = player.status_effects["Poison"]
    blind = player.status_effects["Blind"]
    poison.active = True
    poison.duration = 3
    blind.active = True
    blind.duration = 3
    promotion_kits.ensure_state(player)["summon_bonds"]["Caladrius"] = 50

    message = promotion_kits.invoke_summon(player, target, "Caladrius")

    assert "cleanses" in message
    assert sum(effect.active for effect in (poison, blind)) == 1


def _active_hodag_engine(monkeypatch):
    player = _thaumaturgist()
    player.spellbook["Skills"]["Conduit Command"] = abilities.ConduitCommand()
    assert companions.choose_xenid(player, "Animal", "Hodag")[0]
    promotion_kits.ensure_state(player)["summon_bonds"]["Hodag"] = 50
    companions.sync_xenid_conduit(player, "Hodag", 50)
    target = enemies.Goblin()
    target.health.max = 1000
    target.health.current = 1000
    engine = BattleEngine(player, target, _CombatTile())
    engine.attacker = player
    engine.defender = target
    summoned = engine.execute_intent(engine.prepare_intent("Summon", "Hodag"))
    assert summoned.summon_started
    monkeypatch.setattr("src.core.combat.battle_engine.actions.random.randint", lambda _a, _b: 1)
    return engine, player, player.summons["Hodag"], target


def test_command_is_consumed_by_next_xenid_hit_and_adds_final_damage(monkeypatch):
    engine, player, hodag, target = _active_hodag_engine(monkeypatch)
    primed = engine.execute_summoner_support_action(
        "Use Skill",
        "Conduit Command",
    )
    assert "empowers" in primed.message

    def weapon_damage(defender, **_kwargs):
        defender.health.current -= 40
        hodag._last_weapon_primary_damage = 40
        hodag._last_weapon_primary_damage_instances = [40]
        return "Hodag hits for 40 damage.\n", True, 1

    monkeypatch.setattr(hodag, "weapon_damage", weapon_damage)
    result = engine.execute_intent(engine.prepare_intent("Attack"))

    assert target.health.current == 950
    assert "Conduit Command adds 10 damage" in result.message
    assert promotion_kits.combat_state(player)["conduit_command"] is False


def test_command_consumes_on_miss_or_non_damage_action(monkeypatch):
    engine, player, hodag, target = _active_hodag_engine(monkeypatch)
    engine.execute_summoner_support_action("Use Skill", "Conduit Command")

    def missed_attack(_defender, **_kwargs):
        hodag._last_weapon_primary_damage = 0
        hodag._last_weapon_primary_damage_instances = []
        return "Hodag misses.\n", False, 1

    monkeypatch.setattr(hodag, "weapon_damage", missed_attack)
    missed = engine.execute_intent(engine.prepare_intent("Attack"))
    assert "is consumed" in missed.message
    assert target.health.current == target.health.max

    engine.execute_summoner_support_action("Use Skill", "Conduit Command")
    defended = engine.execute_intent(engine.prepare_intent("Defend"))
    assert "is consumed" in defended.message
    assert promotion_kits.combat_state(player)["conduit_command"] is False


def test_command_enhances_healing_and_true_name_is_ring_only():
    player = _thaumaturgist()
    hodag = companions.Hodag()
    hodag.initialize_stats(player)
    player.summons["Hodag"] = hodag
    player.active_summon_name = "Hodag"
    promotion_kits.ensure_state(player)["summon_bonds"]["Hodag"] = 100
    hodag.health.current = 100
    assert "empowers" in promotion_kits.conduit_command(player)
    payoff = promotion_kits.begin_conduit_payoff(player, hodag, "Cast Spell", hodag)
    hodag.health.current += 40

    message = promotion_kits.finish_conduit_payoff(player, hodag, hodag, payoff)

    assert hodag.health.current == 150
    assert "additional HP" in message
    assert "True Name" not in message

    player.equipment["Ring"] = items.ClassRing()
    class_rings.ensure_state(player)["awakened"]["Thaumaturgist"] = True
    hodag.health.current = 100
    promotion_kits.conduit_command(player)
    payoff = promotion_kits.begin_conduit_payoff(player, hodag, "Defend", hodag)
    message = promotion_kits.finish_conduit_payoff(player, hodag, hodag, payoff)

    assert "True Name answers" in message
    assert hodag.stat_effects["Attack"].active


@pytest.mark.parametrize("reason", ("is recalled", "falls", "leaves combat"))
def test_command_cleanup_reports_its_lifecycle_reason(reason):
    player = _thaumaturgist()
    hodag = companions.Hodag()
    hodag.initialize_stats(player)
    player.summons["Hodag"] = hodag
    player.active_summon_name = "Hodag"
    promotion_kits.conduit_command(player)

    message = promotion_kits.clear_conduit_command(player, reason)

    assert reason in message
    assert promotion_kits.combat_state(player)["conduit_command"] is False


def test_recall_death_and_combat_end_use_command_cleanup_hooks(monkeypatch):
    engine, player, hodag, _target = _active_hodag_engine(monkeypatch)
    engine.execute_summoner_support_action("Use Skill", "Conduit Command")
    recalled = engine.execute_intent(engine.prepare_intent("Recall"))
    assert "expires" in recalled.message

    player.active_summon_name = "Hodag"
    hodag.health.current = max(1, hodag.health.max)
    promotion_kits.conduit_command(player)
    death = promotion_kits.record_xenid_death(player, "Hodag")
    assert "falls" in death

    promotion_kits.combat_state(player)["fallen_xenid"] = None
    promotion_kits.combat_state(player)["fallen_xenid_conduit_loss"] = 0
    promotion_kits.conduit_command(player)
    ended = promotion_kits.end_combat(player)
    assert "leaves combat" in ended


def test_command_rejects_a_non_xenid_familiar():
    player = _thaumaturgist()
    player.familiar = SimpleNamespace(is_alive=lambda: True)

    assert "active living Xenid" in promotion_kits.conduit_command(player)
