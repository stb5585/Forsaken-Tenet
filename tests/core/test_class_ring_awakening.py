"""Coverage for legacy Class Ring awakening state and mechanics."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.core import abilities, items
from src.core.classes import archdruid, class_rings, demonologist, grandmaster, paladin
from src.core.combat.battle_engine import BattleEngine
from src.core.save_system import PlayerDataSerializer
from tests.test_framework import TestGameState


def _player_with_class_ring(class_name, **kwargs):
    player = TestGameState.create_player(class_name=class_name, race_name="Human", **kwargs)
    ring = items.ClassRing()
    player.equipment["Ring"] = ring
    return player, ring


def test_legacy_class_ring_defaults_to_dormant_description_and_mod():
    player, ring = _player_with_class_ring("Berserker")

    ring.class_mod(player)

    assert player.class_ring_awakening["awakened"]["Berserker"] is False
    assert player.equipment["Ring"].mod == "Dormant Bloodied Crits"
    description = ring.get_description(player)
    assert "Ring location: equipped" in description
    assert "Town-visible: yes" in description
    assert "Activation: No Healing Duel" in description
    assert "Active effect: inactive until awakened" in description


def test_class_ring_presentation_state_names_presence_visibility_and_active_effects():
    no_ring = TestGameState.create_player(class_name="Wizard", race_name="Human")
    no_ring.equipment["Ring"] = items.NoRing()
    no_ring.inventory = {}
    no_ring.storage = {}

    missing = class_rings.presentation_state(no_ring)
    assert missing["location"] == "not present"
    assert missing["town_visible"] is False
    assert missing["effect_active"] is False

    inventory_only = TestGameState.create_player(class_name="Wizard", race_name="Human")
    inventory_only.equipment["Ring"] = items.NoRing()
    inventory_only.inventory = {"Class Ring": [items.ClassRing()]}
    inventory_only.storage = {}

    inventory_state = class_rings.presentation_state(inventory_only)
    assert inventory_state["location"] == "inventory only"
    assert inventory_state["town_visible"] is False
    assert inventory_state["equipped"] is False

    stored = TestGameState.create_player(class_name="Wizard", race_name="Human")
    stored.equipment["Ring"] = items.NoRing()
    stored.inventory = {}
    stored.storage = {"Class Ring": [items.ClassRing()]}

    stored_state = class_rings.presentation_state(stored)
    assert stored_state["location"] == "stored"
    assert stored_state["town_visible"] is True
    assert stored_state["effect_active"] is False
    assert "Ring location: stored" in stored.storage["Class Ring"][0].get_description(stored)

    equipped, ring = _player_with_class_ring("Wizard")
    equipped_state = class_rings.presentation_state(equipped)
    assert equipped_state["location"] == "equipped"
    assert equipped_state["town_visible"] is True
    assert equipped_state["effect_active"] is False
    assert "Active effect: inactive until awakened" in ring.get_description(equipped)

    equipped.awaken_class_ring()
    awakened_state = class_rings.presentation_state(equipped)
    assert awakened_state["state"] == "awakened"
    assert awakened_state["effect_active"] is True
    assert "Active effect: active while equipped" in ring.get_description(equipped)


def test_class_voluntas_identity_summarizes_ring_visibility_and_state():
    no_ring = TestGameState.create_player(class_name="Berserker", race_name="Human")
    no_ring.equipment["Ring"] = items.NoRing()

    hidden = class_rings.class_voluntas_identity(no_ring)

    assert hidden["class_name"] == "Berserker"
    assert hidden["visible"] is False
    assert hidden["location"] == "not present"
    assert hidden["town_visible"] is False
    assert hidden["equipped"] is False
    assert hidden["effect_active"] is False
    assert hidden["awakened"] is False
    assert hidden["activation"] == "No Healing Duel"
    assert hidden["mod"] == "Dormant Bloodied Crits"
    assert "Ring location: not present" in hidden["description"]

    dormant, _ring = _player_with_class_ring("Wizard")
    dormant_identity = class_rings.class_voluntas_identity(dormant)

    assert dormant_identity["visible"] is True
    assert dormant_identity["location"] == "equipped"
    assert dormant_identity["effect_active"] is False
    assert dormant_identity["awakened"] is False
    assert dormant_identity["activation"] == "Four Formulae"
    assert dormant_identity["mod"] == "Dormant School Streak"
    assert "dormant Class Ring for a Wizard" in dormant_identity["description"]
    assert "Active effect: inactive until awakened" in dormant_identity["description"]

    awakened, _ring = _player_with_class_ring("Wizard")
    awakened.awaken_class_ring()
    awakened_identity = class_rings.class_voluntas_identity(awakened)

    assert awakened_identity["visible"] is True
    assert awakened_identity["location"] == "equipped"
    assert awakened_identity["effect_active"] is True
    assert awakened_identity["awakened"] is True
    assert awakened_identity["mod"] == "School Streak"
    assert "awakened Class Ring for a Wizard" in awakened_identity["description"]
    assert "Active effect: active while equipped" in awakened_identity["description"]

    unknown = SimpleNamespace(
        cls=SimpleNamespace(name="Chronomancer"),
        equipment={"Ring": items.ClassRing()},
        storage={},
    )
    unknown_identity = class_rings.class_voluntas_identity(unknown)

    assert unknown_identity["class_name"] == "Chronomancer"
    assert unknown_identity["visible"] is True
    assert unknown_identity["awakened"] is False
    assert unknown_identity["activation"] == "Quest Awakening"
    assert unknown_identity["mod"] == "Special"
    assert "changes depending on" in unknown_identity["description"]
    assert "wearer's specialty" in unknown_identity["description"]


def test_class_voluntas_identity_uses_special_system_awakening_state():
    grandmaster_player, _ring = _player_with_class_ring("Grandmaster of Arms")
    grandmaster.bind_weapon(grandmaster_player, "Sword")

    grandmaster_identity = class_rings.class_voluntas_identity(grandmaster_player)

    assert grandmaster_identity["awakened"] is True
    assert grandmaster_identity["effect_active"] is True
    assert "bound to Sword Discipline" in grandmaster_identity["description"]

    demonologist_player, _ring = _player_with_class_ring("Demonologist")
    demonologist_player.familiar = SimpleNamespace(name="Aegis", race="Homunculus", spec="Defense")
    demonologist.awaken_ring(demonologist_player)

    demonologist_identity = class_rings.class_voluntas_identity(demonologist_player)

    assert demonologist_identity["awakened"] is True
    assert demonologist_identity["effect_active"] is True
    assert "Imprisoned echo: Homunculus" in demonologist_identity["description"]

    archdruid_player, _ring = _player_with_class_ring("Archdruid")
    state = archdruid_player.ensure_archdruid_attunement()
    state["ring_awakened"] = True
    state["aspects"] = {affinity: True for affinity in archdruid.AFFINITIES}
    state["attunement"] = {affinity: 75 for affinity in archdruid.AFFINITIES}
    archdruid_player.archdruid_attunement = state

    archdruid_identity = class_rings.class_voluntas_identity(archdruid_player)

    assert archdruid_identity["awakened"] is True
    assert archdruid_identity["effect_active"] is True
    assert "Current Harmony Bonus: +24%" in archdruid_identity["description"]


def test_berserker_bloodied_crits_and_weapon_damage_require_awakening():
    player, ring = _player_with_class_ring("Berserker", health=(100, 20))
    ring.class_mod(player)
    dormant_crit = player.critical_chance("Weapon")
    dormant_weapon = player.check_mod("weapon")

    ok, _ = player.awaken_class_ring()
    ring.class_mod(player)

    assert ok is True
    assert player.critical_chance("Weapon") >= dormant_crit + 0.14
    assert player.check_mod("weapon") > dormant_weapon
    assert player.equipment["Ring"].mod == "Bloodied Crits"


def test_no_healing_duel_fails_when_player_restores_hp():
    player, _ring = _player_with_class_ring("Berserker", health=(100, 30))
    player.change_location(0, 0, 1)
    player.inventory = {"Health Potion": [items.HealthPotion()]}
    enemy = SimpleNamespace(
        name="Trial Champion",
        health=SimpleNamespace(current=50, max=50),
        mana=SimpleNamespace(current=0, max=1),
        effects=lambda end=False: "",
        is_alive=lambda: True,
        class_ring_trial_enemy=True,
        class_ring_trial_name="No Healing Duel",
        class_ring_no_healing_duel=True,
    )
    tile = SimpleNamespace(available_actions=lambda _player: ["Attack", "Use Item"])
    engine = BattleEngine(player, enemy, tile)
    engine.attacker = player
    engine.defender = enemy

    result = engine.execute_intent(engine.prepare_intent("Use Item", "Health Potion"))
    outcome = engine.end_battle()

    assert "rejects restored life" in result.message
    assert outcome.result == "defeat"
    assert player.health.current == 1
    assert player.in_town() is False


def test_dragoon_jump_mod_stays_dormant_until_guard_the_fall():
    player, ring = _player_with_class_ring("Dragoon")
    jump = abilities.Jump()

    ring.class_mod(player)
    dormant_max = jump.get_max_active_modifications(player)
    assert player.equipment["Ring"].mod == "Dormant Aerial Supremacy"

    ok, _ = player.awaken_class_ring()
    ring.class_mod(player)

    assert ok is True
    assert player.equipment["Ring"].mod == "Aerial Supremacy"
    assert jump.get_max_active_modifications(player) == dormant_max


def test_knight_enchanter_weave_memory_replaces_mana_tap_plus_display():
    player, ring = _player_with_class_ring("Knight Enchanter")

    ring.class_mod(player)
    assert player.equipment["Ring"].mod == "Dormant Weave Memory"

    ok, _ = player.awaken_class_ring()
    ring.class_mod(player)

    assert ok is True
    assert player.equipment["Ring"].mod == "Weave Memory"


def test_thaumaturgist_conduit_ritual_sacrifices_hp_and_empowers_xenids():
    player, ring = _player_with_class_ring("Thaumaturgist", health=(200, 200))

    ok, _ = player.awaken_class_ring()
    ring.class_mod(player)

    assert ok is True
    assert player.health.max == 190
    assert player.health.current == 190
    assert player.equipment["Ring"].mod == "+30% Xenids"
    assert class_rings.summon_multiplier(player) == 1.30


def test_crusader_activation_requires_and_affirms_paladin_vow():
    player, ring = _player_with_class_ring("Crusader")

    ok, message = player.awaken_class_ring()

    assert ok is False
    assert "requires a sworn Paladin vow" in message

    player.choose_paladin_vow("Redemption")
    paladin.trigger_aura(player, "Redemption")
    dormant_rate = paladin.encounter_rate_multiplier(player)

    ok, message = player.awaken_class_ring()
    ring.class_mod(player)

    assert ok is True
    assert "Vow Trial" in message
    assert ring.mod == "Vow Affirmation"
    assert player.class_ring_awakening["data"]["Crusader"]["vow"] == "Redemption"
    assert paladin.encounter_rate_multiplier(player) < dormant_rate


def test_archbishop_intervention_and_reset_combat_flags():
    player, _ring = _player_with_class_ring("Archbishop", health=(100, 40))
    player.awaken_class_ring()
    rng = SimpleNamespace(random=lambda: 0.0)

    healed = class_rings.divine_intervention(player, rng=rng)
    second = class_rings.divine_intervention(player, rng=rng)

    assert healed == 25
    assert second == 0
    class_rings.reset_combat_flags(player)
    player.health.current = 40
    assert class_rings.divine_intervention(player, rng=rng) == 25


def test_rogue_loaded_dice_and_seeker_hidden_cache():
    rogue, _ring = _player_with_class_ring("Rogue")
    rogue.awaken_class_ring()
    assert class_rings.loaded_dice_succeeds(rogue, rng=SimpleNamespace(random=lambda: 0.14))

    seeker, _ring = _player_with_class_ring("Seeker")
    seeker.awaken_class_ring()
    assert class_rings.hidden_cache_available(seeker, 3, reveal_progress=0.75)
    claimed, reward = class_rings.claim_hidden_cache(seeker, 3, reveal_progress=0.75)
    assert claimed is True
    assert reward == "Hidden Utility Cache"
    assert not class_rings.hidden_cache_available(seeker, 3, reveal_progress=1.0)


def test_master_monk_martial_master_and_arcane_trickster_buff():
    monk, _ring = _player_with_class_ring(
        "Master Monk",
        equipment={"Weapon": "No Weapon", "Armor": "No Armor"},
    )
    monk.awaken_class_ring()
    unawakened = TestGameState.create_player(
        class_name="Master Monk",
        race_name="Human",
        equipment={"Weapon": "No Weapon", "Armor": "No Armor"},
    )
    unawakened.equipment["Ring"] = items.NoRing()
    weapon_before = unawakened.check_mod("weapon")
    assert monk.check_mod("weapon") > weapon_before

    trickster, _ring = _player_with_class_ring("Arcane Trickster")
    trickster.awaken_class_ring()
    base_magic = trickster.check_mod("magic")
    class_rings.activate_spell_steal_buff(trickster)
    assert trickster.check_mod("magic") > base_magic


def test_legacy_class_ring_state_save_round_trip():
    player, _ring = _player_with_class_ring("Astromancer")
    player.awaken_class_ring()
    class_rings.advance_constellation(player)

    data = PlayerDataSerializer.serialize(player)
    restored = PlayerDataSerializer.deserialize(data, skip_tiles=True)

    assert restored.class_ring_awakening["awakened"]["Astromancer"] is True
    assert class_rings.active_constellation(restored) == "Tide"
