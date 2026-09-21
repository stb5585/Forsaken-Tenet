from types import SimpleNamespace

from src.core import abilities, enemies, items
from src.core.classes import (
    ability_mechanics,
    bard,
    class_rings,
    demonologist,
    lycan,
    promotion_kits,
)
from src.core.combat.combat_result import CombatResult
from src.core.progression import ABILITY_TREES, ensure_progression
from src.core.save_system import PlayerDataSerializer
from tests.test_framework import TestGameState


def _player(class_name, **kwargs):
    return TestGameState.create_player(class_name=class_name, race_name="Human", level=30, **kwargs)


def _own_talent(player, class_name, talent_key):
    node = next(
        node
        for node in ABILITY_TREES[class_name].nodes
        if node.payload.get("talent_key") == talent_key
    )
    ensure_progression(player).purchased_node_ids.add(node.id)


def test_promotion_kit_state_normalizes_and_round_trips():
    player = _player("Seeker")
    player.promotion_kit_state = {
        "summon_bonds": {"Patagon": 150, "Unknown": 99},
        "case_journal": {"Fiend": 250, "": 20},
        "bard_repertoire": {"Battle Hymn": {"known": True, "practice_xp": 99, "clean_finishes": 4}},
        "lycan_control": {"rank": "Tethered", "stress_events": 3, "dragon_essence": True},
        "favored_enemy": {"type": "Animal", "practice": 1000, "switches": 2},
    }

    state = player.ensure_promotion_kit_state()

    assert state["summon_bonds"]["Patagon"] == 100
    assert "Unknown" not in state["summon_bonds"]
    assert state["case_journal"] == {"Fiend": 100}
    assert state["bard_repertoire"]["Battle Hymn"]["known"] is True
    assert state["lycan_control"]["rank"] == "Tethered"
    assert state["favored_enemy"] == {"type": "Animal", "practice": 999, "switches": 2}

    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(player), skip_tiles=True
    )
    assert restored.promotion_kit_state["case_journal"]["Fiend"] == 100
    assert restored.promotion_kit_state["favored_enemy"]["type"] == "Animal"
    assert promotion_kits.combat_state(restored)["foresight_threads"] == 0


def test_removed_generic_masteries_leave_fixed_caps_and_control_progression():
    rogue = _player("Rogue")
    assert promotion_kits.cap_for(rogue, "fortune") == 3

    lycan = _player("Lycan")
    promotion_kits.record_lycan_stress(lycan, "survive")
    assert promotion_kits.lycan_control_state(lycan)["rank_progress"]["survive"] == 1


def test_resolve_mastery_normalizes_discards_scalar_and_round_trips():
    player = _player("Sentinel")
    state = class_rings.default_state()
    state["data"]["Stalwart Defender"]["resolve_mastery"] = 99
    player.class_ring_awakening = state

    mastery = class_rings.ensure_state(player)["data"]["Stalwart Defender"]["resolve_mastery"]
    assert mastery == {
        "citadel_aegis": 0,
        "ironwall_revenge": 0,
        "last_bastion": 0,
        "stronghold": 0,
    }

    mastery.update(
        {
            "citadel_aegis": 2,
            "ironwall_revenge": 8,
            "last_bastion": "invalid",
            "unknown": 3,
        }
    )
    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(player),
        skip_tiles=True,
    )
    assert class_rings.ensure_state(restored)["data"]["Stalwart Defender"]["resolve_mastery"] == {
        "citadel_aegis": 2,
        "ironwall_revenge": 4,
        "last_bastion": 0,
        "stronghold": 0,
    }


def test_bonded_bulwark_retains_its_authored_companion_payoff():
    beast_master = _player("Beast Master")
    beast_master.tamed_companion = {"active": True, "bond": 100}
    _own_talent(beast_master, "Beast Master", "beast-master.bonded-bulwark")
    assert promotion_kits.companion_bond_multiplier(beast_master) == 1.25


def test_threaded_cast_and_shadowcaster_shade_of_ahool():
    astro = _player("Astromancer", mana=(100, 100))
    assert "requires" in abilities.ThreadedCast().use(astro)
    assert "gains 1 Foresight" in promotion_kits.gain_meter(astro, "foresight_threads", 1, "test")
    assert "prepares Threaded Cast" in abilities.ThreadedCast().use(astro)

    shadow = _player("Shadowcaster", health=(200, 200))
    holy_before = shadow.check_mod("resist", typ="Holy")
    class_rings.ensure_state(shadow)["data"]["Shadowcaster"]["debt"] = 25
    assert "becomes the Shade of Ahool" in abilities.ShadeOfAhool().use(shadow)
    assert class_rings.ensure_state(shadow)["data"]["Shadowcaster"]["eclipse_turns"] == 3
    assert not hasattr(shadow, "shade_of_ahool_turns")
    assert shadow.flying
    assert class_rings.ensure_state(shadow)["data"]["Shadowcaster"]["debt"] == 5
    assert shadow.check_mod("resist", typ="Holy") == holy_before - 0.25


def test_demonologist_corruption_and_mood_gate_intents():
    demo = _player("Demonologist")
    demo.gold = 10000
    demo.demonologist_contracts = demonologist.default_state()
    demo.demonologist_contracts["unlocked_contracts"] = ["Imp"]
    demo.demonologist_contracts["active_patron"] = "Imp"
    demo.ensure_demonologist_contracts()

    assert "Protect" not in demonologist.available_intents(demo, "Imp")
    demo.demonologist_contracts["patron_moods"]["Imp"] = 25
    assert "Protect" in demonologist.available_intents(demo, "Imp")

    target = enemies.Goblin()
    message = demonologist.resolve_contract(
        demo, target, "Protect", rng=SimpleNamespace(random=lambda: 1.0)
    )

    assert "Bargain taint rises" in message
    assert demo.demonologist_contracts["corruption"] > 0
    assert demo.demonologist_contracts["patron_moods"]["Imp"] > 25


def test_representative_active_spends_and_status_text():
    cleric = _player("Cleric", mana=(100, 100))
    promotion_kits.gain_meter(cleric, "devotion", 2, "test")
    assert "Sanctuary Ward" in abilities.SanctuaryWard().use(cleric)

    priest = _player("Priest", mana=(100, 100), health=(120, 40))
    promotion_kits.gain_meter(priest, "prayer", 4, "test")
    mana_before = priest.mana.current
    assert abilities.Supplication().cost == 10
    assert "spends 4 Prayer" in abilities.Supplication().use(priest, priest)
    assert priest.mana.current == mana_before - 10
    assert priest.health.current > 40

    monk = _player("Master Monk", mana=(100, 100))
    target = enemies.Goblin()
    promotion_kits.gain_meter(monk, "ki", promotion_kits.cap_for(monk, "ki"), "test")
    assert "Dim Mak" in abilities.DimMak().use(monk, target)

    assert "Ki:" in monk._class_kit_status_str()


def test_held_devotion_reduces_incoming_damage_until_spent():
    cleric = _player("Cleric", mana=(100, 100))
    attacker = enemies.Goblin()

    hit, message, damage = cleric.damage_reduction(100, attacker, typ="Physical")
    assert hit is True
    assert damage == 100
    assert "Devotion guard" not in message

    promotion_kits.gain_meter(cleric, "devotion", 3, "test")
    hit, message, damage = cleric.damage_reduction(100, attacker, typ="Physical")
    assert hit is True
    assert damage == 91
    assert "Devotion guard reduces damage by 9" in message

    assert "spends 3 Devotion" in abilities.SanctuaryWard().use(cleric)
    hit, message, damage = cleric.damage_reduction(100, attacker, typ="Physical")
    assert hit is True
    assert damage == 100
    assert "Devotion guard" not in message

    templar = _player("Templar", mana=(100, 100))
    promotion_kits.gain_meter(templar, "devotion", 5, "test")
    _hit, message, damage = templar.damage_reduction(100, attacker, typ="Physical")
    assert damage == 85
    assert "Devotion guard reduces damage by 15" in message


def test_deferred_devotion_only_applies_when_defender_survives_action():
    cleric = _player("Cleric")
    target = enemies.Goblin()

    promotion_kits.begin_action(cleric, defer_devotion=True)
    promotion_kits.record_damage_event(
        cleric,
        target,
        12,
        "Holy",
        metadata={"attack_source": "weapon", "weapon_type": "Club"},
    )
    assert promotion_kits.combat_state(cleric)["devotion"] == 0
    assert promotion_kits.finish_action(cleric, defender_survived=False) == ""
    assert promotion_kits.combat_state(cleric)["devotion"] == 0

    promotion_kits.begin_action(cleric, defer_devotion=True)
    promotion_kits.record_damage_event(
        cleric,
        target,
        12,
        "Holy",
        metadata={"attack_source": "weapon", "weapon_type": "Club"},
    )
    message = promotion_kits.finish_action(cleric, defender_survived=True)

    assert "gains 1 Devotion" in message
    assert promotion_kits.combat_state(cleric)["devotion"] == 1


def test_hierophant_devotion_and_consecrated_conduit_payoff():
    hierophant = _player("Hierophant", mana=(100, 100), health=(100, 100))
    hierophant.equipment["Weapon"] = items.Quarterstaff()
    hierophant.spellbook["Skills"]["Staff Conduit"] = abilities.StaffConduit()
    target = enemies.Goblin()

    promotion_kits.begin_action(hierophant)
    promotion_kits.record_healing_done(hierophant, 20)
    promotion_kits.record_damage_event(
        hierophant,
        target,
        12,
        "Physical",
        metadata={"attack_source": "weapon", "weapon_slot": "Weapon", "weapon_type": "Staff"},
    )
    assert promotion_kits.combat_state(hierophant)["devotion"] == 1

    promotion_kits.begin_action(hierophant)
    promotion_kits.record_damage_event(
        hierophant,
        target,
        12,
        "Physical",
        metadata={"attack_source": "weapon", "weapon_slot": "Weapon", "weapon_type": "Staff"},
    )
    assert promotion_kits.combat_state(hierophant)["devotion"] == 2

    message = abilities.ConsecratedConduit().use(hierophant)
    assert "spends 2 Devotion" in message
    promotion_kits.begin_action(hierophant, action="Attack")
    before_hp = target.health.current
    promotion_kits.record_damage_event(
        hierophant,
        target,
        20,
        "Physical",
        metadata={"attack_source": "weapon", "weapon_slot": "Weapon", "weapon_type": "Staff"},
    )
    assert target.health.current < before_hp
    assert promotion_kits.combat_state(hierophant)["consecrated_conduit"] is None
    assert hierophant.magic_effects["Nature Shield"].active is True


def test_hierophant_conduit_gates_and_ring_preserves_after_payoff():
    cleric = _player("Cleric", mana=(100, 100))
    assert "requires Hierophant" in abilities.ConsecratedConduit().use(cleric)

    hierophant = _player("Hierophant", mana=(100, 100))
    assert "requires a staff" in abilities.ConsecratedConduit().use(hierophant)

    hierophant.equipment["Weapon"] = items.Quarterstaff()
    assert "requires Devotion" in abilities.ConsecratedConduit().use(hierophant)

    _awaken_ring(hierophant, "Hierophant")
    promotion_kits.gain_meter(hierophant, "devotion", 3, "test")
    assert "spends 3 Devotion" in abilities.ConsecratedConduit().use(hierophant)
    promotion_kits.begin_action(hierophant, action="Attack")
    target = enemies.Goblin()
    promotion_kits.record_damage_event(
        hierophant,
        target,
        24,
        "Physical",
        metadata={"attack_source": "weapon", "weapon_slot": "Weapon", "weapon_type": "Staff"},
    )
    assert promotion_kits.combat_state(hierophant)["devotion"] == 1
    assert "Sacred Conduit preserves 1 spent devotion" in promotion_kits.pop_messages(hierophant)


def test_sacred_overchannel_boosts_hierophant_devotion_and_payoff():
    hierophant = _player("Hierophant", mana=(100, 80))
    hierophant.equipment["Weapon"] = items.Quarterstaff()
    hierophant.spellbook["Skills"]["Sacred Overchannel"] = abilities.SacredOverchannel()
    hierophant.power_up = True
    hierophant.class_effects["Power Up"].active = True
    hierophant.class_effects["Power Up"].duration = 5
    target = enemies.Goblin()

    promotion_kits.begin_action(hierophant)
    promotion_kits.record_damage_event(
        hierophant,
        target,
        12,
        "Physical",
        metadata={"attack_source": "weapon", "weapon_slot": "Weapon", "weapon_type": "Staff"},
    )
    assert promotion_kits.combat_state(hierophant)["devotion"] == 2

    before_mana = hierophant.mana.current
    assert "spends 2 Devotion" in abilities.ConsecratedConduit().use(hierophant)
    after_cost_mana = hierophant.mana.current
    assert after_cost_mana == before_mana - 10
    promotion_kits.begin_action(hierophant, action="Attack")
    promotion_kits.record_damage_event(
        hierophant,
        target,
        20,
        "Physical",
        metadata={"attack_source": "weapon", "weapon_slot": "Weapon", "weapon_type": "Staff"},
    )
    assert hierophant.mana.current == after_cost_mana + 2


def test_ui_log_polish_status_matrix_surfaces():
    astro = _player("Astromancer", mana=(100, 100))
    _awaken_ring(astro, "Astromancer")
    promotion_kits.gain_meter(astro, "foresight_threads", 1, "test")
    abilities.ThreadedCast().use(astro)
    astro_status = astro._class_kit_status_str()
    assert "Threads:" in astro_status
    assert "Threaded ready" in astro_status
    assert "Threaded:" in astro_status
    assert "Pending next spell" in astro_status
    assert "Ring Ready:" in astro_status

    soulcatcher = _player("Soulcatcher")
    _awaken_ring(soulcatcher, "Soulcatcher")
    soulcatcher.magic_effects["Totem"].active = True
    soulcatcher.magic_effects["Totem"].extra = {"aspect": "Fire", "resonance": 2}
    soul_status = soulcatcher._class_kit_status_str()
    assert "Totem:" in soul_status
    assert "Fire 2/4" in soul_status

    seeker = _player("Seeker")
    target = enemies.Goblin()
    promotion_kits.gain_case_progress(seeker, target.enemy_typ, 75, "test")
    promotion_kits.add_revelation(seeker, target, 2, "test")
    seeker_status = seeker._class_kit_status_str()
    assert "Case:" in seeker_status
    assert "Pattern Lock" in seeker_status
    assert "Revelation:" in seeker_status

    beast = _player("Beast Master")
    beast.tamed_companion = {"active": True, "name": "Wolf", "bond": 50}
    beast.familiar = SimpleNamespace(name="Wolf", spec="Tamed", is_alive=lambda: True)
    beast.spellbook["Skills"]["Pack Strike"] = abilities.PackStrike()
    abilities.PackStrike().use(beast)
    beast_status = beast._class_kit_status_str()
    assert "Companion:" in beast_status
    assert "Battle-Trained" in beast_status
    assert "Command:" in beast_status

    lycan = _player("Lycan")
    promotion_kits.unlock_dragon_essence(lycan)
    lycan_status = lycan._class_kit_status_str()
    assert "Control:" in lycan_status
    assert "Dragon Essence:" in lycan_status


def test_ui_log_polish_persistent_and_preservation_status_lines():
    demo = _player("Demonologist")
    demo.demonologist_contracts = demonologist.default_state()
    demo.demonologist_contracts["unlocked_contracts"] = ["Imp"]
    demo.demonologist_contracts["active_patron"] = "Imp"
    demo.demonologist_contracts["corruption"] = 30
    demo.demonologist_contracts["patron_moods"]["Imp"] = 25
    demo.demonologist_contracts["imprisoned_familiar"] = {
        "name": "Ash",
        "race": "Mephit",
        "spec": "Arcane",
    }
    demo_status = demo._class_kit_status_str()
    assert "Corruption:" in demo_status
    assert "Patron:" in demo_status
    assert "Echo:" in demo_status

    templar = _player("Templar", mana=(100, 100))
    _awaken_ring(templar, "Templar")
    promotion_kits.gain_meter(templar, "devotion", 2, "test")
    ready_status = templar._class_kit_status_str()
    assert "Ring Ready:" in ready_status
    assert "Ring Preserve:" in ready_status
    assert "Ready" in ready_status

    message = abilities.SanctuaryWard().use(templar)
    used_status = templar._class_kit_status_str()
    assert "Ordered Blessings preserves 1 spent devotion" in message
    assert "Ring Preserve:" in used_status
    assert "Used" in used_status


def test_status_summary_rows_are_clean_label_value_pairs():
    dragoon = _player("Dragoon")
    promotion_kits.combat_state(dragoon)["aerial_tempo"] = 2
    assert ("Aerial Tempo", "2/3 Follow-up") in promotion_kits.status_summary_rows(dragoon)
    assert "Aerial Tempo:" in dragoon._class_kit_status_str()

    archbishop = _player("Archbishop", mana=(100, 100))
    _awaken_ring(archbishop, "Archbishop")
    promotion_kits.gain_meter(archbishop, "prayer", 2, "test")
    archbishop_rows = promotion_kits.status_summary_rows(archbishop)
    assert ("Prayer", "2/7 Supplication ready") in archbishop_rows
    assert ("Ring Ready", "Divine Intervention") in archbishop_rows
    assert ("Ring Preserve", "Ready") in archbishop_rows

    demo = _player("Demonologist")
    demo.demonologist_contracts = demonologist.default_state()
    demo.demonologist_contracts["unlocked_contracts"] = ["Imp"]
    demo.demonologist_contracts["active_patron"] = "Imp"
    demo.demonologist_contracts["corruption"] = 40
    demo.demonologist_contracts["patron_moods"]["Imp"] = 12
    demo.demonologist_contracts["imprisoned_familiar"] = {"name": "Ash", "spec": "Arcane"}
    demo_rows = promotion_kits.status_summary_rows(demo)
    assert ("Corruption", "40/100") in demo_rows
    assert ("Patron", "Imp (12)") in demo_rows
    assert ("Echo", "Ash") in demo_rows


def test_ui_log_polish_representative_messages():
    monk = _player("Master Monk")
    cap = promotion_kits.cap_for(monk, "ki")
    assert "gains" in promotion_kits.gain_meter(monk, "ki", cap, "test")
    assert "capped" in promotion_kits.gain_meter(monk, "ki", 1, "test")

    troubadour = _player("Troubadour")
    promotion_kits.gain_meter(troubadour, "crescendo", 1, "song")
    assert "Crescendo clears from interruption" in promotion_kits.clear_crescendo(
        troubadour,
        "interruption",
    )

    shaman = _player("Shaman")
    shaman.magic_effects["Totem"].active = True
    shaman.magic_effects["Totem"].extra = {"aspect": "Fire", "resonance": 3}
    assert "Totem Resonance is capped" in promotion_kits.gain_totem_resonance(
        shaman,
        "pulse",
    )


def test_monk_ki_authored_actions_and_reactions_dedupe_per_action():
    monk = _player("Monk")
    assert promotion_kits.cap_for(monk, "ki") == 3
    promotion_kits.begin_action(monk, action="Use Skill", choice="Double Strike")
    metadata = {"ability_name": "Double Strike", "weapon_type": "Fist"}

    promotion_kits.record_ki_martial_hit(monk, metadata)
    promotion_kits.record_ki_martial_hit(monk, metadata)
    promotion_kits.begin_incoming_ki_action(monk)
    promotion_kits.record_ki_reaction(monk, "dodge")
    promotion_kits.record_ki_reaction(monk, "parry")

    assert promotion_kits.combat_state(monk)["ki"] == 2


def test_ki_spender_consumes_on_attempt_and_chi_heal_applies_rider():
    monk = _player("Monk", health=(100, 50))
    promotion_kits.gain_meter(monk, "ki", 2, "test")

    assert "spends 1 Ki" in promotion_kits.begin_ki_spender(monk, "Chi Heal")
    monk.health.current = 70
    message = promotion_kits.finish_ki_spender(
        monk,
        monk,
        "Chi Heal",
        healing=20,
    )

    assert monk.health.current == 74
    assert "hostile status" in message
    assert promotion_kits.combat_state(monk)["ki"] == 1


def test_dim_mak_requires_full_ki_spends_mp_and_disarms_ordinary_staff(monkeypatch):
    monk = _player("Master Monk", mana=(100, 100))
    monk.equipment["Weapon"] = items.IronshodStaff()
    target = enemies.Goblin()
    monkeypatch.setattr(monk, "weapon_damage", lambda *_args, **_kwargs: ("miss\n", False, False))
    promotion_kits.gain_meter(monk, "ki", 5, "test")

    message = abilities.DimMak().use(monk, target)

    assert "spends 5 Ki" in message
    assert monk.mana.current == 82
    assert monk.equipment["Weapon"].subtyp == "None"
    assert promotion_kits.combat_state(monk)["ki"] == 0


def test_lycan_stress_control_scaling_pushback_and_rank_progression():
    character = _player("Lycan")
    character.progression.purchased_node_ids.add("lycan.ability.transform3")
    lycan.ensure_state(character)["moon_phase"] = "Full"
    control = promotion_kits.lycan_control_state(character)
    control["rank"] = "Tame"

    resisted, _ = lycan.maybe_trigger_frenzy(
        character,
        reason="combat_start",
        rng=SimpleNamespace(random=lambda: 0.10),
    )
    assert resisted is False
    control = promotion_kits.lycan_control_state(character)
    control["rank"] = "Feral"
    triggered, message = lycan.maybe_trigger_frenzy(
        character,
        reason="combat_start",
        rng=SimpleNamespace(random=lambda: 0.10),
    )

    assert triggered is True
    assert "transforms into a Werewolf" in message
    assert character.cls.name == "Werewolf"
    assert lycan.ensure_state(character)["frenzy_turns"] == 4

    character.transform(back=True)
    for _ in range(3):
        promotion_kits.record_lycan_stress(character, "survive")
    assert promotion_kits.lycan_control_state(character)["rank"] == "Muzzled"

    for reason, expected_rank in (
        ("dismiss", "Restive"),
        ("resist", "Tethered"),
        ("safe_dismiss", "Tame"),
    ):
        for _ in range(3):
            promotion_kits.record_lycan_stress(character, reason)
        assert promotion_kits.lycan_control_state(character)["rank"] == expected_rank


def test_winged_pounce_requires_form_essence_and_expires_after_enemy_turn(monkeypatch):
    character = _player("Lycan", mana=(30, 30), skills=["Winged Pounce"])
    character.progression.purchased_node_ids.add("lycan.ability.transform3")
    promotion_kits.lycan_control_state(character)["dragon_essence"] = True
    character.transform()
    target = enemies.Goblin()
    monkeypatch.setattr(
        character,
        "weapon_damage",
        lambda *_args, **_kwargs: ("pounce hit\n", True, False),
    )

    message = promotion_kits.winged_pounce(character, target)

    assert "launches a Winged Pounce" in message
    assert character.mana.max - character.mana.current == 12
    assert character.flying is True
    assert promotion_kits.combat_state(character)["winged_pounce_flight"] == 1

    from src.core.combat.battle_engine import BattleEngine

    class _Tile:
        def available_actions(self, _player):
            return ["Attack"]

    engine = BattleEngine(character, target, _Tile())
    engine.attacker = target
    engine.defender = character
    monkeypatch.setattr(
        target,
        "weapon_damage",
        lambda *_args, **_kwargs: ("miss\n", False, False),
    )
    engine.execute_intent(engine.prepare_intent("Attack"))
    assert character.flying is False


def test_resolve_aerial_aspect_totem_and_beast_commands():
    sentinel = _player("Sentinel")
    sentinel.equipment["OffHand"] = items.Glagwa()
    assert "Resolve" in promotion_kits.build_resolve(sentinel, 50, "test")
    assert class_rings.ensure_state(sentinel)["data"]["Stalwart Defender"]["guard_meter"] == 50
    assert "Bulwark Guard" in abilities.BulwarkGuard().use(sentinel)

    defender = _player("Stalwart Defender")
    defender.equipment["OffHand"] = items.Glagwa()
    assert "Resolve" in promotion_kits.build_resolve(defender, 100, "test")
    mastery = class_rings.ensure_state(defender)["data"]["Stalwart Defender"]["resolve_mastery"]
    mastery.update({key: 4 for key in mastery})
    assert all(
        promotion_kits.resolve_surge_unlocked(defender, surge)
        for surge in (
            "Citadel Aegis",
            "Ironwall Revenge",
            "Last Bastion",
            "Stronghold",
        )
    )
    assert "Citadel Aegis" in abilities.CitadelAegis().use(defender)
    assert class_rings.ensure_state(defender)["data"]["Stalwart Defender"]["guard_meter"] == 0
    assert promotion_kits.resolve_surge_unlocked(defender, "Ironwall Revenge")

    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(defender), skip_tiles=True
    )
    assert promotion_kits.resolve_surge_unlocked(restored, "Ironwall Revenge")

    dragoon = _player("Dragoon")
    promotion_kits.combat_state(dragoon)["aerial_tempo"] = 2
    assert "Aerial Tempo:" in dragoon._class_kit_status_str()

    archdruid = _player("Archdruid", mana=(100, 100), health=(150, 100))
    target = enemies.Goblin()
    assert "Venom" in promotion_kits.add_aspect(archdruid, "Venom")
    assert "Growth" in promotion_kits.add_aspect(archdruid, "Growth")
    assert "Fourfold Surge" in abilities.FourfoldSurge().use(archdruid, target)

    shaman = _player("Shaman", mana=(100, 100))
    shaman.magic_effects["Totem"].active = True
    shaman.magic_effects["Totem"].extra = {"aspect": "Fire", "resonance": 1}
    shaman.spellbook["Spells"]["Fireball"] = abilities.Fireball()
    assert "force Fireball" in abilities.TotemSurge().use(shaman, target)

    beast = _player("Beast Master")
    beast.tamed_companion = {"active": True, "name": "Companion", "bond": 50}
    beast.familiar = SimpleNamespace(name="Companion", spec="Tamed", is_alive=lambda: True)
    assert "Pack Strike" in abilities.PackStrike().use(beast)


def test_case_revelation_death_mark_stolen_charge_and_summon_bond():
    seeker = _player("Seeker")
    target = enemies.Goblin()
    assert "Revelation" in promotion_kits.add_revelation(seeker, target, 1, "test")
    assert "Case Journal" in promotion_kits.gain_case_progress(seeker, target.enemy_typ, 50, "test")

    ninja = _player("Ninja")
    assert "Death Mark" in promotion_kits.apply_death_mark(ninja, target, "test")

    trickster = _player("Arcane Trickster")
    assert "Stolen Charge" in promotion_kits.gain_stolen_charge(trickster, "test")

    summoner = _player("Thaumaturgist", mana=(100, 100))
    assert "Patagon's conduit" in promotion_kits.gain_summon_bond(summoner, "Patagon", 50, "test")
    assert ("Xenid Conduit", "Patagon 50/100 Invoke ready") in promotion_kits.status_summary_rows(
        summoner
    )
    assert "invokes Patagon" in abilities.InvokePatagon().use(summoner, target)


def test_stolen_charge_payoff_has_meaningful_damage_floor():
    trickster = _player("Arcane Trickster")
    target = enemies.Goblin()
    target.health.current = 100
    state = promotion_kits.combat_state(trickster)
    state["stolen_charge"] = 3

    promotion_kits.prepare_stolen_charge_payoff(trickster, "Attack")
    promotion_kits.record_action_resolution(
        trickster,
        CombatResult(
            action="Attack",
            actor=trickster,
            target=target,
            hit=True,
            damage=6,
        ),
    )

    assert target.health.current == 88
    assert state["stolen_charge"] == 0


def test_summon_conduit_gain_uses_global_level_scaled_roll(monkeypatch):
    from src.core import companions

    summoner = _player("Thaumaturgist")
    summon = companions.Patagon()
    summon.level.level = 2
    summon.level.pro_level = 1
    summon.exp_scale = 250
    summoner.summons = {"Patagon": summon}
    summoner.active_summon_name = "Patagon"
    monkeypatch.setattr("src.core.classes.promotion_kits.random.random", lambda: 0.01)

    assert promotion_kits.summon_bond_gain_for_victory(summoner, 50) > 0


def test_summon_conduit_gain_allows_new_xenids_and_can_fail_roll(monkeypatch):
    from src.core import companions

    summoner = _player("Thaumaturgist")
    summon = companions.Patagon()
    summoner.summons = {"Patagon": summon}
    summoner.active_summon_name = "Patagon"

    assert (
        promotion_kits.summon_bond_gain_for_victory(
            summoner,
            9999,
            guaranteed=True,
        )
        > 0
    )
    monkeypatch.setattr("src.core.classes.promotion_kits.random.random", lambda: 0.99)
    assert promotion_kits.summon_bond_gain_for_victory(summoner, 50) == 0
    message = promotion_kits.gain_summon_bond_for_active(summoner, 0, "victory")
    assert "Xenid Conduit: Patagon conduit holds steady" in message


def test_summon_defaults_and_dilong_starting_stats(monkeypatch):
    from src.core import companions

    player = _player("Thaumaturgist")
    dilong = companions.Dilong()
    monkeypatch.setattr("src.core.companions.random.randint", lambda _low, _high: 15)
    dilong.initialize_stats(player)

    assert dilong.exp_scale == 1000
    assert dilong.level.exp_to_gain == 2000
    assert dilong.combat.magic > 0
    assert dilong.combat.magic_def > 0
    assert "Surface" in dilong.spellbook["Skills"]


def test_lycan_control_and_dragon_essence():
    lycan = _player("Lycan")
    assert "rank Feral" in promotion_kits.record_lycan_stress(lycan, "survive")
    assert "Dragon Essence" in promotion_kits.unlock_dragon_essence(lycan)
    target = enemies.Goblin()
    assert "Winged Pounce" in abilities.WingedPounce().use(lycan, target)


def _awaken_ring(player, class_name):
    player.equipment["Ring"] = items.ClassRing()
    class_rings.ensure_state(player)["awakened"][class_name] = True
    player.equipment["Ring"].class_mod(player)


def test_ring_smoothing_preserves_devotion_prayer_and_rogue_luck(monkeypatch):
    templar = _player("Templar", mana=(100, 100))
    _awaken_ring(templar, "Templar")
    promotion_kits.gain_meter(templar, "devotion", 3, "test")
    message = abilities.SanctuaryWard().use(templar)
    assert "Ordered Blessings preserves 1 spent devotion" in message
    assert promotion_kits.combat_state(templar)["devotion"] == 1

    archbishop = _player("Archbishop", mana=(100, 100), health=(100, 40))
    _awaken_ring(archbishop, "Archbishop")
    promotion_kits.gain_meter(archbishop, "prayer", 3, "test")
    message = abilities.Supplication().use(archbishop, archbishop)
    assert "Divine Intervention preserves 1 spent prayer" in message
    assert promotion_kits.combat_state(archbishop)["prayer"] == 1

    rogue = _player("Rogue")
    _awaken_ring(rogue, "Rogue")
    promotion_kits.gain_meter(rogue, "fortune", 2, "test")
    monkeypatch.setattr("random.random", lambda: 0.0)
    reliability, message = promotion_kits.consume_fortune_for_risky_action(rogue, "Steal")
    assert reliability == 0.10
    message += promotion_kits.finish_fortune_payoff(rogue, True)
    assert "Loaded Dice preserves 1 spent fortune" in message
    assert promotion_kits.combat_state(rogue)["fortune"] == 1

    target = enemies.Goblin()
    promotion_kits.gain_meter(rogue, "misfortune", 3, "test")
    before = target.health.current
    message = promotion_kits.resolve_misfortune_payoff(rogue, target, 50, "Mug")
    assert "Loaded Dice preserves 1 spent misfortune" not in message
    assert target.health.current < before
    assert promotion_kits.combat_state(rogue)["misfortune"] == 0


def test_devotion_and_prayer_gain_once_per_authored_action():
    target = enemies.Goblin()
    target.health.max = target.health.current = 100
    cleric = _player("Cleric")

    promotion_kits.begin_action(
        cleric,
        defer_devotion=True,
        action="Cast Spell",
        choice="Holy",
        round_number=1,
    )
    for _ in range(3):
        promotion_kits.record_damage_event(
            cleric,
            target,
            10,
            "Holy",
            metadata={"ability_name": "Holy", "source": "spell"},
        )
    message = promotion_kits.finish_action(cleric, defender_survived=True)
    assert "gains 1 Devotion" in message
    assert promotion_kits.combat_state(cleric)["devotion"] == 1

    priest = _player("Priest")
    promotion_kits.begin_action(
        priest,
        action="Cast Spell",
        choice="Holy2",
        round_number=1,
    )
    promotion_kits.record_damage_event(priest, target, 10, "Holy")
    promotion_kits.record_damage_event(priest, target, 10, "Holy")
    promotion_kits.record_healing_done(priest, 10, source="Heal", target=priest)
    assert promotion_kits.combat_state(priest)["prayer"] == 1
    promotion_kits.begin_action(priest, action="Effects", choice="Regen", round_number=2)
    promotion_kits.record_healing_done(priest, 20, source="Regen", target=priest)
    assert promotion_kits.combat_state(priest)["prayer"] == 1


def test_holy_retribution_and_great_gospel_add_one_gain_per_round():
    target = enemies.Goblin()
    templar = _player("Templar")
    templar.spellbook["Skills"]["Holy Retribution"] = abilities.HolyRetribution()
    templar.power_up = True
    templar.class_effects["Power Up"].active = True
    templar.class_effects["Power Up"].duration = 5

    promotion_kits.begin_action(templar, action="Cast Spell", choice="Holy", round_number=3)
    promotion_kits.record_damage_event(templar, target, 5, "Holy")
    promotion_kits.finish_action(templar, defender_survived=True)
    assert promotion_kits.combat_state(templar)["devotion"] == 2
    promotion_kits.begin_action(templar, action="Cast Spell", choice="Holy", round_number=3)
    promotion_kits.record_damage_event(templar, target, 5, "Holy")
    promotion_kits.finish_action(templar, defender_survived=True)
    assert promotion_kits.combat_state(templar)["devotion"] == 3

    archbishop = _player("Archbishop")
    archbishop.spellbook["Skills"]["Great Gospel"] = abilities.GreatGospel()
    archbishop.power_up = True
    archbishop.class_effects["Power Up"].active = True
    archbishop.class_effects["Power Up"].duration = 5
    promotion_kits.begin_action(archbishop, action="Cast Spell", choice="Bless", round_number=4)
    result = SimpleNamespace(
        damage=0,
        healing=0,
        hit=True,
        effects_applied={"Magic": ["Bless"]},
    )
    promotion_kits.record_action_resolution(archbishop, result)
    assert promotion_kits.combat_state(archbishop)["prayer"] == 2


def test_supplication_and_benediction_complete_support_payoffs(monkeypatch):
    archbishop = _player("Archbishop", mana=(100, 100), health=(200, 80))
    archbishop.status_effects["Blind"].active = True
    promotion_kits.gain_meter(archbishop, "prayer", 4, "test")
    monkeypatch.setattr("random.random", lambda: 0.0)

    message = abilities.Supplication().use(archbishop, archbishop)
    assert archbishop.mana.current == 90
    assert archbishop.health.current > 80
    assert archbishop.magic_effects["Nature Shield"].active
    assert "cleanses Blind" in message

    promotion_kits.gain_meter(archbishop, "prayer", 6, "test")
    message = abilities.GreatBenediction().use(archbishop)
    payload = promotion_kits.combat_state(archbishop)["great_benediction"]
    assert "Great Benediction" in message
    assert payload["turns"] == 4
    assert payload["mana"] == 2
    reduced, _message = promotion_kits.benediction_damage_reduction(archbishop, 100)
    assert reduced == 88


def test_aspect_harmony_tracks_charges_and_preserves_latest_clean_aspect():
    archdruid = _player("Archdruid", mana=(100, 100), health=(200, 100))
    target = enemies.Goblin()
    target.health.max = target.health.current = 200
    _awaken_ring(archdruid, "Archdruid")
    archdruid.archdruid_attunement["ring_awakened"] = True

    promotion_kits.begin_action(archdruid, action="Cast Spell", choice="Poison Breath")
    promotion_kits.add_aspect(archdruid, "Venom")
    promotion_kits.add_aspect(archdruid, "Venom")
    promotion_kits.begin_action(archdruid, action="Cast Spell", choice="Heal")
    promotion_kits.add_aspect(archdruid, "Growth")
    counts = promotion_kits.combat_state(archdruid)["aspect_harmony"]
    assert counts == {"Venom": 1, "Growth": 1}

    message = abilities.FourfoldSurge().use(archdruid, target)
    assert "Harmony Bonus preserves Growth" in message
    assert promotion_kits.combat_state(archdruid)["aspect_harmony"] == {"Growth": 1}


def test_matching_totem_cast_gains_after_success_and_not_on_miss():
    shaman = _player("Shaman")
    shaman.magic_effects["Totem"].active = True
    shaman.magic_effects["Totem"].extra = {"aspect": "Fire", "resonance": 0}
    promotion_kits.begin_action(shaman, action="Cast Spell", choice="Fireball")
    miss = SimpleNamespace(damage=0, healing=0, hit=False, effects_applied={})
    promotion_kits.record_action_resolution(shaman, miss)
    assert promotion_kits.totem_resonance(shaman) == 0

    promotion_kits.begin_action(shaman, action="Cast Spell", choice="Fireball")
    hit = SimpleNamespace(damage=12, healing=0, hit=True, effects_applied={})
    promotion_kits.record_action_resolution(shaman, hit)
    promotion_kits.record_action_resolution(shaman, hit)
    assert promotion_kits.totem_resonance(shaman) == 1


def test_rogue_cheat_death_spends_misfortune_and_applies_jinx(monkeypatch):
    rogue = _player("Rogue", health=(100, 0))
    rogue.spellbook["Skills"]["Cheat Death"] = abilities.CheatDeath()
    _awaken_ring(rogue, "Rogue")
    promotion_kits.gain_meter(rogue, "misfortune", 3, "test")
    monkeypatch.setattr("random.random", lambda: 0.0)

    message = promotion_kits.cheat_death(rogue)

    assert "Cheat Death spends 3 Misfortune" in message
    assert rogue.health.current == 1
    assert promotion_kits.combat_state(rogue)["jinx_turns"] == 2
    assert "Jinx:" in rogue._class_kit_status_str()
    rogue.effects()
    rogue.effects()
    assert promotion_kits.combat_state(rogue)["jinx_turns"] == 0


def test_thief_rogue_fortune_grows_once_for_meaningful_weapon_damage():
    thief = _player("Thief")
    target = enemies.Goblin()

    promotion_kits.record_damage_event(
        thief,
        target,
        10,
        "Physical",
        metadata={"attack_source": "weapon", "is_critical": False},
    )
    assert promotion_kits.combat_state(thief)["fortune"] == 1

    promotion_kits.record_damage_event(
        thief,
        target,
        10,
        "Physical",
        metadata={"attack_source": "weapon", "is_critical": True},
    )
    assert promotion_kits.combat_state(thief)["fortune"] == 1


def test_risky_thief_ability_miss_adds_misfortune_without_noncrit_fortune(monkeypatch):
    thief = _player("Thief", mana=(100, 100))
    target = enemies.Goblin()

    monkeypatch.setattr(thief, "weapon_damage", lambda *_args, **_kwargs: ("misses.\n", False, 1))
    abilities.Mug().use(thief, target)
    state = promotion_kits.combat_state(thief)
    assert state["fortune"] == 0
    assert state["misfortune"] == 1

    state["misfortune"] = 0

    def noncritical_hit(target, **_kwargs):
        target.health.current -= 5
        return "hits.\n", True, 1

    monkeypatch.setattr(thief, "weapon_damage", noncritical_hit)
    abilities.Mug().use(thief, target)
    assert state["fortune"] == 0
    assert state["misfortune"] == 0


def test_troubadour_crescendo_coda_practice_and_encore_preservation():
    troubadour = _player("Troubadour", mana=(100, 100))
    troubadour.equipment["OffHand"] = items.Lute()
    _awaken_ring(troubadour, "Troubadour")

    ok, message = bard.start_song(troubadour, "Battle Hymn", target=enemies.Goblin())
    assert ok is True
    for _ in range(3):
        message += bard.tick_song(troubadour)

    state = promotion_kits.combat_state(troubadour)
    repertoire = promotion_kits.ensure_state(troubadour)["bard_repertoire"]["Battle Hymn"]
    assert "spends 3 Crescendo" in message
    assert "Encore preserves 1 spent crescendo" in message
    assert state["crescendo"] == 1
    assert repertoire["practice_xp"] == 6
    assert repertoire["clean_finishes"] == 1


def test_troubadour_exploration_completion_practice_route_coda_and_save():
    troubadour = _player("Troubadour")
    troubadour.equipment["OffHand"] = items.Tambourine()

    composed, message = bard.compose_sheet_music(
        troubadour,
        "Symphony of Disfunction",
    )
    assert composed is True
    assert "1 practice XP from composition" in message
    started, _ = bard.start_song(troubadour, "Symphony of Disfunction")
    assert started is True
    message = bard.tick_exploration_song(troubadour, 80)
    repertoire = promotion_kits.ensure_state(troubadour)["bard_repertoire"][
        "Symphony of Disfunction"
    ]
    assert repertoire["practice_xp"] == 8
    assert repertoire["clean_finishes"] == 1
    assert "reduced Symphony of Disfunction route coda" in message

    restored = PlayerDataSerializer.deserialize(
        PlayerDataSerializer.serialize(troubadour),
        skip_tiles=True,
    )
    assert bard.active_exploration_effect(restored) == "enemy_attack_down"
    enemy = enemies.Goblin()
    assert "offense falters" in bard.apply_enemy_opening_debuffs(restored, enemy)
    assert bard.active_exploration_effect(restored) is None


def test_mastered_repertoire_costs_mp_and_chorus_coda_resolves_once():
    troubadour = _player("Troubadour", mana=(100, 100))
    troubadour.equipment["OffHand"] = items.Lute()
    promotion_kits.ensure_state(troubadour)["bard_repertoire"]["Battle Hymn"]["known"] = True

    started, message = bard.perform_repertoire_song(
        troubadour,
        "Battle Hymn",
        target=enemies.Goblin(),
    )
    assert started is True
    assert troubadour.mana.current == 86
    assert "spends 14 MP" in message

    promotion_kits.combat_state(troubadour)["crescendo"] = 3
    message = promotion_kits.complete_song(troubadour, "Chorus Time")
    assert "readies one final reduced tempo check" in message

    class WinningContest:
        calls = 0

        def randint(self, low, high):
            self.calls += 1
            return high if self.calls == 1 else low

    assert (
        bard.consume_chorus_time_coda(
            troubadour,
            enemies.Goblin(),
            rng=WinningContest(),
        )
        is True
    )
    assert (
        bard.consume_chorus_time_coda(
            troubadour,
            enemies.Goblin(),
            rng=WinningContest(),
        )
        is False
    )


def test_shared_recovery_scales_with_companion_bond():
    beast = _player("Beast Master")
    _awaken_ring(beast, "Beast Master")
    beast.tamed_companion = {"active": True, "bond": 100}

    assert class_rings.shared_recovery_amount(beast, 100) == 35


def test_shared_recovery_ring_strengthens_each_companion_command():
    beast = _player("Beast Master", health=(100, 50))
    captured = {}

    def weapon_damage(_target, **kwargs):
        captured.update(kwargs)
        return "hits.\n", True, 1

    beast.familiar = SimpleNamespace(
        name="Wolf",
        spec="Tamed",
        health=SimpleNamespace(max=100, current=50),
        bond=100,
        is_alive=lambda: True,
        weapon_damage=weapon_damage,
    )
    beast.tamed_companion = {"active": True, "bond": 100}
    enemy = enemies.Goblin()
    _awaken_ring(beast, "Beast Master")

    ability_mechanics.set_pending_companion_command(beast, "Pack Strike")
    message = ability_mechanics.resolve_tamed_companion_command(beast, enemy)
    assert captured["accuracy_modifier"] == 0.10
    assert "Shared Recovery strengthens" in message

    ability_mechanics.set_pending_companion_command(beast, "Guard Partner")
    ability_mechanics.resolve_tamed_companion_command(beast, enemy)
    assert beast.magic_effects["Nature Shield"].duration == 3
    assert beast.magic_effects["Nature Shield"].extra == 31

    ability_mechanics.set_pending_companion_command(beast, "Harry Prey")
    ability_mechanics.resolve_tamed_companion_command(beast, enemy)
    assert enemy.stat_effects["Defense"].extra == -6
    assert enemy.stat_effects["Speed"].duration == 3

    ability_mechanics.set_pending_companion_command(beast, "Mend Wounds")
    message = ability_mechanics.resolve_tamed_companion_command(beast, enemy)
    assert beast.health.current == 93
    assert "43 HP" in message
