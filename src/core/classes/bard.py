"""Bard class definition and active song helpers."""

from __future__ import annotations

from typing import Any

from src.core.randomness import gameplay_random as random

from .. import items
from .base import Job

SONGS = {
    "Valor": {
        "description": "Raises weapon and magic damage for 3 turns.",
        "damage_bonus": 0.10,
    },
    "Shelter": {
        "description": "Reduces incoming damage for 3 turns.",
        "damage_reduction": 0.10,
    },
    "Renewal": {
        "description": "Restores a small amount of HP and MP each turn for 3 turns.",
        "recovery": 0.05,
    },
    "Battle Hymn": {
        "description": "All combat participants become berserk for 3 turns.",
        "berserk_all": True,
    },
    "Ode to the Ramparts": {
        "description": "Increases defense and magic defense for 5 turns.",
        "defense_bonus": 0.20,
        "duration": 5,
    },
    "Symphony of Disfunction": {
        "description": "Lowers enemy attack and magic attack while active.",
        "exploration_effect": "enemy_attack_down",
    },
    "Low-defense-ian Rhapsody": {
        "description": "Lowers enemy defense and magic defense while active.",
        "exploration_effect": "enemy_defense_down",
    },
    "Slow Ride": {
        "description": "Lowers enemy speed-related modifiers while active.",
        "exploration_effect": "enemy_speed_down",
    },
    "Bones, Thugs, and Harmony": {
        "description": "Shifts enemy encounter rate while active.",
        "exploration_effect": "encounter_rate_shift",
    },
    "Scores and Scores Score": {
        "description": "Shifts enemy difficulty while active.",
        "exploration_effect": "enemy_difficulty_shift",
    },
    "Gold Trigger": {
        "description": "Increases enemy loot drop rate while active.",
        "exploration_effect": "loot_rate_up",
    },
    "Chorus Time": {
        "description": "Enemies may become dumbfounded and lose their turn.",
        "dumbfound": True,
    },
}
SONG_DURATION = 3
EXPLORATION_SONG_STEPS = 80
EXPLORATION_PRACTICE_STEP = 20
ROUTE_CODA_STEPS = 20
REPERTOIRE_MP_COSTS = {
    "Battle Hymn": 14,
    "Ode to the Ramparts": 12,
    "Symphony of Disfunction": 10,
    "Low-defense-ian Rhapsody": 10,
    "Slow Ride": 10,
    "Bones, Thugs, and Harmony": 12,
    "Scores and Scores Score": 12,
    "Gold Trigger": 12,
    "Chorus Time": 16,
}
COMPOSITIONS = {
    "Battle Hymn": ("Lute", "BattleHymnSheet"),
    "Ode to the Ramparts": ("Mbira", "RampartsOdeSheet"),
    "Slow Ride": ("Lyre", "SlowRideSheet"),
    "Symphony of Disfunction": ("Tambourine", "DysfunctionSymphonySheet"),
    "Low-defense-ian Rhapsody": ("Accordina", "LowDefenseRhapsodySheet"),
    "Bones, Thugs, and Harmony": ("Didgeridoo", "BonesThugsHarmonySheet"),
    "Scores and Scores Score": ("Sitar", "ScoresAndScoresScoreSheet"),
    "Gold Trigger": ("Bagpipes", "GoldTriggerSheet"),
    "Chorus Time": ("GrandPiano", "ChorusTimeSheet"),
}


class Bard(Job):
    """
    Promotion: Healer -> Bard -> Troubadour
    Pros: Gain access to musical instruments and can wield daggers and Swords;
      gains songs that have affects in and out of combat; increased strength and dex gain
    Cons: Lose access to clubs; lower wisdom gain
    Special Mechanic: Plays active songs that bolster damage, shelter the Bard, or renew HP/MP.
    """

    def __init__(self):
        super().__init__(
            name="Bard",
            description="The Bard is a master of performance and inspiration, blending "
            "healing arts with the power of music and storytelling. They can "
            "weave enchanting melodies to bolster their own strength, restore "
            "health, and demoralize enemies. Bards excel at turning the tide of "
            "battle through clever improvisation, crowd control, and "
            "spellcasting.",
            str_plus=1,
            int_plus=1,
            wis_plus=1,
            con_plus=1,
            cha_plus=1,
            dex_plus=1,
            att_plus=1,
            def_plus=1,
            magic_plus=3,
            magic_def_plus=3,
            restrictions={
                "Weapon": ["Dagger", "Sword", "Staff"],
                "OffHand": ["Musical Instrument"],
                "Armor": ["Cloth", "Light"],
            },
            pro_level=2,
        )


def default_song_state() -> dict[str, Any]:
    return {"active": None, "turns": 0, "encore": None}


def normalize_song_state(state: Any) -> dict[str, Any]:
    normalized = default_song_state()
    if isinstance(state, dict):
        active = state.get("active")
        normalized["active"] = active if active in SONGS else None
        try:
            normalized["turns"] = max(0, int(state.get("turns", 0) or 0))
        except (TypeError, ValueError):
            normalized["turns"] = 0
        encore = state.get("encore")
        normalized["encore"] = encore if encore in SONGS else None
    return normalized


def ensure_song_state(character: Any) -> dict[str, Any]:
    state = normalize_song_state(getattr(character, "bard_song", None))
    setattr(character, "bard_song", state)
    return state


def has_instrument(character: Any) -> bool:
    offhand = getattr(character, "equipment", {}).get("OffHand")
    return getattr(offhand, "subtyp", None) == "Musical Instrument"


def equipped_instrument_name(character: Any) -> str:
    offhand = getattr(character, "equipment", {}).get("OffHand")
    return str(getattr(offhand, "name", "") or "")


def available_compositions(character: Any) -> dict[str, str]:
    if getattr(getattr(character, "cls", None), "name", "") not in {"Bard", "Troubadour"}:
        return {}
    instrument_name = equipped_instrument_name(character)
    return {
        song: sheet_cls
        for song, (required_instrument, sheet_cls) in COMPOSITIONS.items()
        if instrument_name == required_instrument
    }


def _has_talent(character: Any, talent_key: str) -> bool:
    """Return whether a Bard-family talent is currently purchased."""
    try:
        from ..progression import has_talent

        return has_talent(character, talent_key)
    except (AttributeError, KeyError, TypeError):
        return False


def compose_sheet_music(
    character: Any,
    song: str,
    *,
    rng: Any = random,
) -> tuple[bool, str]:
    options = available_compositions(character)
    if song not in options:
        required = COMPOSITIONS.get(song, ("a matching instrument", ""))[0]
        return False, f"{character.name} needs {required} to compose {song}.\n"

    sheet = getattr(items, options[song])()
    character.modify_inventory(sheet)
    message = f"{character.name} composes {sheet.song_name} onto sheet music.\n"
    if _has_talent(character, "bard.copyist") and rng.random() < 0.25:
        character.modify_inventory(getattr(items, options[song])())
        message += "Careful copywork produces a second sheet.\n"
    if getattr(getattr(character, "cls", None), "name", "") == "Troubadour":
        from . import promotion_kits

        message += promotion_kits.gain_bard_practice(
            character,
            song,
            2 if _has_talent(character, "troubadour.composers-memory") else 1,
            "composition",
        )
    return True, message


def song_strength(character: Any) -> float:
    strength = 1.0
    if getattr(getattr(character, "cls", None), "name", "") == "Troubadour":
        strength *= 1.5
    if _has_talent(character, "bard.resonant-hall"):
        strength *= 1.10
    if _has_talent(character, "troubadour.commanding-stage"):
        strength *= 1.10
    if _has_talent(character, "troubadour.repertoire-authority"):
        strength *= 1.10
    return strength


def _song_duration(character: Any, song: str) -> int:
    """Return the purchased duration for a newly started combat song."""
    duration = int(SONGS[song].get("duration", SONG_DURATION))
    if _has_talent(character, "bard.sustained-performance"):
        duration += 1
    if _has_talent(character, "troubadour.long-form"):
        duration += 1
    if song in REPERTOIRE_MP_COSTS and _has_talent(character, "bard.battle-arrangement"):
        duration += 1
    return duration


def default_exploration_song_state() -> dict[str, Any]:
    return {
        "active": None,
        "steps": 0,
        "effect": None,
        "practice_steps": 0,
        "route_effect": None,
        "route_steps": 0,
    }


def normalize_exploration_song_state(state: Any) -> dict[str, Any]:
    normalized = default_exploration_song_state()
    if isinstance(state, dict):
        active = state.get("active")
        normalized["active"] = active if active in SONGS else None
        normalized["effect"] = state.get("effect") if normalized["active"] else None
        try:
            normalized["steps"] = max(0, int(state.get("steps", 0) or 0))
            normalized["practice_steps"] = max(
                0,
                int(state.get("practice_steps", 0) or 0),
            )
            normalized["route_steps"] = max(
                0,
                int(state.get("route_steps", 0) or 0),
            )
        except (TypeError, ValueError):
            normalized["steps"] = 0
            normalized["practice_steps"] = 0
            normalized["route_steps"] = 0
        route_effect = state.get("route_effect")
        if route_effect in {
            spec.get("exploration_effect")
            for spec in SONGS.values()
            if spec.get("exploration_effect")
        }:
            normalized["route_effect"] = route_effect
    return normalized


def ensure_exploration_song_state(character: Any) -> dict[str, Any]:
    state = normalize_exploration_song_state(getattr(character, "bard_exploration_song", None))
    setattr(character, "bard_exploration_song", state)
    return state


def tick_exploration_song(character: Any, steps: int = 1) -> str:
    state = ensure_exploration_song_state(character)
    step_count = max(0, int(steps))
    message = ""
    if state.get("route_effect") == "encounter_rate_shift":
        state["route_steps"] = max(0, int(state.get("route_steps", 0)) - step_count)
        if state["route_steps"] <= 0:
            state["route_effect"] = None
    song = state.get("active")
    if not song or step_count <= 0:
        return message
    carried = min(step_count, int(state.get("steps", 0) or 0))
    before_practice = min(80, int(state.get("practice_steps", 0) or 0))
    after_practice = min(80, before_practice + carried)
    state["practice_steps"] = after_practice
    state["steps"] = max(0, int(state.get("steps", 0) or 0) - step_count)
    if getattr(getattr(character, "cls", None), "name", "") == "Troubadour":
        practice_step = (
            16 if _has_talent(character, "troubadour.road-tested") else EXPLORATION_PRACTICE_STEP
        )
        gained = after_practice // practice_step - before_practice // practice_step
        if gained:
            from . import promotion_kits

            message += promotion_kits.gain_bard_practice(
                character,
                song,
                gained,
                "carried steps",
            )
    if state["steps"] <= 0:
        message += _complete_exploration_song(character, song, state)
    return message


def _complete_exploration_song(
    character: Any,
    song: str,
    state: dict[str, Any],
) -> str:
    """Resolve clean practice and retain one conservative route coda."""
    message = f"{character.name}'s exploration performance of {song} ends cleanly.\n"
    if getattr(getattr(character, "cls", None), "name", "") == "Troubadour":
        from . import promotion_kits

        entry = promotion_kits.ensure_state(character)["bard_repertoire"][song]
        entry["clean_finishes"] = min(
            999,
            int(entry.get("clean_finishes", 0) or 0) + 1,
        )
        message += f"{song} records a clean finish ({entry['clean_finishes']}/3).\n"
        message += promotion_kits.gain_bard_practice(
            character,
            song,
            3,
            "natural completion",
        )
    route_effect = SONGS[song].get("exploration_effect")
    state.update(default_exploration_song_state())
    state["route_effect"] = route_effect
    if route_effect == "encounter_rate_shift":
        state["route_steps"] = (
            30 if _has_talent(character, "troubadour.lasting-impression") else ROUTE_CODA_STEPS
        )
    message += f"A reduced {song} route coda lingers.\n"
    return message


def active_exploration_effect(character: Any) -> str | None:
    state = ensure_exploration_song_state(character)
    if state.get("active"):
        return str(state.get("effect") or "") or None
    return str(state.get("route_effect") or "") or None


def _consume_route_effect(character: Any, effect: str) -> bool:
    state = ensure_exploration_song_state(character)
    if state.get("active") or state.get("route_effect") != effect:
        return False
    state["route_effect"] = None
    state["route_steps"] = 0
    return True


def loot_drop_multiplier(character: Any) -> float:
    if active_exploration_effect(character) != "loot_rate_up":
        return 1.0
    lingering = _consume_route_effect(character, "loot_rate_up")
    if _has_talent(character, "bard.gilded-verse"):
        return 1.35 if lingering else 2.25
    return 1.25 if lingering else 2.0


def encounter_rate_multiplier(character: Any) -> float:
    effect = active_exploration_effect(character)
    if effect != "encounter_rate_shift":
        return 1.0
    state = ensure_exploration_song_state(character)
    return 0.75 if state.get("active") else 0.875


def enemy_difficulty_shift(character: Any) -> int:
    if active_exploration_effect(character) != "enemy_difficulty_shift":
        return 0
    _consume_route_effect(character, "enemy_difficulty_shift")
    return -1


def apply_enemy_opening_debuffs(character: Any, enemy: Any) -> str:
    effect = active_exploration_effect(character)
    if not effect:
        return ""
    route_coda = _consume_route_effect(character, effect)
    scale = 0.10 if route_coda else 0.15
    if _has_talent(character, "bard.pointed-satire"):
        scale += 0.05
    if _has_talent(character, "troubadour.cutting-encore"):
        scale += 0.05
    if effect == "enemy_attack_down":
        for stat_name in ("Attack", "Magic"):
            stat = enemy.stat_effects[stat_name]
            stat.active = True
            stat.duration = max(stat.duration, 3)
            stat.extra = min(
                int(stat.extra or 0), -max(1, int(getattr(enemy.combat, "attack", 5) * scale))
            )
        return f"{enemy.name}'s offense falters under Symphony of Disfunction.\n"
    if effect == "enemy_defense_down":
        for stat_name in ("Defense", "Magic Defense"):
            stat = enemy.stat_effects[stat_name]
            stat.active = True
            stat.duration = max(stat.duration, 3)
            stat.extra = min(
                int(stat.extra or 0), -max(1, int(getattr(enemy.combat, "defense", 5) * scale))
            )
        return f"{enemy.name}'s guard falters under Low-defense-ian Rhapsody.\n"
    if effect == "enemy_speed_down":
        stat = enemy.stat_effects["Speed"]
        stat.active = True
        stat.duration = max(stat.duration, 3)
        speed_scale = 0.15 if route_coda else 0.20
        stat.extra = min(
            int(stat.extra or 0), -max(1, int(getattr(enemy.stats, "dex", 10) * speed_scale))
        )
        return f"{enemy.name}'s rhythm drags under Slow Ride.\n"
    return ""


def perform_repertoire_song(
    character: Any,
    song: str,
    target: Any | None = None,
    battle_engine: Any | None = None,
) -> tuple[bool, str]:
    """Perform one mastered advanced song for its authored MP cost."""
    if getattr(getattr(character, "cls", None), "name", "") != "Troubadour":
        return False, f"{character.name} has no mastered Troubadour repertoire.\n"
    if song not in REPERTOIRE_MP_COSTS:
        return False, f"{song} is not an advanced repertoire song.\n"
    from . import promotion_kits

    entry = promotion_kits.ensure_state(character)["bard_repertoire"][song]
    if not entry.get("known"):
        return False, f"{character.name} has not mastered {song}.\n"
    cost = REPERTOIRE_MP_COSTS[song]
    if _has_talent(character, "troubadour.efficient-repertoire"):
        cost = max(1, cost - 2)
    if int(character.mana.current) < cost:
        return False, f"{character.name} needs {cost} MP to perform {song}.\n"
    success, message = start_song(
        character,
        song,
        target=target,
        battle_engine=battle_engine,
    )
    if not success:
        return False, message
    character.mana.current -= cost
    return True, f"{character.name} spends {cost} MP from mastered repertoire.\n{message}"


def mastered_repertoire_songs(character: Any) -> list[str]:
    """Return advanced songs currently available for permanent performance."""
    if getattr(getattr(character, "cls", None), "name", "") != "Troubadour":
        return []
    from . import promotion_kits

    repertoire = promotion_kits.ensure_state(character)["bard_repertoire"]
    return [song for song in REPERTOIRE_MP_COSTS if repertoire[song].get("known")]


def start_song(
    character: Any, song: str, target: Any | None = None, battle_engine: Any | None = None
) -> tuple[bool, str]:
    if song not in SONGS:
        return False, f"{song} is not a known song.\n"
    if getattr(getattr(character, "cls", None), "name", "") not in {"Bard", "Troubadour"}:
        return False, f"{character.name} does not know the bardic forms.\n"
    if not has_instrument(character):
        return False, f"{character.name} needs an equipped musical instrument.\n"
    spec = SONGS[song]
    if spec.get("exploration_effect"):
        state = ensure_exploration_song_state(character)
        state["active"] = song
        state["effect"] = spec["exploration_effect"]
        state["steps"] = EXPLORATION_SONG_STEPS
        if _has_talent(character, "bard.road-song"):
            state["steps"] += 20
        if _has_talent(character, "troubadour.endless-refrain"):
            state["steps"] += 20
        state["practice_steps"] = 0
        state["route_effect"] = None
        state["route_steps"] = 0
        return (
            True,
            f"{character.name} begins {song}; its refrain will carry for {EXPLORATION_SONG_STEPS} steps.\n",
        )

    duration = _song_duration(character, song)
    state = ensure_song_state(character)
    if state.get("active") and state.get("turns", 0) > 0:
        from . import promotion_kits

        if _has_talent(character, "bard.seamless-transition"):
            meter = promotion_kits.combat_state(character)
            retained = min(1, int(meter.get("crescendo", 0) or 0))
            meter["crescendo"] = retained
            messages = f"Seamless Transition retains {retained} Crescendo.\n" if retained else ""
        else:
            messages = promotion_kits.clear_crescendo(character, "song replacement")
    else:
        messages = ""
    state["active"] = song
    state["turns"] = duration
    state["encore"] = None
    messages += f"{character.name} begins the Song of {song}.\n"

    if spec.get("berserk_all"):
        participants = [character]
        if target is not None and target not in participants:
            participants.append(target)
        if battle_engine is not None:
            for participant_name in ("player", "enemy", "summon"):
                participant = getattr(battle_engine, participant_name, None)
                if participant is not None and participant not in participants:
                    participants.append(participant)
        for participant in participants:
            if participant.has_status_protection("Berserk"):
                continue
            berserk = participant.status_effects["Berserk"]
            berserk.active = True
            berserk.duration = max(berserk.duration, 3)
        messages += "Battle Hymn drives the combatants into a battle frenzy.\n"

    if spec.get("defense_bonus"):
        amount = max(
            1,
            int(
                (character.check_mod("armor") + character.check_mod("magic def"))
                * spec["defense_bonus"]
                / 2
            ),
        )
        for stat_name in ("Defense", "Magic Defense"):
            effect = character.stat_effects[stat_name]
            effect.active = True
            effect.duration = max(effect.duration, duration)
            effect.extra = max(int(effect.extra or 0), amount)
        messages += f"Ode to the Ramparts raises {character.name}'s defenses by {amount}.\n"

    messages += _song_recovery_pulse(character, song, strength=song_strength(character))
    if song in REPERTOIRE_MP_COSTS and _has_talent(character, "troubadour.virtuoso-repertoire"):
        from . import promotion_kits

        messages += promotion_kits.gain_meter(
            character,
            "crescendo",
            1,
            "Virtuoso Repertoire",
        )
    return True, messages


def chorus_time_dumbfounds(
    character: Any,
    enemy: Any,
    *,
    multiplier: float = 1.0,
    rng: Any = random,
) -> bool:
    """Resolve Chorus Time's Charisma/Intellect control contest."""
    performer_stat = (
        int(getattr(character.stats, "charisma", 0))
        + int(getattr(character.stats, "intel", 0)) // 2
    )
    performer_stat = max(2, int(performer_stat * max(0.0, multiplier)))
    enemy_con = max(1, int(getattr(enemy.stats, "con", 1) or 1))
    return rng.randint(1, performer_stat) > rng.randint(1, enemy_con * 2)


def consume_chorus_time_coda(character: Any, enemy: Any, *, rng: Any = random) -> bool:
    """Spend the pending reduced Chorus Time coda on one enemy turn."""
    from . import promotion_kits

    state = promotion_kits.combat_state(character)
    spent = max(0, int(state.pop("chorus_time_coda", 0) or 0))
    if spent <= 0:
        return False
    return chorus_time_dumbfounds(
        character,
        enemy,
        multiplier=min(0.65, 0.35 + spent * 0.10),
        rng=rng,
    )


def active_song(character: Any) -> str | None:
    state = ensure_song_state(character)
    return state["active"] if state.get("turns", 0) > 0 else None


def damage_bonus(character: Any) -> float:
    state = ensure_song_state(character)
    bonus = 0.0
    if state.get("active") and state.get("turns", 0) > 0:
        bonus += SONGS.get(state.get("active"), {}).get("damage_bonus", 0.0) * song_strength(
            character
        )
    if state.get("encore"):
        bonus += SONGS.get(state.get("encore"), {}).get("damage_bonus", 0.0) * _encore_strength(
            character
        )
    if bonus and _has_talent(character, "bard.driving-rhythm"):
        bonus += 0.05
    return bonus


def damage_reduction(character: Any) -> float:
    state = ensure_song_state(character)
    reduction = 0.0
    if state.get("active") and state.get("turns", 0) > 0:
        reduction += SONGS.get(state.get("active"), {}).get(
            "damage_reduction", 0.0
        ) * song_strength(character)
    if state.get("encore"):
        reduction += SONGS.get(state.get("encore"), {}).get(
            "damage_reduction", 0.0
        ) * _encore_strength(character)
    if reduction and _has_talent(character, "bard.sheltering-refrain"):
        reduction += 0.05
    return min(0.75, reduction)


def tick_song(character: Any) -> str:
    state = ensure_song_state(character)
    messages = ""
    if state.get("encore"):
        state["encore"] = None
    song = state.get("active")
    if not song or state.get("turns", 0) <= 0:
        return messages
    messages += _song_recovery_pulse(character, song, strength=song_strength(character))
    from . import promotion_kits

    messages += promotion_kits.record_song_turn(character, song)
    state["turns"] -= 1
    if state["turns"] <= 0:
        from . import class_rings

        encore_strength = class_rings.encore_strength(character)
        if _has_talent(character, "troubadour.learned-encore"):
            encore_strength = max(encore_strength, 0.35)
        messages += f"{character.name}'s Song of {song} ends.\n"
        messages += promotion_kits.complete_song(character, song)
        state["active"] = None
        if encore_strength:
            if SONGS.get(song, {}).get("recovery"):
                messages += _song_recovery_pulse(
                    character, song, strength=song_strength(character) * encore_strength
                )
            else:
                state["encore"] = song
                messages += f"Encore carries the Song of {song} for one final beat.\n"
    return messages


def grand_finale(character: Any, *, cost: int = 8) -> str:
    """Spend MP to end the active combat song and resolve its coda now."""
    if getattr(getattr(character, "cls", None), "name", "") != "Troubadour":
        return "Grand Finale requires Troubadour training.\n"
    state = ensure_song_state(character)
    song = state.get("active") if int(state.get("turns", 0) or 0) > 0 else None
    if not song:
        return "Grand Finale requires an active combat song.\n"
    if _has_talent(character, "troubadour.decisive-ending"):
        cost = max(1, cost - 2)
    if int(character.mana.current) < cost:
        return f"{character.name} needs {cost} MP for Grand Finale.\n"
    from . import promotion_kits

    character.mana.current -= cost
    state["active"] = None
    state["turns"] = 0
    message = f"{character.name} ends Song of {song} with Grand Finale.\n"
    message += promotion_kits.complete_song(character, song)
    return message


def _encore_strength(character: Any) -> float:
    from . import class_rings

    return song_strength(character) * class_rings.encore_strength(character)


def _renewal_pulse(character: Any, *, strength: float) -> str:
    hp_max = max(1, int(getattr(character.health, "max", 1) or 1))
    mp_max = max(1, int(getattr(character.mana, "max", 1) or 1))
    recovery = SONGS["Renewal"]["recovery"]
    if _has_talent(character, "bard.restorative-harmony"):
        recovery += 0.02
    hp = max(1, int(hp_max * recovery * strength))
    mp = max(1, int(mp_max * recovery * strength))
    before_hp = character.health.current
    before_mp = character.mana.current
    character.health.current = min(hp_max, character.health.current + hp)
    character.mana.current = min(mp_max, character.mana.current + mp)
    gained_hp = character.health.current - before_hp
    gained_mp = character.mana.current - before_mp
    if gained_hp or gained_mp:
        return f"Song of Renewal restores {gained_hp} HP and {gained_mp} MP.\n"
    return ""


def _song_recovery_pulse(character: Any, song: str, *, strength: float) -> str:
    recovery = SONGS.get(song, {}).get("recovery", 0.0)
    if not recovery:
        return ""
    old_recovery = SONGS["Renewal"]["recovery"]
    try:
        SONGS["Renewal"]["recovery"] = recovery
        return _renewal_pulse(character, strength=strength)
    finally:
        SONGS["Renewal"]["recovery"] = old_recovery
