"""Coverage for Diviner/Astromancer rune foundation mechanics."""

from __future__ import annotations

import pytest

from src.core import abilities, items
from src.core.classes import astromancer, promotion_kits
from src.core.combat.battle_engine import BattleEngine
from src.core.combat.combat_result import CombatResult
from src.core.save_system import PlayerDataSerializer
from tests.test_framework import TestGameState


class DummyCombatTile:
    def available_actions(self, _player):
        return ["Attack", "Cast Spell", "Use Skill", "Flee"]


def _make_engine(player, enemy):
    engine = BattleEngine(player, enemy, DummyCombatTile())
    engine.attacker = player
    engine.defender = enemy
    return engine


def test_diviner_rune_state_round_trips_through_save_serializer():
    player = TestGameState.create_player(class_name="Diviner", race_name="Human")
    astromancer.add_rune(player, "Ember", 2)
    astromancer.add_rune(player, "Tide", 5)

    data = PlayerDataSerializer.serialize(player)
    restored = PlayerDataSerializer.deserialize(data, skip_tiles=True)

    assert restored.astromancer_state["runes"]["Ember"] == 2
    assert restored.astromancer_state["runes"]["Tide"] == astromancer.RUNE_CAP


def test_rune_drop_chance_uses_active_sign_and_resistance_scaling():
    player = TestGameState.create_player(class_name="Astromancer", race_name="Human")
    spell = abilities.Firebolt()
    enemy = TestGameState.create_player(class_name="Warrior", race_name="Human")
    enemy.resistance["Fire"] = 0.25

    sign, chance = astromancer.rune_drop_chance(player, enemy, spell)

    assert sign == "Ember"
    assert chance == 0.375


def test_rune_drop_chance_weakness_scales_up():
    player = TestGameState.create_player(class_name="Diviner", race_name="Human")
    spell = abilities.Firebolt()
    enemy = TestGameState.create_player(class_name="Warrior", race_name="Human")
    enemy.resistance["Fire"] = -0.5

    sign, chance = astromancer.rune_drop_chance(player, enemy, spell)

    assert sign == "Ember"
    assert chance == 0.375


def test_runic_boost_consumes_rune_casts_spell_and_advances_astromancer_cycle(monkeypatch):
    player = TestGameState.create_player(
        class_name="Astromancer",
        race_name="Human",
        spells=["Firebolt"],
        mana=(100, 100),
    )
    enemy = TestGameState.create_player(class_name="Warrior", race_name="Human", health=(20, 20))
    enemy.dodge_chance = lambda *_args, **_kwargs: False
    player.hit_chance = lambda *_args, **_kwargs: True
    astromancer.add_rune(player, "Ember", 1)
    monkeypatch.setattr("src.core.classes.astromancer.random.random", lambda: 1.0)
    engine = _make_engine(player, enemy)

    result = engine.execute_intent(engine.prepare_intent("Runic Boost", "Firebolt"))

    assert "spends one Ember rune" in result.message
    assert player.astromancer_state["runes"]["Ember"] == 0
    assert enemy.health.current < 20
    assert astromancer.active_constellation(player) == "Tide"


def test_runic_boost_kill_can_award_rune(monkeypatch):
    player = TestGameState.create_player(
        class_name="Diviner",
        race_name="Human",
        spells=["Firebolt"],
        mana=(100, 100),
    )
    enemy = TestGameState.create_player(class_name="Warrior", race_name="Human", health=(1, 1))
    enemy.dodge_chance = lambda *_args, **_kwargs: False
    player.hit_chance = lambda *_args, **_kwargs: True
    astromancer.add_rune(player, "Ember", 1)
    monkeypatch.setattr("src.core.classes.astromancer.random.random", lambda: 0.0)
    engine = _make_engine(player, enemy)

    result = engine.execute_intent(engine.prepare_intent("Runic Boost", "Firebolt"))

    assert "claims an Ember rune" in result.message
    assert player.astromancer_state["runes"]["Ember"] == 1


def test_astral_judgment_kill_does_not_award_rune(monkeypatch):
    player = TestGameState.create_player(
        class_name="Astromancer",
        race_name="Human",
        skills=["Astral Judgment"],
        mana=(100, 100),
    )
    enemy = TestGameState.create_player(class_name="Warrior", race_name="Human", health=(1, 1))
    monkeypatch.setattr("src.core.classes.astromancer.random.random", lambda: 0.0)
    engine = _make_engine(player, enemy)

    result = engine.execute_intent(engine.prepare_intent("Use Skill", "Astral Judgment"))

    assert "Astral Judgment" in result.message
    assert player.astromancer_state["runes"]["Ember"] == 0


def test_class_ring_upgrades_active_sign_runic_boost_floor_only_when_equipped():
    player = TestGameState.create_player(class_name="Astromancer", race_name="Human")
    player.equipment["Ring"] = items.ClassRing()
    player.awaken_class_ring()

    assert astromancer.runic_boost_floor(player, "Ember") == 1.0

    player.equipment["Ring"] = items.NoRing()
    assert astromancer.runic_boost_floor(player, "Ember") == 0.75


def test_diviner_guaranteed_learning_uses_explicit_rank_metadata_and_fresh_instance():
    player = TestGameState.create_player(class_name="Diviner", race_name="Human")
    player.spellbook["Skills"]["Learn Spell"] = abilities.LearnSpell()
    witnessed = abilities.Aqualung()
    result = CombatResult(
        action="Aqualung",
        actor=object(),
        target=object(),
        hit=True,
        message="The spell resolves.",
    )

    message = astromancer.learn_witnessed_spell(player, witnessed, result)

    assert "learns Aqualung" in message
    assert player.spellbook["Spells"]["Aqualung"] is not witnessed
    assert astromancer.learn_witnessed_spell(player, witnessed, result) == ""
    assert astromancer.learn_witnessed_spell(player, abilities.Tornado(), result) == ""


def test_astromancer_learning_rejects_miss_rank_three_and_unranked_spell():
    player = TestGameState.create_player(class_name="Astromancer", race_name="Human")
    player.spellbook["Skills"]["Learn Spell"] = abilities.LearnSpell2()
    miss = CombatResult(action="Spell", actor=object(), target=object(), hit=False)
    success = CombatResult(action="Spell", actor=object(), target=object(), hit=True)

    assert astromancer.learn_witnessed_spell(player, abilities.Tornado(), miss) == ""
    assert astromancer.learn_witnessed_spell(player, abilities.PhotonSphere(), success) == ""
    assert astromancer.learn_witnessed_spell(player, abilities.Firebolt(), success) == ""
    assert "learns Tornado" in astromancer.learn_witnessed_spell(
        player,
        abilities.Tornado(),
        success,
    )


def test_witnessed_learning_includes_stupefy_and_volcano_at_authored_ranks():
    diviner = TestGameState.create_player(class_name="Diviner", race_name="Human")
    diviner.spellbook["Skills"]["Learn Spell"] = abilities.LearnSpell()
    astromancer_player = TestGameState.create_player(
        class_name="Astromancer",
        race_name="Human",
    )
    astromancer_player.spellbook["Skills"]["Learn Spell"] = abilities.LearnSpell2()
    success = CombatResult(action="Spell", actor=object(), target=object(), hit=True)

    assert abilities.Stupefy().rank == 1
    assert "learns Stupefy" in astromancer.learn_witnessed_spell(
        diviner,
        abilities.Stupefy(),
        success,
    )
    assert abilities.Volcano().rank == 2
    assert (
        astromancer.learn_witnessed_spell(
            diviner,
            abilities.Volcano(),
            success,
        )
        == ""
    )
    assert "learns Volcano" in astromancer.learn_witnessed_spell(
        astromancer_player,
        abilities.Volcano(),
        success,
    )


def test_thread_sources_dedupe_and_threaded_cast_spends_all_for_exact_bonuses():
    player = TestGameState.create_player(class_name="Astromancer", race_name="Human")
    promotion_kits.begin_action(player, action="Use Skill", choice="Foretell")
    astromancer.record_thread_action(player, "Foretell", successful=True)
    astromancer.record_thread_action(player, "Foretell", successful=True)
    promotion_kits.begin_action(player, action="Use Skill", choice="Twist Fate")
    astromancer.record_thread_action(player, "Twist Fate", successful=True)
    promotion_kits.begin_action(player, action="Use Skill", choice="Wormhole")
    astromancer.record_thread_action(player, "Wormhole", successful=True)

    assert promotion_kits.combat_state(player)["foresight_threads"] == 3
    assert "prepares Threaded Cast" in promotion_kits.threaded_cast(player)
    assert "already prepared" in promotion_kits.threaded_cast(player)
    spent, _message = astromancer.begin_threaded_spell(player, abilities.Firebolt())

    assert spent == 3
    assert astromancer.threaded_bonus(player, "accuracy") == pytest.approx(0.15)
    assert astromancer.threaded_bonus(player, "status") == pytest.approx(0.15)
    assert astromancer.threaded_bonus(player, "output") == pytest.approx(0.18)
    assert promotion_kits.combat_state(player)["foresight_threads"] == 0
    assert promotion_kits.combat_state(player)["threaded_cast_pending"] is False
