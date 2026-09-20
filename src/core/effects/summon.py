"""Summon companion ultimate effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Effect

if TYPE_CHECKING:
    from ..character import Character
    from ..combat.combat_result import CombatResult


class TitanicSlamEffect(Effect):
    """
    Patagon ultimate: massive weapon strike (4x) + guaranteed stun 2 turns.

    Bypasses stun immunity checks — the sheer force overwhelms all defenses
    except Mana Shield (which absorbs the stun but not the damage).
    """

    def __init__(
        self,
        dmg_mod: float = 4.0,
        crit_override: int = 2,
        stun_duration: int = 2,
    ):
        self.dmg_mod = dmg_mod
        self.crit_override = crit_override
        self.stun_duration = stun_duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:

        messages = result.extra.setdefault("messages", [])
        cover = result.extra.get("cover", False)

        messages.append(
            f"{actor.name} raises both fists and brings them crashing " f"down on {target.name}!\n"
        )

        # ── Weapon damage ───────────────────────────────────────────
        wd_str, hit, crit = actor.weapon_damage(
            target,
            cover=cover,
            dmg_mod=self.dmg_mod,
            crit=self.crit_override,
        )
        messages.append(wd_str)
        result.hit = hit
        result.crit = crit if crit > 1 else None

        # ── Post-hit guaranteed stun ────────────────────────────────
        if hit and target.is_alive():
            if not target.magic_effects["Mana Shield"].active:
                if target.apply_stun(self.stun_duration, source="Titanic Slam", applier=actor):
                    messages.append(
                        f"The earth-shattering blow stuns {target.name} "
                        f"for {self.stun_duration} turns!\n"
                    )
            else:
                messages.append("The mana shield absorbs the stunning force.\n")


class DevourEffect(Effect):
    """
    Dilong ultimate: swallow the target, dealing % max HP damage over
    multiple bites plus a final spit-out with bonus damage.

    Mechanics: 3 hits at (str + con) * multiplier each, applied through
    Earth resistance. Ignores dodge/cover — the target is inside the worm.
    """

    def __init__(
        self,
        num_bites: int = 3,
        multiplier: float = 1.5,
        element: str = "Earth",
    ):
        self.num_bites = num_bites
        self.multiplier = multiplier
        self.element = element

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])
        messages.append(f"{actor.name} lunges forward and swallows " f"{target.name} whole!\n")

        total_damage = 0
        for i in range(self.num_bites):
            base = int((actor.stats.strength + actor.stats.con) * self.multiplier)
            variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
            damage = int(base * variance)

            _, red_msg, damage = target.damage_reduction(
                damage,
                actor,
                typ=self.element,
            )
            if red_msg:
                messages.append(red_msg)

            if damage > 0:
                target.health.current -= damage
                total_damage += damage
                if i < self.num_bites - 1:
                    messages.append(
                        f"{actor.name} crushes {target.name} for " f"{damage} damage!\n"
                    )

            if not target.is_alive():
                messages.append(f"{actor.name} devours {target.name} completely!\n")
                break

        if target.is_alive():
            messages.append(
                f"{actor.name} spits out {target.name}, dealing " f"{total_damage} total damage!\n"
            )

        result.damage = total_damage
        result.hit = total_damage > 0


class AbsoluteZeroEffect(Effect):
    """
    Agloolik ultimate: heavy ice damage (3x) + freeze (Stun 3 turns)
    + permanent defense reduction.
    """

    def __init__(
        self,
        damage_mod: float = 3.0,
        stun_duration: int = 3,
        def_reduction: int = 5,
    ):
        self.damage_mod = damage_mod
        self.stun_duration = stun_duration
        self.def_reduction = def_reduction

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])
        messages.append(f"{actor.name} channels the essence of absolute cold!\n")

        # ── Ice damage ──────────────────────────────────────────────
        base = int(actor.stats.intel * self.damage_mod)
        variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        damage = int(base * variance)

        hit, def_msg, damage = target.handle_defenses(
            actor,
            damage,
            typ="Magic",
        )
        if def_msg:
            messages.append(def_msg)

        _, red_msg, damage = target.damage_reduction(
            damage,
            actor,
            typ="Ice",
        )
        if red_msg:
            messages.append(red_msg)

        if hit and damage > 0:
            target.health.current -= damage
            result.damage = damage
            result.hit = True
            messages.append(
                f"{target.name} takes {damage} ice damage as the " f"temperature plummets!\n"
            )
        else:
            messages.append(f"The freezing blast has no effect on {target.name}.\n")
            return

        if not target.is_alive():
            return

        # ── Freeze (stun) ──────────────────────────────────────────
        if not target.magic_effects["Mana Shield"].active:
            if target.apply_stun(self.stun_duration, source="Absolute Zero", applier=actor):
                messages.append(
                    f"{target.name} is frozen solid for " f"{self.stun_duration} turns!\n"
                )

        # ── Defense shatter ─────────────────────────────────────────
        if target.combat.defense > self.def_reduction:
            target.combat.defense -= self.def_reduction
            messages.append(
                f"{target.name}'s defense is permanently shattered " f"by {self.def_reduction}!\n"
            )


class EruptionEffect(Effect):
    """
    Cacus ultimate: massive fire damage (3.5x) + Burn DOT
    + self Vulcanize buff (defense +25% for 3 turns).
    """

    def __init__(
        self,
        damage_mod: float = 3.5,
        burn_duration: int = 3,
        vulcanize_duration: int = 3,
    ):
        self.damage_mod = damage_mod
        self.burn_duration = burn_duration
        self.vulcanize_duration = vulcanize_duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])
        messages.append(f"{actor.name} erupts in a cataclysmic blaze of fire!\n")

        # ── Fire damage ─────────────────────────────────────────────
        base = int((actor.stats.strength + actor.stats.intel) * self.damage_mod)
        variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        damage = int(base * variance)

        hit, def_msg, damage = target.handle_defenses(
            actor,
            damage,
            typ="Magic",
        )
        if def_msg:
            messages.append(def_msg)

        _, red_msg, damage = target.damage_reduction(
            damage,
            actor,
            typ="Fire",
        )
        if red_msg:
            messages.append(red_msg)

        if hit and damage > 0:
            target.health.current -= damage
            result.damage = damage
            result.hit = True
            messages.append(f"{target.name} is engulfed in flames for {damage} damage!\n")
        else:
            messages.append(f"The eruption has no effect on {target.name}.\n")
            return

        if not target.is_alive():
            return

        # ── Burn DOT ────────────────────────────────────────────────
        if "DOT" not in target.status_immunity and not target.magic_effects["DOT"].active:
            target.magic_effects["DOT"].active = True
            target.magic_effects["DOT"].duration = self.burn_duration
            target.magic_effects["DOT"].extra = max(
                1,
                actor.stats.intel // 4,
            )
            target.magic_effects["DOT"].source = "Burn"
            messages.append(f"{target.name} is set ablaze!\n")

        # ── Self Vulcanize buff ─────────────────────────────────────
        if hasattr(actor, "stat_effects") and "Defense" in actor.stat_effects:
            actor.stat_effects["Defense"].active = True
            actor.stat_effects["Defense"].duration = self.vulcanize_duration
            actor.stat_effects["Defense"].extra = max(
                1,
                actor.combat.defense // 4,
            )
            messages.append(f"{actor.name}'s skin hardens into volcanic rock!\n")


class MaelstromVortexEffect(Effect):
    """
    Fuath ultimate: heavy water damage (3x) + apply Blind, Silence,
    and Terrify — the maddening vortex overwhelms the senses.
    """

    def __init__(
        self,
        damage_mod: float = 3.0,
        status_duration: int = 3,
    ):
        self.damage_mod = damage_mod
        self.status_duration = status_duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])
        messages.append(f"{actor.name} summons a maddening vortex of swirling water!\n")

        # ── Water damage ────────────────────────────────────────────
        base = int(actor.stats.intel * self.damage_mod)
        variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        damage = int(base * variance)

        hit, def_msg, damage = target.handle_defenses(
            actor,
            damage,
            typ="Magic",
        )
        if def_msg:
            messages.append(def_msg)

        _, red_msg, damage = target.damage_reduction(
            damage,
            actor,
            typ="Water",
        )
        if red_msg:
            messages.append(red_msg)

        if hit and damage > 0:
            target.health.current -= damage
            result.damage = damage
            result.hit = True
            messages.append(f"{target.name} is torn apart by the vortex for " f"{damage} damage!\n")
        else:
            messages.append(f"The vortex has no effect on {target.name}.\n")
            return

        if not target.is_alive():
            return

        # ── Apply triple debuff ─────────────────────────────────────
        for status_name, msg in [
            ("Blind", f"{target.name} is blinded by the churning waters!\n"),
            ("Silence", f"{target.name} is silenced by the roaring waves!\n"),
        ]:
            if (
                status_name not in target.status_immunity
                and f"Status-{status_name}" not in target.equipment["Pendant"].mod
                and "Status-All" not in target.equipment["Pendant"].mod
                and not target.status_effects[status_name].active
                and not target.magic_effects["Mana Shield"].active
            ):
                target.status_effects[status_name].active = True
                target.status_effects[status_name].duration = self.status_duration
                try:
                    actor._emit_status_event(
                        target,
                        status_name,
                        applied=True,
                        duration=self.status_duration,
                        source="Maelstrom Vortex",
                    )
                except (AttributeError, Exception):
                    pass
                messages.append(msg)

        # Terrify uses magic_effects
        if (
            target.magic_effects.get("Terrify") is not None
            and not target.magic_effects["Terrify"].active
        ):
            target.magic_effects["Terrify"].active = True
            target.magic_effects["Terrify"].duration = self.status_duration
            messages.append(f"{target.name} is terrified by the maelstrom!\n")


class ThunderstrikeEffect(Effect):
    """
    Izulu ultimate: lightning damage (3x) + 2 chain hits at 50% damage
    + stun.  The lightning bird's devastating electrical assault.
    """

    def __init__(
        self,
        damage_mod: float = 3.0,
        chain_hits: int = 2,
        chain_multiplier: float = 0.5,
        stun_duration: int = 2,
    ):
        self.damage_mod = damage_mod
        self.chain_hits = chain_hits
        self.chain_multiplier = chain_multiplier
        self.stun_duration = stun_duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])
        messages.append(
            f"{actor.name} screeches and calls down a devastating " f"bolt of lightning!\n"
        )

        total_damage = 0

        # ── Primary strike ──────────────────────────────────────────
        base = int(actor.stats.intel * self.damage_mod)
        variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        damage = int(base * variance)

        hit, def_msg, damage = target.handle_defenses(
            actor,
            damage,
            typ="Magic",
        )
        if def_msg:
            messages.append(def_msg)

        _, red_msg, damage = target.damage_reduction(
            damage,
            actor,
            typ="Electric",
        )
        if red_msg:
            messages.append(red_msg)

        if hit and damage > 0:
            target.health.current -= damage
            total_damage += damage
            messages.append(f"The lightning strikes {target.name} for {damage} damage!\n")
        else:
            messages.append(f"The lightning has no effect on {target.name}.\n")
            result.damage = 0
            return

        # ── Chain hits ──────────────────────────────────────────────
        for i in range(self.chain_hits):
            if not target.is_alive():
                break
            chain_base = int(base * self.chain_multiplier)
            variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
            chain_dmg = int(chain_base * variance)

            _, red_msg, chain_dmg = target.damage_reduction(
                chain_dmg,
                actor,
                typ="Electric",
            )
            if red_msg:
                messages.append(red_msg)

            if chain_dmg > 0:
                target.health.current -= chain_dmg
                total_damage += chain_dmg
                messages.append(
                    f"The lightning chains through {target.name} for " f"{chain_dmg} damage!\n"
                )

        result.damage = total_damage
        result.hit = total_damage > 0

        # ── Stun ────────────────────────────────────────────────────
        if target.is_alive() and total_damage > 0:
            if (
                "Stun" not in target.status_immunity
                and "Status-Stun" not in target.equipment["Pendant"].mod
                and "Status-All" not in target.equipment["Pendant"].mod
                and not target.magic_effects["Mana Shield"].active
            ):
                if target.apply_stun(self.stun_duration, source="Thunderstrike", applier=actor):
                    messages.append(f"{target.name} is paralyzed by the electrical " f"surge!\n")


class WindShrapnelEffect(Effect):
    """
    Hala ultimate: 5 wind-element hits, each with independent crit
    chance.  A storm of razor-sharp wind fragments.
    """

    def __init__(
        self,
        num_hits: int = 5,
        damage_mod: float = 1.2,
        crit_chance: float = 0.25,
        crit_multiplier: float = 2.0,
    ):
        self.num_hits = num_hits
        self.damage_mod = damage_mod
        self.crit_chance = crit_chance
        self.crit_multiplier = crit_multiplier

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])
        messages.append(f"{actor.name} conjures a storm of razor-sharp wind blades!\n")

        total_damage = 0
        total_crits = 0

        for i in range(self.num_hits):
            if not target.is_alive():
                break

            is_crit = random.random() < self.crit_chance
            crit_mod = self.crit_multiplier if is_crit else 1.0

            base = int(actor.stats.intel * self.damage_mod * crit_mod)
            variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
            damage = int(base * variance)

            _, red_msg, damage = target.damage_reduction(
                damage,
                actor,
                typ="Wind",
            )
            if red_msg:
                messages.append(red_msg)

            if damage > 0:
                target.health.current -= damage
                total_damage += damage
                if is_crit:
                    total_crits += 1
                crit_str = " (Critical!)" if is_crit else ""
                messages.append(
                    f"Wind blade hits {target.name} for " f"{damage} damage!{crit_str}\n"
                )

        if total_damage > 0:
            messages.append(
                f"Total: {total_damage} damage across {self.num_hits} "
                f"hits ({total_crits} critical).\n"
            )

        result.damage = total_damage
        result.hit = total_damage > 0


class DivineJudgmentEffect(Effect):
    """
    Seraphim ultimate: holy damage (3x, double vs undead) + heal the
    summoner + cleanse all status effects on the summoner.

    The angelic Watcher passes divine judgment on the enemy.
    """

    def __init__(
        self,
        damage_mod: float = 3.0,
        undead_multiplier: float = 2.0,
        heal_fraction: float = 0.5,
    ):
        self.damage_mod = damage_mod
        self.undead_multiplier = undead_multiplier
        self.heal_fraction = heal_fraction

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])
        messages.append(f"{actor.name} raises a holy sword and passes " f"divine judgment!\n")

        # ── Holy damage ─────────────────────────────────────────────
        mod = self.damage_mod
        is_undead = getattr(target, "enemy_typ", "") == "Undead"
        if is_undead:
            mod *= self.undead_multiplier
            messages.append("The holy light burns with terrible fury " "against the undead!\n")

        base = int(actor.stats.wisdom * mod)
        variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        damage = int(base * variance)

        hit, def_msg, damage = target.handle_defenses(
            actor,
            damage,
            typ="Magic",
        )
        if def_msg:
            messages.append(def_msg)

        _, red_msg, damage = target.damage_reduction(
            damage,
            actor,
            typ="Holy",
        )
        if red_msg:
            messages.append(red_msg)

        if hit and damage > 0:
            target.health.current -= damage
            result.damage = damage
            result.hit = True
            messages.append(f"Divine light strikes {target.name} for " f"{damage} damage!\n")
        else:
            messages.append(f"The divine judgment has no effect on {target.name}.\n")

        # ── Heal the summoner (actor's owner) ───────────────────────
        # Summons are the actor; try to heal via owner reference,
        # otherwise heal self as fallback.
        healer = getattr(actor, "owner", actor)
        heal_amount = int(healer.health.max * self.heal_fraction)
        actual_heal = min(heal_amount, healer.health.max - healer.health.current)
        if actual_heal > 0:
            healer.health.current += actual_heal
            messages.append(f"Holy light restores {actual_heal} HP to " f"{healer.name}!\n")

        # ── Cleanse status effects on the summoner ──────────────────
        cleansed = []
        for status_name, status in healer.status_effects.items():
            if status.active and status_name not in ("Regen",):
                status.active = False
                status.duration = 0
                cleansed.append(status_name)
        if cleansed:
            messages.append(f"{healer.name} is cleansed of " f"{', '.join(cleansed)}!\n")


class OblivionEffect(Effect):
    """
    Bardi ultimate: massive shadow damage (4x) + % instant kill chance
    + permanent stat drain on survivor.  The bringer of death and darkness
    unleashes oblivion.
    """

    def __init__(
        self,
        damage_mod: float = 4.0,
        kill_chance: float = 0.2,
        stat_drain: int = 3,
    ):
        self.damage_mod = damage_mod
        self.kill_chance = kill_chance
        self.stat_drain = stat_drain

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])
        messages.append(
            f"{actor.name} tears open a rift to the void, " f"unleashing pure oblivion!\n"
        )

        # ── Shadow damage ───────────────────────────────────────────
        base = int(actor.stats.intel * self.damage_mod)
        variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        damage = int(base * variance)

        hit, def_msg, damage = target.handle_defenses(
            actor,
            damage,
            typ="Magic",
        )
        if def_msg:
            messages.append(def_msg)

        _, red_msg, damage = target.damage_reduction(
            damage,
            actor,
            typ="Shadow",
        )
        if red_msg:
            messages.append(red_msg)

        if hit and damage > 0:
            target.health.current -= damage
            result.damage = damage
            result.hit = True
            messages.append(f"The void consumes {target.name} for {damage} damage!\n")
        else:
            messages.append(f"The void has no hold on {target.name}.\n")
            return

        if not target.is_alive():
            return

        # ── Instant kill chance ─────────────────────────────────────
        if "Death" not in target.status_immunity and random.random() < self.kill_chance:
            resist = target.check_mod("resist", enemy=actor, typ="Death")
            if resist < 1:
                target.health.current = 0
                messages.append(f"{target.name} is consumed by oblivion!\n")
                return

        # ── Permanent stat drain ────────────────────────────────────
        stats_to_drain = ["strength", "intel", "wisdom", "con"]
        drained = []
        for stat in stats_to_drain:
            current = getattr(target.stats, stat, 0)
            if current > self.stat_drain:
                setattr(target.stats, stat, current - self.stat_drain)
                drained.append(stat)
        if drained:
            messages.append(
                f"The lingering void drains {target.name}'s "
                f"{', '.join(drained)} by {self.stat_drain}!\n"
            )


class GrandHeistEffect(Effect):
    """
    Kobalos ultimate: steal gold + steal item + random powerful debuff
    + Gold Toss finisher.  The ultimate trickster heist.
    """

    def __init__(
        self,
        gold_multiplier: float = 2.0,
        debuff_duration: int = 3,
    ):
        self.gold_multiplier = gold_multiplier
        self.debuff_duration = debuff_duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        messages = result.extra.setdefault("messages", [])
        messages.append(f"{actor.name} cackles and launches into the heist " f"of a lifetime!\n")

        total_damage = 0

        # ── Steal gold ──────────────────────────────────────────────
        gold = getattr(target, "gold", 0)
        stolen_gold = int(gold * 0.3) if gold > 0 else 0
        if stolen_gold > 0:
            target.gold -= stolen_gold
            if hasattr(actor, "owner"):
                actor.owner.gold += stolen_gold
            else:
                actor.gold += stolen_gold
            messages.append(f"{actor.name} steals {stolen_gold} gold from " f"{target.name}!\n")

        # ── Random debuff ───────────────────────────────────────────
        possible_debuffs = ["Blind", "Silence", "Poison"]
        debuff = random.choice(possible_debuffs)
        if (
            debuff not in target.status_immunity
            and f"Status-{debuff}" not in target.equipment["Pendant"].mod
            and "Status-All" not in target.equipment["Pendant"].mod
            and not target.status_effects[debuff].active
            and not target.magic_effects["Mana Shield"].active
        ):
            target.status_effects[debuff].active = True
            target.status_effects[debuff].duration = self.debuff_duration
            if debuff == "Poison":
                target.status_effects[debuff].extra = max(
                    1,
                    actor.stats.dex // 4,
                )
            try:
                actor._emit_status_event(
                    target,
                    debuff,
                    applied=True,
                    duration=self.debuff_duration,
                    source="Grand Heist",
                )
            except (AttributeError, Exception):
                pass
            messages.append(f"{actor.name} inflicts {debuff} on {target.name}!\n")

        # ── Gold Toss finisher ──────────────────────────────────────
        recipient = getattr(actor, "owner", actor)
        toss_gold = getattr(recipient, "gold", 0)
        if toss_gold > 0:
            gold_dmg = int(random.randint(1, max(1, int(toss_gold**0.5))) * self.gold_multiplier)
            _, red_msg, gold_dmg = target.damage_reduction(
                gold_dmg,
                actor,
                typ="Physical",
            )
            if red_msg:
                messages.append(red_msg)
            if gold_dmg > 0:
                target.health.current -= gold_dmg
                total_damage += gold_dmg
                messages.append(
                    f"{actor.name} hurls a shower of gold coins at "
                    f"{target.name} for {gold_dmg} damage!\n"
                )

        result.damage = total_damage
        result.hit = True


class CataclysmEffect(Effect):
    """
    Zahhak ultimate: cast 3 random high-tier spells from spellbook
    + Dragon Breath + Power Up self.  The dragon of apocalypse
    unleashes everything at once.
    """

    def __init__(
        self,
        spell_count: int = 3,
        breath_multiplier: float = 2.0,
        power_up_duration: int = 3,
    ):
        self.spell_count = spell_count
        self.breath_multiplier = breath_multiplier
        self.power_up_duration = power_up_duration

    def apply(self, actor: Character, target: Character, result: CombatResult) -> None:
        import random

        from src.core.constants import DAMAGE_VARIANCE_HIGH, DAMAGE_VARIANCE_LOW

        messages = result.extra.setdefault("messages", [])
        messages.append(f"{actor.name} roars and unleashes total cataclysm!\n")

        total_damage = 0

        # ── Cast spells from spellbook ──────────────────────────────
        spells = list(actor.spellbook.get("Spells", {}).items())
        if spells:
            chosen = random.sample(
                spells,
                min(self.spell_count, len(spells)),
            )
            for spell_name, spell in chosen:
                try:
                    cast_result = spell.cast(actor, target, special=True)
                    cast_msg = cast_result if isinstance(cast_result, str) else str(cast_result)
                    messages.append(cast_msg)
                except Exception:
                    messages.append(f"{actor.name} attempts {spell_name} " f"but it fizzles.\n")

        # ── Dragon Breath ───────────────────────────────────────────
        base = int((actor.stats.strength + actor.stats.intel) * self.breath_multiplier)
        variance = random.uniform(DAMAGE_VARIANCE_LOW, DAMAGE_VARIANCE_HIGH)
        breath_dmg = int(base * variance)

        _, red_msg, breath_dmg = target.damage_reduction(
            breath_dmg,
            actor,
            typ="Fire",
        )
        if red_msg:
            messages.append(red_msg)

        if breath_dmg > 0 and target.is_alive():
            target.health.current -= breath_dmg
            total_damage += breath_dmg
            messages.append(
                f"{actor.name} unleashes a devastating breath of fire "
                f"for {breath_dmg} damage!\n"
            )

        # ── Power Up self ───────────────────────────────────────────
        if hasattr(actor, "stat_effects") and "Attack" in actor.stat_effects:
            actor.stat_effects["Attack"].active = True
            actor.stat_effects["Attack"].duration = self.power_up_duration
            actor.stat_effects["Attack"].extra = max(
                1,
                actor.combat.attack // 4,
            )
            messages.append(f"{actor.name} surges with draconic power!\n")

        result.damage = total_damage
        result.hit = True
