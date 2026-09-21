"""Focused coverage for additive foundational gameplay contracts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import yaml

from src.core.combat.targeting import (
    ActionIntent,
)
from src.core.combat.targeting import TargetLossPolicy as LegacyTargetLossPolicy
from src.core.combat.targeting import TargetScope as LegacyTargetScope
from src.core.combat.targeting import canonical_targeting_policy
from src.core.contracts import (
    AbilityActivation,
    AbilityDefinition,
    AbilityForm,
    AbilityMethod,
    AbilityOrigin,
    AbilityTaxonomy,
    ActionAvailability,
    ActionAvailabilityCode,
    ActionDefinition,
    ActionReference,
    ActionReferenceKind,
    CombatResourcePresentation,
    PrimaryIntent,
    TargetingPolicy,
    TargetLossPolicy,
    TargetScope,
    TimelineEntry,
    VisibilityState,
)
from src.core.data.ability_loader import AbilityFactory
from src.core.data.ability_schema import (
    ABILITY_DIRECTORY,
    load_legacy_allowlist,
    validate_ability_directory,
)


def test_closed_ability_taxonomy_and_internal_trait_filtering():
    assert {member.value for member in AbilityOrigin} == {
        "martial",
        "arcane",
        "divine",
        "natural",
        "spiritual",
        "extraplanar",
        "innate",
        "alchemical",
    }
    taxonomy = AbilityTaxonomy(
        AbilityOrigin.ARCANE,
        AbilityMethod.PROJECTION,
        PrimaryIntent.DAMAGE,
        AbilityActivation.ACTIVE,
        AbilityForm.DIRECT,
        frozenset({"combat.projectile", "internal.combo_trigger"}),
    )
    definition = AbilityDefinition(
        "magic_missile_2",
        "Magic Missile",
        "Launches two arcane missiles.",
        taxonomy,
        TargetingPolicy(
            TargetScope.SINGLE_OPPONENT,
            TargetLossPolicy.RETARGET_FOCUS,
            hostile=True,
        ),
        aliases=("MagicMissile2",),
    )

    assert definition.player_facing_traits == ("combat.projectile",)
    assert AbilityForm("item_action") is AbilityForm.ITEM_ACTION
    assert AbilityActivation("reaction") is AbilityActivation.REACTION


def test_targeting_policy_enforces_area_snapshot_contract():
    policy = TargetingPolicy(
        TargetScope.ALL_OPPONENTS,
        TargetLossPolicy.SNAPSHOT_ROSTER,
        hostile=True,
    )

    assert policy.scope is TargetScope.ALL_OPPONENTS
    with pytest.raises(ValueError, match="snapshot"):
        TargetingPolicy(TargetScope.ALL_OPPONENTS, TargetLossPolicy.RETARGET_FOCUS)
    with pytest.raises(ValueError, match="only"):
        TargetingPolicy(TargetScope.SINGLE_OPPONENT, TargetLossPolicy.SNAPSHOT_ROSTER)


def test_ability_factory_uses_canonical_targeting_metadata_at_runtime():
    direct = AbilityFactory.create_from_yaml(ABILITY_DIRECTORY / "magic_missile_2.yaml")
    locked_charge = AbilityFactory.create_from_yaml(ABILITY_DIRECTORY / "shadow_strike.yaml")

    assert direct.target_scope is LegacyTargetScope.SINGLE_ENEMY
    assert direct.target_loss_policy is LegacyTargetLossPolicy.RETARGET_FOCUS
    assert direct.targeting_hostile is True
    assert locked_charge.target_loss_policy is LegacyTargetLossPolicy.LOCKED


def test_action_intent_uses_canonical_id_without_internal_legacy_accessor():
    canonical = ActionIntent(action_id="system.attack", target_ids=("enemy-a",))

    assert canonical.action_id == "system.attack"
    assert not hasattr(canonical, "action")
    with pytest.raises(ValueError, match="must not be empty"):
        ActionIntent(action_id="")

    adapted = canonical_targeting_policy(
        LegacyTargetScope.ALL_ENEMIES,
        LegacyTargetLossPolicy.SNAPSHOT_ROSTER,
        hostile=True,
    )
    assert adapted == TargetingPolicy(
        TargetScope.ALL_OPPONENTS,
        TargetLossPolicy.SNAPSHOT_ROSTER,
        hostile=True,
    )


def test_action_and_presentation_models_are_typed_and_text_complete():
    reference = ActionReference(ActionReferenceKind.ITEM, "ThrowingDaggers")
    action = ActionDefinition(
        "item.ThrowingDaggers",
        "Throwing Daggers",
        AbilityActivation.ACTIVE,
        TargetingPolicy(TargetScope.SINGLE_OPPONENT, TargetLossPolicy.RETARGET_FOCUS),
    )
    unavailable = ActionAvailability(
        ActionAvailabilityCode.INSUFFICIENT_ITEM_COUNT,
        "No throwing daggers remain.",
    )
    resource = CombatResourcePresentation(
        "warrior.resolve",
        "Resolve",
        10,
        "resource.resolve",
        value=3,
        capacity=3,
        state_text="Full",
        ready=True,
    )

    assert ActionReference.from_dict(reference.to_dict()) == reference
    assert action.action_id == "item.ThrowingDaggers"
    assert unavailable.available is False
    assert resource.ready is True and resource.label == "Resolve"
    assert TimelineEntry("player", "Hero", 25.5).ready_at == 25.5
    assert VisibilityState("enemy-a", concealed=True).hostile_single_target_legal is False
    assert (
        VisibilityState(
            "enemy-a", concealed=True, revealed_by=frozenset({"sight.player"})
        ).hostile_single_target_legal
        is True
    )


def test_complete_ability_taxonomy_has_no_legacy_allowlist():
    allowlist = load_legacy_allowlist()
    report = validate_ability_directory(require_complete=True)

    assert allowlist == frozenset()
    assert report.valid is True
    assert len(report.definitions) == 197
    assert report.legacy_ability_ids == ()
    assert {definition.ability_id for definition in report.definitions} == {
        path.stem for path in ABILITY_DIRECTORY.glob("*.yaml")
    }


def test_complete_taxonomy_matches_reviewed_inventory_and_semantic_exceptions():
    definitions = validate_ability_directory(require_complete=True).definitions
    by_id = {definition.ability_id: definition for definition in definitions}

    assert Counter(definition.taxonomy.origin.value for definition in definitions) == {
        "martial": 56,
        "innate": 34,
        "natural": 30,
        "arcane": 29,
        "divine": 27,
        "extraplanar": 11,
        "spiritual": 6,
        "alchemical": 4,
    }
    assert Counter(definition.taxonomy.activation.value for definition in definitions) == {
        "active": 192,
        "passive": 3,
        "reaction": 2,
    }
    assert Counter(definition.taxonomy.primary_intent.value for definition in definitions) == {
        "damage": 112,
        "protection": 29,
        "control": 25,
        "restoration": 12,
        "utility": 9,
        "mobility": 7,
        "information": 2,
        "summoning": 1,
    }
    assert by_id["arcane_blast"].taxonomy.primary_intent is PrimaryIntent.DAMAGE
    assert by_id["great_gospel"].taxonomy.primary_intent is PrimaryIntent.RESTORATION
    assert by_id["consume_item"].taxonomy.form is AbilityForm.DIRECT
    assert by_id["consume_item"].taxonomy.method is AbilityMethod.CONSUMPTION
    assert by_id["consume_item"].targeting.hostile is True
    assert by_id["imbue_weapon"].taxonomy.primary_intent is PrimaryIntent.DAMAGE
    assert by_id["smoke_screen"].targeting.scope is TargetScope.SELF
    assert "Heal" in by_id["heal"].aliases and "Heal" in by_id["heal_2"].aliases


def test_yaml_loader_assigns_immutable_filename_slug_and_aliases():
    ability = AbilityFactory.create_from_yaml(ABILITY_DIRECTORY / "magic_missile_2.yaml")

    assert ability.ability_id == "magic_missile_2"
    assert {"MagicMissile2", "Magic Missile II"}.issubset(ability.aliases)
    with pytest.raises(AttributeError, match="immutable"):
        ability.ability_id = "different_slug"


def test_validator_accepts_complete_metadata_and_rejects_stale_allowlist(tmp_path: Path):
    ability_dir = tmp_path / "abilities"
    ability_dir.mkdir()
    payload = {
        "id": "test_bolt",
        "aliases": ["TestBolt", "Test Bolt"],
        "name": "Test Bolt",
        "description": "A test projection.",
        "type": "Spell",
        "taxonomy": {
            "origin": "arcane",
            "method": "projection",
            "primary_intent": "damage",
            "activation": "active",
            "form": "direct",
            "traits": [],
        },
        "targeting": {
            "scope": "single_opponent",
            "loss_policy": "retarget_focus",
            "hostile": True,
        },
        "effects": [],
    }
    (ability_dir / "test_bolt.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")
    allowlist_path = tmp_path / "allowlist.txt"
    allowlist_path.write_text("", encoding="utf-8")

    report = validate_ability_directory(ability_dir, allowlist_path=allowlist_path)

    assert report.valid is True
    assert report.definitions[0].ability_id == "test_bolt"

    allowlist_path.write_text("test_bolt\n", encoding="utf-8")
    stale = validate_ability_directory(ability_dir, allowlist_path=allowlist_path)
    assert [(issue.ability_id, issue.code) for issue in stale.issues] == [
        ("test_bolt", "stale_allowlist")
    ]


def test_validator_allows_shared_display_names_but_not_shared_class_aliases(tmp_path: Path):
    ability_dir = tmp_path / "abilities"
    ability_dir.mkdir()
    allowlist_path = tmp_path / "allowlist.txt"
    allowlist_path.write_text("", encoding="utf-8")

    def payload(ability_id: str, class_alias: str) -> dict[str, object]:
        return {
            "id": ability_id,
            "aliases": [class_alias, "Heal"],
            "name": "Heal",
            "description": "Test healing.",
            "taxonomy": {
                "origin": "divine",
                "method": "channeling",
                "primary_intent": "restoration",
                "activation": "active",
                "form": "direct",
                "traits": [],
            },
            "targeting": {"scope": "self", "loss_policy": "locked", "hostile": False},
        }

    first = payload("heal_a", "HealA")
    second = payload("heal_b", "HealB")
    (ability_dir / "heal_a.yaml").write_text(yaml.safe_dump(first), encoding="utf-8")
    (ability_dir / "heal_b.yaml").write_text(yaml.safe_dump(second), encoding="utf-8")
    assert validate_ability_directory(ability_dir, allowlist_path=allowlist_path).valid

    second["aliases"] = ["HealA", "Heal"]
    (ability_dir / "heal_b.yaml").write_text(yaml.safe_dump(second), encoding="utf-8")
    report = validate_ability_directory(ability_dir, allowlist_path=allowlist_path)
    assert [(issue.ability_id, issue.code) for issue in report.issues] == [
        ("heal_b", "duplicate_alias")
    ]


def test_validator_rejects_unknown_traits_and_partial_metadata(tmp_path: Path):
    ability_dir = tmp_path / "abilities"
    ability_dir.mkdir()
    (ability_dir / "partial.yaml").write_text("id: partial\nname: Partial\n", encoding="utf-8")
    allowlist_path = tmp_path / "allowlist.txt"
    allowlist_path.write_text("", encoding="utf-8")

    report = validate_ability_directory(ability_dir, allowlist_path=allowlist_path)

    assert [(issue.ability_id, issue.code) for issue in report.issues] == [
        ("partial", "partial_metadata")
    ]

    (ability_dir / "partial.yaml").unlink()
    unknown_trait = {
        "id": "unknown_trait",
        "aliases": ["Unknown Trait"],
        "name": "Unknown Trait",
        "description": "Invalid test metadata.",
        "taxonomy": {
            "origin": "innate",
            "method": "command",
            "primary_intent": "utility",
            "activation": "active",
            "form": "direct",
            "traits": ["unregistered.example"],
        },
        "targeting": {
            "scope": "self",
            "loss_policy": "retarget_focus",
            "hostile": False,
        },
    }
    (ability_dir / "unknown_trait.yaml").write_text(yaml.safe_dump(unknown_trait), encoding="utf-8")

    report = validate_ability_directory(ability_dir, allowlist_path=allowlist_path)
    assert [(issue.ability_id, issue.code) for issue in report.issues] == [
        ("unknown_trait", "invalid_metadata")
    ]
    assert "unregistered traits" in report.issues[0].message
