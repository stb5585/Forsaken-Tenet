#!/usr/bin/env python3
"""
Additional save-system coverage for serializers and SaveManager flows.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.core import abilities, companions, enemies, items, quest_progress, thieves_guild
from src.core.contracts import ActionReference, ActionReferenceKind
from src.core.save_system import (
    SAVE_SCHEMA_VERSION,
    AbilitySerializer,
    EnemyStateSerializer,
    ItemSerializer,
    PlayerDataSerializer,
    SaveCompatibilityStatus,
    SaveLoadCode,
    SaveManager,
    SaveValidationError,
    TileStateSerializer,
)
from tests.test_framework import TestGameState


def test_item_serializer_rejects_none_and_round_trips_accessory():
    ring_data = ItemSerializer.serialize(items.PowerRing())
    ring_data["typ"] = "Accessory"

    restored_ring = ItemSerializer.deserialize(ring_data)

    with pytest.raises(SaveValidationError, match="registered Item"):
        ItemSerializer.serialize(None)
    assert restored_ring.name == "Power Ring"


def test_item_serializer_rejects_unknown_id():
    with pytest.raises(SaveValidationError, match="unknown item id"):
        ItemSerializer.deserialize(
            {
                "item_id": "missing_item",
                "name": "Mystery Blade",
                "typ": "Weapon",
                "subtyp": "Sword",
            }
        )


def test_item_serializer_uses_canonical_name_not_cosmetic_theme_name():
    item = items.PowerRing()

    assert items.stat_themed_item_name(item) == "Mighty Power Ring"
    assert item.name == "Power Ring"
    assert ItemSerializer.serialize(item)["name"] == "Power Ring"


def test_item_serializer_round_trips_charge_based_tools():
    lockpick_kit = items.LockpickKit(charges=2)
    stolen_scroll = items.InscribedSpellScroll("Firebolt", charges=2)

    serialized_kit = ItemSerializer.serialize(lockpick_kit)
    serialized_scroll = ItemSerializer.serialize(stolen_scroll)
    restored_kit = ItemSerializer.deserialize(serialized_kit)
    restored_scroll = ItemSerializer.deserialize(serialized_scroll)

    assert serialized_kit["charges"] == 2
    assert restored_kit.name == "Lockpick Kit"
    assert restored_kit.charges == 2
    assert "Durability: 2" in restored_kit.description
    assert serialized_scroll["charges"] == 2
    assert restored_scroll.name == "Stolen Firebolt Scroll"
    assert restored_scroll.charges == 2


def test_ability_serializer_accepts_only_canonical_ids():
    heal = abilities.Heal()
    heal._class_name = "HealYaml"

    assert AbilitySerializer.serialize(heal) == "heal"
    assert AbilitySerializer.deserialize("heal_2").ability_id == "heal_2"
    assert AbilitySerializer.deserialize("") is None
    with pytest.raises(SaveValidationError, match="invalid ability id"):
        AbilitySerializer.deserialize("Heal2")
    with pytest.raises(SaveValidationError, match="invalid ability id"):
        AbilitySerializer.deserialize("Heal")


def test_enemy_state_serializer_round_trips_class_and_instance_state():
    goblin = enemies.Goblin()
    goblin.health.current = 7

    class_state = EnemyStateSerializer.serialize(enemies.Goblin)
    instance_state = EnemyStateSerializer.serialize(goblin)

    restored_class = EnemyStateSerializer.deserialize(class_state)
    restored_enemy = EnemyStateSerializer.deserialize(instance_state)

    assert restored_class is enemies.Goblin
    assert restored_enemy.name == "Goblin"
    assert restored_enemy.health.current == 7
    with pytest.raises(SaveValidationError, match="enemy_id"):
        EnemyStateSerializer.deserialize({"enemy_id": "missing_enemy"})


def test_tile_state_keeps_strict_enemy_state_without_runtime_encounter_state():
    tile = SimpleNamespace(
        visited=True,
        near=False,
        open=False,
        read=False,
        blocked=None,
        warped=False,
        defeated=False,
        enemy=enemies.Goblin(),
    )

    payload = TileStateSerializer.serialize_tile_state({(1, 2, 3): tile})
    state = payload["(1, 2, 3)"]

    assert state["enemy_state"]["enemy_id"] == "goblin"
    assert "encounter_state" not in state


def test_tile_state_restore_ignores_invalid_or_executable_position_keys(tmp_path):
    marker = tmp_path / "should_not_exist.txt"
    world = {
        (1, 2, 3): SimpleNamespace(visited=False, near=False, open=False),
        (4, 5, 6): SimpleNamespace(visited=False, near=False, open=False),
    }
    tile_states = {
        "(1, 2, 3)": {"visited": True, "open": True, "mystery": "legacy"},
        "(4, 5, 6)": "not-a-state-dict",
        "[1, 2, 3]": {"visited": False},
        "(1, 2)": {"visited": False},
        "(9, 9, 9)": {"visited": True},
        f"__import__('pathlib').Path({str(marker)!r}).write_text('bad')": {"visited": False},
    }

    assert TileStateSerializer.summarize_tile_state_payload(world, tile_states) == {
        "total_entries": 6,
        "valid_entries": 1,
        "malformed_position_count": 3,
        "malformed_state_count": 1,
        "missing_world_position_count": 1,
        "restorable_attribute_counts": {"open": 1, "visited": 1},
        "unknown_attribute_count": 1,
        "unknown_attribute_keys": ("mystery",),
    }
    assert TileStateSerializer.summarize_tile_state_payload(world, None) == {
        "total_entries": 0,
        "valid_entries": 0,
        "malformed_position_count": 0,
        "malformed_state_count": 0,
        "missing_world_position_count": 0,
        "restorable_attribute_counts": {},
        "unknown_attribute_count": 0,
        "unknown_attribute_keys": (),
    }

    TileStateSerializer.restore_tile_state(world, tile_states)

    assert world[(1, 2, 3)].visited is True
    assert world[(1, 2, 3)].open is True
    assert world[(4, 5, 6)].visited is False
    assert not marker.exists()


def test_player_data_deserialize_marks_killed_boss_tiles_defeated_without_world_state(monkeypatch):
    player = TestGameState.create_player(
        name="BossSlayer", class_name="Warrior", race_name="Human", level=12
    )
    player.kill_dict = {"Boss": {"Minotaur": 1}}
    serialized = PlayerDataSerializer.serialize(player)
    serialized.pop("world_state", None)

    class DummyTile:
        def __init__(self, enemy=None):
            self.enemy = enemy
            self.defeated = False

    def fake_load_tiles(self):
        self.world_dict = {
            (1, 1, 0): DummyTile(enemy=SimpleNamespace(name="Minotaur")),
            (2, 2, 0): DummyTile(enemy=SimpleNamespace(name="Goblin")),
        }

    monkeypatch.setattr("src.core.player.Player.load_tiles", fake_load_tiles)

    restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=False)

    assert restored.world_dict[(1, 1, 0)].defeated is True
    assert restored.world_dict[(1, 1, 0)].enemy is None
    assert restored.world_dict[(2, 2, 0)].defeated is False


def test_player_data_serializer_round_trips_bestiary_records():
    player = TestGameState.create_player(
        name="Scout", class_name="Warrior", race_name="Human", level=12
    )
    player.bestiary = {
        "Seen Only": {
            "name": "Seen Only",
            "type": "Regular",
            "seen_count": 3,
            "details_unlocked": False,
        },
        "Goblin": {
            "name": "Goblin",
            "type": "Regular",
            "seen_count": 1,
            "details_unlocked": True,
            "difficulty_level": 1,
            "resistances": {"Fire": 0.25},
            "known_abilities": ["Hex"],
            "features": ["Sight"],
        },
    }

    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(player), skip_tiles=True
    )

    assert restored.bestiary == player.bestiary


def test_player_data_serializer_round_trips_summons():
    player = TestGameState.create_player(
        name="Thaumaturgist",
        class_name="Thaumaturgist",
        race_name="Human",
        level=12,
    )
    summon = companions.Patagon()
    summon.initialize_stats(player)
    summon.health.current = max(1, summon.health.max - 7)
    summon.mana.current = max(0, summon.mana.max - 3)
    summon.level.level = 3
    summon.level.exp = 123
    player.summons["Patagon"] = summon

    serialized = PlayerDataSerializer.serialize(player)
    restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

    assert "Patagon" in serialized["summons"]
    assert "Patagon" in restored.summons
    restored_summon = restored.summons["Patagon"]
    assert restored_summon.name == "Patagon"
    assert restored_summon.health.current == summon.health.current
    assert restored_summon.mana.current == summon.mana.current
    assert restored_summon.level.level == 3
    assert restored_summon.level.exp == 123


def test_player_data_serializer_round_trips_xenid_spellbook_sections():
    player = TestGameState.create_player(
        name="Thaumaturgist",
        class_name="Thaumaturgist",
        race_name="Human",
        level=12,
    )
    summon = companions.Seraphim()
    summon.initialize_stats(player)
    player.summons["Seraphim"] = summon

    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(player),
        skip_tiles=True,
    )

    assert "Smite" in restored.summons["Seraphim"].spellbook["Spells"]
    assert "Shield Slam" in restored.summons["Seraphim"].spellbook["Skills"]


def test_player_data_deserialize_does_not_grant_an_unselected_xenid():
    player = TestGameState.create_player(
        name="Thaumaturgist",
        class_name="Thaumaturgist",
        race_name="Human",
        level=12,
    )
    serialized = PlayerDataSerializer.serialize(player)
    serialized.pop("summons", None)

    restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

    assert restored.summons == {}


def test_player_data_deserialize_deactivates_funhouse_teleporter_for_existing_jester_save(
    monkeypatch,
):
    player = TestGameState.create_player(
        name="JesterSlayer", class_name="Warrior", race_name="Human", level=12
    )
    player.kill_dict = {"Boss": {"Jester": 1}}
    serialized = PlayerDataSerializer.serialize(player)
    serialized["world_state"] = {
        "(11, 0, 4)": {
            "visited": True,
            "near": True,
            "active": True,
        }
    }

    class FunhouseTeleporter:
        def __init__(self):
            self.visited = False
            self.near = False
            self.active = True

    def fake_load_tiles(self):
        self.world_dict = {(11, 0, 4): FunhouseTeleporter()}

    monkeypatch.setattr("src.core.player.Player.load_tiles", fake_load_tiles)

    restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=False)

    teleporter = restored.world_dict[(11, 0, 4)]
    assert teleporter.visited is True
    assert teleporter.active is False


def test_player_data_deserialize_migrates_jester_tokens_to_special_inventory():
    player = TestGameState.create_player(
        name="TokenTester", class_name="Warrior", race_name="Human", level=12
    )
    player.inventory = {"Jester Token": [items.JesterToken() for _ in range(2)]}
    serialized = PlayerDataSerializer.serialize(player)

    restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

    assert "Jester Token" not in restored.inventory
    assert len(restored.special_inventory["Jester Token"]) == 2


def test_player_data_deserialize_replaces_legacy_holy_relics_by_relic_count():
    relic_items = [
        ("Triangulus", items.Relic1()),
        ("Quadrata", items.Relic2()),
        ("Hexagonum", items.Relic3()),
        ("Luna", items.Relic4()),
        ("Polaris", items.Relic5()),
        ("Infinitas", items.Relic6()),
    ]
    cases = [
        (0, False, False, quest_progress.UNCERTAIN_REPORTS, False, False),
        (1, False, False, quest_progress.HOLY_RELICS, False, False),
        (5, False, False, quest_progress.HOLY_RELICS, False, False),
        (6, False, False, quest_progress.HOLY_RELICS, True, False),
        (6, True, True, quest_progress.HOLY_RELICS, True, True),
    ]

    for (
        count,
        old_completed,
        old_turned_in,
        expected_name,
        expected_completed,
        expected_turned_in,
    ) in cases:
        player = TestGameState.create_player(
            name=f"Relic{count}",
            class_name="Warrior",
            race_name="Human",
            level=30,
        )
        player.special_inventory = {name: [item] for name, item in relic_items[:count]}
        player.quest_dict["Main"][quest_progress.HOLY_RELICS] = {
            "Who": "Sergeant",
            "Type": "Collect",
            "What": "Relics",
            "Total": 6,
            "Reward": [],
            "Reward Number": 1,
            "Experience": 500000,
            "Completed": old_completed,
            "Turned In": old_turned_in,
        }

        restored = PlayerDataSerializer.deserialize(
            PlayerDataSerializer.serialize(player), skip_tiles=True
        )

        assert list(restored.quest_dict["Main"]) == [expected_name]
        restored_quest = restored.quest_dict["Main"][expected_name]
        assert restored_quest["Completed"] is expected_completed
        assert restored_quest["Turned In"] is expected_turned_in
        if expected_name == quest_progress.HOLY_RELICS:
            assert restored_quest["Stage"] == "collecting"
        else:
            assert restored_quest["Stage"] == "investigate"


def test_save_manager_round_trip_list_and_delete(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))

    player = TestGameState.create_player(
        name="Saver", class_name="Warrior", race_name="Human", level=10
    )

    assert SaveManager.save_player(player, "hero.save") is True
    assert SaveManager.save_player(player, "alpha.save") is True
    (save_dir / "hero.save.tmp").write_text("partial", encoding="utf-8")
    (save_dir / "directory.save").mkdir()
    assert "hero.save" in SaveManager.list_saves()
    assert SaveManager.list_saves() == ["alpha.save", "hero.save"]

    restored = SaveManager.load_player("hero.save", skip_tiles=True)
    assert restored is not None
    assert restored.name == "Saver"

    assert SaveManager.save_player(player, "hero.tmp", is_tmp=True) is True
    restored_tmp = SaveManager.load_player("hero.tmp", is_tmp=True, skip_tiles=True)
    assert restored_tmp is not None
    assert restored_tmp.name == "Saver"

    assert SaveManager.delete_save("hero.save") is True
    assert SaveManager.load_player("hero.save", skip_tiles=True) is None


def test_save_manager_rejects_unmarked_save_and_reports_new_game_status(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))
    SaveManager.ensure_dirs()
    (save_dir / "legacy.save").write_text(json.dumps({"name": "Old Hero"}), encoding="utf-8")

    metadata = SaveManager.describe_save_file("legacy.save")
    result = SaveManager.load_player_result("legacy.save", skip_tiles=True)

    assert metadata["compatibility_status"] is SaveCompatibilityStatus.PRE_FOUNDATION
    assert metadata["schema_version"] is None
    assert metadata["loadable"] is False
    assert "Start a new game" in metadata["status_message"]
    assert result.player is None
    assert result.code is SaveLoadCode.INCOMPATIBLE_SCHEMA
    assert result.error is not None and "Start a new game" in result.error


def test_version_two_save_round_trips_typed_action_bar_references(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))
    player = TestGameState.create_player(
        name="Shortcut Saver", class_name="Warrior", race_name="Human", level=10
    )
    player.action_bar_assignments = (
        ActionReference(ActionReferenceKind.ABILITY, "true_strike"),
        None,
        ActionReference(ActionReferenceKind.ITEM, "MissingFutureItem"),
    )

    assert SaveManager.save_player(player, "shortcuts.save") is True
    payload = json.loads((save_dir / "shortcuts.save").read_text(encoding="utf-8"))
    restored = SaveManager.load_player("shortcuts.save", skip_tiles=True)

    assert payload["schema_version"] == SAVE_SCHEMA_VERSION == 2
    assert len(payload["action_bar_assignments"]) == 6
    assert restored is not None
    assert restored.action_bar_assignments == (
        ActionReference(ActionReferenceKind.ABILITY, "true_strike"),
        None,
        ActionReference(ActionReferenceKind.ITEM, "MissingFutureItem"),
        None,
        None,
        None,
    )


@pytest.mark.parametrize(
    ("path", "bad_value", "error_fragment"),
    [
        (("class_id",), "missing_class", "unknown class id"),
        (("race_id",), "missing_race", "unknown race id"),
        (("equipment", "Weapon", "item_id"), "missing_item", "unknown item id"),
    ],
)
def test_version_two_rejects_unknown_registered_ids_atomically(
    monkeypatch,
    tmp_path,
    path,
    bad_value,
    error_fragment,
):
    save_dir = tmp_path / "saves"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_path / "tmp"))
    player = TestGameState.create_player(class_name="Warrior", race_name="Human")
    assert SaveManager.save_player(player, "invalid-id.save") is True

    save_path = save_dir / "invalid-id.save"
    payload = json.loads(save_path.read_text(encoding="utf-8"))
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = bad_value
    save_path.write_text(json.dumps(payload), encoding="utf-8")
    before = save_path.read_text(encoding="utf-8")

    result = SaveManager.load_player_result("invalid-id.save", skip_tiles=True)

    assert result.player is None
    assert result.code is SaveLoadCode.INVALID_DATA
    assert result.error is not None and error_fragment in result.error
    assert save_path.read_text(encoding="utf-8") == before


def test_save_manager_round_trip_preserves_old_key_counts(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))

    player = TestGameState.create_player(
        name="KeySaver", class_name="Warrior", race_name="Human", level=10
    )
    player.inventory = {"Old Key": [items.OldKey() for _ in range(5)]}

    assert SaveManager.save_player(player, "keys.save") is True
    restored = SaveManager.load_player("keys.save", skip_tiles=True)

    assert restored is not None
    assert "Old Key" in restored.inventory
    assert len(restored.inventory["Old Key"]) == 5
    assert all(item.name == "Old Key" for item in restored.inventory["Old Key"])


def test_player_data_preserves_and_defaults_thieves_guild_state():
    player = TestGameState.create_player(
        name="GuildSaver", class_name="Rogue", race_name="Human", level=10
    )
    player.thieves_guild = {
        "member": True,
        "trial_started": True,
        "trial_branch": "cutpurse",
        "starter_kit_claimed": True,
    }

    serialized = PlayerDataSerializer.serialize(player)
    restored = PlayerDataSerializer.deserialize(serialized, skip_tiles=True)

    assert restored.thieves_guild == player.thieves_guild

    legacy_data = dict(serialized)
    legacy_data.pop("thieves_guild")
    legacy_restored = PlayerDataSerializer.deserialize(legacy_data, skip_tiles=True)

    assert legacy_restored.thieves_guild == thieves_guild.default_state()


def test_load_player_rejects_missing_equipment_slots(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))

    player = TestGameState.create_player(
        name="SlotSaver", class_name="Warrior", race_name="Human", level=10
    )
    assert SaveManager.save_player(player, "slots.save") is True

    save_path = save_dir / "slots.save"
    data = json.loads(save_path.read_text(encoding="utf-8"))
    for slot in ("Weapon", "OffHand", "Armor", "Helmet", "Ring", "Pendant"):
        data["equipment"].pop(slot, None)
    save_path.write_text(json.dumps(data), encoding="utf-8")

    before = save_path.read_text(encoding="utf-8")
    result = SaveManager.load_player_result("slots.save", skip_tiles=True)

    assert result.player is None
    assert result.code is SaveLoadCode.INVALID_DATA
    assert result.error is not None and "missing required slots" in result.error
    assert save_path.read_text(encoding="utf-8") == before


def test_save_manager_describes_save_files_with_schema_status(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))
    SaveManager.ensure_dirs()

    (save_dir / "hero.save").write_text("{not json", encoding="utf-8")
    (save_dir / "folder.save").mkdir()
    (tmp_dir / "hero.tmp").write_text("tmp", encoding="utf-8")

    assert SaveManager.describe_save_file("hero.save") == {
        "filename": "hero.save",
        "is_tmp": False,
        "valid": True,
        "expected_extension": ".save",
        "extension_matches_expected": True,
        "path": str(save_dir / "hero.save"),
        "exists": True,
        "is_file": True,
        "is_dir": False,
        "loadable": False,
        "size": len("{not json"),
        "empty": False,
        "schema_version": None,
        "compatibility_status": SaveCompatibilityStatus.UNREADABLE,
        "status_message": "Save file is unreadable or corrupted.",
    }
    assert SaveManager.describe_save_file("missing.save") == {
        "filename": "missing.save",
        "is_tmp": False,
        "valid": True,
        "expected_extension": ".save",
        "extension_matches_expected": True,
        "path": str(save_dir / "missing.save"),
        "exists": False,
        "is_file": False,
        "is_dir": False,
        "loadable": False,
        "size": None,
        "empty": False,
        "schema_version": None,
        "compatibility_status": SaveCompatibilityStatus.NOT_A_FILE,
        "status_message": "Save file not found.",
    }
    assert SaveManager.describe_save_file("folder.save")["is_dir"] is True
    assert SaveManager.describe_save_file("folder.save")["loadable"] is False
    assert SaveManager.describe_save_file("hero.tmp", is_tmp=True)["path"] == str(
        tmp_dir / "hero.tmp"
    )
    assert (
        SaveManager.describe_save_file("hero.tmp", is_tmp=True)["extension_matches_expected"]
        is True
    )
    assert (
        SaveManager.describe_save_file("hero.tmp", is_tmp=False)["extension_matches_expected"]
        is False
    )
    assert SaveManager.describe_save_file("../outside.save") == {
        "filename": "../outside.save",
        "is_tmp": False,
        "valid": False,
        "expected_extension": ".save",
        "extension_matches_expected": False,
        "path": None,
        "exists": False,
        "is_file": False,
        "is_dir": False,
        "loadable": False,
        "size": None,
        "empty": False,
        "schema_version": None,
        "compatibility_status": SaveCompatibilityStatus.INVALID_NAME,
        "status_message": "Invalid save filename.",
    }


def test_save_manager_lists_metadata_for_visible_save_files(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))
    SaveManager.ensure_dirs()

    zeta_payload = json.dumps({"schema_version": SAVE_SCHEMA_VERSION, "name": "zeta"})
    alpha_payload = json.dumps({"schema_version": SAVE_SCHEMA_VERSION, "name": "alpha"})
    (save_dir / "zeta.save").write_text(zeta_payload, encoding="utf-8")
    (save_dir / "alpha.save").write_text(alpha_payload, encoding="utf-8")
    (save_dir / "empty.save").write_text("", encoding="utf-8")
    (save_dir / "alpha.save.tmp").write_text("partial", encoding="utf-8")
    (save_dir / "folder.save").mkdir()

    metadata = SaveManager.list_save_metadata()

    assert [entry["filename"] for entry in metadata] == ["alpha.save", "empty.save", "zeta.save"]
    assert [entry["size"] for entry in metadata] == [len(alpha_payload), 0, len(zeta_payload)]
    assert [entry["empty"] for entry in metadata] == [False, True, False]
    assert all(entry["valid"] and entry["is_file"] for entry in metadata)
    assert all(not entry["is_tmp"] for entry in metadata)
    assert all(entry["extension_matches_expected"] for entry in metadata)
    assert [entry["loadable"] for entry in metadata] == [True, False, True]
    assert SaveManager.summarize_save_metadata() == {
        "visible_count": 3,
        "visible_filenames": ["alpha.save", "empty.save", "zeta.save"],
        "loadable_count": 2,
        "total_size": len(alpha_payload) + len(zeta_payload),
        "empty_save_count": 1,
        "largest_save": "alpha.save",
        "largest_size": len(alpha_payload),
    }
    (save_dir / "notes.txt").write_text("ignore me", encoding="utf-8")
    assert SaveManager.summarize_save_directory() == {
        "visible_count": 3,
        "visible_filenames": ["alpha.save", "empty.save", "zeta.save"],
        "tmp_leftover_count": 1,
        "tmp_leftover_filenames": ["alpha.save.tmp"],
        "directory_entry_count": 1,
        "directory_entry_filenames": ["folder.save"],
        "ignored_entry_count": 1,
        "ignored_filenames": ["notes.txt"],
        "hidden_entry_count": 3,
    }

    (save_dir / "alpha.save").unlink()
    (save_dir / "zeta.save").unlink()
    (save_dir / "empty.save").unlink()
    assert SaveManager.summarize_save_metadata() == {
        "visible_count": 0,
        "visible_filenames": [],
        "loadable_count": 0,
        "total_size": 0,
        "empty_save_count": 0,
        "largest_save": None,
        "largest_size": None,
    }


def test_save_manager_rejects_path_components(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))

    player = TestGameState.create_player(
        name="Traveler", class_name="Warrior", race_name="Human", level=10
    )

    assert SaveManager.is_valid_save_filename("hero.save") is True
    assert SaveManager.is_valid_save_filename("hero.tmp") is True
    assert SaveManager.is_valid_save_filename("../outside.save") is False
    assert SaveManager.is_valid_save_filename("nested/hero.save") is False
    assert SaveManager.is_valid_save_filename("nested\\hero.save") is False
    assert SaveManager.is_valid_save_filename(str(tmp_path / "hero.save")) is False
    assert SaveManager.is_valid_save_filename("   ") is False
    assert SaveManager.is_valid_save_filename(".") is False
    assert SaveManager.is_valid_save_filename("..") is False
    assert SaveManager.is_valid_save_filename(None) is False
    assert SaveManager.is_valid_save_filename(42) is False

    assert SaveManager.save_player(player, "../outside.save") is False
    assert SaveManager.load_player("../outside.save", skip_tiles=True) is None
    assert SaveManager.delete_save("../outside.save") is False
    assert SaveManager.save_player(player, "   ") is False
    assert SaveManager.load_player("   ", skip_tiles=True) is None
    assert SaveManager.delete_save("   ") is False
    assert not (tmp_path / "outside.save").exists()
    assert not (save_dir / "   ").exists()

    (save_dir / "folder.save").mkdir(parents=True)
    (tmp_dir / "folder.tmp").mkdir(parents=True)
    assert SaveManager.load_player("folder.save", skip_tiles=True) is None
    assert SaveManager.load_player("folder.tmp", is_tmp=True, skip_tiles=True) is None
    assert SaveManager.delete_save("folder.save") is False
    assert (save_dir / "folder.save").is_dir()
    assert (tmp_dir / "folder.tmp").is_dir()


def test_save_manager_failed_atomic_write_preserves_existing_save(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))

    stable_player = TestGameState.create_player(
        name="Stable", class_name="Warrior", race_name="Human", level=10
    )
    broken_player = TestGameState.create_player(
        name="Broken", class_name="Warrior", race_name="Human", level=10
    )
    assert SaveManager.save_player(stable_player, "hero.save") is True

    def failing_dump(_data, file_obj, *args, **kwargs):
        file_obj.write('{"partial":')
        raise TypeError("dump fail")

    monkeypatch.setattr("src.core.save_system.json.dump", failing_dump)

    assert SaveManager.save_player(broken_player, "hero.save") is False
    assert not (save_dir / "hero.save.tmp").exists()
    with open(save_dir / "hero.save", "r") as file_obj:
        saved_data = json.load(file_obj)
    assert saved_data["name"] == "Stable"


def test_atomic_writer_rejects_non_json_state_without_replacing_save(tmp_path):
    """Unsupported runtime objects must not be stringified into the save schema."""
    save_path = tmp_path / "hero.save"
    save_path.write_text('{"name": "Stable"}', encoding="utf-8")

    with pytest.raises(TypeError):
        SaveManager._write_json_atomic(str(save_path), {"unsupported": object()})

    assert json.loads(save_path.read_text(encoding="utf-8")) == {"name": "Stable"}
    assert not (tmp_path / "hero.save.tmp").exists()


def test_save_manager_file_round_trip_restores_mutable_tile_state(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))

    door_pos = (1, 2, 0)
    boss_pos = (3, 4, 0)
    player = TestGameState.create_player(
        name="TileSaver", class_name="Warrior", race_name="Human", level=10
    )
    player.world_dict = {
        door_pos: SimpleNamespace(
            visited=True,
            near=True,
            open=True,
            read=True,
            blocked="north",
            warped=True,
            active=False,
        ),
        boss_pos: SimpleNamespace(
            visited=True,
            near=False,
            open=False,
            read=False,
            blocked=None,
            warped=False,
            defeated=True,
            enemy=enemies.Goblin(),
        ),
    }

    def fake_load_tiles(self):
        self.world_dict = {
            door_pos: SimpleNamespace(
                visited=False,
                near=False,
                open=False,
                read=False,
                blocked=None,
                warped=False,
                active=True,
            ),
            boss_pos: SimpleNamespace(
                visited=False,
                near=False,
                open=False,
                read=False,
                blocked=None,
                warped=False,
                defeated=False,
                enemy=enemies.Goblin(),
            ),
        }

    monkeypatch.setattr("src.core.player.Player.load_tiles", fake_load_tiles)

    assert SaveManager.save_player(player, "tiles.save") is True
    restored = SaveManager.load_player("tiles.save", skip_tiles=False)

    restored_door = restored.world_dict[door_pos]
    restored_boss = restored.world_dict[boss_pos]
    assert restored_door.visited is True
    assert restored_door.near is True
    assert restored_door.open is True
    assert restored_door.read is True
    assert restored_door.blocked == "north"
    assert restored_door.warped is True
    assert restored_door.active is False
    assert restored_boss.defeated is True
    assert restored_boss.enemy is None


def test_save_manager_returns_false_or_none_on_failures(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))

    player = TestGameState.create_player(
        name="Broken", class_name="Warrior", race_name="Human", level=10
    )

    monkeypatch.setattr(
        "src.core.save_system.json.dump",
        lambda *args, **kwargs: (_ for _ in ()).throw(TypeError("dump fail")),
    )
    assert SaveManager.save_player(player, "broken.save") is False

    assert SaveManager.load_player("missing.save", skip_tiles=True) is None
    assert SaveManager.delete_save("missing.save") is False


def test_save_manager_corrupt_json_load_returns_none_without_deleting_file(monkeypatch, tmp_path):
    save_dir = tmp_path / "saves"
    tmp_dir = tmp_path / "tmp"
    monkeypatch.setattr(SaveManager, "SAVE_DIR", str(save_dir))
    monkeypatch.setattr(SaveManager, "TMP_DIR", str(tmp_dir))
    SaveManager.ensure_dirs()

    save_path = save_dir / "corrupt.save"
    tmp_path_file = tmp_dir / "corrupt.tmp"
    save_path.write_text("{bad json", encoding="utf-8")
    tmp_path_file.write_text("{bad json", encoding="utf-8")

    assert SaveManager.load_player("corrupt.save", skip_tiles=True) is None
    assert SaveManager.load_player("corrupt.tmp", is_tmp=True, skip_tiles=True) is None
    assert save_path.read_text(encoding="utf-8") == "{bad json"
    assert tmp_path_file.read_text(encoding="utf-8") == "{bad json"
