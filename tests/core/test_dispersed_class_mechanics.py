"""Parameterized coverage for class mechanics implemented across shared hooks."""

from types import SimpleNamespace

import pytest

from src.core import abilities, enemies
from src.core.abilities import promotions as promotion_abilities
from src.core.classes import class_rings, grandmaster, mage_mechanics
from src.core.classes.promotion_kits import resolve
from src.core.combat.battle_engine import BattleEngine
from src.core.combat.combat_result import CombatResult
from src.core.data.data_driven_abilities import DataDrivenSpell
from src.core.effects.common import CleanseEffect
from src.core.effects.skills import GoldTossEffect
from src.core.map_tiles.paths import CavePath
from src.core.progression import ABILITY_TREES
from tests.test_framework import TestGameState


class _BattleTile:
    def available_actions(self, _player):
        return ["Attack"]


class _AlwaysTrigger:
    @staticmethod
    def random() -> float:
        return 0.0


def test_momentum_keeps_death_mark_copy_on_the_ninja_tree_only():
    assert "Death Mark" not in abilities.Momentum().description
    ninja_momentum = next(node for node in ABILITY_TREES["Ninja"].nodes if node.name == "Momentum")
    assert ninja_momentum.payload["description"].startswith("Death Mark setup:")
    for class_name in ("Weapon Master", "Berserker"):
        momentum = next(node for node in ABILITY_TREES[class_name].nodes if node.name == "Momentum")
        assert "Death Mark" not in momentum.payload.get("description", "")


def test_retired_resolve_actives_are_absent_while_passives_remain():
    for class_name in (
        "ShieldBash",
        "Bulwark",
        "ShieldRiposte",
        "CoveringGuard",
        "SpellReflection",
    ):
        assert not hasattr(promotion_abilities, class_name)
    for function_name in (
        "shield_check",
        "shield_bash",
        "bulwark",
        "shield_riposte",
        "covering_guard",
        "prepare_spell_reflection",
        "spell_reflection_ready",
        "consume_spell_reflection",
        "tick_spell_reflection",
    ):
        assert not hasattr(resolve, function_name)
    assert abilities.ShieldRiposte.__module__.endswith(".defender")
    assert abilities.SpellReflection.__module__.endswith(".defender")


WEAPON_ART_CASES = (
    ("Fist", abilities.IronPalm, abilities.IronPalm2, abilities.IronPalm3, "Attack"),
    ("Dagger", abilities.Hemorrhage, abilities.Hemorrhage2, abilities.Hemorrhage3, "Bleed"),
    (
        "Sword",
        abilities.RiposteLine,
        abilities.RiposteLine2,
        abilities.RiposteLine3,
        "_riposte_line",
    ),
    ("Club", abilities.LowSweep, abilities.LowSweep2, abilities.LowSweep3, "Speed"),
    (
        "Longsword",
        abilities.GuardCleaver,
        abilities.GuardCleaver2,
        abilities.GuardCleaver3,
        "Defense",
    ),
    (
        "Battle Axe",
        abilities.ReaversMark,
        abilities.ReaversMark2,
        abilities.ReaversMark3,
        "_reavers_mark",
    ),
    ("Polearm", abilities.Brace, abilities.Brace2, abilities.Brace3, "_brace_art"),
    ("Hammer", abilities.AnvilStrike, abilities.AnvilStrike2, abilities.AnvilStrike3, "Defense"),
)


@pytest.mark.parametrize(
    ("weapon_type", "art_one", "art_two", "art_three", "effect_key"),
    WEAPON_ART_CASES,
)
@pytest.mark.parametrize(("art_index", "rank"), ((0, 1), (1, 5), (2, 10)))
def test_every_weapon_art_form_validates_cost_and_applies_its_identity(
    monkeypatch,
    weapon_type,
    art_one,
    art_two,
    art_three,
    effect_key,
    art_index,
    rank,
):
    player = TestGameState.create_player(
        class_name="Grandmaster of Arms",
        race_name="Human",
        level=90,
        mana=(200, 200),
    )
    target = enemies.Goblin()
    target.health.current = target.health.max = 500
    player.equipment["Weapon"] = SimpleNamespace(
        name=f"Test {weapon_type}",
        typ="Weapon",
        subtyp=weapon_type,
    )
    threshold = grandmaster.XP_THRESHOLDS[rank - 1]
    player.grandmaster_discipline["disciplines"][weapon_type]["xp"] = threshold
    player.ensure_grandmaster_discipline()
    player.record_grandmaster_weapon_art = lambda *_args: (rank, rank, 0)
    player.weapon_damage = lambda *_args, **_kwargs: ("The art lands.\n", True, 1)
    monkeypatch.setattr(grandmaster.random, "random", lambda: 1.0)
    art = (art_one, art_two, art_three)[art_index]()
    mana_before = player.mana.current

    message = art.use(player, target)

    assert "requires" not in message
    assert "not enough mana" not in message
    assert player.mana.current == mana_before - art.cost
    if effect_key in target.stat_effects:
        assert target.stat_effects[effect_key].active
    elif effect_key in target.physical_effects:
        assert target.physical_effects[effect_key].active
    elif effect_key.startswith("_") and hasattr(target, effect_key):
        assert getattr(target, effect_key)
    else:
        assert getattr(player, effect_key)


WIZARD_MODIFIER_CASES = (
    ("Fire", "Inferno", "Inferno"),
    ("Ice", "Subzero", "frozen solid"),
    ("Electric", "Electrical Burns", "charge courses"),
    ("Wind", "Divine Wind", "Fujin"),
    ("Water", "Unrelenting Waves", "Unrelenting Waves"),
    ("Earth", "Aftershock", "reverberate"),
)


@pytest.mark.parametrize(
    ("school", "skill_name", "message_fragment"),
    WIZARD_MODIFIER_CASES,
)
def test_every_wizard_school_modifier_has_a_live_damage_hook(
    school,
    skill_name,
    message_fragment,
):
    wizard = TestGameState.create_player(class_name="Wizard", race_name="Human")
    target = enemies.Goblin()
    target.health.current = target.health.max = 500
    wizard.spellbook["Skills"][skill_name] = SimpleNamespace(passive=True)
    if school == "Electric":
        wizard.spellbook["Skills"]["Aspirate"] = SimpleNamespace(passive=True)
        target.magic_effects["DOT"].active = True
        target.magic_effects["DOT"].source = "Drowning"
    spell = SimpleNamespace(
        result=CombatResult(action="Cast Spell", damage=40, hit=True),
    )

    message = mage_mechanics._apply_wizard_modifier(
        wizard,
        spell,
        target,
        school,
        rng=_AlwaysTrigger(),
    )

    assert message_fragment in message


@pytest.mark.parametrize(
    ("bond_name", "expected_roll_max"),
    ((None, 3), ("Familiar Bond", 2), ("Familiar Bond II", 1)),
)
def test_warlock_familiar_bonds_change_the_action_roll(
    monkeypatch,
    bond_name,
    expected_roll_max,
):
    warlock = TestGameState.create_player(class_name="Warlock", race_name="Human")
    warlock.familiar = SimpleNamespace(spec="Defense")
    target = enemies.Goblin()
    if bond_name:
        warlock.spellbook["Skills"][bond_name] = SimpleNamespace(passive=True)
    rolls = []

    def miss_roll(low, high):
        rolls.append((low, high))
        return high

    monkeypatch.setattr("src.core.player.combat.random.randint", miss_roll)

    assert warlock.familiar_turn(target) == ""
    assert rolls[-1] == (0, expected_roll_max)


def test_each_warlock_familiar_specialization_modifier_reaches_its_shared_hook(
    monkeypatch,
):
    warlock = TestGameState.create_player(class_name="Warlock", race_name="Human")
    attacker = enemies.Goblin()
    attacker.health.current = attacker.health.max = 100

    warlock.familiar = SimpleNamespace(name="Homunculus", spec="Defense")
    warlock.spellbook["Skills"]["Thorn By My Side"] = SimpleNamespace(passive=True)
    attacker._apply_absorption(
        warlock,
        damage=12,
        raw_dmg=12,
        crit_per=0,
        att="Attack",
        cover=True,
        crit=1,
    )
    assert attacker.health.current == 88

    warlock.familiar = SimpleNamespace(spec="Support")
    warlock.spellbook["Skills"]["Restorative Barrier"] = SimpleNamespace(passive=True)
    warlock._emit_healing_event(17, source="Heal")
    assert warlock.restorative_barrier == 17

    spell = DataDrivenSpell(
        name="Familiar Bolt",
        description="Coverage spell.",
        cost=0,
        dmg_mod=1,
        crit=999,
        subtyp="Arcane",
        school="Arcane",
    )
    warlock.familiar = SimpleNamespace(spec="Arcane")
    warlock.spellbook["Skills"]["Insult to Injury"] = SimpleNamespace(passive=True)
    corrupted = enemies.Goblin()
    corrupted.health.current = corrupted.health.max = 500
    corrupted.magic_effects["DOT"].source = "Corruption"
    monkeypatch.setattr(
        "src.core.data.data_driven_abilities.base.random.uniform",
        lambda *_args: 1.0,
    )
    monkeypatch.setattr(
        "src.core.data.data_driven_abilities.base.random.randint",
        lambda low, _high: low,
    )
    monkeypatch.setattr(
        "src.core.data.data_driven_abilities.base.random.random",
        lambda: 0.0,
    )
    result = spell.cast(warlock, corrupted, fam=True)
    assert result.damage > int(warlock.check_mod("magic") * spell.dmg_mod)

    warlock.familiar = SimpleNamespace(spec="Luck")
    warlock.spellbook["Skills"]["Bullionaire"] = SimpleNamespace(passive=True)
    toss_result = CombatResult(
        action="Gold Toss",
        actor=warlock,
        target=corrupted,
        extra={"use_kwargs": {"fam": True}},
    )
    monkeypatch.setattr("random.randint", lambda low, high: high)
    GoldTossEffect().apply(warlock, corrupted, toss_result)
    assert warlock.bullionaire_bonus_gold > 0


@pytest.mark.parametrize(("mastered", "expected_depth"), ((False, 4), (True, 5)))
def test_master_locator_improves_the_jinkin_find_depth(
    monkeypatch,
    mastered,
    expected_depth,
):
    warlock = TestGameState.create_player(class_name="Warlock", race_name="Human")
    warlock.familiar = SimpleNamespace(
        race="Jinkin",
        level=SimpleNamespace(pro_level=3),
    )
    if mastered:
        warlock.spellbook["Skills"]["Master Locator"] = SimpleNamespace(passive=True)
    found_depths = []
    found_items = []
    warlock.modify_inventory = lambda item, *_args, **_kwargs: found_items.append(item)
    tile = CavePath(0, 0, 4)
    game = SimpleNamespace(player_char=warlock, _random_combat=False)
    monkeypatch.setattr("src.core.map_tiles.traps.trigger_tile_trap", lambda *_args: None)
    monkeypatch.setattr("src.core.map_tiles.paths.random.randint", lambda *_args: 0)

    def item_for_depth(depth):
        found_depths.append(depth)
        return lambda: SimpleNamespace(name="Jinkin Find")

    monkeypatch.setattr("src.core.map_tiles.paths.items.random_item", item_for_depth)

    tile.modify_player(game)

    assert found_depths == [expected_depth]
    assert len(found_items) == 1


def test_shadowcaster_terminal_passives_cover_deep_shadow_veil_and_death(
    monkeypatch,
):
    shadow = TestGameState.create_player(class_name="Shadowcaster", race_name="Human")
    target = enemies.Goblin()
    shadow._piercing_bolt_cast = True
    target.check_mod = lambda mod, **_kwargs: 0.50 if mod == "resist" else 0
    _hit, _message, pierced = target.damage_reduction(100, shadow, typ="Shadow")
    shadow._piercing_bolt_cast = False
    _hit, _message, ordinary = target.damage_reduction(100, shadow, typ="Shadow")
    assert pierced > ordinary

    shadow.spellbook["Skills"]["Sciophobia"] = SimpleNamespace(passive=True)
    shadow.shadow_curtain_turns = 2
    attacker = enemies.Goblin()
    monkeypatch.setattr("src.core.character.events.random.random", lambda: 0.0)
    attacker._emit_damage_event(shadow, 5, damage_type="Physical")
    assert attacker.haunted_turns == 3

    shadow.spellbook["Skills"]["Death Becomes Us"] = SimpleNamespace(passive=True)

    class _Desoul:
        name = "Desoul"
        cost = 0
        subtyp = "Shadow"
        school = "Shadow"

        def cast(self, caster, target=None, **_kwargs):
            target.health.current = 0
            return CombatResult(
                action="Desoul",
                actor=caster,
                target=target,
                hit=True,
                damage=target.health.max,
                message="The soul is severed.\n",
            )

    victim = enemies.Goblin()
    engine = BattleEngine(shadow, victim, _BattleTile())
    engine.attacker = shadow
    engine.defender = victim
    shadow.spellbook["Spells"]["Desoul"] = _Desoul()
    engine.execute_intent(engine.prepare_intent("Cast Spell", "Desoul"))
    assert shadow.shadow_dungeon_darkness_steps == 100


def test_shadowcaster_familiar_terminal_passives_cover_all_four_echoes(monkeypatch):
    shadow = TestGameState.create_player(class_name="Shadowcaster", race_name="Human")
    target = enemies.Goblin()

    class _Goad:
        name = "Goad"
        typ = "Skill"

        @staticmethod
        def use(_user, target=None, **_kwargs):
            return f"{target.name} is goaded.\n"

    shadow.familiar = SimpleNamespace(
        name="Homunculus",
        spec="Defense",
        spellbook={"Spells": {}, "Skills": {"Goad": _Goad()}},
    )
    shadow.spellbook["Skills"]["Indiscriminate Provocation"] = SimpleNamespace(passive=True)
    rolls = iter((0, 1))
    monkeypatch.setattr(
        "src.core.player.combat.random.randint",
        lambda *_args: next(rolls),
    )
    shadow.familiar_turn(target)
    assert target.confused_turns == 3

    shadow.familiar = SimpleNamespace(spec="Support")
    shadow.spellbook["Skills"]["Uno Reverse Card"] = SimpleNamespace(passive=True)
    shadow.status_effects["Poison"].active = True
    shadow.status_effects["Poison"].duration = 3
    cleanse_result = CombatResult(
        action="Cleanse",
        actor=shadow,
        target=shadow,
        extra={"use_kwargs": {"fam": True}},
    )
    CleanseEffect().apply(shadow, shadow, cleanse_result)
    assert shadow.stat_effects["Defense"].active

    class _FamiliarSpell:
        name = "Bolt"
        typ = "Spell"

        def __init__(self):
            self.casts = 0

        def cast(self, _user, target=None, **_kwargs):
            self.casts += 1
            return f"Bolt hits {target.name}.\n"

    familiar_spell = _FamiliarSpell()
    shadow.familiar = SimpleNamespace(
        name="Mephit",
        spec="Arcane",
        spellbook={"Spells": {"Bolt": familiar_spell}, "Skills": {}},
    )
    shadow.spellbook["Skills"]["Night Moves"] = SimpleNamespace(passive=True)
    class_rings.ensure_state(shadow)["data"]["Shadowcaster"]["eclipse_turns"] = 2
    monkeypatch.setattr("src.core.player.combat.random.randint", lambda *_args: 0)
    monkeypatch.setattr("src.core.player.combat.random.choice", lambda values: values[0])
    shadow.familiar_turn(target)
    assert familiar_spell.casts == 2

    shadow.familiar = SimpleNamespace(spec="Luck")
    shadow.spellbook["Skills"]["Bullionaire"] = SimpleNamespace(passive=True)
    toss_result = CombatResult(
        action="Gold Toss",
        actor=shadow,
        target=target,
        extra={"use_kwargs": {"fam": True}},
    )
    monkeypatch.setattr("random.randint", lambda low, high: high)
    GoldTossEffect().apply(shadow, target, toss_result)
    assert shadow.bullionaire_bonus_gold > 0
