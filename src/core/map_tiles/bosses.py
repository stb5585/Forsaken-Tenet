"""Boss-room tiles and their encounter rules."""

from .. import enemies, thieves_guild
from .paths import SpecialTile
from .rules import (
    JESTER_TOKENS_REQUIRED,
    REALM_OF_CAMBION_LEVEL,
    _apply_cambion_antimagic,
    deactivate_funhouse_teleporters,
    reveal_cambion_code_clue,
)


class BossRoom(SpecialTile):

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = None
        self.defeated = False

    def available_actions(self, player_char):
        if player_char.state == "fight":
            action_list = ["Attack", "Defend", "Use Item"]
            if not player_char.abilities_suppressed():
                if player_char.usable_abilities("Spells"):
                    action_list.insert(1, "Cast Spell")
                if player_char.usable_abilities("Skills"):
                    action_list.insert(1, "Use Skill")
            action_list = player_char.additional_actions(action_list)
            return action_list
        return []

    def modify_player(self, game):
        self.visited = True
        self.adjacent_visited(game.player_char)
        if self.z == REALM_OF_CAMBION_LEVEL:
            reveal_cambion_code_clue(game.player_char, (self.x, self.y, self.z))
        if not self.defeated:
            self.generate_enemy()
            if self.enemy.is_alive():
                self.enter_combat(game.player_char)

    def enter_combat(self, player_char):
        _apply_cambion_antimagic(self, player_char, self.enemy)
        player_char.state = "fight"

    def special_text(self, game):
        if not self.read:
            enemy_instance = (
                self.enemy
                if isinstance(self.enemy, str)
                else (self.enemy() if callable(self.enemy) else self.enemy)
            )
            enemy_name = (
                enemy_instance.name if hasattr(enemy_instance, "name") else str(enemy_instance)
            )
            game.special_event(enemy_name)
            self.read = True

    def generate_enemy(self):
        if self.visited:
            try:
                self.enemy = self.enemy()
            except TypeError:
                pass


class ThievesGuildTrialBossRoom(BossRoom):
    """Hidden initiation fight for promoted Footpad-line guild candidates."""

    BOSS_BY_BRANCH = {
        "cutpurse": enemies.GuildCutpurseBoss,
        "inquest": enemies.GuildInquestBoss,
        "contract": enemies.GuildContractBoss,
        "arcane": enemies.GuildArcaneBoss,
    }

    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.GuildCutpurseBoss

    def _branch_for(self, player_char):
        if thieves_guild.member(player_char) or thieves_guild.has_signet(player_char):
            return ""
        state = thieves_guild.ensure_state(player_char)
        if not state.get("trial_started"):
            return ""
        branch = state.get("trial_branch", "")
        return branch if branch in self.BOSS_BY_BRANCH else ""

    def modify_player(self, game):
        branch = self._branch_for(game.player_char)
        if not branch:
            self.defeated = True
            self.enemy = None
            self.visited = True
            self.adjacent_visited(game.player_char)
            return
        self.enemy = self.BOSS_BY_BRANCH[branch]
        state = thieves_guild.ensure_state(game.player_char)
        state["trial_branch"] = branch
        super().modify_player(game)

    def intro_text(self, game):
        branch = self._branch_for(game.player_char)
        if not branch:
            return (
                "An empty room waits behind the false wall.\n\n"
                "Whatever test belongs here has not been written into the guild ledger yet."
            )
        label = thieves_guild.branch_label(branch)
        return (
            f"{label}\n\n"
            "A masked guild examiner waits behind the false wall, a blackened signet "
            "hanging from one gloved hand. Win the trial and bring the signet home."
        )


class MinotaurBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Minotaur

    def intro_text(self, game):
        if not self.enemy:
            return "The remains of the Minotaur lay at your feet.\n"
        return super().intro_text(game)


class BarghestBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Barghest

    def intro_text(self, game):
        if not self.enemy:
            return "A slumped mass of fur and blood mark where the Barghest was slain.\n"
        return (
            super().intro_text(game)
            + "The shape in the chamber will not hold. Wolf, goblin, hound, and something "
            "between them pass across the same pair of spectral eyes. Every form looks "
            "briefly like the one you expected to see.\n"
        )


class PseudodragonBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Pseudodragon

    def intro_text(self, game):
        if not self.enemy:
            return "A lavish lair bespeckled with the dust of the smote Pseudodragon.\n"
        return super().intro_text(game)


class NightmareBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Nightmare

    def intro_text(self, game):
        if not self.enemy:
            return (
                "A heap of bone and sinew is all that is left of the horror that \n"
                "once befell this hall.\n"
            )
        return super().intro_text(game)


class CockatriceBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Cockatrice

    def intro_text(self, game):
        if not self.enemy:
            return (
                "Nothing but bones and feathers are left to mark the spot where \n"
                "the Cockatrice was defeated."
            )
        return super().intro_text(game)


class WendigoBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Wendigo

    def intro_text(self, game):
        if not self.enemy:
            return "The air feels cold here...but no sign of the slain Wendigo."
        return super().intro_text(game)

    def special_text(self, game):
        return super().special_text(game)


class IronGolemBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.IronGolem

    def intro_text(self, game):
        if not self.enemy:
            return ""
        return super().intro_text(game)


class GolemBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Golem

    def intro_text(self, game):
        if not self.enemy:
            return ""
        return super().intro_text(game)


class JesterBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Jester
        self.tokens_required = JESTER_TOKENS_REQUIRED

    def intro_text(self, game):
        if not self.enemy:
            return "The twisted carnival around you suddenly snaps back to reality. You have vanquished the Jester.\n"
        return super().intro_text(game)

    def special_text(self, game):
        """Handle victory condition and exit the funhouse."""
        if not self.enemy and game.player_char.location_z == 7:
            # Jester defeated - exit the funhouse
            deactivate_funhouse_teleporters(game.player_char)
            game.player_char.exit_funhouse()
            if hasattr(game, "special_event"):
                game.special_event("Jester Defeated")
        else:
            super().special_text(game)


class DomingoBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Domingo

    def intro_text(self, game):
        if not self.enemy:
            return ""
        return super().intro_text(game)


class RedDragonBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.RedDragon

    def intro_text(self, game):
        if not self.enemy:
            return ""
        return super().intro_text(game)


class CirceBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Circe

    def intro_text(self, game):
        if not self.enemy:
            return ""
        return super().intro_text(game)


class MerzhinBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Merzhin

    def intro_text(self, game):
        if not self.enemy:
            return (
                "Merzhin's illusions have collapsed, leaving only the fading hush of the realm.\n"
            )
        return super().intro_text(game)


class CerberusBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Cerberus

    def intro_text(self, game):
        if not self.enemy:
            return ""
        return super().intro_text(game)


class FinalBossRoom(BossRoom):
    def __init__(self, x, y, z):
        super().__init__(x, y, z)
        self.enemy = enemies.Vesperion

    def intro_text(self, game):
        if not self.enemy:
            return ""
        return super().intro_text(game)
