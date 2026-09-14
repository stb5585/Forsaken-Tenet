"""Contract coverage for the foundational combat interface projection."""

from types import SimpleNamespace

from src.core.abilities.utility import Rally
from src.core.combat.action_interface import (
    SHORTCUT_SLOT_COUNT,
    ActionReference,
    ActionReferenceKind,
    assign_shortcut,
    combat_interface_snapshot,
    learned_action_presentations,
    normalize_shortcuts,
    shortcut_presentations,
)
from src.core.contracts import ActionAvailabilityCode, TimelineEntry


def _player() -> SimpleNamespace:
    firebolt = SimpleNamespace(
        ability_id="firebolt",
        passive=False,
        exploration_cast=False,
        cost=3,
        description="A compact fire spell.",
        weapon=False,
    )
    shield_bash = SimpleNamespace(
        ability_id="shield_bash",
        passive=False,
        exploration_cast=False,
        cost=0,
        description="A shield technique.",
        weapon=True,
    )
    return SimpleNamespace(
        spellbook={"Spells": {"Firebolt": firebolt}, "Skills": {"Shield Bash": shield_bash}},
        mana=SimpleNamespace(current=2),
        status_effects={},
        inventory={},
        anti_magic_active=False,
        action_bar_assignments=(),
        action_bar_autofill_complete=False,
        is_disarmed=lambda: False,
    )


def test_new_shortcuts_autofill_once_and_preserve_later_empty_slot():
    player = _player()

    assignments = normalize_shortcuts(player)

    assert len(assignments) == SHORTCUT_SLOT_COUNT
    assert assignments[:2] == (
        ActionReference(ActionReferenceKind.ABILITY, "firebolt"),
        ActionReference(ActionReferenceKind.ABILITY, "shield_bash"),
    )
    assign_shortcut(player, 0, None)

    assert normalize_shortcuts(player)[0] is None


def test_all_actions_keep_unavailable_learned_actions_visible_with_reason():
    player = _player()

    entries = learned_action_presentations(player)

    assert [entry.choice for entry in entries] == ["Firebolt", "Shield Bash"]
    assert entries[0].availability.code is ActionAvailabilityCode.INSUFFICIENT_MP
    assert "Not enough MP" in entries[0].display_label
    assert entries[1].enabled is True
    assert entries[0].icon_key == "spell_arcane"
    assert entries[1].icon_key == "skill_offense"


def test_rally_has_a_stable_reference_and_can_be_assigned_to_a_shortcut():
    """Legacy Python abilities need a stable identity for the shortcut editor."""
    player = _player()
    player.mana.current = 10
    player.spellbook["Skills"] = {"Rally": Rally()}

    rally = next(entry for entry in learned_action_presentations(player) if entry.choice == "Rally")
    assignments = assign_shortcut(player, 0, rally.reference)
    slot = shortcut_presentations(player)[0]

    assert rally.reference == ActionReference(ActionReferenceKind.ABILITY, "rally")
    assert assignments[0] == rally.reference
    assert slot.action is not None
    assert slot.action.choice == "Rally"


def test_engine_owned_target_scope_marks_single_target_action_without_a_target():
    player = _player()
    player.mana.current = 10
    engine = SimpleNamespace(
        target_scope_for_action=lambda _action, _choice: "single_opponent",
        encounter=SimpleNamespace(living_members=()),
    )

    entry = learned_action_presentations(player, engine=engine)[0]

    assert entry.availability.code is ActionAvailabilityCode.NO_LEGAL_TARGET
    assert "No legal target" in entry.display_label


def test_class_resource_actions_remain_visible_through_magic_suppression():
    player = _player()
    player.anti_magic_active = True
    player.spellbook["Skills"] = {
        "Brace": SimpleNamespace(
            ability_id="brace",
            passive=False,
            exploration_cast=False,
            cost=0,
            description="A Resolve technique.",
            resource_type="Resolve",
        )
    }

    entry = next(entry for entry in learned_action_presentations(player) if entry.choice == "Brace")

    assert entry.availability.code is ActionAvailabilityCode.AVAILABLE


def test_missing_item_shortcut_stays_visible_and_disabled():
    player = _player()
    player.action_bar_assignments = (
        ActionReference(ActionReferenceKind.ITEM, "Throwing Daggers"),
        None,
        None,
        None,
        None,
        None,
    )
    player.action_bar_autofill_complete = True

    slot = shortcut_presentations(player)[0]

    assert slot.action is not None
    assert slot.action.availability.code is ActionAvailabilityCode.MISSING_ITEM
    assert "unavailable" in slot.display_label.lower()


def test_snapshot_uses_engine_timeline_and_class_resource_provider(monkeypatch):
    player = _player()
    engine = SimpleNamespace(
        timeline_entries=lambda limit: (TimelineEntry("player", "Hero", 0.0),)[:limit],
        _focused_enemy=lambda: None,
    )
    monkeypatch.setattr(
        "src.core.classes.promotion_kits.status_summary_rows",
        lambda _player, _target: [("Resolve", "100/100 Guard ready")],
    )

    snapshot = combat_interface_snapshot(engine, player)

    assert snapshot.timeline == (TimelineEntry("player", "Hero", 0.0),)
    assert snapshot.resources[0].stable_key == "class_resource.resolve"
    assert snapshot.resources[0].ready is True
    assert len(snapshot.shortcuts) == SHORTCUT_SLOT_COUNT


def test_snapshot_exposes_active_environmental_effects(monkeypatch):
    player = _player()
    player.anti_magic_active = True
    engine = SimpleNamespace(timeline_entries=lambda _limit: (), _focused_enemy=lambda: None)
    monkeypatch.setattr(
        "src.core.classes.promotion_kits.status_summary_rows",
        lambda _player, _target: [],
    )

    snapshot = combat_interface_snapshot(engine, player)

    assert snapshot.environmental_effects[0].stable_key == "environment.anti_magic_field"
    assert snapshot.environmental_effects[0].icon_label == "AM"
