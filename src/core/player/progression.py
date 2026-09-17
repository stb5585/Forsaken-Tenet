"""Player leveling, class upgrades, and quest progression."""

import random

from .. import quest_progress


class PlayerProgressionMixin:
    def level_up(self):
        """Award enough experience to reach the next character level."""
        from ..progression import (
            award_experience,
            cumulative_experience_for_level,
            ensure_progression,
        )

        progression = ensure_progression(self)
        if progression.level >= 100:
            return None
        required_total = cumulative_experience_for_level(progression.level + 1)
        return award_experience(
            self,
            max(0, required_total - progression.total_xp),
            rng=random,
        )

    def class_upgrades(self, game, enemy):
        upgrade_str = ""
        if self.cls.name == "Soulcatcher":
            state = getattr(self, "absorb_essence_state", None)
            if not isinstance(state, dict):
                self.absorb_essence_state = {}
                state = self.absorb_essence_state

            state.setdefault("floor", self.location_z)
            state.setdefault("procs_this_floor", 0)
            state.setdefault("procs_by_enemy", {})
            state.setdefault(
                "stat_gains",
                {
                    "strength": 0,
                    "intel": 0,
                    "wisdom": 0,
                    "con": 0,
                    "charisma": 0,
                    "dex": 0,
                },
            )
            state.setdefault("health_gains", 0)
            state.setdefault("mana_gains", 0)
            state.setdefault("level_gains", 0)
            state.setdefault("dragon_gold_claimed", False)

            if state["floor"] != self.location_z:
                state["floor"] = self.location_z
                state["procs_this_floor"] = 0
                state["procs_by_enemy"] = {}

            if state["procs_this_floor"] >= self.ABSORB_ESSENCE_MAX_PROCS_PER_FLOOR:
                return upgrade_str

            enemy_proc_count = state["procs_by_enemy"].get(enemy.name, 0)
            if enemy_proc_count >= self.ABSORB_ESSENCE_MAX_PROCS_PER_ENEMY_PER_FLOOR:
                return upgrade_str

            luck_bonus = min(4, self.check_mod("luck", enemy=enemy, luck_factor=20))
            chance = max(12, 19 - luck_bonus)
            from ..progression import has_talent

            if has_talent(self, "soulcatcher.discerning-vessel"):
                chance = max(6, chance - 8)
            if not random.randint(0, chance):
                applied = False

                if (
                    enemy.name in ["Behemoth", "Golem", "Iron Golem"]
                    and state["stat_gains"]["strength"] < self.ABSORB_ESSENCE_MAX_STAT_GAINS
                ):
                    upgrade_str += "Gain 1 strength.\n"
                    self.stats.strength += 1
                    state["stat_gains"]["strength"] += 1
                    applied = True

                if (
                    enemy.name in ["Lich", "Brain Gorger"]
                    and state["stat_gains"]["intel"] < self.ABSORB_ESSENCE_MAX_STAT_GAINS
                ):
                    upgrade_str += "Gain 1 intelligence.\n"
                    self.stats.intel += 1
                    state["stat_gains"]["intel"] += 1
                    applied = True

                if (
                    enemy.name in ["Aboleth", "Hydra"]
                    and state["stat_gains"]["wisdom"] < self.ABSORB_ESSENCE_MAX_STAT_GAINS
                ):
                    upgrade_str += "Gain 1 wisdom.\n"
                    self.stats.wisdom += 1
                    state["stat_gains"]["wisdom"] += 1
                    applied = True

                if (
                    enemy.name in ["Warforged", "Archvile"]
                    and state["stat_gains"]["con"] < self.ABSORB_ESSENCE_MAX_STAT_GAINS
                ):
                    upgrade_str += "Gain 1 constitution.\n"
                    self.stats.con += 1
                    state["stat_gains"]["con"] += 1
                    applied = True

                if (
                    enemy.name in ["Beholder", "Wyrm"]
                    and state["stat_gains"]["charisma"] < self.ABSORB_ESSENCE_MAX_STAT_GAINS
                ):
                    upgrade_str += "Gain 1 charisma.\n"
                    self.stats.charisma += 1
                    state["stat_gains"]["charisma"] += 1
                    applied = True

                if (
                    enemy.name in ["Shadow Serpent", "Wyvern"]
                    and state["stat_gains"]["dex"] < self.ABSORB_ESSENCE_MAX_STAT_GAINS
                ):
                    upgrade_str += "Gain 1 dexterity.\n"
                    self.stats.dex += 1
                    state["stat_gains"]["dex"] += 1
                    applied = True

                if (
                    enemy.name in ["Basilisk", "Sandworm"]
                    and state["health_gains"] < self.ABSORB_ESSENCE_MAX_HEALTH_GAINS
                ):
                    hp_gain = min(5, self.ABSORB_ESSENCE_MAX_HEALTH_GAINS - state["health_gains"])
                    if hp_gain > 0:
                        upgrade_str += f"Gain {hp_gain} hit points.\n"
                        self.health.max += hp_gain
                        self.health.current += hp_gain
                        state["health_gains"] += hp_gain
                        applied = True

                if (
                    enemy.name == "Mind Flayer"
                    and state["mana_gains"] < self.ABSORB_ESSENCE_MAX_MANA_GAINS
                ):
                    mana_gain = min(5, self.ABSORB_ESSENCE_MAX_MANA_GAINS - state["mana_gains"])
                    if mana_gain > 0:
                        upgrade_str += f"Gain {mana_gain} mana points.\n"
                        self.mana.max += mana_gain
                        self.mana.current += mana_gain
                        state["mana_gains"] += mana_gain
                        applied = True

                if (
                    enemy.name in ["Jester", "Domingo", "Cerberus"]
                    and state["level_gains"] < self.ABSORB_ESSENCE_MAX_LEVEL_GAINS
                    and not self.max_level()
                ):
                    upgrade_str += "Gain enough experience to level.\n"
                    self.level_up()
                    state["level_gains"] += 1
                    applied = True

                if enemy.name == "Red Dragon" and not state["dragon_gold_claimed"]:
                    upgrade_str += "You find a cache of gold, doubling your current stash.\n"
                    self.gold *= 2
                    state["dragon_gold_claimed"] = True
                    applied = True

                if applied:
                    upgrade_str = f"You absorb part of the {enemy.name}'s soul.\n" + upgrade_str
                    state["procs_this_floor"] += 1
                    state["procs_by_enemy"][enemy.name] = enemy_proc_count + 1
                    if has_talent(self, "soulcatcher.eternal-harvest"):
                        restored = min(
                            int(self.mana.max) - int(self.mana.current),
                            max(1, int(self.mana.max * 0.05)),
                        )
                        self.mana.current += restored
                        upgrade_str += f"Eternal Harvest restores {restored} mana.\n"
        from ..classes import promotion_kits, transformation

        if transformation.permanent_class_name(self) == "Lycan" and enemy.name == "Red Dragon":
            essence_message = promotion_kits.unlock_dragon_essence(self)
            if essence_message:
                upgrade_str += essence_message
        return upgrade_str

    def quests(self, enemy: object | None = None, item: object | None = None) -> str:
        """Update quest completion state for enemy, item, or relic progress.

        Enemy completions cover bounties plus named Main/Side defeat quests.
        Item completions match either item display names or class names so
        JSON-loaded quest definitions and object-backed definitions both work.
        When no enemy or item is supplied, the Holy Relics aggregate is checked.
        """
        quest_message = ""
        if enemy is not None:
            try:
                from ..classes import wizard

                quest_message += wizard.record_ultimate_quest_defeat(
                    self,
                    enemy.name,
                )
            except Exception:
                pass
            if enemy.name in self.quest_dict["Bounty"]:
                if not self.quest_dict["Bounty"][enemy.name][2]:
                    self.quest_dict["Bounty"][enemy.name][1] += 1
                    if (
                        self.quest_dict["Bounty"][enemy.name][1]
                        >= self.quest_dict["Bounty"][enemy.name][0]["num"]
                    ):
                        self.quest_dict["Bounty"][enemy.name][2] = True
            if enemy.name == "Waitress":
                self.quest_dict["Side"]["Something to Cry About"]["Completed"] = True
                quest_message += "You have completed the quest Something to Cry About.\n"
            else:
                for quest in self.quest_dict["Main"]:
                    if (
                        self.quest_dict["Main"][quest]["What"] == enemy.name
                        and not self.quest_dict["Main"][quest]["Completed"]
                    ):
                        self.quest_dict["Main"][quest]["Completed"] = True
                        quest_message += f"You have completed the quest {quest}.\n"

                quest_message += quest_progress.record_defeat(self, enemy.name)
        elif item is not None:
            quest_message += quest_progress.record_collection(self, item)
        else:
            quest_message += quest_progress.sync_relic_story_progress(self)
        return quest_message
