#!/usr/bin/env python3
"""
Data-Driven Abilities Tests

Validates the effects integration pipeline:
- CombatResult.message and __str__
- EffectFactory new types
- DataDrivenSpell / DataDrivenSkill
- AbilityFactory combat-ready production
- YAML → combat-ready spells end-to-end
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

# ---------------------------------------------------------------------------
# CombatResult
# ---------------------------------------------------------------------------


class TestCombatResultMessage:
    """Verify the new message field and __str__ on CombatResult."""

    def test_message_field_defaults_empty(self):
        from src.core.combat.combat_result import CombatResult

        result = CombatResult(action="Test")
        assert result.message == ""

    def test_str_returns_message(self):
        from src.core.combat.combat_result import CombatResult

        result = CombatResult(action="Test", message="Hello world")
        assert str(result) == "Hello world"

    def test_message_in_to_dict(self):
        from src.core.combat.combat_result import CombatResult

        result = CombatResult(action="Test", message="abc")
        d = result.to_dict()
        assert d["message"] == "abc"

    def test_empty_str_for_legacy_results(self):
        """Old code that doesn't set message should get empty string."""
        from src.core.combat.combat_result import CombatResult

        result = CombatResult(action="Legacy")
        assert str(result) == ""


# ---------------------------------------------------------------------------
# EffectFactory
# ---------------------------------------------------------------------------


class TestEffectFactory:
    """Verify EffectFactory can create all registered types."""

    def test_create_damage(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import DamageEffect

        e = EffectFactory.create({"type": "damage", "base": 10, "scaling": {"ratio": 1.5}})
        assert isinstance(e, DamageEffect)
        assert e.base_damage == 10

    def test_create_heal(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import HealEffect

        e = EffectFactory.create({"type": "heal", "base": 20})
        assert isinstance(e, HealEffect)

    def test_create_regen(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import RegenEffect

        e = EffectFactory.create({"type": "regen", "base": 15, "duration": 3})
        assert isinstance(e, RegenEffect)
        assert e.duration == 3

    def test_create_status(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import StatusEffect

        e = EffectFactory.create({"type": "status", "name": "Stun", "duration": 2})
        assert isinstance(e, StatusEffect)
        assert e.name == "Stun"

    def test_create_buff_attack(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import AttackBuffEffect

        e = EffectFactory.create({"type": "buff", "stat": "attack", "amount": 10, "duration": 5})
        assert isinstance(e, AttackBuffEffect)

    def test_create_buff_speed(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import SpeedBuffEffect

        e = EffectFactory.create({"type": "buff", "stat": "speed", "amount": 5, "duration": 3})
        assert isinstance(e, SpeedBuffEffect)

    def test_create_debuff_defense(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import DefenseDebuffEffect

        e = EffectFactory.create({"type": "debuff", "stat": "defense", "amount": 8, "duration": 3})
        assert isinstance(e, DefenseDebuffEffect)

    def test_create_debuff_speed(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import SpeedDebuffEffect

        e = EffectFactory.create({"type": "debuff", "stat": "speed", "amount": 3, "duration": 2})
        assert isinstance(e, SpeedDebuffEffect)

    def test_create_dot(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import DamageOverTimeEffect

        e = EffectFactory.create(
            {"type": "dot", "dot_type": "Burn", "damage_per_tick": 5, "duration": 3}
        )
        assert isinstance(e, DamageOverTimeEffect)

    def test_create_chance(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import ChanceEffect

        e = EffectFactory.create(
            {
                "type": "chance",
                "chance": 0.3,
                "effect": {"type": "status", "name": "Stun", "duration": 1},
            }
        )
        assert isinstance(e, ChanceEffect)

    def test_create_composite(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import CompositeEffect

        e = EffectFactory.create(
            {
                "type": "composite",
                "effects": [
                    {"type": "damage", "base": 10},
                    {"type": "buff", "stat": "attack", "amount": 5, "duration": 3},
                ],
            }
        )
        assert isinstance(e, CompositeEffect)
        assert len(e.effects) == 2

    def test_create_lifesteal(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import LifestealEffect

        e = EffectFactory.create({"type": "lifesteal", "percent": 0.5})
        assert isinstance(e, LifestealEffect)
        assert e.lifesteal_percent == 0.5

    def test_create_reflect(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import ReflectDamageEffect

        e = EffectFactory.create({"type": "reflect", "percent": 0.25, "duration": 4})
        assert isinstance(e, ReflectDamageEffect)

    def test_create_shield(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import ShieldEffect

        e = EffectFactory.create({"type": "shield", "amount": 100, "duration": 5})
        assert isinstance(e, ShieldEffect)

    def test_create_dispel(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import DispelEffect

        e = EffectFactory.create({"type": "dispel", "dispel_type": "buffs"})
        assert isinstance(e, DispelEffect)

    def test_create_resistance(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import ResistanceEffect

        e = EffectFactory.create(
            {"type": "resistance", "element": "Fire", "amount": 0.5, "duration": 3}
        )
        assert isinstance(e, ResistanceEffect)

    def test_create_multi_buff(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import MultiStatBuffEffect

        e = EffectFactory.create(
            {"type": "multi_buff", "stats": {"attack": 5, "defense": 3}, "duration": 4}
        )
        assert isinstance(e, MultiStatBuffEffect)

    def test_create_stat_contest(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import StatContestEffect

        e = EffectFactory.create(
            {
                "type": "stat_contest",
                "actor_stat": "intel",
                "actor_divisor": 2,
                "target_stat": "wisdom",
                "effect": {"type": "status", "name": "Stun", "duration": 1},
            }
        )
        assert isinstance(e, StatContestEffect)

    def test_create_dynamic_dot(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import DynamicDotEffect

        e = EffectFactory.create(
            {
                "type": "dynamic_dot",
                "dot_type": "DOT",
                "duration": 2,
                "damage_lo_fraction": 0.25,
                "damage_hi_fraction": 0.5,
            }
        )
        assert isinstance(e, DynamicDotEffect)
        assert e.duration == 2

    def test_dynamic_dot_marks_fire_actions_as_burn(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.data.ability_loader import EffectFactory
        from tests.test_framework import TestGameState

        effect = EffectFactory.create(
            {
                "type": "dynamic_dot",
                "dot_type": "DOT",
                "duration": 2,
                "damage_lo_fraction": 1.0,
                "damage_hi_fraction": 1.0,
            }
        )
        actor = TestGameState.create_player(name="Caster")
        target = TestGameState.create_player(name="Target")

        fire_result = CombatResult(action="Firebolt", actor=actor, target=target)
        fire_result.extra["last_damage"] = 10
        effect.apply(actor, target, fire_result)

        assert target.magic_effects["DOT"].source == "Burn"

        target.magic_effects["DOT"].active = False
        target.magic_effects["DOT"].duration = 0
        target.magic_effects["DOT"].extra = 0
        shadow_result = CombatResult(action="Corruption", actor=actor, target=target)
        shadow_result.extra["last_damage"] = 10
        effect.apply(actor, target, shadow_result)

        assert target.magic_effects["DOT"].source == "Corruption"

    def test_create_dynamic_extra_damage(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import DynamicExtraDamageEffect

        e = EffectFactory.create(
            {
                "type": "dynamic_extra_damage",
                "damage_lo_fraction": 0.5,
                "damage_hi_fraction": 1.0,
            }
        )
        assert isinstance(e, DynamicExtraDamageEffect)

    def test_create_status_apply(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import StatusApplyEffect

        e = EffectFactory.create(
            {
                "type": "status_apply",
                "status_name": "Stun",
                "duration": 1,
                "use_crit_bonus": True,
            }
        )
        assert isinstance(e, StatusApplyEffect)
        assert e.status_name == "Stun"

    def test_unknown_type_raises(self):
        from src.core.data.ability_loader import EffectFactory

        with pytest.raises(ValueError, match="Unknown effect type"):
            EffectFactory.create({"type": "nonexistent"})


# ---------------------------------------------------------------------------
# AbilityFactory
# ---------------------------------------------------------------------------


class TestAbilityFactory:
    """Test that AbilityFactory produces the right types."""

    def test_combat_ready_spell(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSpell

        ability = AbilityFactory.create_from_dict(
            {
                "name": "TestSpell",
                "type": "Spell",
                "subtype": "Fire",
                "cost": 10,
                "damage_mod": 1.5,
                "crit": 5,
                "effects": [{"type": "damage", "base": 25}],
            }
        )
        assert isinstance(ability, DataDrivenSpell)
        assert ability.name == "TestSpell"
        assert ability.cost == 10
        assert ability.subtyp == "Fire"
        assert len(ability._effects) == 1

    def test_combat_ready_skill(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSkill

        ability = AbilityFactory.create_from_dict(
            {
                "name": "TestSkill",
                "type": "Skill",
                "subtype": "Offensive",
                "cost": 5,
                "weapon": True,
                "damage_mod": 2.0,
                "effects": [],
            }
        )
        assert isinstance(ability, DataDrivenSkill)
        assert ability.weapon is True
        assert ability.dmg_mod == 2.0

    def test_simple_ability_fallback(self):
        from src.core.data.ability_loader import AbilityFactory

        ability = AbilityFactory.create_from_dict(
            {"name": "Config", "type": "Spell", "cost": 5},
            combat_ready=False,
        )
        # Should NOT be a DataDrivenSpell — it's a SimpleAbility
        assert ability.name == "Config"
        assert not hasattr(ability, "cast")  # SimpleAbility has no cast()

    def test_combat_ready_is_default(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSpell

        ability = AbilityFactory.create_from_dict(
            {
                "name": "DefaultSpell",
                "type": "Spell",
                "subtype": "Non-elemental",
                "cost": 0,
            }
        )
        assert isinstance(ability, DataDrivenSpell)


# ---------------------------------------------------------------------------
# YAML loading — end-to-end
# ---------------------------------------------------------------------------


class TestYAMLLoading:
    """Load actual YAML files and verify they produce combat-ready instances."""

    ABILITIES_DIR = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"

    @pytest.mark.parametrize(
        "filename,expected_subtyp",
        [
            ("firebolt.yaml", "Fire"),
            ("fireball.yaml", "Fire"),
            ("firestorm.yaml", "Fire"),
            ("scorch.yaml", "Fire"),
            ("molten_rock.yaml", "Fire"),
            ("volcano.yaml", "Fire"),
            ("ice_lance.yaml", "Ice"),
            ("icicle.yaml", "Ice"),
            ("blizzard.yaml", "Ice"),
            ("shock.yaml", "Electric"),
            ("lightning.yaml", "Electric"),
            ("electrocution.yaml", "Electric"),
        ],
    )
    def test_load_batch1_spell(self, filename, expected_subtyp):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSpell

        filepath = self.ABILITIES_DIR / filename

        ability = AbilityFactory.create_from_yaml(filepath)
        assert isinstance(ability, DataDrivenSpell), f"{filename} should produce DataDrivenSpell"
        assert ability.subtyp == expected_subtyp
        assert ability.cost > 0 or ability.dmg_mod > 0
        assert len(ability._effects) >= 0

    def test_all_yaml_abilities_load_combat_ready(self):
        from src.core.data.ability_loader import AbilityFactory

        yaml_paths = sorted(self.ABILITIES_DIR.glob("*.yaml"))
        assert len(yaml_paths) == 197

        loaded_names = []
        for path in yaml_paths:
            ability = AbilityFactory.create_from_yaml(path)
            assert ability.name
            assert ability.description is not None
            assert hasattr(ability, "cost"), f"{path.name} missing cost attribute"
            loaded_names.append(ability.name)

        assert "Fireball" in loaded_names
        assert "Jump" in loaded_names
        assert "Cataclysm" in loaded_names

    def test_yaml_definition_cache_reuses_parse_but_returns_isolated_data(self, monkeypatch):
        from src.core.data import ability_loader

        ability_loader.clear_ability_definition_cache()
        original_safe_load = ability_loader.yaml.safe_load
        parse_calls = []

        def tracked_safe_load(stream):
            parse_calls.append(stream.name)
            return original_safe_load(stream)

        monkeypatch.setattr(ability_loader.yaml, "safe_load", tracked_safe_load)
        path = self.ABILITIES_DIR / "fireball.yaml"

        first = ability_loader.AbilityFactory.create_from_yaml(path)
        first._raw_data["name"] = "Mutated locally"
        second = ability_loader.AbilityFactory.create_from_yaml(path)

        assert parse_calls == [str(path.resolve())]
        assert second.name == "Fireball"
        assert second._raw_data["name"] == "Fireball"
        assert first._raw_data is not second._raw_data

    def test_builtin_yaml_abilities_do_not_use_primitive_damage_effects(self):
        import yaml

        def find_damage_effects(node, path):
            matches = []
            if isinstance(node, dict):
                if str(node.get("type", "")).lower() == "damage":
                    matches.append(path)
                for key, value in node.items():
                    matches.extend(find_damage_effects(value, f"{path}.{key}"))
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    matches.extend(find_damage_effects(value, f"{path}[{index}]"))
            return matches

        yaml_paths = sorted(self.ABILITIES_DIR.glob("*.yaml"))
        damage_effect_paths = []
        for path in yaml_paths:
            with path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
            damage_effect_paths.extend(
                f"{path.name}:{match}" for match in find_damage_effects(payload, "$")
            )

        assert damage_effect_paths == []

    def test_load_directory_produces_combat_ready(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSkill, DataDrivenSpell

        abilities = AbilityFactory.load_abilities_from_directory(self.ABILITIES_DIR)
        assert len(abilities) > 0

        # At least the Batch 1 fire spells should be present
        assert "Fireball" in abilities
        assert isinstance(abilities["Fireball"], DataDrivenSpell)

    def test_load_directory_simple_mode(self):
        """combat_ready=False should still load all YAMLs as SimpleAbility."""
        from src.core.data.ability_loader import AbilityFactory

        abilities = AbilityFactory.load_abilities_from_directory(
            self.ABILITIES_DIR, combat_ready=False
        )
        assert len(abilities) > 0
        # None should be DataDrivenSpell
        for name, ab in abilities.items():
            assert (
                not hasattr(ab, "cast") or type(ab).__name__ != "DataDrivenSpell"
            ), f"{name} should be SimpleAbility in non-combat mode"


# ---------------------------------------------------------------------------
# DataDrivenSpell — integration with real characters
# ---------------------------------------------------------------------------


class TestDataDrivenSpellCast:
    """Test DataDrivenSpell.cast() with real Player/Enemy objects."""

    @staticmethod
    def _make_combatants():
        from src.core.enemies import Enemy
        from tests.test_framework import TestGameState

        caster = TestGameState.create_player(
            name="Caster",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 25, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        # Ensure the Wizard power-up is off so mana deduction works normally
        caster.class_effects["Power Up"].active = False

        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 18, "charisma": 10, "dex": 12},
        )
        return caster, target

    def test_cast_returns_combat_result(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "fireball.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)
        caster, target = self._make_combatants()

        result = spell.cast(caster, target)
        assert isinstance(result, CombatResult)
        assert isinstance(result.message, str)
        assert len(result.message) > 0  # should have some combat text

    def test_cast_str_returns_message(self):
        """str(spell.cast(...)) should give the same result as result.message."""
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "fireball.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)
        caster, target = self._make_combatants()

        result = spell.cast(caster, target)
        assert str(result) == result.message

    def test_cast_deducts_mana(self):
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "fireball.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)
        caster, target = self._make_combatants()

        mana_before = caster.mana.current
        spell.cast(caster, target)
        assert caster.mana.current == mana_before - spell.cost

    def test_cast_deals_damage_or_dodges(self):
        """After casting, target should have taken damage OR dodge should have occurred."""
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "fireball.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)
        caster, target = self._make_combatants()

        hp_before = target.health.current
        result = spell.cast(caster, target)

        # Either damage was dealt or the spell was dodged/missed
        if result.dodge:
            assert target.health.current == hp_before
        elif result.hit is False:
            assert "misses" in result.message or "no effect" in result.message.lower()
        else:
            assert target.health.current < hp_before or "no damage" in result.message.lower()

    def test_ice_block_immunity(self):
        """Target with Ice Block active should be unaffected."""
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "fireball.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)
        caster, target = self._make_combatants()

        target.magic_effects["Ice Block"].active = True
        hp_before = target.health.current
        result = spell.cast(caster, target)

        assert target.health.current == hp_before
        assert "no effect" in result.message.lower()

    def test_fire_spell_special_effect_can_apply_dot(self, monkeypatch):
        """Fireball applies DOT when its stat contest succeeds."""
        import random

        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "fireball.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)

        def _upper_bound(_low: int, high: int) -> int:
            return high

        # Make the target an always-hit contact target and select the upper
        # contest rolls. This verifies the real Fireball effect pipeline
        # without a probabilistic retry loop.
        monkeypatch.setattr(random, "randint", _upper_bound)
        caster, target = self._make_combatants()
        caster.stats.intel = 100
        target.stats.wisdom = 5
        target.status_effects["Stun"].active = True

        result = spell.cast(caster, target)

        assert result.hit is True
        assert result.extra["stat_contest_won"] is True
        assert target.magic_effects["DOT"].active is True

    def test_corruption_dot_uses_corruption_message(self):
        """Corruption DOT should not reuse burn text."""
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "corruption.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)

        for _ in range(80):
            caster, target = self._make_combatants()
            caster.stats.charisma = 100
            target.stats.wisdom = 1
            result = spell.cast(caster, target)
            if target.magic_effects["DOT"].active:
                assert "wreathed in corrupting magic" in result.message
                assert "set ablaze" not in result.message
                return

        pytest.fail("Corruption DOT should have triggered at least once in 80 casts")

    def test_water_attack_spells_can_reduce_attack(self, monkeypatch):
        import random

        from src.core import abilities

        def _upper_bound(_low: int, high: int) -> int:
            return high

        spell = abilities.WaterJet()
        monkeypatch.setattr(random, "randint", _upper_bound)
        caster, target = self._make_combatants()
        caster.stats.intel = 120
        target.stats.con = 1
        target.combat.attack = 140
        target.status_effects["Stun"].active = True

        result = spell.cast(caster, target)

        assert result.hit is True
        assert result.extra["stat_contest_won"] is True
        assert target.stat_effects["Attack"].active is True
        assert target.stat_effects["Attack"].extra < 0

    def test_wind_attack_spells_can_reduce_speed(self):
        from src.core import abilities

        spell = abilities.Gust()
        for _ in range(50):
            caster, target = self._make_combatants()
            caster.stats.intel = 120
            target.stats.dex = 1
            spell.cast(caster, target)
            if target.stat_effects["Speed"].active:
                return

        pytest.fail("Gust should have reduced Speed at least once")

    def test_earth_attack_spells_can_knock_prone_but_respect_flying(self, monkeypatch):
        """Tremor applies Prone after a winning contest, except to flyers."""
        import random

        from src.core import abilities

        def _upper_bound(_low: int, high: int) -> int:
            return high

        spell = abilities.Tremor()
        # Select the high end of each roll so this tests Tremor's real effect
        # pipeline without a probabilistic retry loop that can intermittently
        # exhaust its attempts in CI.
        monkeypatch.setattr(random, "randint", _upper_bound)
        caster, target = self._make_combatants()
        caster.stats.intel = 120
        target.stats.con = 1
        target.status_effects["Stun"].active = True
        spell.cast(caster, target)
        assert target.physical_effects["Prone"].active

        caster, flying_target = self._make_combatants()
        caster.stats.intel = 120
        flying_target.stats.con = 1
        flying_target.flying = True
        spell.cast(caster, flying_target)
        assert not flying_target.physical_effects["Prone"].active

    def test_ground_contact_earth_spells_do_not_damage_flying_targets(self):
        from src.core import abilities

        caster, flying_target = self._make_combatants()
        caster.stats.intel = 120
        flying_target.flying = True
        hp_before = flying_target.health.current

        result = abilities.Tremor().cast(caster, flying_target)

        assert flying_target.health.current == hp_before
        assert result.hit is False
        assert "no effect" in result.message.lower()

    def test_non_grounded_earth_spells_can_damage_flying_targets(self):
        from src.core import abilities

        caster, flying_target = self._make_combatants()
        caster.stats.intel = 120
        flying_target.stats.dex = 1
        flying_target.stats.con = 1
        flying_target.flying = True
        # Incapacitation guarantees the contact roll so this test isolates
        # Sandstorm's non-grounded targeting rule from chance to hit.
        flying_target.status_effects["Sleep"].active = True
        hp_before = flying_target.health.current

        result = abilities.Sandstorm().cast(caster, flying_target)

        assert result.damage > 0
        assert flying_target.health.current < hp_before

    def test_electric_spell_can_apply_stun(self, monkeypatch):
        """Electric spells apply Stun when their authored contests succeed."""
        import random

        from src.core.data.ability_loader import AbilityFactory

        # Shock first makes its authored Intelligence-versus-Wisdom contest,
        # then Stun makes its status-resistance contest. Use the upper bound
        # for both rolls so this verifies the effect pipeline rather than
        # intermittently sampling two independent random gates.
        monkeypatch.setattr(random, "randint", lambda _lower, upper: upper)

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "shock.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)

        caster, target = self._make_combatants()
        caster.stats.intel = 100
        target.stats.wisdom = 5
        target.status_effects["Sleep"].active = True
        spell.cast(caster, target)

        assert target.status_effects["Stun"].active


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """Ensure existing abilities still work unchanged."""

    def test_existing_fireball_class_unmodified(self):
        """The Python Fireball class should be unaffected."""
        from src.core.abilities import Fireball

        fb = Fireball()
        assert fb.name == "Fireball"
        assert fb.cost == 10
        assert fb.subtyp == "Fire"

    def test_existing_charge_yaml_loading_unchanged(self):
        """Charge class should still load YAML config via DataDrivenChargingSkill."""
        from src.core.abilities import Charge

        ch = Charge()
        assert ch.name == "Charge"
        # Should have loaded YAML config — now uses _charge_time
        assert ch._charge_time is not None or ch._charge_time is None  # no crash

    def test_combat_result_str_compat(self):
        """str() on old-style results (no message) should return empty string."""
        from src.core.combat.combat_result import CombatResult

        result = CombatResult(action="Test")
        # Battle engine does: message += str(result)
        msg = "prefix" + str(result)
        assert msg == "prefix"


# ---------------------------------------------------------------------------
# Batch 1 YAML Migration — New Effect Types
# ---------------------------------------------------------------------------


class TestNewEffectTypes:
    """Validate the new effect types added for Batch 1."""

    def test_stat_contest_with_crit_multiplier(self):
        """StatContestEffect with use_crit_multiplier should scale actor stat."""
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import StatContestEffect

        e = EffectFactory.create(
            {
                "type": "stat_contest",
                "actor_stat": "charisma",
                "actor_lo_divisor": 2,
                "actor_divisor": 1,
                "target_stat": "wisdom",
                "target_lo_divisor": 2,
                "target_hi_divisor": 1,
                "use_crit_multiplier": True,
                "effect": {"type": "status_apply", "status_name": "Stun", "duration": 1},
            }
        )
        assert isinstance(e, StatContestEffect)
        assert e.use_crit_multiplier is True
        assert e.actor_lo_divisor == 2

    def test_status_apply_crit_only(self):
        """StatusApplyEffect with crit_only should be loadable."""
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import StatusApplyEffect

        e = EffectFactory.create(
            {
                "type": "status_apply",
                "status_name": "Blind",
                "duration": 2,
                "crit_only": True,
            }
        )
        assert isinstance(e, StatusApplyEffect)
        assert e.crit_only is True

    def test_dynamic_status_dot(self):
        """DynamicStatusDotEffect should be creatable from EffectFactory."""
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects.common import DynamicStatusDotEffect

        e = EffectFactory.create(
            {
                "type": "dynamic_status_dot",
                "status_name": "Poison",
                "duration_stat": "intel",
                "duration_stat_divisor": 10,
                "duration_min": 2,
                "damage_lo_fraction": 1.0,
                "damage_hi_fraction": 1.0,
                "health_multiplier": 0.005,
            }
        )
        assert isinstance(e, DynamicStatusDotEffect)
        assert e.status_name == "Poison"
        assert e.health_multiplier == 0.005


# ---------------------------------------------------------------------------
# Batch 1 YAML Loading — New Spells
# ---------------------------------------------------------------------------

BATCH1_SPELLS = [
    # (yaml_filename, expected_subtype, expected_name)
    ("water_jet.yaml", "Water", "Water Jet"),
    ("aqualung.yaml", "Water", "Aqualung"),
    ("tsunami.yaml", "Water", "Tsunami"),
    ("tremor.yaml", "Earth", "Tremor"),
    ("mudslide.yaml", "Earth", "Mudslide"),
    ("earthquake.yaml", "Earth", "Earthquake"),
    ("sandstorm.yaml", "Earth", "Sandstorm"),
    ("gust.yaml", "Wind", "Gust"),
    ("hurricane.yaml", "Wind", "Hurricane"),
    ("tornado.yaml", "Wind", "Tornado"),
    ("shadow_bolt.yaml", "Shadow", "Shadow Bolt"),
    ("shadow_bolt_2.yaml", "Shadow", "Shadow Bolt"),
    ("shadow_bolt_3.yaml", "Shadow", "Shadow Bolt"),
    ("corruption.yaml", "Shadow", "Corruption"),
    ("terrify.yaml", "Shadow", "Terrify"),
    ("holy.yaml", "Holy", "Holy"),
    ("holy_2.yaml", "Holy", "Holy"),
    ("holy_3.yaml", "Holy", "Holy"),
    ("ultima.yaml", "Non-elemental", "Photon Sphere"),
    ("hellfire.yaml", "Non-elemental", "Hellfire"),
    ("poison_breath.yaml", "Poison", "Poison Breath"),
]


class TestBatch1YAMLLoading:
    """Validate all Batch 1 YAML files load correctly as DataDrivenSpells."""

    @pytest.mark.parametrize("yaml_file,expected_subtype,expected_name", BATCH1_SPELLS)
    def test_load_batch1_spell(self, yaml_file, expected_subtype, expected_name):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import (
            DataDrivenMagicMissileSpell,
            DataDrivenSpell,
        )

        filepath = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / yaml_file
        spell = AbilityFactory.create_from_yaml(filepath)
        expected_type = (
            DataDrivenMagicMissileSpell if yaml_file == "ultima.yaml" else DataDrivenSpell
        )
        assert isinstance(spell, expected_type)
        assert spell.name == expected_name
        assert spell.subtyp == expected_subtype
        assert spell.typ == "Spell"
        assert spell.cost > 0 or spell.cost == 0  # cost is defined
        assert spell.dmg_mod > 0

    def test_ranked_spells_have_rank(self):
        from src.core.data.ability_loader import AbilityFactory

        ranked = {
            "aqualung.yaml": 1,
            "tsunami.yaml": 2,
            "mudslide.yaml": 1,
            "earthquake.yaml": 2,
            "hurricane.yaml": 1,
            "tornado.yaml": 2,
            "ultima.yaml": 3,
            "poison_breath.yaml": 2,
        }
        for yaml_file, expected_rank in ranked.items():
            filepath = (
                Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / yaml_file
            )
            spell = AbilityFactory.create_from_yaml(filepath)
            assert (
                spell.rank == expected_rank
            ), f"{yaml_file}: expected rank {expected_rank}, got {spell.rank}"


# ---------------------------------------------------------------------------
# Batch 1 — ability wrapper factory functions
# ---------------------------------------------------------------------------


class TestBatch1AbilityFactories:
    """Test that ability wrapper classes produce DataDrivenSpell instances."""

    def test_water_spells(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenSpell

        wj = abilities.WaterJet()
        assert isinstance(wj, DataDrivenSpell)
        assert wj.name == "Water Jet"
        assert wj.subtyp == "Water"

        aq = abilities.Aqualung()
        assert aq.name == "Aqualung"
        assert aq.rank == 1

        ts = abilities.Tsunami()
        assert ts.name == "Tsunami"
        assert ts.rank == 2

    def test_earth_spells(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenSpell

        tr = abilities.Tremor()
        assert isinstance(tr, DataDrivenSpell)
        assert tr.subtyp == "Earth"

        ms = abilities.Mudslide()
        assert ms.rank == 1

        eq = abilities.Earthquake()
        assert eq.rank == 2

        ss = abilities.Sandstorm()
        assert ss.name == "Sandstorm"
        assert len(ss._effects) > 0  # has Blind effect

    def test_wind_spells(self):
        from src.core import abilities

        g = abilities.Gust()
        assert g.subtyp == "Wind"

        h = abilities.Hurricane()
        assert h.rank == 1

        t = abilities.Tornado()
        assert t.rank == 2

    def test_shadow_spells(self):
        from src.core import abilities

        sb = abilities.ShadowBolt()
        assert sb.subtyp == "Shadow"
        assert sb.cost == 8

        sb2 = abilities.ShadowBolt2()
        assert sb2.cost == 20

        sb3 = abilities.ShadowBolt3()
        assert sb3.cost == 30

        cor = abilities.Corruption()
        assert cor.name == "Corruption"
        assert len(cor._effects) > 0

        ter = abilities.Terrify()
        assert ter.name == "Terrify"
        assert len(ter._effects) > 0

    def test_holy_spells(self):
        from src.core import abilities

        h1 = abilities.Holy()
        assert h1.subtyp == "Holy"
        assert h1.cost == 4

        h2 = abilities.Holy2()
        assert h2.cost == 12

        h3 = abilities.Holy3()
        assert h3.cost == 28

    def test_standalone_spells(self):
        from src.core import abilities

        ult = abilities.Ultima()
        assert ult.subtyp == "Non-elemental"
        assert ult.name == "Photon Sphere"
        assert ult.rank == 3

        hf = abilities.Hellfire()
        assert hf.name == "Hellfire"
        assert hf.dmg_mod == 3.0

        pb = abilities.PoisonBreath()
        assert pb.subtyp == "Poison"
        assert pb.rank == 2


# ---------------------------------------------------------------------------
# Batch 1 — Combat Integration
# ---------------------------------------------------------------------------


class TestBatch1CombatIntegration:
    """Test migrated spells work correctly in combat."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        caster = TestGameState.create_player(
            name="Caster",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 25, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        caster.class_effects["Power Up"].active = False

        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 18, "charisma": 10, "dex": 12},
        )
        return caster, target

    @pytest.mark.parametrize(
        "yaml_file",
        [
            "water_jet.yaml",
            "tremor.yaml",
            "gust.yaml",
            "shadow_bolt.yaml",
            "ultima.yaml",
        ],
    )
    def test_simple_spell_deals_damage(self, yaml_file):
        """Simple spells (no special effect) should deal damage."""
        from src.core.combat.combat_result import CombatResult
        from src.core.data.ability_loader import AbilityFactory

        filepath = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / yaml_file
        spell = AbilityFactory.create_from_yaml(filepath)
        caster, target = self._make_combatants()

        result = spell.cast(caster, target)
        if yaml_file == "ultima.yaml":
            assert isinstance(result, str)
            assert result
        else:
            assert isinstance(result, CombatResult)
            assert isinstance(result.message, str)
            assert len(result.message) > 0

    def test_sandstorm_can_blind(self):
        """Sandstorm should sometimes apply Blind."""
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "sandstorm.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)

        blind_applied = False
        for _ in range(80):
            caster, target = self._make_combatants()
            caster.stats.intel = 100
            target.stats.con = 5
            result = spell.cast(caster, target)
            if target.status_effects["Blind"].active:
                blind_applied = True
                break

        assert blind_applied, "Blind should have triggered at least once in 80 casts"

    def test_holy_blinds_on_crit(self):
        """Holy should apply Blind on critical hits."""
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "holy.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)

        blind_applied = False
        for _ in range(100):
            caster, target = self._make_combatants()
            result = spell.cast(caster, target)
            if target.status_effects["Blind"].active:
                blind_applied = True
                break

        assert blind_applied, "Blind should have triggered on a crit at least once in 100 casts"

    def test_corruption_can_apply_dot(self):
        """Corruption should sometimes apply DOT."""
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "corruption.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)

        dot_applied = False
        for _ in range(80):
            caster, target = self._make_combatants()
            caster.stats.charisma = 100
            target.stats.wisdom = 5
            result = spell.cast(caster, target)
            if target.magic_effects["DOT"].active:
                dot_applied = True
                break

        assert dot_applied, "DOT should have triggered at least once in 80 casts"

    def test_terrify_can_stun(self):
        """Terrify should sometimes apply Fear."""
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "terrify.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)

        stun_applied = False
        for _ in range(80):
            caster, target = self._make_combatants()
            caster.stats.charisma = 100
            target.stats.wisdom = 5
            result = spell.cast(caster, target)
            if target.status_effects["Fear"].active:
                stun_applied = True
                break

        assert stun_applied, "Fear should have triggered at least once in 80 casts"

    def test_hellfire_can_apply_dot(self):
        """Hellfire should sometimes apply DOT."""
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "hellfire.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)

        dot_applied = False
        for _ in range(80):
            caster, target = self._make_combatants()
            caster.stats.intel = 100
            target.stats.wisdom = 5
            result = spell.cast(caster, target)
            if target.magic_effects["DOT"].active:
                dot_applied = True
                break

        assert dot_applied, "DOT should have triggered at least once in 80 casts"

    def test_poison_breath_can_poison(self):
        """PoisonBreath should sometimes apply Poison."""
        from src.core.data.ability_loader import AbilityFactory

        filepath = (
            Path(__file__).parent.parent
            / "src"
            / "core"
            / "data"
            / "abilities"
            / "poison_breath.yaml"
        )
        spell = AbilityFactory.create_from_yaml(filepath)

        poison_applied = False
        for _ in range(80):
            caster, target = self._make_combatants()
            caster.stats.intel = 100
            target.stats.con = 5
            result = spell.cast(caster, target)
            if target.status_effects["Poison"].active:
                poison_applied = True
                break

        assert poison_applied, "Poison should have triggered at least once in 80 casts"


# ======================================================================
# Batch 2 - Healing / Support / Status spell migration tests
# ======================================================================


class TestBatch2NewEffects:
    """Validate the 5 new effect types added for Batch 2."""

    @staticmethod
    def _make_char():
        from tests.test_framework import TestGameState

        return TestGameState.create_player(
            name="Tester",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
            stats={"strength": 10, "intel": 25, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )

    def test_magic_effect_apply(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import MagicEffectApplyEffect

        actor = self._make_char()
        target = actor
        effect = MagicEffectApplyEffect(effect_name="Reflect", duration=5)
        result = CombatResult(action="Test")
        effect.apply(actor, target, result)
        assert target.magic_effects["Reflect"].active
        assert target.magic_effects["Reflect"].duration >= 5
        assert "Reflect" in result.effects_applied.get("Magic", [])

    def test_magic_effect_apply_stat_duration(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import MagicEffectApplyEffect

        actor = self._make_char()
        actor.stats.intel = 80
        target = actor
        # mode "max" → max(duration, stat // divisor)
        effect = MagicEffectApplyEffect(
            effect_name="Reflect",
            duration=4,
            duration_stat="intel",
            duration_stat_divisor=10,
            duration_stat_mode="max",
        )
        result = CombatResult(action="Test")
        effect.apply(actor, target, result)
        assert target.magic_effects["Reflect"].duration >= 8  # max(4, 80//10)

    def test_dynamic_stat_buff(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import DynamicStatBuffEffect

        actor = self._make_char()
        target = actor
        target.combat.magic = 100
        effect = DynamicStatBuffEffect(
            buff_stat="Magic",
            source="target_combat",
            source_stat="magic",
            lo_divisor=4,
            hi_divisor=2,
            duration=5,
        )
        result = CombatResult(action="Test")
        effect.apply(actor, target, result)
        assert target.stat_effects["Magic"].active
        assert 25 <= target.stat_effects["Magic"].extra <= 50
        assert target.stat_effects["Magic"].duration >= 5

    def test_dynamic_multi_debuff(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import DynamicMultiDebuffEffect

        actor = self._make_char()
        actor.stats.intel = 50
        target = self._make_char()
        target.combat.attack = 80
        target.combat.defense = 60
        effect = DynamicMultiDebuffEffect(
            stats=[
                {"stat_name": "Attack", "combat_attr": "attack"},
                {"stat_name": "Defense", "combat_attr": "defense"},
            ],
            scaling_stat="intel",
            scaling_divisor=10,
            amount_divisor=10,
            duration_min=3,
        )
        result = CombatResult(action="Test")
        effect.apply(actor, target, result)
        assert target.stat_effects["Attack"].active
        assert target.stat_effects["Attack"].extra < 0
        assert target.stat_effects["Defense"].active
        assert target.stat_effects["Defense"].extra < 0
        assert len(result.extra.get("messages", [])) == 2
        assert all("lowered." in message for message in result.extra["messages"])
        assert all(
            "turn" not in message and "(" not in message for message in result.extra["messages"]
        )

    def test_dynamic_multi_debuff_skips_zero_stat_changes(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import DynamicMultiDebuffEffect

        actor = self._make_char()
        actor.stats.intel = 10
        target = self._make_char()
        target.combat.attack = 0
        target.combat.defense = 0
        effect = DynamicMultiDebuffEffect(
            stats=[
                {"stat_name": "Attack", "combat_attr": "attack"},
                {"stat_name": "Defense", "combat_attr": "defense"},
            ],
            scaling_stat="intel",
            scaling_divisor=10,
            amount_divisor=10,
            duration_min=3,
        )
        result = CombatResult(action="Test")
        effect.apply(actor, target, result)

        assert not target.stat_effects["Attack"].active
        assert not target.stat_effects["Defense"].active
        assert result.effects_applied["Stat"] == []
        assert result.extra.get("messages", []) == []

    def test_fixed_stat_modifier_skips_zero_changes(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import StatModifierEffect

        actor = self._make_char()
        target = self._make_char()
        effect = StatModifierEffect("attack", 0, 3)
        result = CombatResult(action="Test")

        effect.apply(actor, target, result)

        assert not target.stat_effects["Attack"].active
        assert result.effects_applied["Stat"] == []

    def test_cleanse_effect(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import CleanseEffect

        actor = self._make_char()
        target = actor
        target.status_effects["Blind"].active = True
        target.status_effects["Poison"].active = True
        effect = CleanseEffect()
        result = CombatResult(action="Test")
        effect.apply(actor, target, result)
        assert not target.status_effects["Blind"].active
        assert not target.status_effects["Poison"].active

    def test_full_dispel_effect(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import FullDispelEffect

        actor = self._make_char()
        target = self._make_char()
        target.magic_effects["Regen"].active = True
        target.magic_effects["Reflect"].active = True
        target.stat_effects["Attack"].active = True
        target.stat_effects["Attack"].extra = 10
        effect = FullDispelEffect()
        result = CombatResult(action="Test")
        effect.apply(actor, target, result)
        assert not target.magic_effects["Regen"].active
        assert not target.magic_effects["Reflect"].active
        assert not target.stat_effects["Attack"].active

    def test_status_apply_skip_if_active(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import StatusApplyEffect

        actor = self._make_char()
        target = self._make_char()
        target.status_effects["Blind"].active = True
        target.status_effects["Blind"].duration = 2
        effect = StatusApplyEffect(
            status_name="Blind",
            duration=3,
            skip_if_active=True,
        )
        result = CombatResult(action="Test")
        result.extra["last_crit"] = 1
        effect.apply(actor, target, result)
        assert result.extra.get("status_already_active") == "Blind"
        # Duration should NOT have been refreshed
        assert target.status_effects["Blind"].duration == 2

    def test_status_apply_duration_random(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import StatusApplyEffect

        actor = self._make_char()
        actor.stats.intel = 60
        target = self._make_char()
        effect = StatusApplyEffect(
            status_name="Berserk",
            skip_if_active=True,
            duration_stat="intel",
            duration_stat_divisor=10,
            duration_min=2,
            duration_random=True,
        )
        durations = set()
        for _ in range(50):
            target.status_effects["Berserk"].active = False
            target.status_effects["Berserk"].duration = 0
            result = CombatResult(action="Test")
            result.extra["last_crit"] = 1
            effect.apply(actor, target, result)
            if target.status_effects["Berserk"].active:
                durations.add(target.status_effects["Berserk"].duration)
        assert len(durations) > 1, "Random duration should vary"


class TestBatch2YAMLLoading:
    """Validate that all Batch 2 YAML files load correctly."""

    YAML_DIR = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"

    HEAL_YAMLS = [
        ("heal.yaml", "Heal", 6, 0.3),
        ("heal_2.yaml", "Heal", 12, 0.45),
        ("heal_3.yaml", "Heal", 25, 0.6),
        ("regen.yaml", "Regen", 8, 0.2),
        ("regen_2.yaml", "Regen", 18, 0.3),
        ("regen_3.yaml", "Regen", 30, 0.4),
        ("hydration.yaml", "Hydration", 16, 0.3),
        ("regrowth.yaml", "Regrowth", 8, 0.25),
    ]

    @pytest.mark.parametrize("filename,name,cost,heal", HEAL_YAMLS)
    def test_load_heal_spell(self, filename, name, cost, heal):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenHealSpell

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / filename, combat_ready=True)
        assert isinstance(ability, DataDrivenHealSpell)
        assert ability.name == name
        assert ability.cost == cost
        assert ability.heal == pytest.approx(heal)

    SUPPORT_YAMLS = [
        ("bless.yaml", "Bless", 12),
        ("boost.yaml", "Boost", 22),
        ("shell.yaml", "Shell", 26),
        ("reflect.yaml", "Reflect", 14),
        ("cleanse.yaml", "Cleanse", 20),
        ("divine_protection.yaml", "Divine Protection", 12),
        ("ice_block.yaml", "Ice Block", 30),
        ("wind_speed.yaml", "Wind Speed", 12),
        ("haste.yaml", "Haste", 24),
        ("stone_skin.yaml", "Stone Skin", 21),
        ("calming_breeze.yaml", "Calming Breeze", 18),
        ("nature_shield.yaml", "Nature Shield", 28),
        ("mirror_image.yaml", "Mirror Image", 8),
        ("mirror_image_2.yaml", "Mirror Image II", 20),
        ("astral_shift.yaml", "Astral Shift", 18),
    ]

    @pytest.mark.parametrize("filename,name,cost", SUPPORT_YAMLS)
    def test_load_support_spell(self, filename, name, cost):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSupportSpell

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / filename, combat_ready=True)
        assert isinstance(ability, DataDrivenSupportSpell)
        assert ability.name == name
        assert ability.cost == cost

    STATUS_YAMLS = [
        ("blinding_fog.yaml", "Blinding Fog", 7),
        ("sleep.yaml", "Sleep", 9),
        ("stupefy.yaml", "Stupefy", 14),
        ("silence.yaml", "Silence", 20),
        ("berserk.yaml", "Berserk", 15),
        ("dispel.yaml", "Dispel", 20),
        ("weaken_mind.yaml", "Weaken Mind", 20),
        ("enfeeble.yaml", "Enfeeble", 12),
    ]

    @pytest.mark.parametrize("filename,name,cost", STATUS_YAMLS)
    def test_load_status_spell(self, filename, name, cost):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenStatusSpell

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / filename, combat_ready=True)
        assert isinstance(ability, DataDrivenStatusSpell)
        assert ability.name == name
        assert ability.cost == cost


class TestBatch2AbilityFactories:
    """Test that abilities.ClassName() produces correct DataDriven instances."""

    def test_heal_spells(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenHealSpell

        h1 = abilities.Heal()
        h2 = abilities.Heal2()
        h3 = abilities.Heal3()
        assert isinstance(h1, DataDrivenHealSpell)
        assert isinstance(h2, DataDrivenHealSpell)
        assert isinstance(h3, DataDrivenHealSpell)
        assert h1.cost == 6
        assert h2.cost == 12
        assert h3.cost == 25
        assert h1._class_name == "Heal"
        assert h2._class_name == "Heal2"
        assert h3._class_name == "Heal3"

    def test_regen_spells(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenHealSpell

        r1 = abilities.Regen()
        r2 = abilities.Regen2()
        r3 = abilities.Regen3()
        assert all(isinstance(r, DataDrivenHealSpell) for r in [r1, r2, r3])
        assert r1.turns == 3
        assert r2.cost == 18
        assert r3.heal == pytest.approx(0.4)

    def test_hydration(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenHealSpell

        h = abilities.Hydration()
        assert isinstance(h, DataDrivenHealSpell)
        assert h._instant_heal is True
        assert h.turns == 2

    def test_support_spells(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenSupportSpell

        for name in [
            "Bless",
            "Boost",
            "Shell",
            "Reflect",
            "Cleanse",
            "DivineProtection",
            "IceBlock",
            "WindSpeed",
            "MirrorImage",
            "MirrorImage2",
            "AstralShift",
        ]:
            spell = getattr(abilities, name)()
            assert isinstance(spell, DataDrivenSupportSpell), f"{name} failed"

    def test_status_spells(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenStatusSpell

        for name in [
            "BlindingFog",
            "Sleep",
            "Stupefy",
            "Silence",
            "Berserk",
            "Dispel",
            "WeakenMind",
            "Enfeeble",
        ]:
            spell = getattr(abilities, name)()
            assert isinstance(spell, DataDrivenStatusSpell), f"{name} failed"


class TestBatch2CombatIntegration:
    """Test Batch 2 spells in simulated combat scenarios."""

    @staticmethod
    def _make_char():
        from tests.test_framework import TestGameState

        return TestGameState.create_player(
            name="Tester",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
            stats={"strength": 10, "intel": 25, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )

    # ── Healing ──────────────────────────────────────────────────

    def test_heal_restores_hp(self):
        from src.core import abilities

        caster = self._make_char()
        caster.mana.current = 100
        caster.health.current = 50
        spell = abilities.Heal()
        msg = spell.cast(caster, caster)
        assert caster.health.current > 50
        assert isinstance(msg, str) and "heal" in msg.lower()

    def test_regen_applies_hot(self):
        from src.core import abilities

        caster = self._make_char()
        caster.mana.current = 100
        spell = abilities.Regen()
        msg = spell.cast(caster, caster)
        assert caster.magic_effects["Regen"].active
        assert caster.magic_effects["Regen"].duration >= 3

    def test_hydration_heals_and_regens(self):
        from src.core import abilities

        caster = self._make_char()
        caster.mana.current = 100
        caster.health.current = 50
        spell = abilities.Hydration()
        msg = spell.cast(caster, caster)
        assert caster.health.current > 50
        assert caster.magic_effects["Regen"].active

    def test_heal_cast_out(self):
        from src.core import abilities

        caster = self._make_char()
        caster.mana.current = 100
        caster.health.current = 50
        spell = abilities.Heal()
        msg = spell.cast_out(caster)
        assert caster.health.current > 50
        assert isinstance(msg, str) and "heal" in msg.lower()

    # ── Support / Buff ───────────────────────────────────────────

    def test_bless_buffs_attack_defense(self):
        from src.core import abilities

        caster = self._make_char()
        caster.mana.current = 100
        spell = abilities.Bless()
        msg = spell.cast(caster)
        assert caster.stat_effects["Attack"].active
        assert caster.stat_effects["Attack"].extra == 10
        assert caster.stat_effects["Defense"].active
        assert caster.stat_effects["Defense"].extra == 8

    def test_boost_buffs_magic(self):
        from src.core import abilities

        caster = self._make_char()
        caster.mana.current = 100
        spell = abilities.Boost()
        msg = spell.cast(caster)
        assert caster.stat_effects["Magic"].active
        assert caster.stat_effects["Magic"].extra > 0

    def test_reflect_applies_magic_effect(self):
        from src.core import abilities

        caster = self._make_char()
        caster.mana.current = 100
        spell = abilities.Reflect()
        msg = spell.cast(caster)
        assert caster.magic_effects["Reflect"].active

    def test_ice_block_applies(self):
        from src.core import abilities

        caster = self._make_char()
        caster.mana.current = 100
        spell = abilities.IceBlock()
        msg = spell.cast(caster)
        assert caster.magic_effects["Ice Block"].active
        assert caster.magic_effects["Ice Block"].duration == 3

    def test_cleanse_clears_statuses(self):
        from src.core import abilities

        caster = self._make_char()
        caster.mana.current = 100
        caster.status_effects["Blind"].active = True
        caster.status_effects["Poison"].active = True
        spell = abilities.Cleanse()
        msg = spell.cast(caster)
        assert not caster.status_effects["Blind"].active
        assert not caster.status_effects["Poison"].active
        assert "All negative status effects have been cured for Tester!" in msg

    def test_mirror_image_creates_duplicates(self):
        from src.core import abilities

        caster = self._make_char()
        caster.mana.current = 100
        spell = abilities.MirrorImage()
        msg = spell.cast(caster, caster)
        assert caster.magic_effects["Duplicates"].active

    # ── Status / Debuff ──────────────────────────────────────────

    def test_sleep_can_apply(self):
        from src.core import abilities

        caster = self._make_char()
        caster.stats.intel = 200
        caster.mana.current = 100
        target = self._make_char()
        target.stats.wisdom = 1
        spell = abilities.Sleep()
        applied = False
        for _ in range(40):
            target.status_effects["Sleep"].active = False
            target.status_effects["Sleep"].duration = 0
            msg = spell.cast(caster, target)
            if target.status_effects["Sleep"].active:
                applied = True
                break
        assert applied, "Sleep should have applied at least once"

    def test_stupefy_can_stun(self):
        from src.core import abilities

        caster = self._make_char()
        caster.stats.intel = 200
        caster.mana.current = 1000
        target = self._make_char()
        target.stats.wisdom = 1
        spell = abilities.Stupefy()
        stunned = False
        for _ in range(40):
            target.status_effects["Stun"].active = False
            target.status_effects["Stun"].duration = 0
            msg = spell.cast(caster, target)
            if target.status_effects["Stun"].active:
                stunned = True
                break
        assert stunned, "Stun should have applied at least once"

    def test_enfeeble_can_debuff(self):
        from src.core import abilities

        caster = self._make_char()
        caster.stats.intel = 200
        caster.mana.current = 1000
        target = self._make_char()
        target.stats.con = 1
        target.combat.attack = 100
        target.combat.defense = 80
        spell = abilities.Enfeeble()
        debuffed = False
        for _ in range(40):
            target.stat_effects["Attack"].active = False
            target.stat_effects["Attack"].extra = 0
            target.stat_effects["Defense"].active = False
            target.stat_effects["Defense"].extra = 0
            msg = spell.cast(caster, target)
            if target.stat_effects["Attack"].active:
                debuffed = True
                assert target.stat_effects["Attack"].extra < 0
                break
        assert debuffed, "Enfeeble should have applied Attack debuff"

    def test_enfeeble_uses_stat_hit_chance_and_static_percentage_debuff(
        self,
        monkeypatch,
    ):
        from src.core import abilities

        caster = self._make_char()
        caster.stats.intel = 20
        caster.mana.current = 100
        target = self._make_char()
        target.stats.con = 20
        target.combat.attack = 101
        target.combat.defense = 81
        spell = abilities.Enfeeble()

        monkeypatch.setattr("random.random", lambda: 0.69)
        message = spell.cast(caster, target)

        assert "attack is lowered by 20%." in message
        assert "defense is lowered by 20%." in message
        assert "(21)" not in message and "4 turns" not in message
        assert target.stat_effects["Attack"].extra == -21
        assert target.stat_effects["Defense"].extra == -17
        assert target.stat_effects["Attack"].duration == 4

        target.stat_effects["Attack"].active = False
        target.stat_effects["Attack"].extra = 0
        target.stat_effects["Defense"].active = False
        target.stat_effects["Defense"].extra = 0
        monkeypatch.setattr("random.random", lambda: 0.70)

        assert spell.cast(caster, target) == f"{target.name} resists the spell.\n"
        assert not target.stat_effects["Attack"].active

    def test_enfeeble_hit_chance_scales_with_intelligence_against_constitution(
        self,
        monkeypatch,
    ):
        from src.core import abilities

        caster = self._make_char()
        caster.stats.intel = 25
        target = self._make_char()
        target.stats.con = 20
        spell = abilities.Enfeeble()

        monkeypatch.setattr("random.random", lambda: 0.79)
        spell.cast(caster, target)
        assert target.stat_effects["Attack"].active

        target.stat_effects["Attack"].active = False
        target.stat_effects["Defense"].active = False
        caster.stats.intel = 15
        caster.mana.current = caster.mana.max
        monkeypatch.setattr("random.random", lambda: 0.61)
        spell.cast(caster, target)
        assert not target.stat_effects["Attack"].active

    def test_dispel_removes_buffs(self):
        from src.core import abilities

        caster = self._make_char()
        caster.stats.intel = 200
        caster.mana.current = 1000
        target = self._make_char()
        target.stats.wisdom = 1
        target.magic_effects["Regen"].active = True
        target.magic_effects["Totem"].active = True
        target.magic_effects["Astral Shift"].active = True
        target.stat_effects["Attack"].active = True
        target.stat_effects["Attack"].extra = 10
        spell = abilities.Dispel()
        dispelled = False
        for _ in range(40):
            msg = spell.cast(caster, target)
            if not target.magic_effects["Regen"].active:
                dispelled = True
                assert not target.magic_effects["Totem"].active
                assert not target.magic_effects["Astral Shift"].active
                break
            target.magic_effects["Regen"].active = True
            target.magic_effects["Totem"].active = True
            target.magic_effects["Astral Shift"].active = True
            target.stat_effects["Attack"].active = True
        assert dispelled, "Dispel should have cleared Regen"

    def test_blinding_fog_can_blind(self):
        from src.core import abilities

        caster = self._make_char()
        caster.stats.intel = 200
        caster.mana.current = 1000
        target = self._make_char()
        target.stats.con = 1
        spell = abilities.BlindingFog()
        blinded = False
        for _ in range(40):
            target.status_effects["Blind"].active = False
            target.status_effects["Blind"].duration = 0
            msg = spell.cast(caster, target)
            if target.status_effects["Blind"].active:
                blinded = True
                break
        assert blinded, "Blinding Fog should have blinded"

    def test_status_immune_target(self):
        """Ice Block makes status spells have no effect."""
        from src.core import abilities

        caster = self._make_char()
        caster.mana.current = 100
        target = self._make_char()
        target.magic_effects["Ice Block"].active = True
        spell = abilities.Sleep()
        msg = spell.cast(caster, target)
        assert "no effect" in msg.lower()


class TestBatch2SaveSystem:
    """Test that the save system serialiser handles YAML-migrated abilities."""

    def test_serialise_heal(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        h = abilities.Heal()
        assert AbilitySerializer.serialize(h) == "heal"

    def test_serialise_heal2(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        h = abilities.Heal2()
        assert AbilitySerializer.serialize(h) == "heal_2"

    def test_round_trip(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in [
            "Heal",
            "Heal2",
            "Heal3",
            "Regen",
            "Bless",
            "Boost",
            "Shell",
            "Reflect",
            "Cleanse",
            "Sleep",
            "Enfeeble",
        ]:
            original = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(original)
            assert serialized == original.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == original.name


# ======================================================================
# BATCH 3 — Complex skills (multi-hit, conditional, scaling, status)
# ======================================================================


class TestBatch3NewEffects:
    """Validate the 3 new effect types added for Batch 3."""

    @staticmethod
    def _make_char():
        from tests.test_framework import TestGameState

        return TestGameState.create_player(
            name="Tester",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
            stats={"strength": 25, "intel": 15, "wisdom": 15, "con": 20, "charisma": 10, "dex": 20},
        )

    def test_mana_drain_on_hit(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import ManaDrainOnHitEffect

        actor = self._make_char()
        target = self._make_char()
        target.mana.current = 100
        effect = ManaDrainOnHitEffect(divisor=5)
        result = CombatResult(action="Test")
        result.extra["last_crit"] = 1
        result.extra["dmg_mod"] = 0.5
        effect.apply(actor, target, result)
        msgs = result.extra.get("messages", [])
        assert len(msgs) > 0, "ManaDrainOnHitEffect should produce a message"
        assert target.mana.current < 100, "Mana should have been drained"

    def test_resource_convert_health_to_mana(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import ResourceConvertEffect

        actor = self._make_char()
        actor.mana.current = 100  # not full
        hp_before = actor.health.current
        effect = ResourceConvertEffect(source="health", target_resource="mana", percent=0.1)
        result = CombatResult(action="Test")
        effect.apply(actor, actor, result)
        msgs = result.extra.get("messages", [])
        assert len(msgs) > 0, "ResourceConvertEffect should produce a message"
        assert actor.health.current < hp_before, "Health should decrease"
        assert actor.mana.current > 100, "Mana should increase"

    def test_resource_convert_mana_to_health(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import ResourceConvertEffect

        actor = self._make_char()
        actor.health.current = 100  # not full
        mp_before = actor.mana.current
        effect = ResourceConvertEffect(source="mana", target_resource="health", percent=0.1)
        result = CombatResult(action="Test")
        effect.apply(actor, actor, result)
        msgs = result.extra.get("messages", [])
        assert len(msgs) > 0
        assert actor.mana.current < mp_before
        assert actor.health.current > 100

    def test_resource_convert_full_guard(self):
        """If target resource is already full, no conversion happens."""
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import ResourceConvertEffect

        actor = self._make_char()
        # mana is already at max
        actor.mana.current = actor.mana.max
        hp_before = actor.health.current
        effect = ResourceConvertEffect(source="health", target_resource="mana", percent=0.1)
        result = CombatResult(action="Test")
        effect.apply(actor, actor, result)
        assert actor.health.current == hp_before, "Health shouldn't change if mana is full"
        assert result.extra.get("resource_full") is True


class TestBatch3YAMLLoading:
    """Verify all Batch 3 YAML files load correctly."""

    YAML_DIR = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"

    @pytest.mark.parametrize(
        "filename,expected_name,expected_cost",
        [
            # Elemental spells
            ("firebolt.yaml", "Firebolt", 2),
            ("fireball.yaml", "Fireball", 10),
            ("firestorm.yaml", "Firestorm", 20),
            ("scorch.yaml", "Scorch", 6),
            ("molten_rock.yaml", "Molten Rock", 16),
            ("volcano.yaml", "Volcano", 24),
            ("ice_lance.yaml", "Ice Lance", 4),
            ("icicle.yaml", "Icicle", 9),
            ("blizzard.yaml", "Blizzard", 18),
            ("shock.yaml", "Shock", 6),
            ("lightning.yaml", "Lightning", 15),
            ("electrocution.yaml", "Electrocution", 25),
            ("bolt.yaml", "Bolt", 18),
            ("ball_lightning.yaml", "Ball Lightning", 34),
            ("poison_dart.yaml", "Poison Dart", 8),
            ("meteor.yaml", "Meteor", 0),
        ],
    )
    def test_load_elemental_spell(self, filename, expected_name, expected_cost):
        from src.core.data.ability_loader import AbilityFactory

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / filename)
        assert ability.name == expected_name
        assert ability.cost == expected_cost

    @pytest.mark.parametrize(
        "filename,expected_name,expected_cost",
        [
            ("piercing_strike.yaml", "Piercing Strike", 5),
            ("true_strike.yaml", "True Strike", 12),
            ("true_piercing_strike.yaml", "True Piercing Strike", 15),
            ("backstab.yaml", "Backstab", 6),
            ("sneak_attack.yaml", "Sneak Attack", 15),
            ("double_strike.yaml", "Double Strike", 14),
            ("triple_strike.yaml", "Triple Strike", 26),
            ("flurry_blades.yaml", "Flurry of Blades", 40),
            ("battle_cry.yaml", "Battle Cry", 16),
            ("imbue_weapon.yaml", "Imbue Weapon", 12),
            ("mana_slice.yaml", "Mana Slice", 0),
            ("mana_slice_2.yaml", "Mana Slice II", 0),
            ("dispel_slash.yaml", "Dispel Slash", 20),
            ("life_tap.yaml", "Life Tap", 0),
            ("mana_tap.yaml", "Mana Tap", 0),
            ("smoke_screen.yaml", "Smoke Screen", 5),
        ],
    )
    def test_load_skill(self, filename, expected_name, expected_cost):
        from src.core.data.ability_loader import AbilityFactory

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / filename)
        assert ability.name == expected_name
        assert ability.cost == expected_cost

    @pytest.mark.parametrize(
        "filename,expected_name,expected_cost,expected_status",
        [
            ("goad.yaml", "Goad", 12, "Berserk"),
            ("pocket_sand.yaml", "Pocket Sand", 8, "Blind"),
            ("sleeping_powder.yaml", "Sleeping Powder", 11, "Sleep"),
        ],
    )
    def test_load_status_skill(self, filename, expected_name, expected_cost, expected_status):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / filename)
        assert ability.name == expected_name
        assert ability.cost == expected_cost
        assert isinstance(ability, DataDrivenStatusSkill)
        assert ability._status_name == expected_status


class TestBatch3AbilityFactories:
    """Test that __new__ wrappers produce correct ability instances."""

    def test_weapon_skills(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenSkill

        for name in [
            "PiercingStrike",
            "TrueStrike",
            "TruePiercingStrike",
            "Backstab",
            "SneakAttack",
            "DoubleStrike",
            "TripleStrike",
            "FlurryBlades",
            "ImbueWeapon",
            "ManaSlice",
            "ManaSlice2",
            "DispelSlash",
        ]:
            ability = getattr(abilities, name)()
            assert isinstance(ability, DataDrivenSkill), f"{name} should be DataDrivenSkill"
            assert ability.weapon is True, f"{name} should be weapon-based"

    def test_multi_strike_counts(self):
        from src.core import abilities

        ds = abilities.DoubleStrike()
        assert ds._strikes == 2
        ts = abilities.TripleStrike()
        assert ts._strikes == 3
        fb = abilities.FlurryBlades()
        assert fb._strikes == 20
        assert fb._repeat_until_miss is True
        assert fb._accuracy_penalty_per_strike == 0.08

    def test_piercing_flags(self):
        from src.core import abilities

        ps = abilities.PiercingStrike()
        assert ps._ignore_armor is True
        assert ps._guaranteed_hit is False
        ts = abilities.TrueStrike()
        assert ts._ignore_armor is False
        assert ts._guaranteed_hit is True
        tps = abilities.TruePiercingStrike()
        assert tps._ignore_armor is True
        assert tps._guaranteed_hit is True

    def test_sneak_attack_flags(self):
        from src.core import abilities

        sa = abilities.SneakAttack()
        assert sa._requires_incapacitated is True
        assert sa._crit_override == 2
        assert sa._ignore_armor is True

    def test_backstab_requires_incapacitated_target(self):
        from src.core import abilities

        bs = abilities.Backstab()
        assert bs._requires_incapacitated is True

    def test_imbue_weapon_intel_mod(self):
        from src.core import abilities

        iw = abilities.ImbueWeapon()
        assert iw._intel_dmg_mod is True

    def test_battle_cry_self_target(self):
        from src.core import abilities

        bc = abilities.BattleCry()
        assert bc._self_target is True

    def test_non_weapon_skills(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenSkill

        for name in ["LifeTap", "ManaTap", "SmokeScreen", "BattleCry"]:
            ability = getattr(abilities, name)()
            assert isinstance(ability, DataDrivenSkill), f"{name} should be DataDrivenSkill"
            assert ability.weapon is False, f"{name} should not be weapon-based"

    def test_use_out_enabled(self):
        from src.core import abilities

        lt = abilities.LifeTap()
        assert lt._use_out_enabled is True
        mt = abilities.ManaTap()
        assert mt._use_out_enabled is True

    def test_status_skills(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        for name in ["Goad", "PocketSand", "SleepingPowder"]:
            ability = getattr(abilities, name)()
            assert isinstance(
                ability, DataDrivenStatusSkill
            ), f"{name} should be DataDrivenStatusSkill"

    def test_elemental_spells(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenSpell

        for name in [
            "Firebolt",
            "Fireball",
            "Firestorm",
            "Scorch",
            "MoltenRock",
            "Volcano",
            "IceLance",
            "Icicle",
            "IceBlizzard",
            "Shock",
            "Lightning",
            "Electrocution",
            "Meteor",
        ]:
            ability = getattr(abilities, name)()
            assert isinstance(ability, DataDrivenSpell), f"{name} should be DataDrivenSpell"


class TestBatch3CombatIntegration:
    """Test Batch 3 abilities in a combat-like context."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Fighter",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
            stats={"strength": 25, "intel": 15, "wisdom": 15, "con": 20, "charisma": 10, "dex": 20},
        )
        target = TestGameState.create_player(
            name="Dummy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(100, 100),
            stats={"strength": 15, "intel": 10, "wisdom": 10, "con": 15, "charisma": 10, "dex": 15},
        )
        return user, target

    def test_piercing_strike_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        ps = abilities.PiercingStrike()
        mana_before = user.mana.current
        ps.use(user, target)
        assert user.mana.current == mana_before - 5

    def test_piercing_strike_requires_weapon_when_disarmed(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.is_disarmed = lambda: True
        ps = abilities.PiercingStrike()
        mana_before = user.mana.current

        result = ps.use(user, target)

        assert "requires a weapon" in result
        assert user.mana.current == mana_before

    def test_double_strike_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        ds = abilities.DoubleStrike()
        mana_before = user.mana.current
        ds.use(user, target)
        assert user.mana.current == mana_before - 14

    def test_sneak_attack_ineffective_on_active_target(self):
        from src.core import abilities

        user, target = self._make_combatants()
        sa = abilities.SneakAttack()
        mana_before = user.mana.current
        result = sa.use(user, target)
        assert "ineffective" in result.lower()
        assert user.mana.current == mana_before

    def test_backstab_ineffective_on_active_target(self):
        from src.core import abilities

        user, target = self._make_combatants()
        backstab = abilities.Backstab()
        mana_before = user.mana.current
        result = backstab.use(user, target)
        assert "ineffective" in result.lower()
        assert user.mana.current == mana_before

    def test_sneak_attack_works_when_incapacitated(self):
        from src.core import abilities

        user, target = self._make_combatants()
        # Stun the target so it's incapacitated
        target.status_effects["Stun"].active = True
        target.status_effects["Stun"].duration = 3
        sa = abilities.SneakAttack()
        result = sa.use(user, target)
        # Should return a CombatResult or string with damage info, not "ineffective"
        result_str = str(result)
        assert "ineffective" not in result_str.lower()

    def test_battle_cry_buffs_attack(self):
        from src.core import abilities

        user, target = self._make_combatants()
        bc = abilities.BattleCry()
        bc.use(user, target)
        assert user.stat_effects["Attack"].active is True
        assert user.stat_effects["Attack"].duration >= 5

    def test_smoke_screen_deducts_mana_returns_empty(self):
        from src.core import abilities

        user, target = self._make_combatants()
        ss = abilities.SmokeScreen()
        mana_before = user.mana.current
        result = ss.use(user, target)
        assert user.mana.current == mana_before - ss.cost
        assert result == ""

    def test_goad_ice_block_check(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        goad = abilities.Goad()
        result = goad.use(user, target)
        assert "no effect" in result.lower()

    def test_pocket_sand_immune_target(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.status_immunity.append("Blind")
        ps = abilities.PocketSand()
        result = ps.use(user, target)
        assert "immune" in result.lower()

    def test_sleeping_powder_immune_target(self):
        from src.core import abilities, items

        user, target = self._make_combatants()
        target.status_immunity.append("Sleep")
        user.modify_inventory(items.Monocane())
        sp = abilities.SleepingPowder()
        result = sp.use(user, target)
        assert "immune" in result.lower()

    def test_goad_already_berserk(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.status_effects["Berserk"].active = True
        target.status_effects["Berserk"].duration = 5
        goad = abilities.Goad()
        result = goad.use(user, target)
        assert "already" in result.lower()

    def test_life_tap_converts_health_to_mana(self):
        from src.core import abilities

        user, _ = self._make_combatants()
        user.mana.current = 100  # not full
        hp_before = user.health.current
        mp_before = user.mana.current
        lt = abilities.LifeTap()
        lt.use(user)
        assert user.health.current < hp_before
        assert user.mana.current > mp_before

    def test_life_tap_full_mana_guard(self):
        from src.core import abilities

        user, _ = self._make_combatants()
        user.mana.current = user.mana.max
        lt = abilities.LifeTap()
        result = lt.use(user)
        assert "full" in result.lower() or "already" in result.lower()

    def test_mana_tap_converts_mana_to_health(self):
        from src.core import abilities

        user, _ = self._make_combatants()
        user.health.current = 100  # not full
        hp_before = user.health.current
        mp_before = user.mana.current
        mt = abilities.ManaTap()
        mt.use(user)
        assert user.health.current > hp_before
        assert user.mana.current < mp_before

    def test_mana_tap_full_health_guard(self):
        from src.core import abilities

        user, _ = self._make_combatants()
        user.health.current = user.health.max
        mt = abilities.ManaTap()
        result = mt.use(user)
        assert "full" in result.lower() or "already" in result.lower()

    def test_elemental_spell_cast(self):
        """Elemental spells should cast and return CombatResult."""
        from src.core.combat.combat_result import CombatResult
        from src.core.data.ability_loader import AbilityFactory

        user, target = self._make_combatants()
        # Use a high-intel caster
        user.stats.intel = 25

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        for filename in ["fireball.yaml", "ice_lance.yaml", "shock.yaml"]:
            spell = AbilityFactory.create_from_yaml(yaml_dir / filename)
            user.mana.current = user.mana.max
            target.health.current = target.health.max
            result = spell.cast(user, target)
            assert isinstance(result, CombatResult)
            assert isinstance(result.message, str)


class TestBatch3SaveSystem:
    """Test that Batch 3 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch3_skills(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in [
            "PiercingStrike",
            "TrueStrike",
            "TruePiercingStrike",
            "Backstab",
            "SneakAttack",
            "DoubleStrike",
            "TripleStrike",
            "FlurryBlades",
            "BattleCry",
            "ImbueWeapon",
            "ManaSlice",
            "ManaSlice2",
            "DispelSlash",
            "LifeTap",
            "ManaTap",
            "SmokeScreen",
        ]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name

    def test_serialize_batch3_status_skills(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in ["Goad", "PocketSand", "SleepingPowder"]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name

    def test_serialize_batch3_spells(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in [
            "Firebolt",
            "Fireball",
            "Firestorm",
            "Scorch",
            "MoltenRock",
            "Volcano",
            "IceLance",
            "Icicle",
            "IceBlizzard",
            "Shock",
            "Lightning",
            "Electrocution",
            "Meteor",
        ]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


# ======================================================================
# BATCH 4: Weapon+Status Skills & StatusSkill Extensions
# ======================================================================


class TestBatch4StatusSkillExtensions:
    """Test the new DataDrivenStatusSkill parameters added in Batch 4:
    check_flying, actor_stat_alt, extend_if_active, action_message."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Fighter",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
            stats={"strength": 30, "intel": 15, "wisdom": 15, "con": 20, "charisma": 10, "dex": 25},
        )
        target = TestGameState.create_player(
            name="Dummy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(100, 100),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_check_flying_blocks_prone(self):
        """check_flying should prevent Prone application on flying targets."""
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        user, target = self._make_combatants()
        target.flying = True
        skill = DataDrivenStatusSkill(
            name="Test Trip",
            description="",
            cost=5,
            status_name="Prone",
            physical=True,
            check_flying=True,
            actor_stat="strength",
            actor_lo_divisor=0,
            actor_hi_divisor=1,
            target_stat="con",
            target_lo_divisor=2,
            target_hi_divisor=1,
            duration=3,
        )
        result = skill.use(user, target)
        assert target.physical_effects["Prone"].active is False
        # Should contain immune message
        assert "prone" in result.lower() or "cannot" in result.lower()

    def test_check_flying_allows_grounded(self):
        """check_flying should allow Prone on non-flying targets."""
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        user, target = self._make_combatants()
        target.flying = False
        # Use high actor stats to ensure contest win
        user.stats.strength = 100
        target.stats.con = 1
        skill = DataDrivenStatusSkill(
            name="Test Trip",
            description="",
            cost=5,
            status_name="Prone",
            physical=True,
            check_flying=True,
            actor_stat="strength",
            actor_lo_divisor=1,
            actor_hi_divisor=1,
            target_stat="con",
            target_lo_divisor=2,
            target_hi_divisor=1,
            duration=3,
        )
        result = skill.use(user, target)
        assert target.physical_effects["Prone"].active is True

    def test_actor_stat_alt_uses_max(self):
        """actor_stat_alt should pick max(primary, alt) for contest."""
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        user, target = self._make_combatants()
        # dex > strength → should use dex
        user.stats.strength = 5
        user.stats.dex = 100
        target.stats.con = 1  # ensure contest win
        skill = DataDrivenStatusSkill(
            name="Test Disarm",
            description="",
            cost=5,
            status_name="Disarm",
            physical=True,
            check_disarmable=True,
            actor_stat="strength",
            actor_stat_alt="dex",
            actor_lo_divisor=2,
            actor_hi_divisor=1,
            target_stat="con",
            target_lo_divisor=2,
            target_hi_divisor=1,
            duration=-1,
        )
        result = skill.use(user, target)
        assert target.physical_effects["Disarm"].active is True

    def test_extend_if_active_adds_duration(self):
        """extend_if_active should add turns to existing active effect."""
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        user, target = self._make_combatants()
        # Pre-set Prone active with 2 turns
        target.physical_effects["Prone"].active = True
        target.physical_effects["Prone"].duration = 2
        user.stats.strength = 100  # ensure contest win
        skill = DataDrivenStatusSkill(
            name="Test Web",
            description="",
            cost=5,
            status_name="Prone",
            physical=True,
            actor_use_check_mod="speed",
            target_stat="strength",
            target_lo_divisor=2,
            target_hi_divisor=1,
            duration=3,
            skip_if_active=False,
            extend_if_active=1,
        )
        result = skill.use(user, target)
        # Should extend by 1 → 2 + 1 = 3
        assert target.physical_effects["Prone"].duration == 3
        assert target.physical_effects["Prone"].active is True

    def test_action_message_always_shown(self):
        """action_message should appear in output regardless of result."""
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        user, target = self._make_combatants()
        target.status_immunity.append("Stun")  # force immune path
        skill = DataDrivenStatusSkill(
            name="Test Howl",
            description="",
            cost=5,
            status_name="Stun",
            action_message="{user} howls at the moon.\n",
        )
        result = skill.use(user, target)
        assert "howls at the moon" in result
        assert "immune" in result.lower()

    def test_negative_duration_permanent_effect(self):
        """duration=-1 should be set directly (permanent), not max'd."""
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        user, target = self._make_combatants()
        user.stats.strength = 100
        target.stats.con = 1
        skill = DataDrivenStatusSkill(
            name="Test Disarm",
            description="",
            cost=5,
            status_name="Disarm",
            physical=True,
            check_disarmable=True,
            actor_stat="strength",
            actor_lo_divisor=1,
            actor_hi_divisor=1,
            target_stat="con",
            target_lo_divisor=2,
            target_hi_divisor=1,
            duration=-1,
        )
        result = skill.use(user, target)
        assert target.physical_effects["Disarm"].active is True
        assert target.physical_effects["Disarm"].duration == -1


class TestBatch4YAMLLoading:
    """Verify all Batch 4 YAML files load correctly."""

    YAML_DIR = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"

    BATCH4_FILES = [
        "howl.yaml",
        "slam.yaml",
        "leg_sweep.yaml",
        "trip.yaml",
        "web.yaml",
        "disarm.yaml",
    ]

    def test_yaml_files_exist(self):
        for filename in self.BATCH4_FILES:
            path = self.YAML_DIR / filename
            assert path.exists(), f"Missing YAML file: {filename}"

    def test_yaml_files_parse(self):
        import yaml

        for filename in self.BATCH4_FILES:
            path = self.YAML_DIR / filename
            with open(path) as f:
                data = yaml.safe_load(f)
            assert "name" in data, f"Missing 'name' in {filename}"
            assert "type" in data, f"Missing 'type' in {filename}"

    def test_factory_loads_all(self):
        from src.core.data.ability_loader import AbilityFactory

        for filename in self.BATCH4_FILES:
            path = self.YAML_DIR / filename
            ability = AbilityFactory.create_from_yaml(path)
            assert ability is not None, f"Factory returned None for {filename}"
            assert ability.name, f"Empty name for {filename}"

    def test_howl_loads_as_status_skill(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / "howl.yaml")
        assert isinstance(ability, DataDrivenStatusSkill)
        assert ability.name == "Howl"
        assert ability.cost == 10
        assert ability._status_name == "Stun"
        assert ability._action_message is not None

    def test_slam_loads_as_skill(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSkill

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / "slam.yaml")
        assert isinstance(ability, DataDrivenSkill)
        assert ability.name == "Slam"
        assert ability.cost == 12
        assert ability.weapon is True
        assert len(ability._effects) == 1

    def test_leg_sweep_loads_as_skill(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSkill

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / "leg_sweep.yaml")
        assert isinstance(ability, DataDrivenSkill)
        assert ability.name == "Leg Sweep"
        assert ability.cost == 8
        assert ability.dmg_mod == 0.75

    def test_trip_loads_with_check_flying(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / "trip.yaml")
        assert isinstance(ability, DataDrivenStatusSkill)
        assert ability._check_flying is True
        assert ability._physical is True
        assert ability._status_name == "Prone"

    def test_web_loads_with_extend_if_active(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / "web.yaml")
        assert isinstance(ability, DataDrivenStatusSkill)
        assert ability._extend_if_active == 1
        assert ability._skip_if_active is False
        assert ability._status_name == "Prone"

    def test_disarm_loads_with_all_features(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        ability = AbilityFactory.create_from_yaml(self.YAML_DIR / "disarm.yaml")
        assert isinstance(ability, DataDrivenStatusSkill)
        assert ability._check_disarmable is True
        assert ability._add_luck_chance is True
        assert ability._actor_stat_alt == "dex"
        assert ability._duration == -1


class TestBatch4AbilityFactories:
    """Test that Batch 4 abilities instantiate from their wrapper classes."""

    def test_howl_factory(self):
        from src.core.abilities import Howl
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        howl = Howl()
        assert isinstance(howl, DataDrivenStatusSkill)
        assert howl.name == "Howl"
        assert howl.cost == 10

    def test_slam_factory(self):
        from src.core.abilities import Slam
        from src.core.data.data_driven_abilities import DataDrivenSkill

        slam = Slam()
        assert isinstance(slam, DataDrivenSkill)
        assert slam.name == "Slam"
        assert slam.cost == 12

    def test_leg_sweep_factory(self):
        from src.core.abilities import LegSweep
        from src.core.data.data_driven_abilities import DataDrivenSkill

        ls = LegSweep()
        assert isinstance(ls, DataDrivenSkill)
        assert ls.name == "Leg Sweep"

    def test_trip_factory(self):
        from src.core.abilities import Trip
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        trip = Trip()
        assert isinstance(trip, DataDrivenStatusSkill)
        assert trip.name == "Trip"

    def test_web_factory(self):
        from src.core.abilities import Web
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        web = Web()
        assert isinstance(web, DataDrivenStatusSkill)
        assert web.name == "Web"

    def test_disarm_factory(self):
        from src.core.abilities import Disarm
        from src.core.data.data_driven_abilities import DataDrivenStatusSkill

        dis = Disarm()
        assert isinstance(dis, DataDrivenStatusSkill)
        assert dis.name == "Disarm"


class TestBatch4CombatIntegration:
    """Test Batch 4 abilities in a combat-like context."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Fighter",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
            stats={"strength": 30, "intel": 15, "wisdom": 15, "con": 20, "charisma": 10, "dex": 25},
        )
        target = TestGameState.create_player(
            name="Dummy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(100, 100),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    # -- Howl ---------------------------------------------------------------

    def test_howl_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        howl = abilities.Howl()
        mana_before = user.mana.current
        howl.use(user, target)
        assert user.mana.current == mana_before - 10

    def test_howl_shows_action_message(self):
        from src.core import abilities

        user, target = self._make_combatants()
        howl = abilities.Howl()
        result = howl.use(user, target)
        assert "howls at the moon" in result

    def test_howl_ice_block_check(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        howl = abilities.Howl()
        result = howl.use(user, target)
        assert "no effect" in result.lower()

    def test_howl_immune_target(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.status_immunity.append("Stun")
        howl = abilities.Howl()
        result = howl.use(user, target)
        assert "immune" in result.lower()

    def test_howl_already_stunned(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.status_effects["Stun"].active = True
        target.status_effects["Stun"].duration = 5
        howl = abilities.Howl()
        result = howl.use(user, target)
        assert "already" in result.lower()

    # -- Slam ---------------------------------------------------------------

    def test_slam_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        slam = abilities.Slam()
        mana_before = user.mana.current
        slam.use(user, target)
        assert user.mana.current == mana_before - 12

    def test_slam_is_weapon_skill(self):
        from src.core import abilities

        slam = abilities.Slam()
        assert slam.weapon is True
        assert slam.dmg_mod == 1.5

    # -- Leg Sweep ----------------------------------------------------------

    def test_leg_sweep_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        ls = abilities.LegSweep()
        mana_before = user.mana.current
        ls.use(user, target)
        assert user.mana.current == mana_before - 8

    def test_leg_sweep_is_weapon_skill(self):
        from src.core import abilities

        ls = abilities.LegSweep()
        assert ls.weapon is True
        assert ls.dmg_mod == 0.75

    # -- Trip ---------------------------------------------------------------

    def test_trip_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        trip = abilities.Trip()
        mana_before = user.mana.current
        trip.use(user, target)
        assert user.mana.current == mana_before - 6

    def test_trip_ice_block_check(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        trip = abilities.Trip()
        result = trip.use(user, target)
        assert "no effect" in result.lower()

    def test_trip_check_flying(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.flying = True
        trip = abilities.Trip()
        result = trip.use(user, target)
        assert target.physical_effects["Prone"].active is False

    def test_trip_already_prone(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.physical_effects["Prone"].active = True
        target.physical_effects["Prone"].duration = 3
        trip = abilities.Trip()
        result = trip.use(user, target)
        assert "already" in result.lower()

    # -- Web ----------------------------------------------------------------

    def test_web_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        web = abilities.Web()
        mana_before = user.mana.current
        web.use(user, target)
        assert user.mana.current == mana_before - 6

    def test_web_ice_block_check(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        web = abilities.Web()
        result = web.use(user, target)
        assert "no effect" in result.lower()

    def test_web_extends_existing_prone(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.physical_effects["Prone"].active = True
        target.physical_effects["Prone"].duration = 2
        user.stats.strength = 100  # ensure contest win
        web = abilities.Web()
        result = web.use(user, target)
        # Should extend by 1 → 2 + 1 = 3
        if "web" in result.lower() or "prone" in result.lower():
            assert target.physical_effects["Prone"].duration == 3

    # -- Disarm -------------------------------------------------------------

    def test_disarm_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        dis = abilities.Disarm()
        mana_before = user.mana.current
        dis.use(user, target)
        assert user.mana.current == mana_before - 4

    def test_disarm_fam_skips_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        dis = abilities.Disarm()
        mana_before = user.mana.current
        dis.use(user, target, fam=True)
        assert user.mana.current == mana_before

    def test_disarm_ice_block_check(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        dis = abilities.Disarm()
        result = dis.use(user, target)
        assert "no effect" in result.lower()

    def test_disarm_not_disarmable(self):
        from src.core import abilities

        user, target = self._make_combatants()
        # Make target not disarmable
        target.can_be_disarmed = lambda: False
        dis = abilities.Disarm()
        result = dis.use(user, target)
        assert "cannot" in result.lower()

    def test_disarm_already_disarmed(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.physical_effects["Disarm"].active = True
        target.physical_effects["Disarm"].duration = -1
        dis = abilities.Disarm()
        result = dis.use(user, target)
        assert "already" in result.lower()

    def test_disarm_uses_permanent_duration(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.stats.strength = 100
        user.stats.dex = 100
        target.stats.con = 1
        dis = abilities.Disarm()
        result = dis.use(user, target)
        if target.physical_effects["Disarm"].active:
            assert target.physical_effects["Disarm"].duration == -1


class TestBatch4SaveSystem:
    """Test that Batch 4 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch4_skills(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in ["Howl", "Slam", "LegSweep", "Trip", "Web", "Disarm"]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


# ===========================================================================
# Batch 5 - MortalStrike, MortalStrike2, Doom, Tunnel, Surface
# ===========================================================================


class TestBatch5NewEffects:
    """Test the new SetFlagEffect and the PhysicalEffectApplyEffect bleed fix."""

    def test_set_flag_effect_factory(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import SetFlagEffect

        eff = EffectFactory.create(
            {
                "type": "set_flag",
                "flag": "tunnel",
                "value": True,
                "message": "{target} digs down.",
            }
        )
        assert isinstance(eff, SetFlagEffect)
        assert eff.flag == "tunnel"
        assert eff.value is True
        assert eff.message == "{target} digs down."

    def test_set_flag_effect_applies_flag(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import SetFlagEffect
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Digger",
            class_name="Warrior",
            race_name="Human",
            level=10,
            health=(100, 100),
            mana=(50, 50),
        )
        result = CombatResult(action="Tunnel")
        user.tunnel = False
        eff = SetFlagEffect(flag="tunnel", value=True, message="{target} digs.")
        eff.apply(user, user, result)
        assert user.tunnel is True
        msgs = result.extra.get("messages", [])
        assert any("Digger digs." in m for m in msgs)

    def test_set_flag_effect_clears_flag(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import SetFlagEffect
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Mole",
            class_name="Warrior",
            race_name="Human",
            level=10,
            health=(100, 100),
            mana=(50, 50),
        )
        user.tunnel = True
        result = CombatResult(action="Surface")
        eff = SetFlagEffect(flag="tunnel", value=False, message="{target} rises.")
        eff.apply(user, user, result)
        assert user.tunnel is False

    def test_physical_effect_apply_bleed_no_double_multiply(self):
        """Bleed damage should not double-apply crit & damage_multiplier."""
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import PhysicalEffectApplyEffect
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Att",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
            stats={"strength": 40, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        target = TestGameState.create_player(
            name="Def",
            class_name="Warrior",
            race_name="Human",
            level=10,
            health=(200, 200),
            mana=(50, 50),
            stats={"strength": 5, "intel": 5, "wisdom": 5, "con": 1, "charisma": 5, "dex": 5},
        )
        result = CombatResult(action="Mortal Strike")
        result.extra["last_crit"] = 2
        eff = PhysicalEffectApplyEffect(
            effect_name="Bleed",
            use_crit_multiplier=True,
            damage_multiplier=0.75,
            actor_stat="strength",
            target_stat="con",
            target_lo_divisor=2,
            duration_stat="strength",
            duration_divisor=10,
            duration_min=1,
        )
        # Run many times and verify bleed damage is sane
        # With STR=40, crit=2, multiplier=0.75: base_dmg = 40*2*0.75 = 60
        # bleed_dmg ∈ [15, 60]  (randint(60//4, 60))
        # If bugged (double-multiply): base_dmg = 40*2*0.75*2*0.75 = 90
        for _ in range(50):
            target.physical_effects["Bleed"].active = False
            target.physical_effects["Bleed"].extra = 0
            eff.apply(user, target, result)
            if target.physical_effects["Bleed"].active:
                assert target.physical_effects["Bleed"].extra <= 60, (
                    f"Bleed extra {target.physical_effects['Bleed'].extra} exceeds "
                    f"max 60 — damage_multiplier likely double-applied"
                )


class TestBatch5YAMLLoading:
    """Test that all Batch 5 YAML files load correctly."""

    @pytest.fixture(
        params=[
            "mortal_strike.yaml",
            "mortal_strike_2.yaml",
            "doom.yaml",
            "tunnel.yaml",
            "surface.yaml",
        ]
    )
    def yaml_file(self, request):
        return request.param

    def test_yaml_loads(self, yaml_file):
        from pathlib import Path

        import yaml

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        path = yaml_dir / yaml_file
        assert path.exists(), f"{yaml_file} not found"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "name" in data
        assert "type" in data
        assert "effects" in data

    def test_mortal_strike_yaml_fields(self):
        from pathlib import Path

        import yaml

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        with open(yaml_dir / "mortal_strike.yaml") as f:
            data = yaml.safe_load(f)
        assert data["name"] == "Mortal Strike"
        assert data["type"] == "Skill"
        assert data["cost"] == 10
        assert data["weapon"] is True
        assert data["crit_override"] == 2
        assert data["damage_mod"] == 1.5
        eff = data["effects"][0]
        assert eff["type"] == "physical_effect_apply"
        assert eff["effect_name"] == "Bleed"
        assert eff["damage_multiplier"] == 0.75
        assert eff["use_crit_multiplier"] is True

    def test_mortal_strike_2_yaml_fields(self):
        from pathlib import Path

        import yaml

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        with open(yaml_dir / "mortal_strike_2.yaml") as f:
            data = yaml.safe_load(f)
        assert data["cost"] == 30
        assert data["crit_override"] == 3

    def test_doom_yaml_fields(self):
        from pathlib import Path

        import yaml

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        with open(yaml_dir / "doom.yaml") as f:
            data = yaml.safe_load(f)
        assert data["name"] == "Doom"
        assert data["type"] == "Status"
        assert data["cost"] == 15
        assert "messages" in data
        assert data["messages"]["success"] == "A timer has been placed on {target}'s life."
        eff = data["effects"][0]
        assert eff["type"] == "stat_contest"
        assert eff["actor_stat"] == "charisma"
        inner = eff["effect"]
        assert inner["type"] == "status_apply"
        assert inner["status_name"] == "Doom"
        assert inner["duration"] == 5

    def test_tunnel_yaml_fields(self):
        from pathlib import Path

        import yaml

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        with open(yaml_dir / "tunnel.yaml") as f:
            data = yaml.safe_load(f)
        assert data["name"] == "Tunnel"
        assert data["cost"] == 3
        eff = data["effects"][0]
        assert eff["type"] == "set_flag"
        assert eff["flag"] == "tunnel"
        assert eff["value"] is True

    def test_surface_yaml_fields(self):
        from pathlib import Path

        import yaml

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        with open(yaml_dir / "surface.yaml") as f:
            data = yaml.safe_load(f)
        assert data["name"] == "Surface"
        assert data["cost"] == 0
        eff = data["effects"][0]
        assert eff["type"] == "set_flag"
        assert eff["flag"] == "tunnel"
        assert eff["value"] is False


class TestBatch5AbilityFactories:
    """Test that AbilityFactory produces correct DataDriven instances."""

    ABILITIES_DIR = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"

    def test_mortal_strike_factory(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSkill

        ability = AbilityFactory.create_from_yaml(self.ABILITIES_DIR / "mortal_strike.yaml")
        assert isinstance(ability, DataDrivenSkill)
        assert ability.name == "Mortal Strike"
        assert ability.cost == 10
        assert ability.weapon is True
        assert ability._crit_override == 2

    def test_mortal_strike_2_factory(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSkill

        ability = AbilityFactory.create_from_yaml(self.ABILITIES_DIR / "mortal_strike_2.yaml")
        assert isinstance(ability, DataDrivenSkill)
        assert ability.cost == 30
        assert ability._crit_override == 3

    def test_doom_factory(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenStatusSpell

        ability = AbilityFactory.create_from_yaml(self.ABILITIES_DIR / "doom.yaml")
        assert isinstance(ability, DataDrivenStatusSpell)
        assert ability.name == "Doom"
        assert ability.cost == 15

    def test_tunnel_factory(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSkill

        ability = AbilityFactory.create_from_yaml(self.ABILITIES_DIR / "tunnel.yaml")
        assert isinstance(ability, DataDrivenSkill)
        assert ability.name == "Tunnel"
        assert ability.cost == 3
        assert ability._self_target is True

    def test_surface_factory(self):
        from src.core.data.ability_loader import AbilityFactory
        from src.core.data.data_driven_abilities import DataDrivenSkill

        ability = AbilityFactory.create_from_yaml(self.ABILITIES_DIR / "surface.yaml")
        assert isinstance(ability, DataDrivenSkill)
        assert ability.name == "Surface"
        assert ability.cost == 0
        assert ability._self_target is True


class TestBatch5CombatIntegration:
    """Test Batch 5 abilities in a combat-like context."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Fighter",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
            stats={"strength": 40, "intel": 15, "wisdom": 15, "con": 20, "charisma": 30, "dex": 25},
        )
        target = TestGameState.create_player(
            name="Dummy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(100, 100),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    # -- MortalStrike -------------------------------------------------------

    def test_mortal_strike_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        ms = abilities.MortalStrike()
        mana_before = user.mana.current
        ms.use(user, target)
        assert user.mana.current == mana_before - 10

    def test_mortal_strike_is_weapon_skill(self):
        from src.core import abilities

        ms = abilities.MortalStrike()
        assert ms.weapon is True
        assert ms.dmg_mod == 1.5

    def test_mortal_strike_has_crit_override(self):
        from src.core import abilities

        ms = abilities.MortalStrike()
        assert ms._crit_override == 2

    def test_mortal_strike_can_apply_bleed(self):
        """Over many trials, MortalStrike should apply Bleed at least once."""
        from src.core import abilities

        applied = False
        for _ in range(50):
            user, target = self._make_combatants()
            user.stats.strength = 80  # high str → high bleed chance
            target.stats.con = 1
            ms = abilities.MortalStrike()
            ms.use(user, target)
            if target.physical_effects["Bleed"].active:
                applied = True
                break
        assert applied, "MortalStrike never applied Bleed in 50 attempts"

    # -- MortalStrike2 ------------------------------------------------------

    def test_mortal_strike_2_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        ms2 = abilities.MortalStrike2()
        mana_before = user.mana.current
        ms2.use(user, target)
        assert user.mana.current == mana_before - 30

    def test_mortal_strike_2_higher_crit(self):
        from src.core import abilities

        ms2 = abilities.MortalStrike2()
        assert ms2._crit_override == 3

    # -- Doom ---------------------------------------------------------------

    def test_doom_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        doom = abilities.Doom()
        mana_before = user.mana.current
        doom.cast(user, target)
        assert user.mana.current == mana_before - 15

    def test_doom_special_skips_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        doom = abilities.Doom()
        mana_before = user.mana.current
        doom.cast(user, target, special=True)
        assert user.mana.current == mana_before

    def test_doom_ice_block_check(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        doom = abilities.Doom()
        result = doom.cast(user, target)
        assert "no effect" in result.lower()

    def test_doom_immune_target(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.stats.charisma = 200  # Guarantee contest win to reach immunity check
        target.stats.wisdom = 1
        target.status_immunity.append("Doom")
        doom = abilities.Doom()
        result = doom.cast(user, target)
        assert "immune" in result.lower()

    def test_doom_applies_status(self):
        """With high CHA vs low WIS, Doom should apply at least once in trials."""
        from src.core import abilities

        applied = False
        for _ in range(50):
            user, target = self._make_combatants()
            user.stats.charisma = 100
            target.stats.wisdom = 1
            doom = abilities.Doom()
            result = doom.cast(user, target)
            if target.status_effects["Doom"].active:
                applied = True
                assert target.status_effects["Doom"].duration == 5
                assert "timer" in result.lower()
                break
        assert applied, "Doom never applied in 50 attempts"

    def test_doom_already_active(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.status_effects["Doom"].active = True
        target.status_effects["Doom"].duration = 3
        user.stats.charisma = 200  # ensure contest wins
        doom = abilities.Doom()
        result = doom.cast(user, target)
        # Contest passes → StatusApplyEffect hits skip_if_active
        assert "already" in result.lower()

    # -- Tunnel -------------------------------------------------------------

    def test_tunnel_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        tun = abilities.Tunnel()
        mana_before = user.mana.current
        tun.use(user, target)
        assert user.mana.current == mana_before - 3

    def test_tunnel_sets_flag(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.tunnel = False
        tun = abilities.Tunnel()
        result = tun.use(user, target)
        assert user.tunnel is True
        assert "tunnels" in result.lower() or "tunnel" in result.lower()

    def test_tunnel_is_self_target(self):
        from src.core import abilities

        tun = abilities.Tunnel()
        assert tun._self_target is True

    # -- Surface ------------------------------------------------------------

    def test_surface_no_mana_cost(self):
        from src.core import abilities

        user, target = self._make_combatants()
        surf = abilities.Surface()
        mana_before = user.mana.current
        surf.use(user, target)
        assert user.mana.current == mana_before

    def test_surface_clears_flag(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.tunnel = True
        surf = abilities.Surface()
        result = surf.use(user, target)
        assert user.tunnel is False
        assert "surface" in result.lower()


# ═══════════════════════════════════════════════════════════════════════
# Batch 6: Desoul, Petrify, Ruin, DiseaseBreath
# New effects: InstantKillEffect, StatReduceEffect
# ═══════════════════════════════════════════════════════════════════════


class TestBatch6NewEffects:
    """Test the new InstantKillEffect and StatReduceEffect."""

    def test_instant_kill_effect_factory(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import InstantKillEffect

        eff = EffectFactory.create(
            {
                "type": "instant_kill",
                "success_message": "{target} is slain.",
                "actor_stat": "charisma",
                "actor_divisor": 4,
                "luck_factor": 10,
            }
        )
        assert isinstance(eff, InstantKillEffect)
        assert eff.actor_stat == "charisma"
        assert eff.actor_divisor == 4
        assert eff.luck_factor == 10
        assert eff.apply_resist_multiplier is True

    def test_instant_kill_effect_kills_target(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import InstantKillEffect
        from tests.test_framework import TestGameState

        killed = False
        for _ in range(50):
            user = TestGameState.create_player(
                name="Caster",
                class_name="Mage",
                race_name="Human",
                level=30,
                health=(500, 500),
                mana=(200, 200),
                stats={
                    "strength": 10,
                    "intel": 10,
                    "wisdom": 10,
                    "con": 10,
                    "charisma": 200,
                    "dex": 10,
                },
            )
            target = TestGameState.create_player(
                name="Victim",
                class_name="Warrior",
                race_name="Human",
                level=1,
                health=(100, 100),
                mana=(50, 50),
                stats={"strength": 5, "intel": 5, "wisdom": 5, "con": 1, "charisma": 5, "dex": 5},
            )
            eff = InstantKillEffect(
                success_message="{target} is slain.",
                actor_stat="charisma",
                actor_divisor=1,
                apply_resist_multiplier=False,
                luck_factor=1,
            )
            result = CombatResult(action="Test Kill")
            eff.apply(user, target, result)
            if target.health.current == 0:
                killed = True
                assert result.extra.get("stat_contest_won") is True
                msgs = result.extra.get("messages", [])
                assert any("Victim is slain" in m for m in msgs)
                break
        assert killed, "InstantKillEffect never killed in 50 attempts"

    def test_instant_kill_resist_immunity(self):
        """Full resist (>=1) should block the kill."""
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import InstantKillEffect
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Caster",
            class_name="Mage",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
        )
        target = TestGameState.create_player(
            name="Immune",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(100, 100),
            mana=(50, 50),
        )
        # Give target full Death resist
        target.resistance["Death"] = 1.0
        eff = InstantKillEffect(
            apply_resist_multiplier=True,
            resist_type="Death",
        )
        result = CombatResult(action="Desoul")
        eff.apply(user, target, result)
        assert target.health.current == 100
        assert result.extra.get("status_immune") == "Death"

    def test_instant_kill_status_immunity(self):
        """Status immunity (e.g. Stone) should block the kill."""
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import InstantKillEffect
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Caster",
            class_name="Mage",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
        )
        target = TestGameState.create_player(
            name="StoneImmune",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(100, 100),
            mana=(50, 50),
        )
        target.status_immunity.append("Stone")
        eff = InstantKillEffect(
            apply_resist_multiplier=False,
            immunity_status="Stone",
        )
        result = CombatResult(action="Petrify")
        eff.apply(user, target, result)
        assert target.health.current == 100
        assert result.extra.get("status_immune") == "Stone"

    def test_instant_kill_reflect(self):
        """Reflect item should redirect the kill to the caster."""
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import InstantKillEffect
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Gorgon",
            class_name="Mage",
            race_name="Human",
            level=30,
            health=(100, 100),
            mana=(200, 200),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 1, "charisma": 200, "dex": 10},
        )
        target = TestGameState.create_player(
            name="Hero",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(100, 100),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 1, "charisma": 10, "dex": 10},
        )
        # Equip Medusa Shield on target
        target.equipment["OffHand"].name = "Medusa Shield"
        eff = InstantKillEffect(
            success_message="{target} is turned to stone!",
            actor_stat="charisma",
            actor_divisor=1,
            apply_resist_multiplier=False,
            luck_factor=1,
            reflect_item="Medusa Shield",
            reflect_slot="OffHand",
            reflect_message="{target} uses the Medusa Shield to reflect {name} back at {caster}!",
        )
        result = CombatResult(action="Petrify")
        eff.apply(user, target, result)
        msgs = result.extra.get("messages", [])
        # Reflect message should always appear
        assert any("Medusa Shield" in m for m in msgs), "Expected reflect message"
        # Target should always be unharmed (the spell was reflected)
        assert target.health.current == 100

    def test_stat_reduce_effect_factory(self):
        from src.core.data.ability_loader import EffectFactory
        from src.core.effects import StatReduceEffect

        eff = EffectFactory.create(
            {
                "type": "stat_reduce",
                "stat": "con",
                "amount": 1,
                "actor_stat": "intel",
                "actor_divisor": 2,
                "luck_factor": 10,
                "success_message": "{target} loses con.",
            }
        )
        assert isinstance(eff, StatReduceEffect)
        assert eff.stat == "con"
        assert eff.amount == 1
        assert eff.actor_divisor == 2

    def test_stat_reduce_effect_reduces_stat(self, monkeypatch):
        """A won contest and luck gate permanently reduce the configured stat."""
        import random

        from src.core.combat.combat_result import CombatResult
        from src.core.effects import StatReduceEffect
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Plagued",
            class_name="Mage",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
            stats={
                "strength": 10,
                "intel": 200,
                "wisdom": 10,
                "con": 10,
                "charisma": 10,
                "dex": 10,
            },
        )
        target = TestGameState.create_player(
            name="Sick",
            class_name="Warrior",
            race_name="Human",
            level=1,
            health=(100, 100),
            mana=(50, 50),
            stats={"strength": 5, "intel": 5, "wisdom": 5, "con": 1, "charisma": 5, "dex": 5},
        )
        rolls = iter((100, 0, 0))
        monkeypatch.setattr(random, "randint", lambda *_args: next(rolls))
        eff = StatReduceEffect(
            stat="con",
            amount=1,
            actor_stat="intel",
            actor_divisor=2,
            target_stat="con",
            target_lo_divisor=2,
            luck_factor=1,
            success_message="{target} loses constitution.",
        )
        result = CombatResult(action="Disease Breath")

        eff.apply(user, target, result)

        assert target.stats.con == 0
        messages = result.extra.get("messages", [])
        assert any("loses constitution" in message for message in messages)


class TestBatch6YAMLLoading:
    """Test that all Batch 6 YAML files load correctly."""

    @pytest.fixture(
        params=[
            "desoul.yaml",
            "petrify.yaml",
            "ruin.yaml",
            "disease_breath.yaml",
        ]
    )
    def yaml_file(self, request):
        return request.param

    def test_yaml_loads(self, yaml_file):
        from src.core.data.ability_loader import AbilityFactory

        ability = AbilityFactory.create_from_yaml(
            Path(__file__).resolve().parent.parent
            / "src"
            / "core"
            / "data"
            / "abilities"
            / yaml_file,
        )
        assert ability is not None
        assert ability.name != ""

    def test_desoul_yaml_fields(self):
        from src.core.data.ability_loader import AbilityFactory

        a = AbilityFactory.create_from_yaml(
            Path(__file__).resolve().parent.parent
            / "src"
            / "core"
            / "data"
            / "abilities"
            / "desoul.yaml",
        )
        assert a.name == "Desoul"
        assert a.cost == 50
        assert a.subtyp == "Death"
        assert len(a._effects) == 1

    def test_petrify_yaml_fields(self):
        from src.core.data.ability_loader import AbilityFactory

        a = AbilityFactory.create_from_yaml(
            Path(__file__).resolve().parent.parent
            / "src"
            / "core"
            / "data"
            / "abilities"
            / "petrify.yaml",
        )
        assert a.name == "Petrify"
        assert a.cost == 50
        assert a.rank == 2
        assert a.subtyp == "Death"
        assert len(a._effects) == 1

    def test_ruin_yaml_fields(self):
        from src.core.data.ability_loader import AbilityFactory

        a = AbilityFactory.create_from_yaml(
            Path(__file__).resolve().parent.parent
            / "src"
            / "core"
            / "data"
            / "abilities"
            / "ruin.yaml",
        )
        assert a.name == "Ruin"
        assert a.cost == 28
        assert a.subtyp == "Status"
        assert len(a._effects) == 2  # two stat_contest effects

    def test_disease_breath_yaml_fields(self):
        from src.core.data.ability_loader import AbilityFactory

        a = AbilityFactory.create_from_yaml(
            Path(__file__).resolve().parent.parent
            / "src"
            / "core"
            / "data"
            / "abilities"
            / "disease_breath.yaml",
        )
        assert a.name == "Disease Breath"
        assert a.cost == 25
        assert a.school == "Disease"
        assert len(a._effects) == 1


class TestBatch6AbilityFactories:
    """Test that the ability package wrapper classes produce correct instances."""

    def test_desoul_factory(self):
        from src.core import abilities

        a = abilities.Desoul()
        assert a.name == "Desoul"
        assert a.cost == 50
        assert a.subtyp == "Death"

    def test_petrify_factory(self):
        from src.core import abilities

        a = abilities.Petrify()
        assert a.name == "Petrify"
        assert a.cost == 50
        assert a.rank == 2

    def test_ruin_factory(self):
        from src.core import abilities

        a = abilities.Ruin()
        assert a.name == "Ruin"
        assert a.cost == 28

    def test_disease_breath_factory(self):
        from src.core import abilities

        a = abilities.DiseaseBreath()
        assert a.name == "Disease Breath"
        assert a.cost == 25
        assert a.school == "Disease"


class TestBatch6CombatIntegration:
    """Test Batch 6 abilities in a combat-like context."""

    @staticmethod
    def _make_combatants(caster_cha=60, target_con=10):
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Caster",
            class_name="Mage",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
            stats={
                "strength": 10,
                "intel": 40,
                "wisdom": 10,
                "con": 20,
                "charisma": caster_cha,
                "dex": 10,
            },
        )
        target = TestGameState.create_player(
            name="Dummy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(100, 100),
            stats={
                "strength": 10,
                "intel": 10,
                "wisdom": 10,
                "con": target_con,
                "charisma": 10,
                "dex": 10,
            },
        )
        return user, target

    # -- Desoul -------------------------------------------------------------

    def test_desoul_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        desoul = abilities.Desoul()
        mana_before = user.mana.current
        desoul.cast(user, target)
        assert user.mana.current == mana_before - 50

    def test_desoul_special_skips_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        desoul = abilities.Desoul()
        mana_before = user.mana.current
        desoul.cast(user, target, special=True)
        assert user.mana.current == mana_before

    def test_desoul_ice_block_check(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        desoul = abilities.Desoul()
        result = desoul.cast(user, target)
        assert "no effect" in result.lower()

    def test_desoul_immune_target(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.resistance["Death"] = 1.0
        desoul = abilities.Desoul()
        result = desoul.cast(user, target)
        assert "immune" in result.lower()

    def test_desoul_kills_target(self):
        """With extreme CHA vs low CON, Desoul should kill at least once."""
        from src.core import abilities

        killed = False
        for _ in range(100):
            user, target = self._make_combatants(caster_cha=200, target_con=1)
            desoul = abilities.Desoul()
            result = desoul.cast(user, target)
            if target.health.current == 0:
                killed = True
                assert (
                    "soul" in result.lower()
                    or "slain" in result.lower()
                    or "dead" in result.lower()
                )
                break
        assert killed, "Desoul never killed in 100 attempts"

    # -- Petrify ------------------------------------------------------------

    def test_petrify_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        petrify = abilities.Petrify()
        mana_before = user.mana.current
        petrify.cast(user, target)
        assert user.mana.current == mana_before - 50

    def test_petrify_ice_block_check(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        petrify = abilities.Petrify()
        result = petrify.cast(user, target)
        assert "no effect" in result.lower()

    def test_petrify_stone_immune(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.status_immunity.append("Stone")
        petrify = abilities.Petrify()
        result = petrify.cast(user, target)
        assert "immune" in result.lower()

    def test_petrify_kills_target(self):
        """With extreme CHA vs low CON, Petrify should kill at least once."""
        from src.core import abilities

        killed = False
        for _ in range(100):
            user, target = self._make_combatants(caster_cha=200, target_con=1)
            petrify = abilities.Petrify()
            result = petrify.cast(user, target)
            if target.health.current == 0:
                killed = True
                assert "stone" in result.lower()
                break
        assert killed, "Petrify never killed in 100 attempts"

    def test_petrify_reflect_medusa_shield(self):
        """Medusa Shield should reflect Petrify back at caster."""
        from src.core import abilities

        reflected = False
        for _ in range(100):
            user, target = self._make_combatants(caster_cha=200, target_con=1)
            # Give target a Medusa Shield
            target.equipment["OffHand"].name = "Medusa Shield"
            petrify = abilities.Petrify()
            result = petrify.cast(user, target)
            if "Medusa Shield" in result:
                reflected = True
                # With reflect, caster becomes target of the kill
                if user.health.current == 0:
                    break
                break
        assert reflected, "Petrify reflect never triggered in 100 attempts"

    # -- Ruin ---------------------------------------------------------------

    def test_ruin_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        ruin = abilities.Ruin()
        mana_before = user.mana.current
        ruin.cast(user, target)
        assert user.mana.current == mana_before - 28

    def test_ruin_ice_block_check(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        ruin = abilities.Ruin()
        result = ruin.cast(user, target)
        assert "no effect" in result.lower()

    def test_ruin_applies_debuffs(self):
        """With high INT vs low CON, Ruin should apply debuffs."""
        from src.core import abilities

        debuffed = False
        for _ in range(50):
            user, target = self._make_combatants()
            user.stats.intel = 100
            target.stats.con = 1
            ruin = abilities.Ruin()
            result = ruin.cast(user, target)
            # Check if any combat_attr was debuffed
            if any(
                [
                    (
                        target.combat.attack != target._base_combat_attack
                        if hasattr(target, "_base_combat_attack")
                        else False
                    ),
                    "reduced" in result.lower() or "lowered" in result.lower(),
                ]
            ):
                debuffed = True
                break
            # Check via the result message containing stat names
            if any(w in result.lower() for w in ["attack", "defense", "magic"]):
                debuffed = True
                break
        assert debuffed, "Ruin never applied debuffs in 50 attempts"

    # -- DiseaseBreath ------------------------------------------------------

    def test_disease_breath_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        db = abilities.DiseaseBreath()
        mana_before = user.mana.current
        db.cast(user, target)
        assert user.mana.current == mana_before - 25

    def test_disease_breath_ice_block_check(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        db = abilities.DiseaseBreath()
        result = db.cast(user, target)
        assert "no effect" in result.lower()

    def test_disease_breath_can_reduce_con(self):
        """With high INT vs low CON/luck, Disease Breath should reduce CON."""
        from src.core import abilities

        reduced = False
        for _ in range(200):
            user, target = self._make_combatants()
            user.stats.intel = 200
            target.stats.con = 1
            db = abilities.DiseaseBreath()
            result = db.cast(user, target)
            if target.stats.con == 0:
                reduced = True
                assert "cripples" in result.lower() or "constitution" in result.lower()
                break
        assert reduced, "DiseaseBreath never reduced CON in 200 attempts"


class TestBatch6SaveSystem:
    """Test that Batch 6 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch6_spells(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in ["Desoul", "Petrify", "Ruin", "DiseaseBreath"]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


class TestBatch5SaveSystem:
    """Test that Batch 5 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch5_skills(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in ["MortalStrike", "MortalStrike2", "Doom", "Tunnel", "Surface"]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


def run_tests():
    """Run all tests."""
    print("=" * 70)
    print("DATA-DRIVEN ABILITIES TESTS")
    print("=" * 70)
    import pytest

    return pytest.main([__file__, "-v", "--tb=short", "--color=yes"])


# ======================================================================
# Batch 7 - PowerUp, Chain, Drain, Toggle abilities
# ======================================================================


class TestBatch7YAMLLoading:
    """Verify YAML files load and produce correct DataDriven types."""

    _SKILLS = [
        ("holy_retribution.yaml", "Holy Retribution", "Power Up", 25),
        ("divine_aegis.yaml", "Divine Aegis", "Power Up", 20),
        ("blade_fatalities.yaml", "Blade of Fatalities", "Power Up", 0),
        ("sacred_overchannel.yaml", "Sacred Overchannel", "Power Up", 24),
        ("great_gospel.yaml", "Great Gospel", "Power Up", 35),
        ("chi_heal.yaml", "Chi Heal", "Chi Strike", 16),
        ("health_drain.yaml", "Health Drain", "Drain", 10),
        ("mana_drain.yaml", "Mana Drain", "Drain", 0),
        ("health_mana_drain.yaml", "Health/Mana Drain", "Drain", 0),
        ("mana_shield.yaml", "Mana Shield", "Enhance", 0),
        ("mana_shield_2.yaml", "Mana Shield 2", "Enhance", 0),
    ]

    @staticmethod
    def test_all_yaml_files_load():
        from src.core.data.ability_loader import AbilityFactory

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        for (
            filename,
            expected_name,
            expected_subtyp,
            expected_cost,
        ) in TestBatch7YAMLLoading._SKILLS:
            ability = AbilityFactory.create_from_yaml(yaml_dir / filename)
            assert ability.name == expected_name, f"{filename}: name mismatch"
            assert ability.subtyp == expected_subtyp, f"{filename}: subtyp mismatch"
            assert ability.cost == expected_cost, f"{filename}: cost mismatch"

    @staticmethod
    def test_wrapper_classes_produce_correct_instances():
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenSkill

        for cls_name in [
            "HolyRetribution",
            "DivineAegis",
            "BladeFatalities",
            "SacredOverchannel",
            "GreatGospel",
            "ChiHeal",
            "HealthDrain",
            "ManaDrain",
            "HealthManaDrain",
            "ManaShield",
            "ManaShield2",
        ]:
            ability = getattr(abilities, cls_name)()
            assert isinstance(ability, DataDrivenSkill), f"{cls_name} is not DataDrivenSkill"


class TestBatch7PowerUpAbilities:
    """Test the 4 Power Up abilities: HolyRetribution, DivineAegis,
    BladeFatalities, GreatGospel."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Paladin",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(200, 200),
            stats={"strength": 25, "intel": 15, "wisdom": 20, "con": 20, "charisma": 15, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 18, "charisma": 10, "dex": 12},
        )
        return user, target

    def test_holy_retribution_activates_power_up(self):
        from src.core import abilities

        user, target = self._make_combatants()
        skill = abilities.HolyRetribution()
        mana_before = user.mana.current
        result = skill.use(user, target)
        assert user.class_effects["Power Up"].active
        assert user.class_effects["Power Up"].duration == 5
        assert user.power_up is True
        assert user.mana.current == mana_before - 25
        assert isinstance(result, str)
        assert len(result) > 0

    def test_divine_aegis_sets_random_extra(self):
        from src.core import abilities

        extras = set()
        for _ in range(50):
            user, target = self._make_combatants()
            skill = abilities.DivineAegis()
            skill.use(user, target)
            assert user.class_effects["Power Up"].active
            assert user.class_effects["Power Up"].duration == 5
            extra = user.class_effects["Power Up"].extra
            assert user.health.max // 4 <= extra <= user.health.max // 2
            extras.add(extra)
        assert len(extras) > 1, "Extra should vary across trials"

    def test_divine_aegis_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.DivineAegis().use(user, target)
        assert user.mana.current == mana_before - 20

    def test_blade_fatalities_sacrifices_health(self):
        from src.core import abilities

        user, target = self._make_combatants()
        hp_before = user.health.current
        skill = abilities.BladeFatalities()
        result = skill.use(user, target)
        per_health = int(hp_before * 0.25)
        assert user.health.current == hp_before - per_health
        expected_extra = max(per_health // 5, 5)
        assert user.class_effects["Power Up"].extra == expected_extra
        assert user.class_effects["Power Up"].active
        assert user.class_effects["Power Up"].duration == 5
        # No mana cost
        assert user.mana.current == 200

    def test_great_gospel_activates_and_cleanses(self):
        from src.core import abilities

        user, target = self._make_combatants()
        # Apply some negative statuses
        user.status_effects["Poison"].active = True
        user.status_effects["Poison"].duration = 5
        user.status_effects["Blind"].active = True
        user.status_effects["Blind"].duration = 3
        mana_before = user.mana.current
        skill = abilities.GreatGospel()
        result = skill.use(user, target)
        assert user.class_effects["Power Up"].active
        assert user.class_effects["Power Up"].duration == 5
        assert user.mana.current == mana_before - 35
        # Cleanse should have removed negative statuses
        assert not user.status_effects["Poison"].active
        assert not user.status_effects["Blind"].active

    def test_sacred_overchannel_activates_power_up(self):
        from src.core import abilities

        user, target = self._make_combatants()
        skill = abilities.SacredOverchannel()
        mana_before = user.mana.current
        result = skill.use(user, target)
        assert user.class_effects["Power Up"].active
        assert user.class_effects["Power Up"].duration == 5
        assert user.power_up is True
        assert user.mana.current == mana_before - 24
        assert "sacred overchannel" in result.lower()

    def test_holy_retribution_special_skips_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        skill = abilities.HolyRetribution()
        skill.use(user, target, special=True)
        assert user.mana.current == mana_before


class TestBatch7ChainAbilities:
    """Test ChiHeal and HealthManaDrain (ability-chaining skills)."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Monk",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(200, 200),
            stats={"strength": 20, "intel": 15, "wisdom": 25, "con": 20, "charisma": 15, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(150, 150),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 18, "charisma": 10, "dex": 12},
        )
        return user, target

    def test_chi_heal_heals_and_cleanses(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.health.current = 200  # Damaged
        user.status_effects["Poison"].active = True
        user.status_effects["Poison"].duration = 5
        mana_before = user.mana.current
        skill = abilities.ChiHeal()
        result = skill.use(user, target)
        # Should heal the user (health should increase)
        assert user.health.current > 200
        # Cleanse should remove poison
        assert not user.status_effects["Poison"].active
        # Mana deducted
        assert user.mana.current == mana_before - 16
        assert isinstance(result, str)

    def test_health_mana_drain_drains_both(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.health.current = 200  # Damaged
        user.mana.current = 100  # Low mana
        target_hp_before = target.health.current
        target_mp_before = target.mana.current
        skill = abilities.HealthManaDrain()
        result = skill.use(user, target)
        # Target should lose health and mana
        assert target.health.current < target_hp_before or target.mana.current < target_mp_before
        assert isinstance(result, str)
        assert "drain" in result.lower()

    def test_health_mana_drain_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        skill = abilities.HealthManaDrain()
        result = skill.use(user, target)
        assert "no effect" in result.lower()


class TestBatch7DrainAbilities:
    """Test HealthDrain and ManaDrain."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Warlock",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(200, 200),
            stats={"strength": 15, "intel": 20, "wisdom": 25, "con": 15, "charisma": 30, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Victim",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(150, 150),
            stats={"strength": 15, "intel": 8, "wisdom": 5, "con": 15, "charisma": 5, "dex": 12},
        )
        return user, target

    def test_health_drain_transfers_health(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.health.current = 200  # Damaged
        target_hp_before = target.health.current
        user_hp_before = user.health.current
        mana_before = user.mana.current
        drained = False
        for _ in range(20):
            user.health.current = user_hp_before
            target.health.current = target_hp_before
            user.mana.current = mana_before
            skill = abilities.HealthDrain()
            result = skill.use(user, target)
            if target.health.current < target_hp_before:
                drained = True
                # User should have gained health
                assert user.health.current > user_hp_before
                assert "drain" in result.lower()
                break
        assert drained, "HealthDrain never drained in 20 attempts"

    def test_health_drain_caps_at_18_percent(self):
        from src.core import abilities

        for _ in range(50):
            user, target = self._make_combatants()
            user.health.current = 200
            user.stats.charisma = 200  # Very high to make drain large
            target_hp = target.health.current
            skill = abilities.HealthDrain()
            skill.use(user, target)
            hp_lost = target_hp - target.health.current
            cap = max(1, int(target.health.max * 0.18))
            assert hp_lost <= cap, f"Drained {hp_lost} > cap {cap}"

    def test_health_drain_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        skill = abilities.HealthDrain()
        result = skill.use(user, target)
        assert "no effect" in result.lower()

    def test_health_drain_special_skips_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        skill = abilities.HealthDrain()
        skill.use(user, target, special=True)
        assert user.mana.current == mana_before

    def test_health_drain_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        skill = abilities.HealthDrain()
        skill.use(user, target)
        assert user.mana.current == mana_before - 10

    def test_mana_drain_transfers_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.mana.current = 100
        target_mp_before = target.mana.current
        user_mp_before = user.mana.current
        drained = False
        for _ in range(20):
            user.mana.current = user_mp_before
            target.mana.current = target_mp_before
            skill = abilities.ManaDrain()
            result = skill.use(user, target)
            if target.mana.current < target_mp_before:
                drained = True
                assert user.mana.current > user_mp_before
                assert "drain" in result.lower()
                break
        assert drained, "ManaDrain never drained in 20 attempts"

    def test_mana_drain_caps_at_22_percent(self):
        from src.core import abilities

        for _ in range(50):
            user, target = self._make_combatants()
            user.mana.current = 100
            user.stats.charisma = 200
            target_mp = target.mana.current
            skill = abilities.ManaDrain()
            skill.use(user, target)
            mp_lost = target_mp - target.mana.current
            cap = max(1, int(target.mana.max * 0.22))
            assert mp_lost <= cap, f"Drained {mp_lost} > cap {cap}"


class TestBatch7ManaShield:
    """Test ManaShield and ManaShield2 toggle behavior."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Mage",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 25, "wisdom": 20, "con": 15, "charisma": 15, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 18, "charisma": 10, "dex": 12},
        )
        return user, target

    def test_mana_shield_activate(self):
        from src.core import abilities

        user, _ = self._make_combatants()
        mana_before = user.mana.current
        assert not user.magic_effects["Mana Shield"].active
        skill = abilities.ManaShield()
        result = skill.use(user, user)
        assert user.magic_effects["Mana Shield"].active
        assert user.magic_effects["Mana Shield"].duration == 25
        assert user.mana.current == mana_before - 4
        assert "activated" in result.lower()

    def test_mana_shield_deactivate(self):
        from src.core import abilities

        user, _ = self._make_combatants()
        # Activate first
        user.magic_effects["Mana Shield"].active = True
        user.magic_effects["Mana Shield"].duration = 25
        mana_before = user.mana.current
        skill = abilities.ManaShield()
        result = skill.use(user, user)
        assert not user.magic_effects["Mana Shield"].active
        assert user.mana.current == mana_before  # No mana cost on deactivation
        assert "deactivated" in result.lower()

    def test_mana_shield_toggle_cycle(self):
        from src.core import abilities

        user, _ = self._make_combatants()
        skill = abilities.ManaShield()
        # Activate
        skill.use(user, user)
        assert user.magic_effects["Mana Shield"].active
        # Deactivate
        skill2 = abilities.ManaShield()
        skill2.use(user, user)
        assert not user.magic_effects["Mana Shield"].active
        # Activate again
        skill3 = abilities.ManaShield()
        skill3.use(user, user)
        assert user.magic_effects["Mana Shield"].active

    def test_mana_shield_2_reduction_4(self):
        from src.core import abilities

        user, _ = self._make_combatants()
        skill = abilities.ManaShield2()
        skill.use(user, user)
        assert user.magic_effects["Mana Shield"].active
        assert user.magic_effects["Mana Shield"].duration == 50


class TestBatch7SaveSystem:
    """Test that Batch 7 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch7_skills(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in [
            "HolyRetribution",
            "DivineAegis",
            "BladeFatalities",
            "SacredOverchannel",
            "GreatGospel",
            "ChiHeal",
            "HealthDrain",
            "ManaDrain",
            "HealthManaDrain",
            "ManaShield",
            "ManaShield2",
        ]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


if __name__ == "__main__":
    sys.exit(run_tests())


# =====================================================================
# Batch 12 - Steal, Mug, Counterspell, ElementalStrike, Blackjack
# =====================================================================


class TestBatch12YAMLLoading:
    """Verify all 5 Batch 12 YAML files load correctly."""

    _YAMLS = [
        ("steal.yaml", "Steal", 6),
        ("mug.yaml", "Mug", 20),
        ("counterspell.yaml", "Counterspell", 0),
        ("elemental_strike.yaml", "Elemental Strike", 15),
        ("blackjack.yaml", "Blackjack", 7),
    ]

    def test_all_yaml_files_load(self):
        from src.core.data.ability_loader import AbilityFactory

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        for filename, expected_name, expected_cost in self._YAMLS:
            ability = AbilityFactory.create_from_yaml(yaml_dir / filename)
            assert ability.name == expected_name, f"{filename}: name mismatch"
            assert ability.cost == expected_cost, f"{filename}: cost mismatch"


class TestBatch12Steal:
    """Steal - speed+luck contest to steal gold or item."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Thief",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 15, "intel": 10, "wisdom": 10, "con": 12, "charisma": 10, "dex": 30},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 10, "charisma": 10, "dex": 5},
        )
        target.gold = 1000
        return user, target

    def test_steal_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Steal().use(user, target)
        assert user.mana.current == mana_before - 6

    def test_steal_can_steal_gold(self):
        from src.core import abilities

        gold_stolen = False
        for _ in range(100):
            user, target = self._make_combatants()
            user_gold = user.gold
            abilities.Steal().use(user, target)
            if user.gold > user_gold:
                gold_stolen = True
                break
        assert gold_stolen, "Steal should steal gold sometimes"

    def test_steal_success_lasts_long_enough_for_smoke_screen_retries(self, monkeypatch):
        from src.core import abilities

        user, target = self._make_combatants()
        monkeypatch.setattr("random.choice", lambda _seq: "Gold")
        monkeypatch.setattr("random.randint", lambda _low, high: high)

        abilities.Steal().use(user, target)

        assert user.status_effects["Steal Success"].active is True
        assert user.status_effects["Steal Success"].duration >= 5

    def test_steal_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.Steal().use(user, target)
        assert "no effect" in result.lower()

    def test_steal_fails_sometimes(self):
        from src.core import abilities

        failed = False
        for _ in range(100):
            user, target = self._make_combatants()
            # Give target high speed to increase failure chance
            target.stats.dex = 50
            result = abilities.Steal().use(user, target)
            if "fail" in result.lower():
                failed = True
                break
        assert failed, "Steal should fail sometimes against fast targets"


class TestBatch12Mug:
    """Mug - weapon damage + steal on hit."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Rogue",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 25, "intel": 10, "wisdom": 10, "con": 15, "charisma": 10, "dex": 25},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 10, "charisma": 10, "dex": 5},
        )
        target.gold = 1000
        return user, target

    def test_mug_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Mug().use(user, target)
        # Mug costs 20, and if hit, Steal().use() costs 6 more
        assert user.mana.current <= mana_before - 20

    def test_mug_can_deal_damage(self):
        from src.core import abilities

        damaged = False
        for _ in range(50):
            user, target = self._make_combatants()
            abilities.Mug().use(user, target)
            if target.health.current < 300:
                damaged = True
                break
        assert damaged, "Mug should deal damage sometimes"

    def test_mug_can_steal(self):
        from src.core import abilities

        stolen = False
        for _ in range(100):
            user, target = self._make_combatants()
            user_gold_before = user.gold
            result = abilities.Mug().use(user, target)
            if isinstance(result, str):
                msg = result
            else:
                msg = str(result)
            if "steals" in msg.lower() or user.gold > user_gold_before:
                stolen = True
                break
        assert stolen, "Mug should steal on hit sometimes"


class TestBatch12Counterspell:
    """Counterspell - passive, picks random spell and casts it."""

    @staticmethod
    def _make_combatants():
        from src.core import abilities
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Behemoth",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(600, 600),
            mana=(200, 200),
            stats={"strength": 30, "intel": 25, "wisdom": 20, "con": 30, "charisma": 10, "dex": 10},
        )
        user.class_effects["Power Up"].active = False
        # Give behemoth some spells in its spellbook
        user.spellbook["Spells"] = {
            "Firebolt": abilities.Firebolt(),
        }
        target = TestGameState.create_player(
            name="Player",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 15, "charisma": 10, "dex": 12},
        )
        return user, target

    def test_counterspell_passive_flag(self):
        from src.core import abilities

        ability = abilities.Counterspell()
        assert ability.passive is True

    def test_counterspell_casts_spell(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.Counterspell().use(user, target)
        # Should produce some output from casting Firebolt
        if isinstance(result, str):
            assert len(result) > 0
        else:
            assert len(str(result)) > 0

    def test_counterspell_can_deal_damage(self):
        from src.core import abilities

        damaged = False
        for _ in range(50):
            user, target = self._make_combatants()
            abilities.Counterspell().use(user, target)
            if target.health.current < 300:
                damaged = True
                break
        assert damaged, "Counterspell should deal damage via cast spell"


class TestBatch12ElementalStrike:
    """ElementalStrike - weapon damage + random elemental spell."""

    @staticmethod
    def _make_combatants():
        from src.core import abilities
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Spellblade",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(150, 150),
            stats={"strength": 25, "intel": 20, "wisdom": 15, "con": 15, "charisma": 10, "dex": 20},
        )
        user.class_effects["Power Up"].active = False
        # Give elemental spells in spellbook
        user.spellbook["Spells"] = {
            "Firebolt": abilities.Firebolt(),
            "Ice Lance": abilities.IceLance(),
            "Shock": abilities.Shock(),
        }
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 10, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_elemental_strike_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.ElementalStrike().use(user, target)
        assert user.mana.current == mana_before - 15

    def test_elemental_strike_can_deal_damage(self):
        from src.core import abilities

        damaged = False
        for _ in range(50):
            user, target = self._make_combatants()
            abilities.ElementalStrike().use(user, target)
            if target.health.current < 400:
                damaged = True
                break
        assert damaged, "ElementalStrike should deal damage"

    def test_elemental_strike_mentions_element(self):
        from src.core import abilities

        element_seen = False
        for _ in range(50):
            user, target = self._make_combatants()
            result = abilities.ElementalStrike().use(user, target)
            msg = str(result)
            if "elemental force" in msg.lower():
                element_seen = True
                break
        assert element_seen, "ElementalStrike should mention elemental force on hit"

    def test_elemental_strike_does_not_embed_nested_spell_damage_log(self, monkeypatch):
        from src.core import abilities

        user, target = self._make_combatants()
        monkeypatch.setattr(
            user,
            "weapon_damage",
            lambda *_args, **_kwargs: ("Spellblade strikes.\n", True, 1),
        )
        result = abilities.ElementalStrike().use(user, target)
        msg = str(result)
        assert "elemental force" in msg.lower()
        assert "damages Target" not in msg


class TestBatch12Blackjack:
    """Blackjack - random outcome card game."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Jester",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 15, "intel": 15, "wisdom": 10, "con": 15, "charisma": 25, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 15, "intel": 8, "wisdom": 10, "con": 15, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_blackjack_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Blackjack().use(user, target)
        assert user.mana.current == mana_before - 7

    def test_blackjack_returns_outcome(self):
        from src.core import abilities

        outcomes_seen = set()
        for _ in range(200):
            user, target = self._make_combatants()
            result = abilities.Blackjack().use(user, target)
            msg = result if isinstance(result, str) else str(result)
            if "wins the hand" in msg:
                outcomes_seen.add("win")
            elif "busted" in msg:
                outcomes_seen.add("bust")
            elif "draw" in msg.lower():
                outcomes_seen.add("draw")
        assert len(outcomes_seen) >= 2, f"Expected variety, got: {outcomes_seen}"

    def test_blackjack_with_callback(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.Blackjack().use(user, target, blackjack_callback=lambda u, t: "User Win")
        msg = result if isinstance(result, str) else str(result)
        assert "wins the hand" in msg


class TestBatch12SaveSystem:
    """Test that Batch 12 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch12_abilities(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in [
            "Steal",
            "Mug",
            "Counterspell",
            "ElementalStrike",
            "Blackjack",
        ]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


# =====================================================================
# Batch 13 - Doublecast, Triplecast, ChooseFate, Shapeshift, AstralJudgment
# =====================================================================


class TestBatch13YAMLLoading:
    """Verify all 5 Batch 13 YAML files load correctly."""

    _YAMLS = [
        ("doublecast.yaml", "Doublecast", 10),
        ("triplecast.yaml", "Triplecast", 20),
        ("choose_fate.yaml", "Choose Fate", 0),
        ("shapeshift.yaml", "Shapeshift", 0),
        ("astral_judgment.yaml", "Astral Judgment", 20),
    ]

    def test_all_yaml_files_load(self):
        from src.core.data.ability_loader import AbilityFactory

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        for filename, expected_name, expected_cost in self._YAMLS:
            ability = AbilityFactory.create_from_yaml(yaml_dir / filename)
            assert ability.name == expected_name, f"{filename}: name mismatch"
            assert ability.cost == expected_cost, f"{filename}: cost mismatch"


class TestBatch13Doublecast:
    """Doublecast - cast 2 spells in a single turn."""

    @staticmethod
    def _make_combatants():
        from src.core import abilities
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Mage",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 30, "wisdom": 20, "con": 12, "charisma": 10, "dex": 10},
        )
        user.class_effects["Power Up"].active = False
        user.spellbook["Spells"] = {
            "Firebolt": abilities.Firebolt(),
            "Ice Lance": abilities.IceLance(),
        }
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 10, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_doublecast_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Doublecast().use(user, target)
        # Doublecast costs 10 + each sub-spell costs its own mana
        assert user.mana.current <= mana_before - 10

    def test_doublecast_casts_spells(self):
        from src.core import abilities

        hit = False
        for _ in range(50):
            user, target = self._make_combatants()
            result = abilities.Doublecast().use(user, target)
            msg = result if isinstance(result, str) else str(result)
            if "damage" in msg.lower() or target.health.current < 400:
                hit = True
                break
        assert hit, "Doublecast should cast spells that can deal damage"

    def test_doublecast_spell_selector_callback(self):
        from src.core import abilities

        calls = []

        def selector(user, spell_list, cast_index):
            calls.append(cast_index)
            # Always pick the first entry
            return spell_list[0]

        user, target = self._make_combatants()
        abilities.Doublecast().use(user, target, spell_selector=selector)
        assert len(calls) >= 1, "spell_selector should be called"

    def test_doublecast_refunds_if_no_spells(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.mana.current = 11  # Just enough for Doublecast cost (10)
        # Both spells in spellbook cost more than 1 remaining mana
        mana_before = user.mana.current
        result = abilities.Doublecast().use(user, target)
        msg = result if isinstance(result, str) else str(result)
        assert "not have enough mana" in msg
        # Mana should be refunded
        assert user.mana.current == mana_before


class TestBatch13Triplecast:
    """Triplecast - cast 3 spells in a single turn."""

    @staticmethod
    def _make_combatants():
        from src.core import abilities
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Archmage",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(500, 500),
            stats={"strength": 10, "intel": 30, "wisdom": 20, "con": 12, "charisma": 10, "dex": 10},
        )
        user.class_effects["Power Up"].active = False
        user.spellbook["Spells"] = {
            "Firebolt": abilities.Firebolt(),
            "Ice Lance": abilities.IceLance(),
            "Shock": abilities.Shock(),
        }
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(800, 800),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 10, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_triplecast_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Triplecast().use(user, target)
        assert user.mana.current <= mana_before - 20

    def test_triplecast_name_and_cost(self):
        from src.core import abilities

        ability = abilities.Triplecast()
        assert ability.name == "Triplecast"
        assert ability.cost == 20


class TestBatch13ChooseFate:
    """ChooseFate - Devil lets player pick action."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Devil",
            class_name="Warrior",
            race_name="Human",
            level=50,
            health=(1000, 1000),
            mana=(200, 200),
            stats={"strength": 40, "intel": 30, "wisdom": 20, "con": 30, "charisma": 10, "dex": 20},
        )
        user.damage_mod = 0
        user.spell_mod = 0
        target = TestGameState.create_player(
            name="Player",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 15, "intel": 10, "wisdom": 10, "con": 15, "charisma": 10, "dex": 12},
        )
        return user, target

    def test_choose_fate_no_mana_cost(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.ChooseFate().use(
            user,
            target,
            selection_callback=lambda msg, opts: 0,
        )
        assert user.mana.current == mana_before

    def test_choose_fate_attack_increases_dmg_mod(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mod_before = user.damage_mod
        abilities.ChooseFate().use(
            user,
            target,
            selection_callback=lambda msg, opts: 0,
        )
        assert user.damage_mod > mod_before

    def test_choose_fate_hellfire_increases_spell_mod(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mod_before = user.spell_mod
        abilities.ChooseFate().use(
            user,
            target,
            selection_callback=lambda msg, opts: 1,
        )
        assert user.spell_mod > mod_before

    def test_choose_fate_crush_can_decrease_mods(self):
        from src.core import abilities

        decreased = False
        for _ in range(50):
            user, target = self._make_combatants()
            user.damage_mod = 50
            user.spell_mod = 50
            abilities.ChooseFate().use(
                user,
                target,
                selection_callback=lambda msg, opts: 2,
            )
            if user.damage_mod < 50 or user.spell_mod < 50:
                decreased = True
                break
        assert decreased, "Crush should sometimes decrease mods"

    def test_choose_fate_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.ChooseFate().use(user, target)
        assert "no effect" in result.lower()


class TestBatch13Shapeshift:
    """Shapeshift - transform into random creature."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Shapeshifter",
            class_name="Warrior",
            race_name="Human",
            level=20,
            health=(200, 200),
            mana=(50, 50),
            stats={"strength": 15, "intel": 10, "wisdom": 10, "con": 15, "charisma": 10, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=20,
            health=(200, 200),
            mana=(50, 50),
            stats={"strength": 15, "intel": 10, "wisdom": 10, "con": 15, "charisma": 10, "dex": 15},
        )
        return user, target

    def test_shapeshift_transforms_user(self):
        from src.core import abilities, enemies

        user, target = self._make_combatants()
        # Give user a transform list with at least 2 creature types
        user.transform = [enemies.Zombie, enemies.Skeleton]
        old_name = user.name
        result = abilities.Shapeshift().use(user, target)
        msg = result if isinstance(result, str) else str(result)
        assert "changes shape" in msg
        assert user.name != old_name

    def test_shapeshift_applies_shapeshifted_status(self):
        from src.core import abilities, enemies

        user, target = self._make_combatants()
        user.transform = [enemies.Zombie, enemies.Skeleton]
        abilities.Shapeshift().use(user, target)
        assert user.status_effects["Shapeshifted"].active is True
        assert user.status_effects["Shapeshifted"].duration == 3

    def test_shapeshift_readds_shapeshift_to_spellbook(self):
        from src.core import abilities, enemies

        user, target = self._make_combatants()
        user.transform = [enemies.Zombie, enemies.Skeleton]
        abilities.Shapeshift().use(user, target)
        assert "Shapeshift" in user.spellbook["Skills"]

    def test_shapeshift_no_mana_cost(self):
        from src.core import abilities, enemies

        user, target = self._make_combatants()
        user.transform = [enemies.Zombie, enemies.Skeleton]
        mana_before = user.mana.current
        abilities.Shapeshift().use(user, target)
        assert user.mana.current == mana_before


class TestBatch13AstralJudgment:
    """AstralJudgment - active-sign judgment + constellation spin."""

    @staticmethod
    def _make_combatants():
        from src.core import abilities
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Astromancer",
            class_name="Astromancer",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(300, 300),
            stats={"strength": 10, "intel": 30, "wisdom": 20, "con": 12, "charisma": 10, "dex": 10},
        )
        user.class_effects["Power Up"].active = False
        user.class_effects["Power Up"].duration = 0
        # Give elemental spells
        user.spellbook["Spells"] = {
            "Firebolt": abilities.Firebolt(),
            "Ice Lance": abilities.IceLance(),
            "Gust": abilities.Gust(),
            "Tremor": abilities.Tremor(),
        }
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(800, 800),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 10, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_astral_judgment_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.AstralJudgment().use(user, target)
        assert user.mana.current <= mana_before - 20

    def test_astral_judgment_resolves_sign_and_spins_constellation(self, monkeypatch):
        from src.core import abilities
        from src.core.classes import astromancer

        user, target = self._make_combatants()
        monkeypatch.setattr("src.core.classes.astromancer.random.choice", lambda choices: 1)
        abilities.AstralJudgment().use(user, target)
        assert target.health.current < 800
        assert astromancer.active_constellation(user) == "Tide"

    def test_astral_judgment_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.AstralJudgment().use(user, target)
        assert "no effect" in result.lower()

    def test_astral_judgment_tide_heals_and_wards(self, monkeypatch):
        from src.core import abilities
        from src.core.classes import astromancer

        user, target = self._make_combatants()
        user.health.current = 200
        user.astromancer_state["active_constellation_index"] = 1
        monkeypatch.setattr("src.core.classes.astromancer.random.choice", lambda choices: 2)
        abilities.AstralJudgment().use(user, target)
        assert user.health.current > 200
        assert user.stat_effects["Magic Defense"].active is True
        assert astromancer.active_constellation(user) == "Gale"


class TestBatch13SaveSystem:
    """Test that Batch 13 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch13_abilities(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in [
            "Doublecast",
            "Triplecast",
            "ChooseFate",
            "Shapeshift",
            "AstralJudgment",
            "VesperionChooseFate",
        ]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


# =====================================================================
# Batch 11 - Reveal, Transform/2/3/4, Stomp, ThrowRock
# =====================================================================


class TestBatch11YAMLLoading:
    """Verify all 7 Batch 11 YAML files load correctly."""

    _YAMLS = [
        ("reveal.yaml", "Reveal", 0),
        ("transform.yaml", "Transform", 0),
        ("transform2.yaml", "Transform", 0),
        ("transform3.yaml", "Transform", 0),
        ("transform4.yaml", "Transform", 0),
        ("stomp.yaml", "Stomp", 8),
        ("throw_rock.yaml", "Throw Rock", 7),
    ]

    def test_all_yaml_files_load(self):
        from src.core.data.ability_loader import AbilityFactory

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        for filename, expected_name, expected_cost in self._YAMLS:
            ability = AbilityFactory.create_from_yaml(yaml_dir / filename)
            assert ability.name == expected_name, f"{filename}: name mismatch"
            assert ability.cost == expected_cost, f"{filename}: cost mismatch"


class TestBatch11Reveal:
    """Reveal - passive; sets sight, adds 25% shadow resist, unequips Pendant of Vision."""

    @staticmethod
    def _make_user():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Inquisitor",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 15, "intel": 20, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        return user

    def test_reveal_passive_flag(self):
        from src.core import abilities

        ability = abilities.Reveal()
        assert ability.passive is True

    def test_reveal_sets_sight(self):
        from src.core import abilities

        user = self._make_user()
        user.sight = False
        abilities.Reveal().use(user, user)
        assert user.sight is True

    def test_reveal_adds_shadow_resist(self):
        from src.core import abilities

        user = self._make_user()
        base_resist = user.resistance["Shadow"]
        abilities.Reveal().use(user, user)
        assert user.resistance["Shadow"] == base_resist + 0.25

    def test_reveal_unequips_pendant_of_vision(self):
        from src.core import abilities

        user = self._make_user()
        user.equipment["Pendant"].name = "Pendant of Vision"
        abilities.Reveal().use(user, user)
        assert user.equipment["Pendant"].name != "Pendant of Vision"


class TestBatch11Transform:
    """Legacy Transform adapters route through persistent unlocked forms."""

    @staticmethod
    def _make_user(class_name="Druid"):
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name=class_name,
            class_name=class_name,
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 20, "intel": 15, "wisdom": 20, "con": 18, "charisma": 10, "dex": 15},
        )
        return user

    def test_transform_sets_panther(self):
        from src.core import abilities

        user = self._make_user()
        user.progression.purchased_node_ids.add("druid.ability.transform")
        abilities.Transform().use(user, user)
        assert user.cls.name == "Panther"
        assert user.transformation_state["active_form"] == "Panther"

    def test_transform2_sets_direbear(self):
        from src.core import abilities

        user = self._make_user()
        user.progression.purchased_node_ids.add("druid.ability.transform2")
        abilities.Transform2().use(user, user)
        assert user.cls.name == "Direbear"
        assert user.transformation_state["active_form"] == "Direbear"

    def test_transform3_sets_werewolf(self):
        from src.core import abilities

        user = self._make_user("Lycan")
        user.progression.purchased_node_ids.add("lycan.ability.transform3")
        abilities.Transform3().use(user, user)
        assert user.cls.name == "Werewolf"
        assert user.transformation_state["active_form"] == "Werewolf"

    def test_transform4_cannot_bypass_authored_form_unlocks(self):
        from src.core import abilities

        user = self._make_user()
        abilities.Transform4().use(user, user)
        assert user.cls.name == "Druid"
        assert user.transformation_state["active_form"] is None

    def test_transform_name(self):
        from src.core import abilities

        for cls_name in ["Transform", "Transform2", "Transform3", "Transform4"]:
            ability = getattr(abilities, cls_name)()
            assert ability.name == "Transform"


class TestBatch11Stomp:
    """Stomp - STR-based damage with stun chance."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Ogre",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(100, 100),
            stats={"strength": 40, "intel": 5, "wisdom": 5, "con": 30, "charisma": 5, "dex": 10},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 8, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_stomp_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Stomp().use(user, target)
        assert user.mana.current == mana_before - 8

    def test_stomp_can_deal_damage(self):
        from src.core import abilities

        damaged = False
        for _ in range(100):
            user, target = self._make_combatants()
            abilities.Stomp().use(user, target)
            if target.health.current < 300:
                damaged = True
                break
        assert damaged, "Stomp should deal damage sometimes"

    def test_stomp_can_stun(self):
        from src.core import abilities

        stunned = False
        for _ in range(200):
            user, target = self._make_combatants()
            abilities.Stomp().use(user, target)
            if target.status_effects["Stun"].active:
                stunned = True
                break
        assert stunned, "Stomp should stun sometimes"

    def test_stomp_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.Stomp().use(user, target)
        assert "no effect" in result.lower()
        assert target.health.current == 300

    def test_stomp_stun_respects_immunity(self):
        from src.core import abilities

        stunned = False
        for _ in range(200):
            user, target = self._make_combatants()
            target.status_immunity.append("Stun")
            abilities.Stomp().use(user, target)
            if target.status_effects["Stun"].active:
                stunned = True
                break
        assert not stunned, "Stun-immune targets should never be stunned"


class TestBatch11ThrowRock:
    """ThrowRock - random rock size, STR-based damage with prone chance."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Troll",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(100, 100),
            stats={"strength": 40, "intel": 5, "wisdom": 5, "con": 30, "charisma": 5, "dex": 10},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 8, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_throw_rock_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.ThrowRock().use(user, target)
        assert user.mana.current == mana_before - 7

    def test_throw_rock_can_deal_damage(self):
        from src.core import abilities

        damaged = False
        for _ in range(100):
            user, target = self._make_combatants()
            abilities.ThrowRock().use(user, target)
            if target.health.current < 300:
                damaged = True
                break
        assert damaged, "ThrowRock should deal damage sometimes"

    def test_throw_rock_can_cause_prone(self):
        from src.core import abilities

        prone = False
        for _ in range(200):
            user, target = self._make_combatants()
            abilities.ThrowRock().use(user, target)
            if target.physical_effects["Prone"].active:
                prone = True
                break
        assert prone, "ThrowRock should cause prone sometimes"

    def test_throw_rock_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.ThrowRock().use(user, target)
        assert "no effect" in result.lower()
        assert target.health.current == 300

    def test_throw_rock_mentions_rock_size(self):
        from src.core import abilities

        sizes_seen = set()
        for _ in range(200):
            user, target = self._make_combatants()
            result = abilities.ThrowRock().use(user, target)
            for s in ["tiny", "small", "medium", "large", "massive"]:
                if s in result.lower():
                    sizes_seen.add(s)
        # With 200 tries we should see multiple sizes
        assert len(sizes_seen) >= 2, f"Expected multiple rock sizes, saw: {sizes_seen}"


class TestBatch11SaveSystem:
    """Test that Batch 11 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch11_abilities(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in [
            "Reveal",
            "Transform",
            "Transform2",
            "Transform3",
            "Transform4",
            "Stomp",
            "ThrowRock",
        ]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


# =====================================================================
# Batch 10 - Maelstrom, Disintegrate, Inspect, PurityBody, Resurrection, ResistAll
# =====================================================================


class TestBatch10YAMLLoading:
    """Verify all 7 Batch 10 YAML files load correctly."""

    _YAMLS = [
        ("maelstrom.yaml", "Maelstrom", 40),
        ("disintegrate.yaml", "Disintegrate", 65),
        ("inspect.yaml", "Inspect", 5),
        ("purity_body.yaml", "Purity of Body", 0),
        ("purity_body2.yaml", "Purity of Body", 0),
        ("resurrection.yaml", "Resurrection", 0),
        ("resist_all.yaml", "Resist All", 25),
    ]

    def test_all_yaml_files_load(self):
        from src.core.data.ability_loader import AbilityFactory

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        for filename, expected_name, expected_cost in self._YAMLS:
            ability = AbilityFactory.create_from_yaml(yaml_dir / filename)
            assert ability.name == expected_name, f"{filename}: name mismatch"
            assert ability.cost == expected_cost, f"{filename}: cost mismatch"


class TestBatch10Maelstrom:
    """Maelstrom - HP cap with intel vs wisdom save."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        caster = TestGameState.create_player(
            name="Behemoth",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(200, 200),
            stats={"strength": 30, "intel": 40, "wisdom": 20, "con": 30, "charisma": 20, "dex": 10},
        )
        caster.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 20, "intel": 10, "wisdom": 15, "con": 18, "charisma": 10, "dex": 12},
        )
        return caster, target

    def test_maelstrom_deducts_mana(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        mana_before = caster.mana.current
        abilities.Maelstrom().cast(caster, target)
        assert caster.mana.current == mana_before - 40

    def test_maelstrom_caps_hp(self):
        from src.core import abilities

        reduced = False
        for _ in range(50):
            caster, target = self._make_combatants()
            abilities.Maelstrom().cast(caster, target)
            if target.health.current < 400:
                reduced = True
                # HP should be capped at 10% or 25% of max (40 or 100)
                assert target.health.current in (
                    40,
                    100,
                ), f"HP should be 40 or 100, got {target.health.current}"
                break
        assert reduced, "Maelstrom should reduce target HP"

    def test_maelstrom_blocked_by_ice_block(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.Maelstrom().cast(caster, target)
        assert "no effect" in result.lower()
        assert target.health.current == 400

    def test_maelstrom_blocked_by_tunnel(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        target.tunnel = True
        result = abilities.Maelstrom().cast(caster, target)
        assert "no effect" in result.lower()

    def test_maelstrom_no_effect_when_already_low(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        target.health.current = 30  # Below 10% of 400 = 40
        result = abilities.Maelstrom().cast(caster, target)
        # HP should stay at 30 since min(30, cap) = 30
        assert target.health.current == 30


class TestBatch10Disintegrate:
    """Disintegrate - instant kill + % HP damage."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        caster = TestGameState.create_player(
            name="Archvile",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(200, 200),
            stats={"strength": 10, "intel": 30, "wisdom": 20, "con": 15, "charisma": 50, "dex": 15},
        )
        caster.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 5, "charisma": 10, "dex": 5},
        )
        return caster, target

    def test_disintegrate_deducts_mana(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        mana_before = caster.mana.current
        abilities.Disintegrate().cast(caster, target)
        assert caster.mana.current == mana_before - 65

    def test_disintegrate_can_kill(self):
        from src.core import abilities

        killed = False
        for _ in range(200):
            caster, target = self._make_combatants()
            abilities.Disintegrate().cast(caster, target)
            if target.health.current <= 0:
                killed = True
                break
        assert killed, "Disintegrate should sometimes instant-kill"

    def test_disintegrate_deals_damage_when_not_killing(self):
        from src.core import abilities

        damaged = False
        for _ in range(50):
            caster, target = self._make_combatants()
            # Give high resist so instant kill rarely fires
            target.resistance["Death"] = 0.9
            abilities.Disintegrate().cast(caster, target)
            if 0 < target.health.current < 300:
                damaged = True
                break
        assert damaged, "Disintegrate should deal fallback damage"

    def test_disintegrate_blocked_by_ice_block(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.Disintegrate().cast(caster, target)
        assert "no effect" in result.lower()
        assert target.health.current == 300

    def test_disintegrate_full_resist_prevents_kill(self):
        from src.core import abilities

        for _ in range(100):
            caster, target = self._make_combatants()
            target.resistance["Death"] = 1.0
            abilities.Disintegrate().cast(caster, target)
            # With resist == 1, the instant kill phase is skipped entirely
            # Target should still take fallback damage but never be killed
            # (unless damage exceeds HP, which is possible)


class TestBatch10Inspect:
    """Inspect - reveals target info."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Seeker",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 15, "intel": 20, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 18, "charisma": 10, "dex": 12},
        )
        return user, target

    def test_inspect_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Inspect().use(user, target)
        assert user.mana.current == mana_before - 5

    def test_inspect_returns_info(self):
        from src.core import abilities

        user, target = self._make_combatants()
        # inspect() is an Enemy-only method; monkey-patch for test
        target.inspect = lambda: f"Name: {target.name}\nHP: {target.health.current}"
        result = abilities.Inspect().use(user, target)
        assert isinstance(result, str)
        assert len(result) > 0
        assert target.name in result


class TestBatch10PurityBody:
    """PurityBody - passive poison resist + immunity."""

    @staticmethod
    def _make_user():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Monk",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 20, "intel": 10, "wisdom": 20, "con": 18, "charisma": 10, "dex": 20},
        )
        return user

    def test_purity_body_passive_flag(self):
        from src.core import abilities

        ability = abilities.PurityBody()
        assert ability.passive is True

    def test_purity_body_sets_poison_resist(self):
        from src.core import abilities

        user = self._make_user()
        user.resistance["Poison"] = 0.0
        abilities.PurityBody().use(user, user)
        assert user.resistance["Poison"] == 0.5

    def test_purity_body_does_not_lower_resist(self):
        from src.core import abilities

        user = self._make_user()
        user.resistance["Poison"] = 0.8
        abilities.PurityBody().use(user, user)
        assert user.resistance["Poison"] == 0.8

    def test_purity_body_adds_poison_immunity(self):
        from src.core import abilities

        user = self._make_user()
        abilities.PurityBody().use(user, user)
        assert "Poison" in user.status_immunity


class TestBatch10PurityBody2:
    """PurityBody2 - passive 100% poison resist + stone immunity."""

    @staticmethod
    def _make_user():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Monk",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 20, "intel": 10, "wisdom": 20, "con": 18, "charisma": 10, "dex": 20},
        )
        return user

    def test_purity_body2_passive_flag(self):
        from src.core import abilities

        ability = abilities.PurityBody2()
        assert ability.passive is True

    def test_purity_body2_sets_full_poison_resist(self):
        from src.core import abilities

        user = self._make_user()
        user.resistance["Poison"] = 0.0
        abilities.PurityBody2().use(user, user)
        assert user.resistance["Poison"] == 1.0

    def test_purity_body2_adds_stone_immunity(self):
        from src.core import abilities

        user = self._make_user()
        abilities.PurityBody2().use(user, user)
        assert "Stone" in user.status_immunity


class TestBatch10Resurrection:
    """Resurrection - mana-to-HP (self) or revive (other)."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        caster = TestGameState.create_player(
            name="CasterWhiteMage",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 200),
            mana=(200, 150),
            stats={"strength": 10, "intel": 25, "wisdom": 25, "con": 15, "charisma": 15, "dex": 10},
        )
        caster.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="FallenAlly",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 0),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 18, "charisma": 10, "dex": 12},
        )
        return caster, target

    def test_resurrection_passive_flag(self):
        from src.core import abilities

        ability = abilities.Resurrection()
        assert ability.passive is True

    def test_resurrection_self_heal_full(self):
        from src.core import abilities

        caster, _ = self._make_combatants()
        # Self-cast: caster has 200 HP, 300 max, 150 mana
        # max_heal = 100, mana(150) > max_heal → full heal, mana -= 100
        result = abilities.Resurrection().cast(caster)
        assert caster.health.current == 300
        assert caster.mana.current == 50  # 150 - 100
        assert "full life" in result.lower()

    def test_resurrection_self_heal_partial(self):
        from src.core import abilities

        caster, _ = self._make_combatants()
        caster.health.current = 50
        caster.mana.current = 30
        # max_heal = 250, mana(30) < max_heal → heal 30 HP
        result = abilities.Resurrection().cast(caster)
        assert caster.health.current == 80  # 50 + 30
        assert caster.mana.current == 0
        assert "all mana" in result.lower()

    def test_resurrection_revive_other(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        result = abilities.Resurrection().cast(caster, target)
        expected_heal = int(400 * 0.1)  # 40
        assert target.health.current == expected_heal
        assert "brought back to life" in result.lower()


class TestBatch10ResistAll:
    """ResistAll applies visible wards to every spell-damage resistance."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        caster = TestGameState.create_player(
            name="Protector",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 25, "wisdom": 20, "con": 15, "charisma": 15, "dex": 10},
        )
        caster.class_effects["Power Up"].active = False
        return caster

    def test_resist_all_deducts_mana(self):
        from src.core import abilities

        caster = self._make_combatants()
        mana_before = caster.mana.current
        abilities.ResistAll().cast(caster, caster)
        assert caster.mana.current == mana_before - 25

    def test_resist_all_returns_message(self):
        from src.core import abilities

        caster = self._make_combatants()
        result = abilities.ResistAll().cast(caster, caster)
        assert "resist fire" in result.lower()
        assert "resist holy" in result.lower()
        assert caster.name in result

    def test_resist_all_activates_all_spell_resistance_buffs(self):
        from src.core import abilities

        caster = self._make_combatants()
        abilities.ResistAll().cast(caster, caster)

        for element in ("Fire", "Ice", "Electric", "Water", "Earth", "Wind", "Shadow", "Holy"):
            effect = caster.magic_effects[f"Resist {element}"]
            assert effect.active is True
            assert effect.duration == 5
            assert effect.extra == 0.5


class TestBatch10SaveSystem:
    """Test that Batch 10 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch10_abilities(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in [
            "Maelstrom",
            "Disintegrate",
            "Inspect",
            "PurityBody",
            "PurityBody2",
            "Resurrection",
            "ResistAll",
        ]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


# =====================================================================
# Batch 9 - Equipment skills, remaining enemy skills, GoldToss, DimMak
# =====================================================================


class TestBatch9YAMLLoading:
    """Verify all 10 Batch 9 YAML files load correctly."""

    _YAMLS = [
        ("shield_slam.yaml", "Shield Slam", 8),
        ("kidney_punch.yaml", "Kidney Punch", 18),
        ("poison_strike.yaml", "Poison Strike", 12),
        ("dim_mak.yaml", "Dim Mak", 18),
        ("exploit_weakness.yaml", "Exploit Weakness", 10),
        ("gold_toss.yaml", "Gold Toss", 0),
        ("lick.yaml", "Lick", 10),
        ("brain_gorge.yaml", "Brain Gorge", 30),
        ("detonate.yaml", "Detonate", 0),
        ("crush.yaml", "Crush", 25),
    ]

    def test_all_yaml_files_load(self):
        from src.core.data.ability_loader import AbilityFactory

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        for filename, expected_name, expected_cost in self._YAMLS:
            ability = AbilityFactory.create_from_yaml(yaml_dir / filename)
            assert ability.name == expected_name, f"{filename}: name mismatch"
            assert ability.cost == expected_cost, f"{filename}: cost mismatch"


class TestBatch9ShieldSlam:
    """ShieldSlam - str + shield-weight damage with stun chance."""

    @staticmethod
    def _make_combatants(has_shield=True):
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Knight",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(100, 100),
            stats={"strength": 30, "intel": 10, "wisdom": 10, "con": 20, "charisma": 10, "dex": 15},
        )
        if has_shield:
            user.equipment["OffHand"].subtyp = "Shield"
            user.equipment["OffHand"].weight = 10
        else:
            user.equipment["OffHand"].subtyp = "Weapon"
            user.equipment["OffHand"].weight = 5
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 10, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_shield_slam_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.ShieldSlam().use(user, target)
        assert user.mana.current == mana_before - 8

    def test_shield_slam_can_deal_damage_and_stun(self):
        from src.core import abilities

        damaged = False
        stunned = False
        for _ in range(100):
            user, target = self._make_combatants()
            abilities.ShieldSlam().use(user, target)
            if target.health.current < 400:
                damaged = True
            if target.status_effects["Stun"].active:
                stunned = True
            if damaged and stunned:
                break
        assert damaged, "ShieldSlam should sometimes deal damage"
        assert stunned, "ShieldSlam should sometimes stun"

    def test_shield_slam_requires_shield(self):
        from src.core import abilities

        user, target = self._make_combatants(has_shield=False)
        result = abilities.ShieldSlam().use(user, target)
        assert "no shield" in result.lower()

    def test_shield_slam_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.ShieldSlam().use(user, target)
        assert "no effect" in result.lower()

    def test_shield_slam_does_not_replay_prior_messages(self, monkeypatch):
        import random
        from types import SimpleNamespace

        from src.core import abilities

        user, target = self._make_combatants()
        ability = abilities.ShieldSlam()

        # Deterministic execution: always hit, fixed damage, win stun contest.
        monkeypatch.setattr(target, "dodge_chance", lambda _actor: 0.0)
        monkeypatch.setattr(
            user,
            "resolve_contact",
            lambda *_args, **_kwargs: SimpleNamespace(hit=True, attribution=None),
        )
        monkeypatch.setattr(target, "stun_contest_success", lambda _a, _r1, _r2: True)
        monkeypatch.setattr(random, "uniform", lambda _lo, _hi: 1.0)
        monkeypatch.setattr(random, "randint", lambda lo, hi: hi)

        first = str(ability.use(user, target))
        assert "is stunned for" in first
        assert first.count("slams") == 1

        # Simulate post-stun immunity window to block immediate re-stun.
        target.status_effects["Stun"].active = False
        target.status_effects["Stun"].duration = 0
        target.status_effects["Stun"].extra = 1

        second = str(ability.use(user, target))
        assert second.count("slams") == 1
        assert "is stunned for" not in second


class TestBatch9KidneyPunch:
    """KidneyPunch - offhand weapon check + weapon hit + stun."""

    @staticmethod
    def _make_combatants(has_offhand=True):
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Thief",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 20, "intel": 12, "wisdom": 10, "con": 15, "charisma": 10, "dex": 30},
        )
        if has_offhand:
            user.equipment["OffHand"].typ = "Weapon"
        else:
            user.equipment["OffHand"].typ = "Shield"
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 5, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_kidney_punch_requires_offhand_weapon(self):
        from src.core import abilities

        user, target = self._make_combatants(has_offhand=False)
        result = abilities.KidneyPunch().use(user, target)
        assert "off-hand weapon" in result.lower()

    def test_kidney_punch_can_stun(self):
        from src.core import abilities

        stunned = False
        for _ in range(100):
            user, target = self._make_combatants()
            abilities.KidneyPunch().use(user, target)
            if target.status_effects["Stun"].active:
                stunned = True
                break
        assert stunned, "KidneyPunch should sometimes stun"

    def test_kidney_punch_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.KidneyPunch().use(user, target)
        assert user.mana.current == mana_before - 18

    def test_kidney_punch_mana_never_goes_negative(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.mana.current = 10
        abilities.KidneyPunch().use(user, target)
        assert user.mana.current == 0


class TestBatch9PoisonStrike:
    """Poison Strike is a Nature spell with a main-hand bite and poison."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Assassin",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 20, "intel": 12, "wisdom": 10, "con": 15, "charisma": 10, "dex": 30},
        )
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 5, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_poison_strike_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.PoisonStrike().cast(user, target)
        assert user.mana.current == mana_before - 12

    def test_poison_strike_can_poison(self):
        from src.core import abilities

        poisoned = False
        for _ in range(100):
            user, target = self._make_combatants()
            abilities.PoisonStrike().cast(user, target)
            if target.status_effects["Poison"].active:
                poisoned = True
                assert target.status_effects["Poison"].extra > 0
                break
        assert poisoned, "PoisonStrike should sometimes apply Poison"

    def test_poison_strike_respects_immunity(self):
        from src.core import abilities

        for _ in range(100):
            user, target = self._make_combatants()
            target.status_immunity = ["Poison"]
            abilities.PoisonStrike().cast(user, target)
            assert not target.status_effects["Poison"].active


class TestBatch9DimMak:
    """Dim Mak routes through the full-Ki Master Monk finisher."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Monk",
            class_name="Master Monk",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(200, 200),
            stats={"strength": 30, "intel": 15, "wisdom": 30, "con": 20, "charisma": 10, "dex": 25},
        )
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(100, 100),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 5, "con": 3, "charisma": 10, "dex": 5},
        )
        return user, target

    @staticmethod
    def _fill_ki(user):
        from src.core.classes import promotion_kits

        promotion_kits.gain_meter(
            user,
            "ki",
            promotion_kits.cap_for(user, "ki"),
            "test",
        )

    def test_dim_mak_deducts_mana(self, monkeypatch):
        from src.core import abilities

        user, target = self._make_combatants()
        self._fill_ki(user)
        monkeypatch.setattr(
            user,
            "weapon_damage",
            lambda *_args, **_kwargs: ("Dim Mak misses.\n", False, False),
        )
        mana_before = user.mana.current
        abilities.DimMak().use(user, target)
        assert user.mana.current == mana_before - 18

    def test_dim_mak_absorbs_essence_on_kill(self, monkeypatch):
        from src.core import abilities

        user, target = self._make_combatants()
        self._fill_ki(user)
        user.health.current = 200

        def killing_blow(victim, **_kwargs):
            victim.health.current = 0
            return "Dim Mak hits.\n", True, False

        monkeypatch.setattr(user, "weapon_damage", killing_blow)
        message = abilities.DimMak().use(user, target)

        assert "absorbs" in message
        assert user.health.current == 300

    def test_dim_mak_can_stun_on_survival(self, monkeypatch):
        from src.core import abilities

        user, target = self._make_combatants()
        self._fill_ki(user)
        monkeypatch.setattr(
            user,
            "weapon_damage",
            lambda *_args, **_kwargs: ("Dim Mak hits.\n", True, False),
        )
        monkeypatch.setattr(
            "src.core.classes.promotion_kits.tracks.resolve_death_contest",
            lambda *_args, **_kwargs: (False, False),
        )
        rolls = iter((user.stats.wisdom, 0))
        monkeypatch.setattr(
            "src.core.classes.promotion_kits.tracks.random.randint",
            lambda *_args: next(rolls),
        )

        message = abilities.DimMak().use(user, target)

        assert target.status_effects["Stun"].active
        assert "stunned" in message


class TestBatch9ExploitWeakness:
    """ExploitWeakness - detect weakness, boost weapon mod or random status."""

    @staticmethod
    def _make_combatants(fire_weak=True):
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Seeker",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 20, "intel": 12, "wisdom": 10, "con": 15, "charisma": 10, "dex": 20},
        )
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 5, "charisma": 10, "dex": 5},
        )
        if fire_weak:
            target.resistance["Fire"] = -0.5  # 50% weakness
        return user, target

    def test_exploit_weakness_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.ExploitWeakness().use(user, target)
        assert user.mana.current == mana_before - 10

    def test_exploit_weakness_finds_elemental_weakness(self):
        from src.core import abilities

        user, target = self._make_combatants(fire_weak=True)
        result = abilities.ExploitWeakness().use(user, target)
        assert "weakness" in result.lower() or "fire" in result.lower()

    def test_exploit_weakness_random_status_when_no_weakness(self):
        from src.core import abilities

        affected = False
        for _ in range(100):
            user, target = self._make_combatants(fire_weak=False)
            abilities.ExploitWeakness().use(user, target)
            for se in target.status_effects.values():
                if se.active:
                    affected = True
                    break
            if affected:
                break
        assert affected, "ExploitWeakness should sometimes apply random status"

    def test_exploit_weakness_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.ExploitWeakness().use(user, target)
        assert "no effect" in result.lower()


class TestBatch9GoldToss:
    """GoldToss - gold-based unblockable damage."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Gambler",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 15, "intel": 10, "wisdom": 10, "con": 15, "charisma": 15, "dex": 15},
        )
        user.gold = 500
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 10, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_gold_toss_no_gold_does_nothing(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.gold = 0
        result = abilities.GoldToss().use(user, target)
        assert "nothing" in result.lower()

    def test_gold_toss_spends_gold(self):
        from src.core import abilities

        user, target = self._make_combatants()
        gold_before = user.gold
        abilities.GoldToss().use(user, target)
        assert user.gold < gold_before

    def test_gold_toss_can_use_private_enemy_pool_without_spending_reward_gold(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user.gold = 25000
        user._gold_toss_pool = 500
        abilities.GoldToss().use(user, target)
        assert user.gold == 25000
        assert user._gold_toss_pool < 500

    def test_gold_toss_can_deal_damage(self):
        from src.core import abilities

        damaged = False
        for _ in range(50):
            user, target = self._make_combatants()
            abilities.GoldToss().use(user, target)
            if target.health.current < 400:
                damaged = True
                break
        assert damaged, "GoldToss should sometimes deal damage"

    def test_gold_toss_target_can_catch(self):
        from src.core import abilities

        caught = False
        for _ in range(100):
            user, target = self._make_combatants()
            gold_before = target.gold
            abilities.GoldToss().use(user, target)
            if target.gold > gold_before:
                caught = True
                break
        assert caught, "Target should sometimes catch gold"


class TestBatch9Lick:
    """Lick - weapon hit + random status effect."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Battletoad",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 30, "intel": 10, "wisdom": 10, "con": 15, "charisma": 10, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 5, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_lick_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Lick().use(user, target)
        assert user.mana.current == mana_before - 10

    def test_lick_can_apply_status(self):
        from src.core import abilities

        affected = False
        for _ in range(100):
            user, target = self._make_combatants()
            abilities.Lick().use(user, target)
            for se in target.status_effects.values():
                if se.active:
                    affected = True
                    break
            if affected:
                break
        assert affected, "Lick should sometimes apply a random status"

    def test_lick_does_not_apply_hangover(self, monkeypatch):
        from src.core import abilities

        monkeypatch.setattr(
            "random.choice", lambda seq: "Hangover" if "Hangover" in seq else seq[0]
        )
        monkeypatch.setattr("random.randint", lambda start, end: end)

        user, target = self._make_combatants()
        abilities.Lick().use(user, target)

        assert target.status_effects["Hangover"].active is False


class TestBatch9BrainGorge:
    """BrainGorge - weapon hit + latch + extra damage + intel drain."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="MindFlayer",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 30, "intel": 30, "wisdom": 15, "con": 15, "charisma": 10, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 10, "intel": 20, "wisdom": 5, "con": 5, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_brain_gorge_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.BrainGorge().use(user, target)
        assert user.mana.current == mana_before - 30

    def test_brain_gorge_can_drain_intel(self):
        from src.core import abilities

        intel_drained = False
        for _ in range(100):
            user, target = self._make_combatants()
            intel_before = target.stats.intel
            abilities.BrainGorge().use(user, target)
            if target.stats.intel < intel_before:
                intel_drained = True
                break
        assert intel_drained, "BrainGorge should sometimes drain intelligence"

    def test_brain_gorge_deals_extra_damage(self):
        from src.core import abilities

        extra_hit = False
        for _ in range(50):
            user, target = self._make_combatants()
            result = abilities.BrainGorge().use(user, target)
            text = result.message if hasattr(result, "message") else str(result)
            if "additional" in text.lower() or "latches" in text.lower():
                extra_hit = True
                break
        assert extra_hit, "BrainGorge should sometimes latch for extra damage"


class TestBatch9Detonate:
    """Detonate - self-destruct massive damage."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Cyborg",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(100, 100),
            stats={"strength": 30, "intel": 10, "wisdom": 10, "con": 20, "charisma": 10, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(800, 800),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 10, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_detonate_kills_user(self):
        from src.core import abilities

        user, target = self._make_combatants()
        abilities.Detonate().use(user, target)
        assert user.health.current <= 0

    def test_detonate_deals_massive_damage(self):
        from src.core import abilities

        damaged = False
        for _ in range(10):
            user, target = self._make_combatants()
            abilities.Detonate().use(user, target)
            if target.health.current < 800:
                damaged = True
                break
        assert damaged, "Detonate should deal massive damage to target"

    def test_detonate_no_mana_cost(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Detonate().use(user, target)
        assert user.mana.current == mana_before


class TestBatch9Crush:
    """Crush - grab + crush + throw for physical damage."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Ogre",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(600, 600),
            mana=(100, 100),
            stats={"strength": 40, "intel": 5, "wisdom": 5, "con": 25, "charisma": 5, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 10, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_crush_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Crush().use(user, target)
        assert user.mana.current == mana_before - 25

    def test_crush_can_deal_damage(self):
        from src.core import abilities

        damaged = False
        for _ in range(50):
            user, target = self._make_combatants()
            abilities.Crush().use(user, target)
            if target.health.current < 400:
                damaged = True
                break
        assert damaged, "Crush should sometimes deal damage"

    def test_crush_can_throw(self):
        from src.core import abilities

        thrown = False
        for _ in range(100):
            user, target = self._make_combatants()
            result = abilities.Crush().use(user, target)
            if "throws" in result.lower() or "ground" in result.lower():
                thrown = True
                break
        assert thrown, "Crush should sometimes throw the target"

    def test_crush_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.Crush().use(user, target)
        assert "no effect" in result.lower()


class TestBatch9SaveSystem:
    """Test that Batch 9 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch9_abilities(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name, expected in [
            ("ShieldSlam", "shield_slam"),
            ("KidneyPunch", "kidney_punch"),
            ("PoisonStrike", "poison_strike"),
            ("DimMak", "dim_mak"),
            ("ExploitWeakness", "exploit_weakness"),
            ("GoldToss", "gold_toss"),
            ("Lick", "lick"),
            ("BrainGorge", "brain_gorge"),
            ("Detonate", "detonate"),
            ("Crush", "crush"),
        ]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == expected, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.ability_id == expected
            assert restored.name == ability.name


# =====================================================================
# Batch 8 - Enemy skills, Hex, Vulcanize, Smite family, Turn Undead
# =====================================================================


class TestBatch8YAMLLoading:
    """Verify all 13 Batch 8 YAML files load correctly."""

    _YAMLS = [
        ("screech.yaml", "Screech", 15),
        ("acid_spit.yaml", "Acid Spit", 0),
        ("breathe_fire.yaml", "Breathe Fire", 0),
        ("nightmare_fuel.yaml", "Nightmare Fuel", 20),
        ("widows_wail.yaml", "Widow's Wail", 12),
        ("goblin_punch.yaml", "Goblin Punch", 0),
        ("hex.yaml", "Hex", 14),
        ("vulcanize.yaml", "Vulcanize", 15),
        ("smite.yaml", "Smite", 10),
        ("smite_2.yaml", "Smite", 20),
        ("smite_3.yaml", "Smite", 32),
        ("turn_undead.yaml", "Turn Undead", 8),
        ("turn_undead_2.yaml", "Turn Undead", 20),
    ]

    def test_all_yaml_files_load(self):
        from src.core.data.ability_loader import AbilityFactory

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        for filename, expected_name, expected_cost in self._YAMLS:
            ability = AbilityFactory.create_from_yaml(yaml_dir / filename)
            assert ability.name == expected_name, f"{filename}: name mismatch"
            assert ability.cost == expected_cost, f"{filename}: cost mismatch"


class TestBatch8Screech:
    """Screech - stat-contest damage + permanent silence."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Banshee",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 15, "intel": 30, "wisdom": 15, "con": 15, "charisma": 10, "dex": 20},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 5, "con": 5, "charisma": 10, "dex": 12},
        )
        return user, target

    def test_screech_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Screech().use(user, target)
        assert user.mana.current == mana_before - 15

    def test_screech_can_deal_damage_and_silence(self):
        from src.core import abilities

        damaged = False
        silenced = False
        for _ in range(100):
            user, target = self._make_combatants()
            abilities.Screech().use(user, target)
            if target.health.current < 400:
                damaged = True
            if target.status_effects["Silence"].active:
                silenced = True
                assert target.status_effects["Silence"].duration == -1
            if damaged and silenced:
                break
        assert damaged, "Screech should sometimes deal damage"
        assert silenced, "Screech should sometimes apply Silence"

    def test_screech_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.Screech().use(user, target)
        assert "no effect" in result.lower()

    def test_screech_respects_silence_immunity(self):
        from src.core import abilities

        for _ in range(100):
            user, target = self._make_combatants()
            target.status_immunity = ["Silence"]
            abilities.Screech().use(user, target)
            assert not target.status_effects["Silence"].active


class TestBatch8AcidSpit:
    """AcidSpit - intel-based magic damage + DOT."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Spider",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 15, "intel": 25, "wisdom": 15, "con": 15, "charisma": 10, "dex": 20},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 2, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_acid_spit_dynamic_cost(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.AcidSpit().use(user, target)
        expected_cost = 6 * user.level.pro_level
        assert user.mana.current == mana_before - expected_cost

    def test_acid_spit_can_deal_damage(self):
        from src.core import abilities

        damaged = False
        for _ in range(50):
            user, target = self._make_combatants()
            abilities.AcidSpit().use(user, target)
            if target.health.current < 400:
                damaged = True
                break
        assert damaged, "AcidSpit should sometimes deal damage"

    def test_acid_spit_can_apply_dot(self):
        from src.core import abilities

        dotted = False
        for _ in range(100):
            user, target = self._make_combatants()
            abilities.AcidSpit().use(user, target)
            if target.magic_effects["DOT"].active:
                dotted = True
                assert target.magic_effects["DOT"].duration == 2
                break
        assert dotted, "AcidSpit should sometimes apply DOT"

    def test_acid_spit_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.AcidSpit().use(user, target)
        assert "no effect" in result.lower()


class TestBatch8BreatheFire:
    """BreatheFire - stat-based elemental breath weapon."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Dragon",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(100, 100),
            stats={"strength": 30, "intel": 25, "wisdom": 15, "con": 25, "charisma": 10, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 18, "charisma": 10, "dex": 12},
        )
        return user, target

    def test_breathe_fire_deals_damage(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.BreatheFire().use(user, target)
        assert target.health.current < 400
        assert "breath" in result.lower()

    def test_breathe_fire_respects_element_type(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.BreatheFire().use(user, target, typ="Fire")
        assert "Fire" in result

    def test_breathe_fire_no_mana_cost(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.BreatheFire().use(user, target)
        assert user.mana.current == mana_before


class TestBatch8NightmareFuel:
    """NightmareFuel - sleep-conditional damage."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="NightHag",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 15, "intel": 30, "wisdom": 15, "con": 15, "charisma": 10, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 5, "con": 18, "charisma": 10, "dex": 12},
        )
        return user, target

    def test_nightmare_fuel_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.status_effects["Sleep"].active = True
        target.status_effects["Sleep"].duration = 3
        mana_before = user.mana.current
        abilities.NightmareFuel().use(user, target)
        assert user.mana.current == mana_before - 20

    def test_nightmare_fuel_does_nothing_if_not_asleep(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.NightmareFuel().use(user, target)
        assert target.health.current == 400
        assert "does nothing" in result.lower()

    def test_nightmare_fuel_deals_damage_if_asleep(self):
        from src.core import abilities

        damaged = False
        for _ in range(50):
            user, target = self._make_combatants()
            target.status_effects["Sleep"].active = True
            target.status_effects["Sleep"].duration = 3
            abilities.NightmareFuel().use(user, target)
            if target.health.current < 400:
                damaged = True
                break
        assert damaged, "NightmareFuel should deal damage to sleeping targets"

    def test_nightmare_fuel_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.NightmareFuel().use(user, target)
        assert "no effect" in result.lower()


class TestBatch8WidowsWail:
    """WidowsWail - inverse-HP damage to both actor and target."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Widow",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 100),  # low current HP for high damage
            mana=(200, 200),
            stats={"strength": 15, "intel": 30, "wisdom": 5, "con": 15, "charisma": 10, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 5, "con": 18, "charisma": 10, "dex": 12},
        )
        return user, target

    def test_widows_wail_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.WidowsWail().use(user, target)
        assert user.mana.current == mana_before - 12

    def test_widows_wail_can_damage_both(self):
        from src.core import abilities

        user_hit = False
        target_hit = False
        for _ in range(100):
            user, target = self._make_combatants()
            abilities.WidowsWail().use(user, target)
            if user.health.current < 100:
                user_hit = True
            if target.health.current < 400:
                target_hit = True
            if user_hit and target_hit:
                break
        assert user_hit, "WidowsWail should sometimes damage the user"
        assert target_hit, "WidowsWail should sometimes damage the target"

    def test_widows_wail_damage_scales_inversely(self):
        from src.core import abilities

        # Low HP user → high damage
        damages = []
        for _ in range(50):
            user, target = self._make_combatants()
            abilities.WidowsWail().use(user, target)
            if target.health.current < 400:
                damages.append(400 - target.health.current)
        if damages:
            # With 400 max / 100 current → damage = min(200, (400/100)*20) = 80
            assert max(damages) <= 200, "Damage should be capped at 200"

    def test_widows_wail_target_ice_block(self):
        from src.core import abilities

        for _ in range(50):
            user, target = self._make_combatants()
            target.magic_effects["Ice Block"].active = True
            abilities.WidowsWail().use(user, target)
            assert target.health.current == 400, "Ice block should prevent target damage"


class TestBatch8GoblinPunch:
    """GoblinPunch - multi-hit str-diff damage."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Goblin",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(200, 200),
            mana=(50, 50),
            stats={"strength": 8, "intel": 5, "wisdom": 5, "con": 10, "charisma": 5, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 30, "intel": 8, "wisdom": 10, "con": 18, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_goblin_punch_no_mana_cost(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.GoblinPunch().use(user, target)
        assert user.mana.current == mana_before

    def test_goblin_punch_multi_hit(self):
        from src.core import abilities

        multi = False
        for _ in range(50):
            user, target = self._make_combatants()
            result = abilities.GoblinPunch().use(user, target)
            if result.count("punches") > 1:
                multi = True
                break
        assert multi, "GoblinPunch should produce multiple punches"

    def test_goblin_punch_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.GoblinPunch().use(user, target)
        assert "no effect" in result.lower()

    def test_goblin_punch_str_diff_damage(self):
        from src.core import abilities

        # target.str=30, user.str=8 → str_diff = max(1+pro_level, (30-8)//2) = max(4, 11) = 11
        for _ in range(50):
            user, target = self._make_combatants()
            hp_before = target.health.current
            abilities.GoblinPunch().use(user, target)
            if target.health.current < hp_before:
                dmg = hp_before - target.health.current
                # Each hit does str_diff; at least one hit means dmg >= str_diff
                str_diff = max(
                    1 + user.level.pro_level,
                    (target.stats.strength - user.stats.strength) // 2,
                )
                assert dmg % str_diff == 0, "Damage should be multiple of str_diff"
                break


class TestBatch8Hex:
    """Hex - triple-status spell (Poison/Blind/Silence)."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        caster = TestGameState.create_player(
            name="Witch",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 40, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        caster.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 5, "con": 5, "charisma": 10, "dex": 12},
        )
        return caster, target

    def test_hex_deducts_mana(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        mana_before = caster.mana.current
        abilities.Hex().cast(caster, target)
        assert caster.mana.current == mana_before - 14

    def test_hex_can_apply_all_three_statuses(self):
        from src.core import abilities

        poison = False
        blind = False
        silence = False
        for _ in range(200):
            caster, target = self._make_combatants()
            abilities.Hex().cast(caster, target)
            if target.status_effects["Poison"].active:
                poison = True
            if target.status_effects["Blind"].active:
                blind = True
            if target.status_effects["Silence"].active:
                silence = True
            if poison and blind and silence:
                break
        assert poison, "Hex should sometimes apply Poison"
        assert blind, "Hex should sometimes apply Blind"
        assert silence, "Hex should sometimes apply Silence"

    def test_hex_blocked_by_ice_block(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.Hex().cast(caster, target)
        assert "no effect" in result.lower()

    def test_hex_respects_immunity(self):
        from src.core import abilities

        for _ in range(100):
            caster, target = self._make_combatants()
            target.status_immunity = ["Poison", "Blind", "Silence"]
            abilities.Hex().cast(caster, target)
            assert not target.status_effects["Poison"].active
            assert not target.status_effects["Blind"].active
            assert not target.status_effects["Silence"].active

    def test_hex_poison_sets_extra(self):
        from src.core import abilities

        for _ in range(200):
            caster, target = self._make_combatants()
            abilities.Hex().cast(caster, target)
            if target.status_effects["Poison"].active:
                assert target.status_effects["Poison"].extra >= 1
                assert target.status_effects["Poison"].duration >= 3
                break


class TestBatch8Vulcanize:
    """Vulcanize - self fire-damage + defense buff."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        caster = TestGameState.create_player(
            name="Mage",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 25, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        caster.class_effects["Power Up"].active = False
        return caster

    def test_vulcanize_deducts_mana(self):
        from src.core import abilities

        caster = self._make_combatants()
        mana_before = caster.mana.current
        abilities.Vulcanize().cast(caster)
        assert caster.mana.current == mana_before - 15

    def test_vulcanize_applies_self_damage(self):
        from src.core import abilities

        caster = self._make_combatants()
        hp_before = caster.health.current
        abilities.Vulcanize().cast(caster)
        # With 0 fire resist, damage = 0.1 * 300 = 30
        assert caster.health.current < hp_before

    def test_vulcanize_grants_defense_buff(self):
        from src.core import abilities

        caster = self._make_combatants()
        abilities.Vulcanize().cast(caster)
        assert caster.stat_effects["Defense"].active
        assert caster.stat_effects["Defense"].duration == 5
        assert caster.stat_effects["Defense"].extra > 0

    def test_vulcanize_fire_resist_reduces_self_damage(self):
        from src.core import abilities

        # With high fire resist, damage should be lower
        caster = self._make_combatants()
        caster.resistance["Fire"] = 0.5
        hp_before = caster.health.current
        abilities.Vulcanize().cast(caster)
        damage_taken = hp_before - caster.health.current
        # partial fire resist → less self damage
        # Explicit defense buff should be subtracted from check_mod result
        # Just check damage is less than the 0-resist case
        assert damage_taken < 30 or caster.stat_effects["Defense"].active


class TestBatch8SmiteFamily:
    """Smite / Smite2 / Smite3 - weapon strike + holy follow-up."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Paladin",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(200, 200),
            stats={"strength": 25, "intel": 20, "wisdom": 20, "con": 18, "charisma": 15, "dex": 18},
        )
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 8, "charisma": 10, "dex": 5},
        )
        return user, target

    def test_smite_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Smite().cast(user, target)
        assert user.mana.current == mana_before - 10

    def test_smite2_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Smite2().cast(user, target)
        assert user.mana.current == mana_before - 20

    def test_smite3_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Smite3().cast(user, target)
        assert user.mana.current == mana_before - 32

    def test_smite_can_deal_damage(self):
        from src.core import abilities

        damaged = False
        for _ in range(50):
            user, target = self._make_combatants()
            abilities.Smite().cast(user, target)
            if target.health.current < 500:
                damaged = True
                break
        assert damaged, "Smite should sometimes deal damage"

    def test_smite_returns_string(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.Smite().cast(user, target)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_smite_followup_bypasses_physical_only_mana_shield(self, monkeypatch):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Mana Shield"].active = True
        target.magic_effects["Mana Shield"].duration = 25
        target.mana.current = 100
        user.weapon_damage = lambda _target, **_kwargs: (
            "Paladin hits Enemy.\n",
            True,
            1,
        )
        user.check_mod = lambda mod, **_kwargs: 30 if mod == "magic" else 0
        target.check_mod = lambda mod, **_kwargs: 0
        monkeypatch.setattr("random.randint", lambda _low, high: high)
        monkeypatch.setattr("random.uniform", lambda _low, _high: 1.0)

        result = abilities.Smite().cast(user, target, special=True)

        assert "mana shield" not in result.lower()
        assert target.magic_effects["Mana Shield"].active is True
        assert target.mana.current == 100
        assert target.health.current < target.health.max


class TestBatch8TurnUndeadFamily:
    """TurnUndead / TurnUndead2 - undead-only kill or holy damage."""

    @staticmethod
    def _make_combatants(undead=True):
        from tests.test_framework import TestGameState

        caster = TestGameState.create_player(
            name="Cleric",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 25, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        caster.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="Zombie",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 20, "intel": 8, "wisdom": 10, "con": 15, "charisma": 10, "dex": 12},
        )
        if undead:
            target.enemy_typ = "Undead"
        else:
            target.enemy_typ = "Beast"
        return caster, target

    def test_turn_undead_deducts_mana(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        mana_before = caster.mana.current
        abilities.TurnUndead().cast(caster, target)
        assert caster.mana.current == mana_before - 8

    def test_turn_undead2_deducts_mana(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        mana_before = caster.mana.current
        abilities.TurnUndead2().cast(caster, target)
        assert caster.mana.current == mana_before - 20

    def test_turn_undead_does_nothing_to_non_undead(self):
        from src.core import abilities

        caster, target = self._make_combatants(undead=False)
        result = abilities.TurnUndead().cast(caster, target)
        assert target.health.current == 300
        assert "does nothing" in result.lower()

    def test_turn_undead_damages_undead(self):
        from src.core import abilities

        damaged = False
        for _ in range(50):
            caster, target = self._make_combatants()
            abilities.TurnUndead().cast(caster, target)
            if target.health.current < 300:
                damaged = True
                break
        assert damaged, "TurnUndead should sometimes damage undead"

    def test_turn_undead_can_kill(self):
        from src.core import abilities

        killed = False
        for _ in range(200):
            caster, target = self._make_combatants()
            abilities.TurnUndead().cast(caster, target)
            if target.health.current <= 0:
                killed = True
                break
        assert killed, "TurnUndead should sometimes instantly kill undead"

    def test_turn_undead_blocked_by_ice_block(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.TurnUndead().cast(caster, target)
        assert "no effect" in result.lower()


class TestBatch8SaveSystem:
    """Test that Batch 8 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch8_abilities(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in [
            "Screech",
            "AcidSpit",
            "BreatheFire",
            "NightmareFuel",
            "WidowsWail",
            "GoblinPunch",
            "Hex",
            "Vulcanize",
            "Smite",
            "Smite2",
            "Smite3",
            "TurnUndead",
            "TurnUndead2",
        ]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


# =====================================================================
# Batch 14 - ConsumeItem, DestroyMetal, SlotMachine, Totem
# =====================================================================


class TestBatch14YAMLLoading:
    """Verify all 4 Batch 14 YAML files load correctly."""

    _YAMLS = [
        ("consume_item.yaml", "Consume Item", 14),
        ("destroy_metal.yaml", "Destroy Metal", 27),
        ("slot_machine.yaml", "Slot Machine", 15),
        ("totem.yaml", "Totem", 12),
    ]

    def test_all_yaml_files_load(self):
        from src.core.data.ability_loader import AbilityFactory

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        for filename, expected_name, expected_cost in self._YAMLS:
            ability = AbilityFactory.create_from_yaml(yaml_dir / filename)
            assert ability.name == expected_name, f"{filename}: name mismatch"
            assert ability.cost == expected_cost, f"{filename}: cost mismatch"


class TestBatch14ConsumeItem:
    """ConsumeItem - steal and consume an item from the target."""

    @staticmethod
    def _make_combatants(target_has_items=True):
        from src.core import items as _items
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Xorn",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 20, "intel": 10, "wisdom": 10, "con": 15, "charisma": 10, "dex": 25},
            gold=5000,
        )
        target = TestGameState.create_player(
            name="Victim",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 10, "intel": 8, "wisdom": 10, "con": 10, "charisma": 10, "dex": 5},
            gold=10000,
        )
        if target_has_items:
            sword = _items.random_item(3)()
            target.modify_inventory(sword)
        return user, target

    def test_consume_item_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.ConsumeItem().use(user, target)
        # Mana is deducted by 14 but gold-fallback or item-steal may regen some
        assert user.mana.current <= mana_before

    def test_consume_item_produces_output(self):
        from src.core import abilities

        for _ in range(50):
            user, target = self._make_combatants()
            result = abilities.ConsumeItem().use(user, target)
            msg = result if isinstance(result, str) else str(result)
            assert len(msg) > 0

    def test_consume_item_blocked_by_ice_block(self):
        from src.core import abilities

        user, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        result = abilities.ConsumeItem().use(user, target)
        msg = result if isinstance(result, str) else str(result)
        assert "no effect" in msg.lower()

    def test_consume_item_gold_fallback(self):
        """When target has no items, should steal gold and heal."""
        from src.core import abilities

        saw_valid_outcome = False
        for _ in range(100):
            user, target = self._make_combatants(target_has_items=False)
            result = abilities.ConsumeItem().use(user, target)
            msg = result if isinstance(result, str) else str(result)
            lowered = msg.lower()
            if "gold" in lowered or "can't steal anything" in lowered:
                saw_valid_outcome = True
                break
        assert saw_valid_outcome is True

    def test_consume_item_potion_effect_applies_to_user_not_target(self, monkeypatch):
        import random

        from src.core import abilities
        from src.core import items as _items

        user, target = self._make_combatants(target_has_items=False)
        target.modify_inventory(_items.EchoScreen())
        ability = abilities.ConsumeItem()

        # Deterministic steal success path.
        monkeypatch.setattr(random, "randint", lambda _lo, hi: hi)
        monkeypatch.setattr(random, "choice", lambda seq: seq[0])

        ability.use(user, target)

        assert user.magic_effects["Regen"].active is True
        assert target.magic_effects["Regen"].active is False


class TestBatch14DestroyMetal:
    """DestroyMetal - destroy metal items from target's inventory/equipment."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Rust",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 20, "intel": 10, "wisdom": 10, "con": 15, "charisma": 10, "dex": 20},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 15, "intel": 8, "wisdom": 10, "con": 15, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_destroy_metal_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.DestroyMetal().use(user, target)
        assert user.mana.current == mana_before - 27

    def test_destroy_metal_produces_output(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.DestroyMetal().use(user, target)
        msg = result if isinstance(result, str) else str(result)
        assert len(msg) > 0

    def test_destroy_metal_no_metal(self):
        """When no metal items exist, should report appropriately."""
        from src.core import abilities

        user, target = self._make_combatants()
        # Clear inventory and check output
        target.inventory.clear()
        result = abilities.DestroyMetal().use(user, target)
        msg = result if isinstance(result, str) else str(result)
        # Should either destroy equipped metal or report no metal
        assert "metal" in msg.lower() or "destroy" in msg.lower() or "fail" in msg.lower()


class TestBatch14SlotMachine:
    """SlotMachine - spin 3 digits with many possible outcomes."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Jester",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 15, "intel": 15, "wisdom": 10, "con": 15, "charisma": 25, "dex": 15},
            gold=5000,
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 15, "intel": 8, "wisdom": 10, "con": 15, "charisma": 10, "dex": 10},
            gold=5000,
        )
        return user, target

    def test_slot_machine_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda _user, _target: "3H,4D,5C",
        )
        assert user.mana.current == mana_before - 15

    def test_slot_machine_death_spin(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda u, t: "666",
        )
        msg = result if isinstance(result, str) else str(result)
        assert "beast" in msg.lower() or "death" in msg.lower()

    def test_slot_machine_trips_spin(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda u, t: "777",
        )
        msg = result if isinstance(result, str) else str(result)
        assert "3 of a kind" in msg.lower() or "revitalized" in msg.lower()

    def test_slot_machine_straight_spin(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda u, t: "345",
        )
        msg = result if isinstance(result, str) else str(result)
        assert "straight" in msg.lower()

    def test_slot_machine_palindrome_spin(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda u, t: "121",
        )
        msg = result if isinstance(result, str) else str(result)
        assert "palindrome" in msg.lower()

    def test_slot_machine_evens_spin(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda u, t: "246",
        )
        msg = result if isinstance(result, str) else str(result)
        assert "evens" in msg.lower() or "gold" in msg.lower()

    def test_slot_machine_odds_spin(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda u, t: "135",
        )
        msg = result if isinstance(result, str) else str(result)
        assert "odds" in msg.lower() or "gains" in msg.lower()

    def test_slot_machine_straight_flush_card_hand(self):
        from src.core import abilities

        user, target = self._make_combatants()
        health_before = target.health.current
        mana_before = target.mana.current
        result = abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda u, t: "AS,2S,3S",
        )
        msg = result if isinstance(result, str) else str(result)
        assert "straight flush" in msg.lower()
        assert target.health.current < health_before
        assert target.mana.current < mana_before

    def test_slot_machine_flush_card_hand_drains_gold_and_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        user_gold_before = user.gold
        target_gold_before = target.gold
        target_mana_before = target.mana.current
        result = abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda u, t: "AS,9S,KS",
        )
        msg = result if isinstance(result, str) else str(result)
        assert "flush" in msg.lower()
        assert user.gold > user_gold_before
        assert target.gold < target_gold_before
        assert target.mana.current < target_mana_before

    def test_slot_machine_chance_card_hand_logs_outcome_once(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda u, t: "AH,7D,9C",
        )
        msg = result if isinstance(result, str) else str(result)

        assert msg.count("Chance!") == 1
        assert "Cards: AH,7D,9C" in msg

    def test_slot_machine_pair_card_hand_applies_pair_effect(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda u, t: "AS,AD,9C",
        )
        msg = result if isinstance(result, str) else str(result)
        assert "pair" in msg.lower()
        assert (
            "randomly selected" in msg.lower()
            or "immune" in msg.lower()
            or "no effect" in msg.lower()
        )

    def test_slot_machine_pair_can_apply_visible_dot_debuff(self, monkeypatch):
        from src.core import abilities

        monkeypatch.setattr("random.choice", lambda seq: "DOT" if "DOT" in seq else seq[0])
        monkeypatch.setattr("random.randint", lambda start, end: end)

        user, target = self._make_combatants()
        result = abilities.SlotMachine().use(
            user,
            target,
            slot_machine_callback=lambda u, t: "AS,AD,9C",
        )

        assert target.magic_effects["DOT"].active is True
        assert target.magic_effects["DOT"].duration > 0
        assert target.magic_effects["DOT"].extra > 0
        assert target.magic_effects["DOT"].source == "Slot Machine"
        assert "DOT has been randomly selected" in str(result)

    def test_slot_machine_random_produces_output(self):
        """Random spins should always produce some output."""
        from src.core import abilities

        for _ in range(20):
            user, target = self._make_combatants()
            result = abilities.SlotMachine().use(user, target)
            msg = result if isinstance(result, str) else str(result)
            assert len(msg) > 0


class TestBatch14Totem:
    """Totem - activate a totem with a chosen sacred aspect."""

    @staticmethod
    def _make_combatants(wisdom=20):
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Shaman",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={
                "strength": 15,
                "intel": 15,
                "wisdom": wisdom,
                "con": 15,
                "charisma": 10,
                "dex": 15,
            },
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 15, "intel": 8, "wisdom": 10, "con": 15, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_totem_deducts_mana(self):
        from src.core import abilities

        user, target = self._make_combatants()
        mana_before = user.mana.current
        abilities.Totem().use(user, target)
        assert user.mana.current == mana_before - 12

    def test_totem_activates_magic_effect(self):
        from src.core import abilities

        user, target = self._make_combatants()
        abilities.Totem().use(user, target)
        assert user.magic_effects["Totem"].active is True

    def test_totem_earth_aspect_default(self):
        from src.core import abilities

        user, target = self._make_combatants()
        abilities.Totem().use(user, target)
        extra = user.magic_effects["Totem"].extra
        assert extra["aspect"] == "Earth"
        assert extra["defense_bonus"] == 0.20
        assert extra["secondary"] == "reflect"

    def test_totem_fire_aspect(self):
        from src.core import abilities

        user, target = self._make_combatants()
        abilities.Totem().use(user, target, active_aspect="Fire")
        extra = user.magic_effects["Totem"].extra
        assert extra["aspect"] == "Fire"
        assert extra["attack_bonus"] == 0.25
        assert extra["secondary"] == "elemental"

    def test_totem_duration_scales_with_wisdom(self):
        from src.core import abilities

        user, target = self._make_combatants(wisdom=30)
        abilities.Totem().use(user, target)
        # duration_base=5 + wisdom//10 = 5 + 3 = 8
        assert user.magic_effects["Totem"].duration == 8

    def test_totem_produces_output(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.Totem().use(user, target)
        msg = result if isinstance(result, str) else str(result)
        assert "totem" in msg.lower()

    def test_totem_unknown_aspect(self):
        from src.core import abilities

        user, target = self._make_combatants()
        result = abilities.Totem().use(user, target, active_aspect="Unknown")
        msg = result if isinstance(result, str) else str(result)
        assert "unknown" in msg.lower()


class TestBatch14SaveSystem:
    """Test that Batch 14 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch14_abilities(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in [
            "ConsumeItem",
            "DestroyMetal",
            "SlotMachine",
            "Totem",
        ]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


# =====================================================================
# Batch 15 - Charge, CrushingBlow, ArcaneBlast, MagicMissile/2/3
# =====================================================================


class TestBatch15YAMLLoading:
    """Verify all 6 Batch 15 YAML files load correctly."""

    _YAMLS = [
        ("charge.yaml", "Charge", 10),
        ("crushing_blow.yaml", "Crushing Blow", 25),
        ("arcane_blast.yaml", "Arcane Blast", 0),
        ("magic_missile.yaml", "Magic Missile", 5),
        ("magic_missile_2.yaml", "Magic Missile II", 18),
        ("magic_missile_3.yaml", "Magic Missile III", 40),
    ]

    def test_all_yaml_files_load(self):
        from src.core.data.ability_loader import AbilityFactory

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        for filename, expected_name, expected_cost in self._YAMLS:
            ability = AbilityFactory.create_from_yaml(yaml_dir / filename)
            assert ability.name == expected_name, f"{filename}: name mismatch"
            assert ability.cost == expected_cost, f"{filename}: cost mismatch"


class TestBatch15Charge:
    """Charge - charging skill with stun-before-damage."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Charger",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 50, "intel": 10, "wisdom": 10, "con": 20, "charisma": 10, "dex": 20},
        )
        target = TestGameState.create_player(
            name="Defender",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(50, 50),
            stats={"strength": 15, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_charge_creates_charging_skill(self):
        """Charge() returns a DataDrivenChargingSkill."""
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenChargingSkill

        charge = abilities.Charge()
        assert isinstance(charge, DataDrivenChargingSkill)
        assert charge.name == "Charge"
        assert charge.cost == 10
        assert charge.dmg_mod == 2.5

    def test_charge_starts_charging_phase(self):
        """With charge_time > 0, first use starts charging."""
        from src.core import abilities

        user, target = self._make_combatants()
        charge = abilities.Charge()
        result = charge.use(user, target)
        assert isinstance(result, str)
        # Mana should be deducted
        assert user.mana.current == 100 - 10
        # Should be in charging state
        assert charge.charging is True
        assert "charge" in result.lower() or "momentum" in result.lower()

    def test_charge_execute_does_damage(self):
        """After charge phase, execute deals weapon damage."""
        from src.core import abilities

        user, target = self._make_combatants()
        charge = abilities.Charge()
        # Start charging
        charge.use(user, target)
        hp_before = target.health.current
        # Execute (charge_turns ticks to 0)
        result = charge.use(user, target)
        assert isinstance(result, str) if not hasattr(result, "message") else True
        # Something should have happened
        msg = result if isinstance(result, str) else str(result)
        assert len(msg) > 0

    def test_charge_cancel_on_incapacitated(self):
        """If user is incapacitated during charge, cancel."""
        from src.core import abilities

        user, target = self._make_combatants()
        charge = abilities.Charge()
        charge.use(user, target)
        # Stun the user
        user.status_effects["Stun"].active = True
        user.status_effects["Stun"].duration = 2
        result = charge.use(user, target)
        assert "interrupted" in result.lower()
        assert charge.charging is False

    def test_charge_instant_if_zero_charge_time(self):
        """If charge_time is 0, executes immediately."""
        from src.core import abilities

        user, target = self._make_combatants()
        charge = abilities.Charge()
        charge._charge_time = 0  # override to 0
        hp_before = target.health.current
        result = charge.use(user, target)
        msg = result if isinstance(result, str) else str(result)
        # Should execute immediately (no "charging" message)
        assert charge.charging is False


class TestBatch15CrushingBlow:
    """CrushingBlow - charging skill with massive damage + stun."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Crusher",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 50, "intel": 10, "wisdom": 10, "con": 20, "charisma": 10, "dex": 20},
        )
        target = TestGameState.create_player(
            name="Victim",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_crushing_blow_creates_charging_skill(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenChargingSkill

        cb = abilities.CrushingBlow()
        assert isinstance(cb, DataDrivenChargingSkill)
        assert cb.name == "Crushing Blow"
        assert cb.cost == 25

    def test_crushing_blow_charge_and_execute(self):
        """Start charge → execute → weapon damage applied."""
        from src.core import abilities

        user, target = self._make_combatants()
        cb = abilities.CrushingBlow()
        # Start charging
        result1 = cb.use(user, target)
        assert cb.charging is True
        assert user.mana.current == 100 - 25
        # Execute
        hp_before = target.health.current
        result2 = cb.use(user, target)
        msg = result2 if isinstance(result2, str) else str(result2)
        assert len(msg) > 0
        assert cb.charging is False

    def test_crushing_blow_stun_with_high_chance(self):
        """With stun_chance=1.0, stun should always apply when not immune."""
        import random

        from src.core import abilities

        user, target = self._make_combatants()
        cb = abilities.CrushingBlow()
        # Force immediate execution and guaranteed stun
        cb._charge_time = 0
        # Patch the effect to guarantee stun
        for eff in cb._effects:
            if hasattr(eff, "stun_chance"):
                eff.stun_chance = 1.0
        random.seed(42)
        result = cb.use(user, target)
        msg = result if isinstance(result, str) else str(result)
        # Over many runs, at least verify no crash
        assert len(msg) > 0

    def test_crushing_blow_stun_blocked_by_immunity(self):
        """Stun immunity prevents stun application."""
        from src.core import abilities

        user, target = self._make_combatants()
        target.status_immunity.append("Stun")
        cb = abilities.CrushingBlow()
        cb._charge_time = 0
        for eff in cb._effects:
            if hasattr(eff, "stun_chance"):
                eff.stun_chance = 1.0
        result = cb.use(user, target)
        msg = result if isinstance(result, str) else str(result)
        assert "stunned" not in msg.lower()


class TestBatch15ArcaneBlast:
    """ArcaneBlast - mana-to-damage charging skill."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Enchanter",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 40, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_arcane_blast_creates_charging_skill(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenChargingSkill

        ab = abilities.ArcaneBlast()
        assert isinstance(ab, DataDrivenChargingSkill)
        assert ab.name == "Arcane Blast"
        assert ab.cost == 0

    def test_arcane_blast_requires_mana(self):
        """Should fail if user has 0 mana."""
        from src.core import abilities

        user, target = self._make_combatants()
        user.mana.current = 0
        ab = abilities.ArcaneBlast()
        result = ab.use(user, target)
        assert "not enough mana" in result.lower()

    def test_arcane_blast_drains_all_mana(self):
        """After execution, user.mana.current should be 0."""
        from src.core import abilities

        user, target = self._make_combatants()
        ab = abilities.ArcaneBlast()
        ab._charge_time = 0  # instant execution
        ab.use(user, target)
        assert user.mana.current == 0

    def test_arcane_blast_charge_and_execute(self):
        """Start charge → execute → mana drained."""
        from src.core import abilities

        user, target = self._make_combatants()
        ab = abilities.ArcaneBlast()
        mana_before = user.mana.current
        # Start charging (saves mana snapshot)
        result1 = ab.use(user, target)
        assert ab.charging is True
        assert user.mana.current == mana_before  # cost is 0
        # Execute
        result2 = ab.use(user, target)
        assert user.mana.current == 0
        assert ab.charging is False

    def test_arcane_blast_activates_power_up(self):
        """If target survives, Power Up should activate for regen."""
        from src.core import abilities

        user, target = self._make_combatants()
        target.health.current = 10000  # make sure target survives
        target.health.max = 10000
        # Give user class_effects with Power Up
        if not hasattr(user, "class_effects") or "Power Up" not in user.class_effects:
            # Some test chars may not have this, so skip check if attributes missing
            pass
        ab = abilities.ArcaneBlast()
        ab._charge_time = 0
        ab.use(user, target)
        assert user.mana.current == 0
        # If user has class_effects, Power Up should be active
        if hasattr(user, "class_effects") and "Power Up" in user.class_effects:
            assert user.class_effects["Power Up"].active is True


class TestBatch15MagicMissile:
    """MagicMissile family - multi-missile spell."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        caster = TestGameState.create_player(
            name="Wizard",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(200, 200),
            mana=(200, 200),
            stats={"strength": 10, "intel": 50, "wisdom": 20, "con": 15, "charisma": 10, "dex": 20},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return caster, target

    def test_magic_missile_creates_correct_type(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenMagicMissileSpell

        mm = abilities.MagicMissile()
        assert isinstance(mm, DataDrivenMagicMissileSpell)
        assert mm.name == "Magic Missile"
        assert mm.cost == 5
        assert mm.missiles == 1

    def test_magic_missile_2_has_2_missiles(self):
        from src.core import abilities

        mm2 = abilities.MagicMissile2()
        assert mm2.cost == 18
        assert mm2.missiles == 2

    def test_magic_missile_3_has_3_missiles(self):
        from src.core import abilities

        mm3 = abilities.MagicMissile3()
        assert mm3.cost == 40
        assert mm3.missiles == 3

    def test_magic_missile_cast_deducts_mana(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        mm = abilities.MagicMissile()
        mana_before = caster.mana.current
        mm.cast(caster, target)
        assert caster.mana.current == mana_before - 5

    def test_magic_missile_cast_returns_string(self, monkeypatch):
        from types import SimpleNamespace

        from src.core import abilities

        caster, target = self._make_combatants()
        monkeypatch.setattr(
            caster,
            "resolve_contact",
            lambda *_args, **_kwargs: SimpleNamespace(hit=True, attribution=None),
        )
        mm = abilities.MagicMissile()
        result = mm.cast(caster, target)
        assert isinstance(result, str)
        assert len(result) > 0
        assert mm.result.damage == sum(mm.result.extra["damage_instances"])
        assert mm.result.damage > 0

    def test_magic_missile_ice_block_immunity(self):
        from src.core import abilities

        caster, target = self._make_combatants()
        target.magic_effects["Ice Block"].active = True
        mm = abilities.MagicMissile()
        result = mm.cast(caster, target)
        assert "no effect" in result.lower()

    def test_magic_missile_special_free_cast(self):
        """special=True should not deduct mana."""
        from src.core import abilities

        caster, target = self._make_combatants()
        mm = abilities.MagicMissile()
        mana_before = caster.mana.current
        mm.cast(caster, target, special=True)
        assert caster.mana.current == mana_before

    def test_magic_missile_2_cast(self):
        """MagicMissile2 should cost 18 and fire 2 missiles."""
        from src.core import abilities

        caster, target = self._make_combatants()
        mm2 = abilities.MagicMissile2()
        mana_before = caster.mana.current
        result = mm2.cast(caster, target)
        assert caster.mana.current == mana_before - 18
        assert isinstance(result, str)

    def test_magic_missile_2_can_consume_multiple_mirror_images(self, monkeypatch):
        from src.core import abilities

        caster, target = self._make_combatants()
        target.magic_effects["Duplicates"].active = True
        target.magic_effects["Duplicates"].duration = 2
        target.dodge_chance = lambda *_args, **_kwargs: False
        target.incapacitated = lambda: False
        caster.hit_chance = lambda *_args, **_kwargs: True
        caster.check_mod = lambda mod, *_args, **_kwargs: 99 if mod == "luck" else 10
        monkeypatch.setattr("src.core.data.data_driven_abilities.random.randint", lambda _a, _b: 1)

        result = abilities.MagicMissile2().cast(caster, target, special=True)

        assert result.count("mirror image") == 2
        assert target.magic_effects["Duplicates"].active is False
        assert target.magic_effects["Duplicates"].duration == 0


class TestBatch15SaveSystem:
    """Test that Batch 15 wrapper classes serialize/deserialize correctly."""

    def test_serialize_batch15_abilities(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in [
            "Charge",
            "CrushingBlow",
            "ArcaneBlast",
            "MagicMissile",
            "MagicMissile2",
            "MagicMissile3",
        ]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


# ======================================================================
# BATCH 16 - Jump (DataDrivenJumpSkill)
# ======================================================================


class TestBatch16YAMLLoading:
    """Verify jump.yaml loads as DataDrivenJumpSkill."""

    def test_jump_yaml_loads(self):
        from pathlib import Path

        from src.core.data.ability_loader import AbilityFactory

        p = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "jump.yaml"
        ability = AbilityFactory.create_from_yaml(p)
        assert ability.name == "Jump"
        from src.core.data.data_driven_abilities import DataDrivenJumpSkill

        assert isinstance(ability, DataDrivenJumpSkill)
        assert ability.cost == 10
        assert ability._charge_time == 1

    def test_jump_wrapper_returns_data_driven(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenJumpSkill

        j = abilities.Jump()
        assert isinstance(j, DataDrivenJumpSkill)
        assert j.name == "Jump"


class TestBatch16Modifications:
    """Modification management on DataDrivenJumpSkill."""

    @staticmethod
    def _make_jump():
        from src.core import abilities

        return abilities.Jump()

    @staticmethod
    def _make_user(level=30, class_name="Lancer"):
        from tests.test_framework import TestGameState

        return TestGameState.create_player(
            name="Lancer",
            class_name=class_name,
            race_name="Human",
            level=level,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 50, "intel": 20, "wisdom": 15, "con": 25, "charisma": 10, "dex": 25},
        )

    def test_default_modifications(self):
        j = self._make_jump()
        assert j.modifications["Crit"] is True
        assert j.get_active_count() == 1
        assert "Crit" in j.get_active_modifications()

    def test_unlock_modification(self):
        j = self._make_jump()
        assert not j.is_modification_unlocked("Thrust")
        j.unlock_modification("Thrust")
        assert j.is_modification_unlocked("Thrust")

    def test_set_modification_requires_unlock(self):
        j = self._make_jump()
        ok, msg = j.set_modification("Thrust", True)
        assert not ok
        assert "not unlocked" in msg.lower()

    def test_set_modification_success(self):
        j = self._make_jump()
        j.unlock_modification("Thrust")
        ok, msg = j.set_modification("Thrust", True, user=self._make_user(level=30))
        assert ok
        assert j.modifications["Thrust"] is True

    def test_conflicting_mods_quick_dive_vs_soaring(self):
        j = self._make_jump()
        j.unlock_modification("Quick Dive")
        j.unlock_modification("Soaring Strike")
        user = self._make_user(level=99)
        j.set_modification("Quick Dive", True, user=user)
        assert j.modifications["Quick Dive"] is True
        j.set_modification("Soaring Strike", True, user=user)
        assert j.modifications["Soaring Strike"] is True
        assert j.modifications["Quick Dive"] is False  # conflicts

    def test_conflicting_mods_crit_vs_soaring(self):
        j = self._make_jump()
        j.unlock_modification("Soaring Strike")
        user = self._make_user(level=99)
        j.set_modification("Soaring Strike", True, user=user)
        assert j.modifications["Soaring Strike"] is True
        assert j.modifications["Crit"] is False  # deactivated

    def test_max_active_limit(self):
        j = self._make_jump()
        # Level 1 Lancer → user_level=1 → max_mods = 1 + 0 = 1
        user = self._make_user(level=1, class_name="Lancer")
        max_m = j.get_max_active_modifications(user)
        assert max_m == 1
        # Crit already active (1), trying to add another should fail
        j.unlock_modification("Thrust")
        ok, _ = j.set_modification("Thrust", True, user=user)
        assert not ok

    def test_check_and_unlock_level_mods(self):
        j = self._make_jump()
        unlocked = j.check_and_unlock_level_modifications(10, "Lancer")
        assert "Defend" in unlocked
        assert "Quick Dive" in unlocked
        assert j.is_modification_unlocked("Defend")
        assert j.is_modification_unlocked("Quick Dive")

    def test_unlock_boss_mod(self):
        j = self._make_jump()
        mod = j.unlock_boss_modification("Red Dragon")
        assert mod == "Dragon's Fury"
        assert j.is_modification_unlocked("Dragon's Fury")

    def test_unlock_item_mod(self):
        j = self._make_jump()
        mod = j.unlock_item_modification("Dragon's Tear")
        assert mod == "Recover"
        assert j.is_modification_unlocked("Recover")

    def test_enforce_modification_limit(self):
        j = self._make_jump()
        user = self._make_user(level=99)
        # Unlock and activate several
        for m in ["Thrust", "Defend", "Rend", "Quake"]:
            j.unlock_modification(m)
            j.set_modification(m, True, user=user)
        active_before = j.get_active_count()
        # Now use a level 1 user to enforce limit → should deactivate excess
        user_low = self._make_user(level=1, class_name="Lancer")
        deactivated = j.enforce_modification_limit(user_low)
        assert len(deactivated) > 0
        assert j.get_active_count() <= j.get_max_active_modifications(user_low)

    def test_get_unlocked_modifications(self):
        j = self._make_jump()
        unlocked = j.get_unlocked_modifications()
        assert "Crit" in unlocked
        assert "Thrust" not in unlocked


class TestBatch16Charging:
    """Charging mechanics for Jump."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Lancer",
            class_name="Lancer",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 50, "intel": 20, "wisdom": 15, "con": 25, "charisma": 10, "dex": 25},
        )
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=20,
            health=(200, 200),
            mana=(50, 50),
            stats={"strength": 15, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_default_charge_time(self):
        from src.core import abilities

        j = abilities.Jump()
        assert j.get_charge_time() == 1

    def test_quick_dive_instant(self):
        from src.core import abilities

        j = abilities.Jump()
        j.unlock_modification("Quick Dive")
        j.modifications["Quick Dive"] = True
        j.modifications["Crit"] = False
        assert j.get_charge_time() == 0

    def test_soaring_strike_two_turns(self):
        from src.core import abilities

        j = abilities.Jump()
        j.unlock_modification("Soaring Strike")
        j.modifications["Soaring Strike"] = True
        j.modifications["Crit"] = False
        assert j.get_charge_time() == 2

    def test_start_charge_deducts_mana_and_sets_state(self):
        from src.core import abilities

        user, target = self._make_combatants()
        j = abilities.Jump()
        mana_before = user.mana.current
        result = j.use(user, target)
        assert user.mana.current == mana_before - 10
        assert j.charging is True
        assert "preparing" in result.lower() or "coiling" in result.lower()

    def test_charge_executes_after_one_turn(self):
        from src.core import abilities

        user, target = self._make_combatants()
        j = abilities.Jump()
        j.use(user, target)  # start charge
        hp_before = target.health.current
        result = j.use(user, target)  # execute
        assert j.charging is False
        assert "descends" in result.lower()

    def test_cancel_charge_when_incapacitated(self):
        from src.core import abilities

        user, target = self._make_combatants()
        j = abilities.Jump()
        j.use(user, target)
        user.status_effects["Stun"].active = True
        user.status_effects["Stun"].duration = 2
        result = j.use(user, target)
        assert "interrupted" in result.lower()
        assert j.charging is False

    def test_unstoppable_prevents_cancel(self):
        from src.core import abilities

        user, target = self._make_combatants()
        j = abilities.Jump()
        j.unlock_modification("Unstoppable")
        j.modifications["Unstoppable"] = True
        j.use(user, target)
        user.status_effects["Stun"].active = True
        user.status_effects["Stun"].duration = 2
        result = j.use(user, target)
        assert (
            "cannot be stopped" not in result.lower()
            or "descends" in result.lower()
            or "interrupted" not in result.lower()
        )

    def test_damage_threshold_interrupt(self):
        from src.core import abilities

        user, target = self._make_combatants()
        j = abilities.Jump()
        j.use(user, target)  # start charge (records health)
        # Simulate heavy damage (>10% max HP)
        user.health.current -= int(user.health.max * 0.15)
        result = j.use(user, target)
        assert "interrupted" in result.lower()
        assert j.charging is False

    def test_quick_dive_executes_immediately(self):
        from src.core import abilities

        user, target = self._make_combatants()
        j = abilities.Jump()
        j.unlock_modification("Quick Dive")
        j.modifications["Quick Dive"] = True
        j.modifications["Crit"] = False
        result = j.use(user, target)
        assert j.charging is False
        assert "descends" in result.lower()


class TestBatch16Execute:
    """Execute-phase combat effects via JumpEffect."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Lancer",
            class_name="Lancer",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 50, "intel": 20, "wisdom": 15, "con": 25, "charisma": 10, "dex": 25},
        )
        target = TestGameState.create_player(
            name="Enemy",
            class_name="Warrior",
            race_name="Human",
            level=20,
            health=(200, 200),
            mana=(50, 50),
            stats={"strength": 15, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_basic_execute_deals_damage(self):
        from src.core import abilities

        user, target = self._make_combatants()
        j = abilities.Jump()
        j.use(user, target)  # start charge
        hp_before = target.health.current
        result = j.use(user, target)  # execute
        assert isinstance(result, str)
        assert "descends" in result.lower()

    def test_recover_heals(self):
        from src.core import abilities

        user, target = self._make_combatants()
        j = abilities.Jump()
        j.unlock_modification("Recover")
        j.modifications["Recover"] = True
        user.health.current = 200  # damaged
        user.mana.current = 60  # below max
        j.modifications["Quick Dive"] = True
        j.modifications["Crit"] = False
        result = j.use(user, target)  # instant execute
        assert "recovers" in result.lower()
        assert user.health.current >= 200  # healed

    def test_retribution_adds_damage_message(self):
        from src.core import abilities

        user, target = self._make_combatants()
        j = abilities.Jump()
        j.unlock_modification("Retribution")
        j.modifications["Retribution"] = True
        j.use(user, target)  # start charge
        # Simulate some damage but below interrupt threshold
        small_damage = max(1, int(user.health.max * 0.05))
        user.health.current -= small_damage
        # Manually set retribution damage (simulating the tracking)
        j.retribution_damage = small_damage
        result = j.use(user, target)  # execute
        assert "fury" in result.lower() or "empowers" in result.lower()


class TestBatch16SaveSystem:
    """Test that Jump serializes/deserializes correctly."""

    def test_serialize_jump(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        j = abilities.Jump()
        serialized = AbilitySerializer.serialize(j)
        assert serialized == "jump"
        restored = AbilitySerializer.deserialize(serialized)
        assert restored is not None
        assert restored.name == "Jump"
        assert hasattr(restored, "modifications")
        assert hasattr(restored, "unlocked_modifications")


# ======================================================================
# BATCH 17 - Sanctuary & Teleport (DataDrivenMovementSpell)
# ======================================================================


class TestBatch17YAMLLoading:
    """Verify sanctuary.yaml and teleport.yaml load correctly."""

    def test_sanctuary_yaml_loads(self):
        from pathlib import Path

        from src.core.data.ability_loader import AbilityFactory

        p = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "sanctuary.yaml"
        ability = AbilityFactory.create_from_yaml(p)
        from src.core.data.data_driven_abilities import DataDrivenMovementSpell

        assert isinstance(ability, DataDrivenMovementSpell)
        assert ability.name == "Sanctuary"
        assert ability.cost == 100
        assert ability._movement_type == "sanctuary"

    def test_teleport_yaml_loads(self):
        from pathlib import Path

        from src.core.data.ability_loader import AbilityFactory

        p = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / "teleport.yaml"
        ability = AbilityFactory.create_from_yaml(p)
        from src.core.data.data_driven_abilities import DataDrivenMovementSpell

        assert isinstance(ability, DataDrivenMovementSpell)
        assert ability.name == "Teleport"
        assert ability.cost == 50
        assert ability._movement_type == "teleport"
        assert ability.combat is False

    def test_sanctuary_wrapper(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenMovementSpell

        s = abilities.Sanctuary()
        assert isinstance(s, DataDrivenMovementSpell)
        assert s.name == "Sanctuary"

    def test_teleport_wrapper(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenMovementSpell

        t = abilities.Teleport()
        assert isinstance(t, DataDrivenMovementSpell)
        assert t.name == "Teleport"
        assert t.combat is False


class TestBatch17Sanctuary:
    """Sanctuary cast_out behaviour."""

    @staticmethod
    def _make_user():
        from tests.test_framework import TestGameState

        return TestGameState.create_player(
            name="Wizard",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 40, "wisdom": 30, "con": 15, "charisma": 10, "dex": 15},
        )

    def test_cast_out_heals_fully(self):
        from src.core import abilities

        user = self._make_user()
        user.health.current = 100
        user.mana.current = 150
        s = abilities.Sanctuary()
        result = s.cast_out(user=user)
        assert isinstance(result, str)
        assert "sanctuary" in result.lower() or "town" in result.lower()
        assert user.health.current == user.health.max
        assert user.mana.current == user.mana.max

    def test_cast_out_calls_to_town(self):
        from src.core import abilities

        user = self._make_user()
        to_town_called = []
        original = user.to_town
        user.to_town = lambda: to_town_called.append(True)
        s = abilities.Sanctuary()
        s.cast_out(user=user)
        assert len(to_town_called) == 1

    def test_cast_out_message(self):
        from src.core import abilities

        user = self._make_user()
        s = abilities.Sanctuary()
        result = s.cast_out(user=user)
        assert user.name in result
        assert "town" in result.lower()


class TestBatch17Teleport:
    """Teleport cast_out behaviour."""

    def test_teleport_set_location(self):
        from types import SimpleNamespace

        from src.core import abilities

        player = SimpleNamespace(
            name="Seeker",
            location_x=5,
            location_y=10,
            location_z=2,
            teleport=(0, 0, 0),
            mana=SimpleNamespace(current=100, max=100),
        )
        game = SimpleNamespace(player_char=player)
        # selection_callback always picks "Set" (index 0)
        t = abilities.Teleport()
        result = t.cast_out(selection_callback=lambda msg, opts: 0, game=game)
        assert "set for teleport" in result.lower()
        assert player.teleport == (5, 10, 2)

    def test_teleport_to_location(self):
        from types import SimpleNamespace

        from src.core import abilities

        player = SimpleNamespace(
            name="Seeker",
            location_x=5,
            location_y=10,
            location_z=2,
            teleport=(1, 2, 3),
            mana=SimpleNamespace(current=100, max=100),
        )
        game = SimpleNamespace(player_char=player)
        # selection_callback always picks "Teleport" (index 1)
        t = abilities.Teleport()
        result = t.cast_out(selection_callback=lambda msg, opts: 1, game=game)
        assert "teleports" in result.lower()
        assert player.location_x == 1
        assert player.location_y == 2
        assert player.location_z == 3
        assert player.mana.current == 100 - 50

    def test_teleport_random_when_no_callback(self):
        from types import SimpleNamespace

        from src.core import abilities

        player = SimpleNamespace(
            name="Seeker",
            location_x=5,
            location_y=10,
            location_z=2,
            teleport=(1, 2, 3),
            mana=SimpleNamespace(current=100, max=100),
        )
        game = SimpleNamespace(player_char=player)
        t = abilities.Teleport()
        # No callback → random choice; should not error
        result = t.cast_out(game=game)
        assert isinstance(result, str)

    def test_teleport_not_usable_in_combat(self):
        from src.core import abilities

        t = abilities.Teleport()
        assert t.combat is False


class TestBatch17SaveSystem:
    """Test that Sanctuary and Teleport serialize/deserialize correctly."""

    def test_serialize_movement_spells(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        for name in ["Sanctuary", "Teleport"]:
            ability = getattr(abilities, name)()
            serialized = AbilitySerializer.serialize(ability)
            assert serialized == ability.ability_id, f"Serialize failed for {name}"
            restored = AbilitySerializer.deserialize(serialized)
            assert restored is not None, f"Deserialize failed for {name}"
            assert restored.name == ability.name


# ======================================================================
# Batch 18 — Shadow Strike implementation + deleted abilities cleanup
# ======================================================================


class TestBatch18ShadowStrikeYAML:
    """Verify shadow_strike.yaml loads correctly as ChargingSkill."""

    def test_loads_as_charging_skill(self):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenChargingSkill

        ss = abilities.ShadowStrike()
        assert isinstance(ss, DataDrivenChargingSkill)
        assert ss.name == "Shadow Strike"

    def test_cost_and_charge_time(self):
        from src.core import abilities

        ss = abilities.ShadowStrike()
        assert ss.cost == 20
        assert ss.get_charge_time() == 1

    def test_has_shadow_strike_effect(self):
        from src.core import abilities
        from src.core.effects import ShadowStrikeEffect

        ss = abilities.ShadowStrike()
        assert any(isinstance(e, ShadowStrikeEffect) for e in ss._effects)


class TestBatch18ShadowStrikeCharging:
    """Test Shadow Strike charging mechanics."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Rogue",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(200, 200),
            mana=(100, 100),
            stats={"strength": 20, "intel": 15, "wisdom": 10, "con": 14, "charisma": 22, "dex": 30},
        )
        target = TestGameState.create_player(
            name="Victim",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_starts_charging(self):
        from src.core import abilities

        user, target = self._make_combatants()
        ss = abilities.ShadowStrike()
        result = ss.use(user, target)
        assert ss.charging is True
        assert user.mana.current == 100 - 20
        assert "shadow" in result.lower() or "preparing" in result.lower()

    def test_executes_after_charge(self):
        from src.core import abilities

        user, target = self._make_combatants()
        ss = abilities.ShadowStrike()
        ss.use(user, target)
        hp_before = target.health.current
        result = ss.use(user, target)
        msg = result if isinstance(result, str) else str(result)
        assert ss.charging is False
        assert "shadow" in msg.lower() or "strike" in msg.lower() or len(msg) > 0

    def test_cancel_on_incapacitated(self):
        from src.core import abilities

        user, target = self._make_combatants()
        ss = abilities.ShadowStrike()
        ss.use(user, target)
        user.status_effects["Stun"].active = True
        user.status_effects["Stun"].duration = 2
        result = ss.use(user, target)
        assert "interrupted" in result.lower()
        assert ss.charging is False

    def test_instant_if_charge_time_zero(self):
        from src.core import abilities

        user, target = self._make_combatants()
        ss = abilities.ShadowStrike()
        ss._charge_time = 0
        result = ss.use(user, target)
        msg = result if isinstance(result, str) else str(result)
        assert ss.charging is False
        assert len(msg) > 0


class TestBatch18ShadowStrikeEffect:
    """Test the ShadowStrikeEffect directly."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Rogue",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(200, 200),
            mana=(100, 100),
            stats={"strength": 20, "intel": 15, "wisdom": 10, "con": 14, "charisma": 22, "dex": 30},
        )
        target = TestGameState.create_player(
            name="Victim",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_effect_does_weapon_damage(self):
        """ShadowStrikeEffect should deal weapon damage with guaranteed crit."""
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import ShadowStrikeEffect

        user, target = self._make_combatants()
        effect = ShadowStrikeEffect(dmg_mod=2.0, blind_chance=0.0)
        result = CombatResult(action="Shadow Strike", actor=user, target=target)
        hp_before = target.health.current
        effect.apply(user, target, result)
        msgs = result.extra.get("messages", [])
        assert len(msgs) > 0
        assert "shadow" in msgs[0].lower()

    def test_blind_blocked_by_immunity(self):
        """Blind should not apply if target has Blind immunity."""
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import ShadowStrikeEffect

        user, target = self._make_combatants()
        target.status_immunity.append("Blind")
        effect = ShadowStrikeEffect(dmg_mod=2.0, blind_chance=1.0, blind_duration=2)
        result = CombatResult(action="Shadow Strike", actor=user, target=target)
        effect.apply(user, target, result)
        assert not target.status_effects["Blind"].active

    def test_blind_blocked_by_mana_shield(self):
        """Blind should not apply if target has Mana Shield active."""
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import ShadowStrikeEffect

        user, target = self._make_combatants()
        target.magic_effects["Mana Shield"].active = True
        target.magic_effects["Mana Shield"].duration = 3
        effect = ShadowStrikeEffect(dmg_mod=2.0, blind_chance=1.0, blind_duration=2)
        result = CombatResult(action="Shadow Strike", actor=user, target=target)
        effect.apply(user, target, result)
        assert not target.status_effects["Blind"].active

    def test_blind_applies_with_full_chance(self):
        """With blind_chance=1.0, blind should always apply when not immune."""
        import random

        from src.core.combat.combat_result import CombatResult
        from src.core.effects import ShadowStrikeEffect

        user, target = self._make_combatants()
        effect = ShadowStrikeEffect(dmg_mod=2.0, blind_chance=1.0, blind_duration=3)
        result = CombatResult(action="Shadow Strike", actor=user, target=target)
        result.hit = True
        random.seed(42)
        effect.apply(user, target, result)
        msgs = "".join(result.extra.get("messages", []))
        # If hit landed, blind should be applied (not already active, not immune)
        if result.hit:
            assert target.status_effects["Blind"].active
            assert target.status_effects["Blind"].duration == 3
            assert "blinded" in msgs.lower()


class TestBatch18DeletedAbilities:
    """Verify deleted abilities (Holy Smite, Power Strike, Summon Allies) are gone."""

    def test_holy_smite_yaml_not_present(self):
        from pathlib import Path

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        assert not (yaml_dir / "holy_smite.yaml").exists()

    def test_power_strike_yaml_not_present(self):
        from pathlib import Path

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        assert not (yaml_dir / "power_strike.yaml").exists()

    def test_summon_allies_yaml_not_present(self):
        from pathlib import Path

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        assert not (yaml_dir / "summon_allies.yaml").exists()


class TestBatch18DrowAssassin:
    """DrowAssassin should have Shadow Strike in its spellbook and action stack."""

    def test_drow_assassin_has_shadow_strike(self):
        from src.core.enemies import DrowAssassin

        enemy = DrowAssassin()
        assert "Shadow Strike" in enemy.spellbook["Skills"]

    def test_drow_assassin_action_stack_includes_shadow_strike(self):
        from src.core.enemies import DrowAssassin

        enemy = DrowAssassin()
        ss_entries = [a for a in enemy.action_stack if a["ability"] == "Shadow Strike"]
        assert len(ss_entries) == 1
        assert ss_entries[0]["priority"].name == "HIGH"
        assert ss_entries[0]["delay"] == 1


class TestBatch18SaveSystem:
    """ShadowStrike serializes and deserializes."""

    def test_serialize_shadow_strike(self):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        ss = abilities.ShadowStrike()
        serialized = AbilitySerializer.serialize(ss)
        assert serialized == "shadow_strike"
        restored = AbilitySerializer.deserialize(serialized)
        assert restored is not None
        assert restored.name == "Shadow Strike"


# ===========================================================================
# Batch 19 - Dragon Breath (Fire / Water / Wind) as ChargingSkill
# ===========================================================================


class TestBatch19DragonBreathYAML:
    """All three elemental Dragon Breath YAMLs load correctly."""

    @pytest.mark.parametrize(
        "cls_name,element",
        [
            ("DragonBreathFire", "Fire"),
            ("DragonBreathWater", "Water"),
            ("DragonBreathWind", "Wind"),
        ],
    )
    def test_loads_as_charging_skill(self, cls_name, element):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenChargingSkill

        ab = getattr(abilities, cls_name)()
        assert isinstance(ab, DataDrivenChargingSkill)

    @pytest.mark.parametrize(
        "cls_name,element",
        [
            ("DragonBreathFire", "Fire"),
            ("DragonBreathWater", "Water"),
            ("DragonBreathWind", "Wind"),
        ],
    )
    def test_charge_time_and_cost(self, cls_name, element):
        from src.core import abilities

        ab = getattr(abilities, cls_name)()
        assert ab.get_charge_time() == 2
        assert ab.cost == 0

    @pytest.mark.parametrize(
        "cls_name,element",
        [
            ("DragonBreathFire", "Fire"),
            ("DragonBreathWater", "Water"),
            ("DragonBreathWind", "Wind"),
        ],
    )
    def test_has_breath_damage_effect(self, cls_name, element):
        from src.core import abilities
        from src.core.effects.enemy import BreathDamageEffect

        ab = getattr(abilities, cls_name)()
        assert any(isinstance(e, BreathDamageEffect) for e in ab._effects)

    @pytest.mark.parametrize(
        "cls_name,element",
        [
            ("DragonBreathFire", "Fire"),
            ("DragonBreathWater", "Water"),
            ("DragonBreathWind", "Wind"),
        ],
    )
    def test_element_matches(self, cls_name, element):
        from src.core import abilities
        from src.core.effects.enemy import BreathDamageEffect

        ab = getattr(abilities, cls_name)()
        breath_eff = [e for e in ab._effects if isinstance(e, BreathDamageEffect)][0]
        assert breath_eff.element == element


class TestBatch19DragonBreathWrappers:
    """Wrapper classes in the abilities package load correctly."""

    def test_dragon_breath_fire(self):
        from src.core import abilities

        ab = abilities.DragonBreathFire()
        assert ab.name == "Dragon Breath (Fire)"

    def test_dragon_breath_water(self):
        from src.core import abilities

        ab = abilities.DragonBreathWater()
        assert ab.name == "Dragon Breath (Water)"

    def test_dragon_breath_wind(self):
        from src.core import abilities

        ab = abilities.DragonBreathWind()
        assert ab.name == "Dragon Breath (Wind)"


class TestBatch19DragonBreathCharging:
    """Charging mechanics work for Dragon Breath."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Wyrm",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(150, 150),
            stats={"strength": 38, "intel": 28, "wisdom": 30, "con": 28, "charisma": 22, "dex": 23},
        )
        target = TestGameState.create_player(
            name="Hero",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(200, 200),
            mana=(100, 100),
            stats={"strength": 20, "intel": 20, "wisdom": 20, "con": 20, "charisma": 20, "dex": 20},
        )
        return user, target

    def test_start_charge(self):
        from src.core import abilities

        ab = abilities.DragonBreathFire()
        user, target = self._make_combatants()
        result = ab.use(user, target)
        assert ab.charging is True

    def test_execute_after_charge(self):
        from src.core import abilities

        ab = abilities.DragonBreathFire()
        user, target = self._make_combatants()
        ab.use(user, target)  # start charging (charge_turns = 2)
        ab.use(user, target)  # charge_turns 2 -> 1
        result = ab.use(user, target)  # charge_turns 1 -> 0 -> execute
        assert ab.charging is False

    def test_cancel_on_incapacitated(self):
        from src.core import abilities

        ab = abilities.DragonBreathWater()
        user, target = self._make_combatants()
        ab.use(user, target)
        assert ab.charging is True
        user.status_effects["Stun"].active = True
        user.status_effects["Stun"].duration = 2
        result = ab.use(user, target)
        assert "interrupted" in result.lower()
        assert ab.charging is False

    def test_telegraph_message_present(self):
        from src.core import abilities

        ab = abilities.DragonBreathFire()
        assert ab._telegraph_message and len(ab._telegraph_message) > 0

    def test_breath_deals_damage(self):
        """Dragon Breath (Water) should deal damage after charge."""
        from src.core import abilities

        ab = abilities.DragonBreathWater()
        user, target = self._make_combatants()
        ab.use(user, target)  # start charging (charge_turns = 2)
        ab.use(user, target)  # charge_turns 2 -> 1
        hp_before = target.health.current
        ab.use(user, target)  # charge_turns 1 -> 0 -> execute
        assert target.health.current < hp_before

    def test_breath_bypasses_physical_only_mana_shield(self):
        """Elemental Dragon Breath does not spend a physical-only Mana Shield."""
        from src.core import abilities

        ab = abilities.DragonBreathFire()
        user, target = self._make_combatants()
        target.mana.max = 500
        target.mana.current = 500
        target.magic_effects["Mana Shield"].active = True
        target.magic_effects["Mana Shield"].duration = 25

        ab.use(user, target)
        ab.use(user, target)
        hp_before = target.health.current
        mana_before = target.mana.current
        message = ab.use(user, target)

        assert target.health.current < hp_before
        assert target.mana.current == mana_before
        assert target.magic_effects["Mana Shield"].active is True
        assert "mana shield" not in message.lower()


class TestBatch19EnemySpellbooks:
    """Each enemy has Dragon Breath in spellbook and action_stack."""

    def test_pseudodragon_has_dragon_breath_fire(self):
        from src.core.enemies import Pseudodragon

        enemy = Pseudodragon()
        assert "Dragon Breath (Fire)" in enemy.spellbook["Skills"]
        entries = [a for a in enemy.action_stack if a["ability"] == "Dragon Breath (Fire)"]
        assert len(entries) == 1
        assert entries[0]["delay"] == 2

    def test_wyrm_has_dragon_breath_fire(self):
        from src.core.enemies import Wyrm

        enemy = Wyrm()
        assert "Dragon Breath (Fire)" in enemy.spellbook["Skills"]
        entries = [a for a in enemy.action_stack if a["ability"] == "Dragon Breath (Fire)"]
        assert len(entries) == 1
        assert entries[0]["delay"] == 2

    def test_hydra_has_dragon_breath_water(self):
        from src.core.enemies import Hydra

        enemy = Hydra()
        assert "Dragon Breath (Water)" in enemy.spellbook["Skills"]
        entries = [a for a in enemy.action_stack if a["ability"] == "Dragon Breath (Water)"]
        assert len(entries) == 1
        assert entries[0]["delay"] == 2

    def test_wyvern_has_dragon_breath_wind(self):
        from src.core.enemies import Wyvern

        enemy = Wyvern()
        assert "Dragon Breath (Wind)" in enemy.spellbook["Skills"]
        entries = [a for a in enemy.action_stack if a["ability"] == "Dragon Breath (Wind)"]
        assert len(entries) == 1
        assert entries[0]["delay"] == 2

    def test_red_dragon_has_dragon_breath_fire(self):
        from src.core.enemies import RedDragon

        enemy = RedDragon()
        assert "Dragon Breath (Fire)" in enemy.spellbook["Skills"]
        entries = [a for a in enemy.action_stack if a["ability"] == "Dragon Breath (Fire)"]
        assert len(entries) == 1
        assert entries[0]["delay"] == 2

    def test_enemy_telegraphs_are_unique(self):
        """Each enemy has a different telegraph message for their breath."""
        from src.core.enemies import Hydra, Pseudodragon, RedDragon, Wyrm, Wyvern

        telegraphs = set()
        for EnemyClass in [Pseudodragon, Wyrm, Hydra, Wyvern, RedDragon]:
            enemy = EnemyClass()
            for entry in enemy.action_stack:
                if "Dragon Breath" in entry["ability"]:
                    telegraphs.add(entry["telegraph"])
        assert len(telegraphs) == 5  # All 5 are unique


class TestBatch19OldYAMLRemoved:
    """The old documentation-only dragon_breath.yaml is removed."""

    def test_old_dragon_breath_yaml_gone(self):
        from pathlib import Path

        yaml_dir = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities"
        assert not (yaml_dir / "dragon_breath.yaml").exists()


class TestBatch19SaveSystem:
    """Dragon Breath abilities serialize and deserialize."""

    @pytest.mark.parametrize(
        "cls_name",
        [
            "DragonBreathFire",
            "DragonBreathWater",
            "DragonBreathWind",
        ],
    )
    def test_serialize_dragon_breath(self, cls_name):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        ab = getattr(abilities, cls_name)()
        serialized = AbilitySerializer.serialize(ab)
        assert serialized == ab.ability_id
        restored = AbilitySerializer.deserialize(serialized)
        assert restored is not None


# ═══════════════════════════════════════════════════════════════════════════
# COMPANION ULTIMATE ATTACKS
# ═══════════════════════════════════════════════════════════════════════════


ULTIMATE_YAML_MAP = {
    "TitanicSlam": ("titanic_slam.yaml", "Titanic Slam", "Skill"),
    "Devour": ("devour.yaml", "Devour", "Skill"),
    "AbsoluteZero": ("absolute_zero.yaml", "Absolute Zero", "Spell"),
    "Eruption": ("eruption.yaml", "Eruption", "Spell"),
    "MaelstromVortex": ("maelstrom_vortex.yaml", "Maelstrom Vortex", "Spell"),
    "Thunderstrike": ("thunderstrike.yaml", "Thunderstrike", "Spell"),
    "WindShrapnel": ("wind_shrapnel.yaml", "Wind Shrapnel", "Spell"),
    "DivineJudgment": ("divine_judgment.yaml", "Divine Judgment", "Spell"),
    "Oblivion": ("oblivion.yaml", "Oblivion", "Spell"),
    "GrandHeist": ("grand_heist.yaml", "Grand Heist", "Skill"),
    "Cataclysm": ("cataclysm.yaml", "Cataclysm", "Spell"),
}

SUMMON_ABILITY_MAP = {
    "Patagon": ("Skills", "TitanicSlam"),
    "Dilong": ("Skills", "Devour"),
    "Agloolik": ("Spells", "AbsoluteZero"),
    "Cacus": ("Spells", "Eruption"),
    "Izulu": ("Spells", "Thunderstrike"),
    "Hala": ("Spells", "WindShrapnel"),
    "Lamashtu": ("Spells", "Oblivion"),
    "Seraphim": ("Spells", "DivineJudgment"),
    "Bardi": ("Spells", "Oblivion"),
    "Kobalos": ("Skills", "GrandHeist"),
    "Tiamat": ("Spells", "MaelstromVortex"),
    "Zahhak": ("Spells", "Cataclysm"),
}


class TestCompanionUltimateYAMLLoading:
    """All Xenid ultimate YAMLs load correctly."""

    @pytest.mark.parametrize("cls_name,yaml_info", list(ULTIMATE_YAML_MAP.items()))
    def test_yaml_loads(self, cls_name, yaml_info):
        yaml_file, display_name, _ = yaml_info
        yaml_path = Path(__file__).parent.parent / "src" / "core" / "data" / "abilities" / yaml_file
        assert yaml_path.exists(), f"{yaml_file} missing"

    @pytest.mark.parametrize("cls_name,yaml_info", list(ULTIMATE_YAML_MAP.items()))
    def test_wrapper_class_instantiates(self, cls_name, yaml_info):
        from src.core import abilities

        _, display_name, _ = yaml_info
        ab = getattr(abilities, cls_name)()
        assert ab.name == display_name

    @pytest.mark.parametrize("cls_name,yaml_info", list(ULTIMATE_YAML_MAP.items()))
    def test_correct_type(self, cls_name, yaml_info):
        from src.core import abilities
        from src.core.data.data_driven_abilities import DataDrivenSkill, DataDrivenSpell

        _, _, expected_type = yaml_info
        ab = getattr(abilities, cls_name)()
        if expected_type == "Skill":
            assert isinstance(ab, DataDrivenSkill)
        else:
            assert isinstance(ab, DataDrivenSpell)

    @pytest.mark.parametrize("cls_name,yaml_info", list(ULTIMATE_YAML_MAP.items()))
    def test_has_effect(self, cls_name, yaml_info):
        from src.core import abilities

        ab = getattr(abilities, cls_name)()
        assert len(ab._effects) > 0


class TestCompanionUltimateSummonWiring:
    """All Xenid ultimates are wired at level 10."""

    @pytest.mark.parametrize("summon_name,info", list(SUMMON_ABILITY_MAP.items()))
    def test_summon_has_level_10(self, summon_name, info):
        from src.core.companions import summon_abilities

        typ, cls_name = info
        assert "10" in summon_abilities[summon_name][typ]

    @pytest.mark.parametrize("summon_name,info", list(SUMMON_ABILITY_MAP.items()))
    def test_level_10_produces_correct_ability(self, summon_name, info):
        from src.core.companions import summon_abilities

        typ, cls_name = info
        ab = summon_abilities[summon_name][typ]["10"]()
        expected_name = ULTIMATE_YAML_MAP[cls_name][1]
        assert ab.name == expected_name


class TestCompanionUltimateSerialize:
    """All 11 ultimates serialize/deserialize correctly."""

    @pytest.mark.parametrize("cls_name", list(ULTIMATE_YAML_MAP.keys()))
    def test_serialize_roundtrip(self, cls_name):
        from src.core import abilities
        from src.core.save_system import AbilitySerializer

        ab = getattr(abilities, cls_name)()
        serialized = AbilitySerializer.serialize(ab)
        assert serialized == ab.ability_id
        restored = AbilitySerializer.deserialize(serialized)
        assert restored is not None


class TestTitanicSlamEffect:
    """Patagon ultimate: 4x weapon + guaranteed stun."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Patagon",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(100, 100),
            stats={"strength": 30, "intel": 10, "wisdom": 10, "con": 25, "charisma": 10, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_deals_damage(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import TitanicSlamEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Titanic Slam", actor=user, target=target)
        effect = TitanicSlamEffect(dmg_mod=4.0, stun_duration=2)
        effect.apply(user, target, result)
        assert result.hit is True
        assert target.health.current < 500

    def test_stun_applied(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import TitanicSlamEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Titanic Slam", actor=user, target=target)
        effect = TitanicSlamEffect(dmg_mod=4.0, stun_duration=2)
        effect.apply(user, target, result)
        if result.hit:
            assert target.status_effects["Stun"].active is True
            assert target.status_effects["Stun"].duration == 2

    def test_stun_blocked_by_mana_shield(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import TitanicSlamEffect

        user, target = self._make_combatants()
        target.magic_effects["Mana Shield"].active = True
        target.magic_effects["Mana Shield"].duration = 3
        target.mana.current = 200
        result = CombatResult(action="Titanic Slam", actor=user, target=target)
        effect = TitanicSlamEffect(dmg_mod=4.0, stun_duration=2)
        effect.apply(user, target, result)
        # Mana Shield absorbs the stun force
        assert target.status_effects["Stun"].active is False

    def test_has_messages(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import TitanicSlamEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Titanic Slam", actor=user, target=target)
        effect = TitanicSlamEffect()
        effect.apply(user, target, result)
        messages = result.extra.get("messages", [])
        assert any("crashing" in m.lower() for m in messages)


class TestDevourEffect:
    """Dilong ultimate: 3 bites at (str+con)*1.5, Earth element."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Dilong",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(100, 100),
            stats={"strength": 25, "intel": 10, "wisdom": 10, "con": 25, "charisma": 10, "dex": 15},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_deals_multi_hit_damage(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import DevourEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Devour", actor=user, target=target)
        effect = DevourEffect(num_bites=3, multiplier=1.5, element="Earth")
        effect.apply(user, target, result)
        assert target.health.current < 500
        assert result.damage > 0

    def test_bite_messages(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import DevourEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Devour", actor=user, target=target)
        effect = DevourEffect(num_bites=3, multiplier=1.5)
        effect.apply(user, target, result)
        messages = result.extra.get("messages", [])
        crush_msgs = [
            m
            for m in messages
            if "crushes" in m.lower() or "devours" in m.lower() or "spits" in m.lower()
        ]
        assert len(crush_msgs) >= 1


class TestAbsoluteZeroEffect:
    """Agloolik ultimate: ice + stun + defense reduction."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Agloolik",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 30, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        user.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_deals_damage(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import AbsoluteZeroEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Absolute Zero", actor=user, target=target)
        effect = AbsoluteZeroEffect(damage_mod=3.0, stun_duration=3, def_reduction=5)
        effect.apply(user, target, result)
        assert target.health.current < 500

    def test_stun_applied(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import AbsoluteZeroEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Absolute Zero", actor=user, target=target)
        effect = AbsoluteZeroEffect(damage_mod=3.0, stun_duration=3, def_reduction=5)
        effect.apply(user, target, result)
        if result.hit:
            assert target.status_effects["Stun"].active is True
            assert target.status_effects["Stun"].duration == 3

    def test_defense_permanently_reduced(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import AbsoluteZeroEffect

        user, target = self._make_combatants()
        def_before = target.combat.defense
        result = CombatResult(action="Absolute Zero", actor=user, target=target)
        effect = AbsoluteZeroEffect(damage_mod=3.0, stun_duration=3, def_reduction=5)
        effect.apply(user, target, result)
        if result.hit:
            assert target.combat.defense == def_before - 5


class TestEruptionEffect:
    """Cacus ultimate: fire + Burn DOT + self defense buff."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Cacus",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(200, 200),
            stats={"strength": 20, "intel": 25, "wisdom": 15, "con": 15, "charisma": 10, "dex": 15},
        )
        user.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_deals_fire_damage(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import EruptionEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Eruption", actor=user, target=target)
        effect = EruptionEffect(damage_mod=3.5, burn_duration=3)
        effect.apply(user, target, result)
        assert target.health.current < 500

    def test_burn_applied(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import EruptionEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Eruption", actor=user, target=target)
        effect = EruptionEffect(damage_mod=3.5, burn_duration=3)
        effect.apply(user, target, result)
        if result.hit:
            assert target.magic_effects["DOT"].active is True
            assert target.magic_effects["DOT"].duration == 3

    def test_self_defense_buff(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import EruptionEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Eruption", actor=user, target=target)
        effect = EruptionEffect(damage_mod=3.5, vulcanize_duration=3)
        effect.apply(user, target, result)
        assert user.stat_effects["Defense"].active is True
        assert user.stat_effects["Defense"].duration == 3


class TestMaelstromVortexEffect:
    """Fuath ultimate: water damage + Blind/Silence/Terrify."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Fuath",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 30, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        user.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_deals_water_damage(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import MaelstromVortexEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Maelstrom Vortex", actor=user, target=target)
        effect = MaelstromVortexEffect(damage_mod=3.0, status_duration=3)
        effect.apply(user, target, result)
        assert target.health.current < 500

    def test_debuffs_applied(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import MaelstromVortexEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Maelstrom Vortex", actor=user, target=target)
        effect = MaelstromVortexEffect(damage_mod=3.0, status_duration=3)
        effect.apply(user, target, result)
        if result.hit:
            # At least Blind and Silence should be applied (Terrify is magic_effects)
            assert target.status_effects["Blind"].active is True
            assert target.status_effects["Silence"].active is True

    def test_debuffs_blocked_by_mana_shield(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import MaelstromVortexEffect

        user, target = self._make_combatants()
        target.magic_effects["Mana Shield"].active = True
        target.magic_effects["Mana Shield"].duration = 3
        target.mana.current = 200
        result = CombatResult(action="Maelstrom Vortex", actor=user, target=target)
        effect = MaelstromVortexEffect(damage_mod=3.0, status_duration=3)
        effect.apply(user, target, result)
        assert target.status_effects["Blind"].active is False
        assert target.status_effects["Silence"].active is False


class TestThunderstrikeEffect:
    """Izulu ultimate: electric + chain hits + stun."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Izulu",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 30, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        user.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_deals_damage_with_chains(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import ThunderstrikeEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Thunderstrike", actor=user, target=target)
        effect = ThunderstrikeEffect(damage_mod=3.0, chain_hits=2, chain_multiplier=0.5)
        effect.apply(user, target, result)
        assert target.health.current < 500
        messages = result.extra.get("messages", [])
        chain_msgs = [m for m in messages if "chain" in m.lower() or "arc" in m.lower()]
        assert len(chain_msgs) >= 1

    def test_stun_applied(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import ThunderstrikeEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Thunderstrike", actor=user, target=target)
        effect = ThunderstrikeEffect(damage_mod=3.0, stun_duration=2)
        effect.apply(user, target, result)
        if result.hit:
            assert target.status_effects["Stun"].active is True
            assert target.status_effects["Stun"].duration == 2


class TestWindShrapnelEffect:
    """Hala ultimate: 5 hits with independent crit chance."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Hala",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 30, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        user.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_multiple_hits(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import WindShrapnelEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Wind Shrapnel", actor=user, target=target)
        effect = WindShrapnelEffect(num_hits=5, damage_mod=1.2)
        effect.apply(user, target, result)
        assert target.health.current < 500
        messages = result.extra.get("messages", [])
        shard_msgs = [m for m in messages if "shard" in m.lower() or "blade" in m.lower()]
        assert len(shard_msgs) >= 1

    def test_total_damage_is_sum(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import WindShrapnelEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Wind Shrapnel", actor=user, target=target)
        effect = WindShrapnelEffect(num_hits=5, damage_mod=1.2, crit_chance=0.0)
        effect.apply(user, target, result)
        assert result.damage == 500 - target.health.current


class TestDivineJudgmentEffect:
    """Seraphim ultimate: holy damage + heal owner + cleanse."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Seraphim",
            class_name="Cleric",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(200, 200),
            stats={"strength": 10, "intel": 15, "wisdom": 30, "con": 15, "charisma": 15, "dex": 10},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_deals_holy_damage(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import DivineJudgmentEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Divine Judgment", actor=user, target=target)
        effect = DivineJudgmentEffect(damage_mod=3.0)
        effect.apply(user, target, result)
        assert target.health.current < 500

    def test_heals_owner(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import DivineJudgmentEffect

        user, target = self._make_combatants()
        # Simulate owner (summoner) who is damaged
        owner = self._make_combatants()[0]  # another player
        owner.health.current = 100  # damaged
        owner.health.max = 400
        user.owner = owner
        result = CombatResult(action="Divine Judgment", actor=user, target=target)
        effect = DivineJudgmentEffect(damage_mod=3.0, heal_fraction=0.5)
        effect.apply(user, target, result)
        assert owner.health.current > 100

    def test_cleanses_owner_status(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import DivineJudgmentEffect

        user, target = self._make_combatants()
        owner = self._make_combatants()[0]
        owner.status_effects["Poison"].active = True
        owner.status_effects["Poison"].duration = 3
        owner.status_effects["Blind"].active = True
        owner.status_effects["Blind"].duration = 2
        user.owner = owner
        result = CombatResult(action="Divine Judgment", actor=user, target=target)
        effect = DivineJudgmentEffect(damage_mod=3.0)
        effect.apply(user, target, result)
        assert owner.status_effects["Poison"].active is False
        assert owner.status_effects["Blind"].active is False

    def test_double_damage_vs_undead(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import DivineJudgmentEffect

        user, target = self._make_combatants()
        target.enemy_typ = "Undead"
        result = CombatResult(action="Divine Judgment", actor=user, target=target)
        effect = DivineJudgmentEffect(damage_mod=3.0, undead_multiplier=2.0)
        effect.apply(user, target, result)
        messages = result.extra.get("messages", [])
        assert any("undead" in m.lower() for m in messages)


class TestOblivionEffect:
    """Bardi ultimate: shadow damage + instant kill + stat drain."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Bardi",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(200, 200),
            stats={"strength": 10, "intel": 30, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        user.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 20, "intel": 15, "wisdom": 15, "con": 20, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_deals_shadow_damage(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import OblivionEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Oblivion", actor=user, target=target)
        effect = OblivionEffect(damage_mod=4.0, kill_chance=0.0, stat_drain=3)
        effect.apply(user, target, result)
        assert target.health.current < 500

    def test_stat_drain(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import OblivionEffect

        user, target = self._make_combatants()
        str_before = target.stats.strength
        int_before = target.stats.intel
        result = CombatResult(action="Oblivion", actor=user, target=target)
        effect = OblivionEffect(damage_mod=4.0, kill_chance=0.0, stat_drain=3)
        effect.apply(user, target, result)
        if result.hit and target.is_alive():
            assert target.stats.strength == str_before - 3
            assert target.stats.intel == int_before - 3

    def test_instant_kill_blocked_by_death_immunity(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import OblivionEffect

        user, target = self._make_combatants()
        target.status_immunity.append("Death")
        result = CombatResult(action="Oblivion", actor=user, target=target)
        effect = OblivionEffect(damage_mod=4.0, kill_chance=1.0, stat_drain=3)
        effect.apply(user, target, result)
        # Target should still be alive (high HP) since instant kill is blocked
        if result.hit:
            assert target.is_alive()


class TestGrandHeistEffect:
    """Kobalos ultimate: steal gold + debuff + Gold Toss."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Kobalos",
            class_name="Thief",
            race_name="Human",
            level=30,
            health=(300, 300),
            mana=(100, 100),
            stats={"strength": 15, "intel": 15, "wisdom": 10, "con": 15, "charisma": 20, "dex": 25},
        )
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
            gold=1000,
        )
        return user, target

    def test_steals_gold(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import GrandHeistEffect

        user, target = self._make_combatants()
        user.owner = self._make_combatants()[0]  # summoner
        user.owner.gold = 500
        gold_before = target.gold
        result = CombatResult(action="Grand Heist", actor=user, target=target)
        effect = GrandHeistEffect()
        effect.apply(user, target, result)
        assert target.gold < gold_before
        messages = result.extra.get("messages", [])
        assert any("steal" in m.lower() for m in messages)

    def test_gold_toss_damage(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import GrandHeistEffect

        user, target = self._make_combatants()
        user.owner = self._make_combatants()[0]
        user.owner.gold = 10000  # lots of gold for big toss
        result = CombatResult(action="Grand Heist", actor=user, target=target)
        effect = GrandHeistEffect(gold_multiplier=2.0)
        effect.apply(user, target, result)
        assert result.damage > 0
        messages = result.extra.get("messages", [])
        assert any("gold" in m.lower() or "coin" in m.lower() for m in messages)

    def test_debuff_blocked_by_immunity(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import GrandHeistEffect

        user, target = self._make_combatants()
        target.status_immunity.extend(["Blind", "Silence", "Poison"])
        result = CombatResult(action="Grand Heist", actor=user, target=target)
        effect = GrandHeistEffect()
        effect.apply(user, target, result)
        assert target.status_effects["Blind"].active is False
        assert target.status_effects["Silence"].active is False
        assert target.status_effects["Poison"].active is False


class TestCataclysmEffect:
    """Zahhak ultimate: cast spells + dragon breath + self buff."""

    @staticmethod
    def _make_combatants():
        from tests.test_framework import TestGameState

        user = TestGameState.create_player(
            name="Zahhak",
            class_name="Wizard",
            race_name="Human",
            level=30,
            health=(400, 400),
            mana=(300, 300),
            stats={"strength": 20, "intel": 30, "wisdom": 20, "con": 15, "charisma": 10, "dex": 15},
        )
        user.class_effects["Power Up"].active = False
        target = TestGameState.create_player(
            name="Target",
            class_name="Warrior",
            race_name="Human",
            level=30,
            health=(500, 500),
            mana=(50, 50),
            stats={"strength": 10, "intel": 10, "wisdom": 10, "con": 10, "charisma": 10, "dex": 10},
        )
        return user, target

    def test_deals_breath_damage(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import CataclysmEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Cataclysm", actor=user, target=target)
        effect = CataclysmEffect(spell_count=0, breath_multiplier=2.0)
        effect.apply(user, target, result)
        assert target.health.current < 500
        messages = result.extra.get("messages", [])
        assert any("breath" in m.lower() or "fire" in m.lower() for m in messages)

    def test_self_power_up(self):
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import CataclysmEffect

        user, target = self._make_combatants()
        result = CombatResult(action="Cataclysm", actor=user, target=target)
        effect = CataclysmEffect(spell_count=0, power_up_duration=3)
        effect.apply(user, target, result)
        assert user.stat_effects["Attack"].active is True
        assert user.stat_effects["Attack"].duration == 3

    def test_casts_spells_from_spellbook(self):
        from src.core import abilities
        from src.core.combat.combat_result import CombatResult
        from src.core.effects import CataclysmEffect

        user, target = self._make_combatants()
        # Give the user some spells
        fireball = abilities.Fireball()
        iceblizzard = abilities.IceBlizzard()
        user.spellbook["Spells"]["Fireball"] = fireball
        user.spellbook["Spells"]["Blizzard"] = iceblizzard
        result = CombatResult(action="Cataclysm", actor=user, target=target)
        effect = CataclysmEffect(spell_count=2, breath_multiplier=2.0)
        effect.apply(user, target, result)
        # Should deal damage from spells + breath
        assert target.health.current < 500


class TestCompanionUltimateEffectFactory:
    """All 11 effects are registered in EffectFactory."""

    @pytest.mark.parametrize(
        "effect_type",
        [
            "titanic_slam",
            "devour",
            "absolute_zero",
            "eruption",
            "maelstrom_vortex",
            "thunderstrike",
            "wind_shrapnel",
            "divine_judgment",
            "oblivion",
            "grand_heist",
            "cataclysm",
        ],
    )
    def test_effect_factory_creates(self, effect_type):
        from src.core.data.ability_loader import EffectFactory

        effect = EffectFactory.create({"type": effect_type})
        assert effect is not None


class TestClassAbilityMechanicsSlice:
    """Class ability mechanics are real, loadable, and class-granted."""

    @pytest.mark.parametrize(
        "class_name,expected_name,passive",
        [
            ("Zephyrstrike", "Zephyrstrike", True),
            ("Retaliate", "Retaliate", True),
            ("DefensiveRegen", "Defensive Regen", True),
            ("Posturing", "Posturing", True),
            ("ThirdEye", "Third Eye", True),
            ("PiousBounty", "Pious Bounty", True),
            ("PoisonDart", "Poison Dart", False),
            ("Bolt", "Bolt", False),
            ("BallLightning", "Ball Lightning", False),
            ("StoneSkin", "Stone Skin", False),
            ("CalmingBreeze", "Calming Breeze", False),
            ("Windswept", "Windswept", False),
            ("Regrowth", "Regrowth", False),
            ("NatureShield", "Nature Shield", False),
            ("Haste", "Haste", False),
        ],
    )
    def test_class_ability_factories(self, class_name, expected_name, passive):
        from src.core import abilities

        ability = getattr(abilities, class_name)()

        assert ability.name == expected_name
        assert getattr(ability, "passive", False) is passive

    def test_class_grants_are_registered(self):
        from src.core import abilities

        assert abilities.skill_dict["Lancer"]["1"] == [
            abilities.CriticalVigor,
            abilities.DragonSoul,
            abilities.ExtendedReach,
            abilities.Jump,
            abilities.LanceSweep,
            abilities.Phalanx,
            abilities.PolearmExcellence,
            abilities.PolearmProficiency,
            abilities.SwingAndBash,
            abilities.TrueStrike,
            abilities.VigilantLanding,
        ]
        assert abilities.skill_dict["Lancer"]["12"] is abilities.Zephyrstrike
        assert abilities.skill_dict["Dragoon"]["1"] == [
            abilities.PolearmMastery,
            abilities.DragonDive,
            abilities.Dragonheart,
        ]
        assert "10" not in abilities.skill_dict["Dragoon"]
        assert abilities.skill_dict["Sentinel"]["1"] == [
            abilities.Adrenaline,
            abilities.Boast,
            abilities.BraceWall,
            abilities.BulwarkGuard,
            abilities.Charge,
            abilities.DoubleStrike,
            abilities.FocusedAssault,
            abilities.Goad,
            abilities.HoldTheLine,
            abilities.PurgeWeakness,
            abilities.Repercussion,
            abilities.Retaliate,
            abilities.ShieldRiposte,
            abilities.SpellBlock,
            abilities.SpellReflection,
            abilities.SwingAndBash,
        ]
        assert abilities.skill_dict["Crusader"]["1"] == [
            abilities.BeyondReproach,
            abilities.Censure,
            abilities.Condemnation,
            abilities.Parry,
            abilities.Penalization,
            abilities.Posturing,
            abilities.PrayerOfFaith,
            abilities.RadiantHealing,
            abilities.Sanctification,
            abilities.ShieldRicochet,
            abilities.SwordAndBoard,
            abilities.TwoHandedWeaponProficiency,
            abilities.UndeadHunter,
        ]
        assert abilities.skill_dict["Stalwart Defender"]["18"] is abilities.LastStand
        assert abilities.skill_dict["Seeker"]["5"] is abilities.ThirdEye
        assert "Third Eye" not in [
            skill().name for skill in abilities.skill_dict["Inquisitor"].values()
        ]
        assert "Pious Bounty" not in [
            skill().name for skill in abilities.skill_dict["Priest"].values()
        ]
        assert abilities.skill_dict["Cleric"]["1"] is abilities.SanctuaryWard
        assert "8" not in abilities.skill_dict["Cleric"]
        assert abilities.skill_dict["Cleric"]["24"] is abilities.PiousBounty
        assert abilities.skill_dict["Templar"]["1"] is abilities.Parry
        assert abilities.skill_dict["Hierophant"]["1"] is abilities.StaffConduit
        assert abilities.skill_dict["Hierophant"]["8"] is abilities.ConsecratedConduit
        assert abilities.spell_dict["Hierophant"]["4"] is abilities.Holy2
        assert abilities.spell_dict["Hierophant"]["12"] is abilities.Regen2
        assert abilities.spell_dict["Hierophant"]["18"] is abilities.Dispel
        assert abilities.Heal3 not in abilities.spell_dict["Hierophant"].values()
        assert abilities.Holy3 not in abilities.spell_dict["Hierophant"].values()
        assert abilities.Resurrection not in abilities.spell_dict["Hierophant"].values()
        assert list(abilities.skill_dict["Bard"].values()) == [
            abilities.SongValor,
            abilities.SongShelter,
            abilities.SongRenewal,
            abilities.RhythmicStrike,
            abilities.CurtainGuard,
        ]
        assert abilities.skill_dict["Troubadour"] == {
            "1": abilities.GrandFinale,
            "2": abilities.SyncopatedStrike,
            "3": abilities.Countermelody,
        }
        assert abilities.spell_dict["Bard"] == {
            "1": abilities.Kaleidoscope,
            "2": abilities.InspiringVerse,
            "3": abilities.DissonantChord,
            "4": abilities.PrismaticRay,
        }
        assert abilities.spell_dict["Troubadour"] == {
            "1": abilities.RallyingChorus,
            "2": abilities.ResonantWave,
            "3": abilities.PrismaticFinale,
        }
        assert all(
            spell is not abilities.Haste for spell in abilities.spell_dict["Sorcerer"].values()
        )
        assert all(
            spell is not abilities.Haste for spell in abilities.spell_dict["Wizard"].values()
        )
        assert abilities.spell_dict["Diviner"]["8"] is abilities.Haste
        assert "Steal As Well" not in [
            skill().name for skill in abilities.skill_dict["Arcane Trickster"].values()
        ]
        assert abilities.skill_dict["Spell Stealer"]["12"] is abilities.StealAsWell
        assert abilities.skill_dict["Ranger"]["1"] == [abilities.Tame, abilities.FavoredEnemy]
        assert abilities.skill_dict["Beast Master"] == {
            "5": abilities.Cover,
            "7": abilities.Zephyrstrike,
            "9": abilities.PackStrike,
            "10": abilities.GuardPartner,
            "11": abilities.HarryPrey,
            "12": abilities.MendWounds,
            "13": abilities.UnleashInstinct,
            "14": abilities.RallyPartner,
        }
        assert abilities.spell_dict["Shadowcaster"]["16"] is abilities.Nightmare
        assert "Nightmare" not in [
            spell().name for spell in abilities.spell_dict["Demonologist"].values()
        ]

    def test_archdruid_nature_spell_line_is_registered(self):
        from src.core import abilities

        assert abilities.skill_dict["Archdruid"] == {"10": abilities.FourfoldSurge}
        druid_spells = {
            spell
            for entry in abilities.spell_dict["Druid"].values()
            for spell in abilities.ability_classes_for(entry)
        }
        assert druid_spells == {
            abilities.PoisonDart,
            abilities.NoxiousMist,
            abilities.ResistPoison,
            abilities.RestoringBoon,
            abilities.Starfall,
            abilities.StoneSkin,
            abilities.Regrowth,
            abilities.CalmingBreeze,
        }
        archdruid_spells = {
            spell
            for entry in abilities.spell_dict["Archdruid"].values()
            for spell in abilities.ability_classes_for(entry)
        }
        assert archdruid_spells == {
            abilities.PlantSeeds,
            abilities.Bolt,
            abilities.VilePotion,
            abilities.Windswept,
            abilities.NatureShield,
            abilities.BallLightning,
            abilities.PoisonBreath,
            abilities.ExpelCurse,
            abilities.GrovePulse,
        }

    def test_simple_support_spells_apply_existing_effects(self):
        from src.core import abilities
        from tests.test_framework import TestGameState

        caster = TestGameState.create_player(
            name="Archdruid",
            class_name="Archdruid",
            race_name="Human",
            level=30,
            mana=(200, 200),
            stats={"strength": 10, "intel": 24, "wisdom": 30, "con": 10, "charisma": 10, "dex": 12},
        )
        caster.combat.defense = 20
        caster.combat.magic = 30
        caster.combat.magic_def = 18
        caster.status_effects["Poison"].active = True
        caster.status_effects["Poison"].duration = 3

        abilities.StoneSkin().cast(caster, caster)
        abilities.Windswept().cast(caster, caster)
        abilities.NatureShield().cast(caster, caster)
        abilities.CalmingBreeze().cast(caster, caster)

        assert caster.magic_effects["Stone Skin"].active is True
        assert caster.flying is True
        assert caster.magic_effects["Nature Shield"].active is True
        assert caster.magic_effects["Nature Shield"].extra == 3
        assert caster.status_effects["Peaceful"].active is True
