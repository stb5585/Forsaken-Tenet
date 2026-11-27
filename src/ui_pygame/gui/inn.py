"""
Inn/Tavern system for GUI - handles rest, patron dialogue, and bounty board.
Implements the core tavern logic from town.py adapted for Pygame presenter.
"""

import random

from src.core import main_story, opening_story
from src.core.town import (
    MAX_ACTIVE_BOUNTIES,
    PATRON_DIALOGUES,
    TAVERN_FLAVOR_DIALOGUES,
    active_bounty_count,
)

from .confirmation_popup import ConfirmationPopup
from .level_up import LevelUpScreen
from .location_menu import LocationMenuScreen
from .story_scene import PLAYER_PORTRAIT_KEY, StoryBeat, StorySceneScreen
from .town_base import TownScreenBase


class InnManager(TownScreenBase):
    """Manages inn/tavern interactions with pygame presenter."""

    background_image = "tavern.jpg"
    background_fallback_image = "town.png"
    PATRON_ROLES = {
        "Oren": "Barkeep",
        "Liora": "Waitress",
        "Pell": "Drunkard",
        "Tavin": "Busboy",
        "Joffrey": "Soldier",
        "Duty Soldier": "Soldier",
        "Hooded Figure": "Hooded Figure",
    }

    def __init__(self, presenter, player_char):
        super().__init__(presenter)
        self.player_char = player_char
        self.level_up_screen = LevelUpScreen(presenter.screen, presenter)

    def visit_inn(self):
        """Visit the inn/tavern - integrates with The Thirsty Dog tavern."""
        inn_options = ["Talk to Patrons", "Bounty Board", "Leave"]

        inn_screen = LocationMenuScreen(
            self.presenter,
            "The Thirsty Dog Tavern",
            background_image="tavern.jpg",
        )
        self._popup_background_draw_func = lambda: inn_screen.draw_frame(do_flip=False)
        self._show_first_relic_aftermath()
        self._show_joffrey_departure()

        while True:
            choice_idx = inn_screen.navigate(
                inn_options,
                reset_cursor=False,
                flush_events=True,
                require_key_release=True,
            )

            if choice_idx is None or choice_idx == 2:  # Leave
                if self._show_hooded_triangulus_response():
                    break
                popup = ConfirmationPopup(
                    self.presenter, "Come back whenever you'd like.", show_buttons=False
                )
                popup.show(**self.popup_show_kwargs())
                break

            elif choice_idx == 0:  # Talk to patrons
                self.talk_to_patrons()

            elif choice_idx == 1:  # Bounty Board
                self.show_bounty_board()

    def _show_first_relic_aftermath(self) -> None:
        """Show the one-time tavern debate after the Triangulus report."""
        story = main_story.ensure_state(self.player_char)
        holy = self.player_char.quest_dict.get("Main", {}).get("The Holy Relics")
        if not isinstance(holy, dict) or story.get("first_relic_tavern_aftermath_seen"):
            return
        scene = StorySceneScreen(
            self.presenter,
            "The Thirsty Dog — After Triangulus",
            participants=("Excited Patron", "Uneasy Patron", "Angry Patron"),
            participant_anchors={"Joffrey": "Oren", "Pell": "Oren", "Tavin": "Oren"},
            background_image="tavern.jpg",
            player_char=self.player_char,
        )
        scene.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "A stool scrapes as you come in. Someone at the bar makes room for you and half the bench leans closer.",
                ),
                StoryBeat(
                    "Excited Patron", "Six of them, is it? Let's see the one you brought up."
                ),
                StoryBeat("Uneasy Patron", "In here? My sister sleeps just upstairs."),
                StoryBeat(
                    "Angry Patron",
                    "Tomas is dead and Mira's gone. Give me a hammer. I'll see to it.",
                ),
                StoryBeat("Liora", "Gone where? If somebody's heard from Mira, I'd like to know."),
                StoryBeat("Angry Patron", "I meant she hasn't come back."),
                StoryBeat("Oren", "Then say that. And you can leave my hammer where it is."),
                StoryBeat(
                    "Joffrey",
                    "Mira drew those marks for us. I'd like another look at what she saw.",
                ),
                StoryBeat(
                    "Pell", "Anybody mind if I finish my supper before you get the hammer out?"
                ),
                StoryBeat(
                    "Narrator",
                    "Oren slides Pell's bowl back within reach. Tavin clears an untouched cup beside you.",
                ),
                StoryBeat("Tavin", "When you picked it up, did it say anything?"),
            )
        )
        story["first_relic_tavern_aftermath_seen"] = True

    def _show_hooded_triangulus_response(self) -> bool:
        """Echo the player's altar answer on the first post-aftermath tavern exit."""
        story = main_story.ensure_state(self.player_char)
        if not story.get("first_relic_tavern_aftermath_seen") or story.get(
            "hooded_figure_triangulus_response_seen"
        ):
            return False
        answer = story.get("triangulus_identity_answer")
        echo = opening_story.TRIANGULUS_ANSWER_TEXT.get(answer) if isinstance(answer, str) else None
        scene = StorySceneScreen(
            self.presenter,
            "Outside The Thirsty Dog",
            participants=("Hooded Figure",),
            background_image="intro_06_thirsty_dog.jpg",
            player_char=self.player_char,
        )
        scene.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "You're two steps past the tavern door when a voice under the eaves speaks.",
                ),
                StoryBeat(
                    "Hooded Figure",
                    f"“{echo}”" if echo else "You answered the question at the altar.",
                ),
            )
        )
        choice = scene.choose(
            "Do you stop?",
            ["Who told you that?", "Keep walking"],
            record_selection=False,
        )
        if choice == 0:
            player_name = str(getattr(self.player_char, "name", None) or "You")
            scene.show_dialogue(
                (
                    StoryBeat(player_name, "Who told you that?", PLAYER_PORTRAIT_KEY),
                    StoryBeat(
                        "Narrator",
                        "The tavern door opens behind you. The Figure waits for it to shut.",
                    ),
                    StoryBeat("Hooded Figure", "Does anyone in there know what you said?"),
                )
            )
        story["hooded_figure_triangulus_response_seen"] = True
        return True

    def _show_joffrey_departure(self) -> None:
        """Send the scout after the missing patrol once his earlier scenes have played."""
        story = main_story.ensure_state(self.player_char)
        if story["joffrey_departed"] or "A Bad Dream" in self.player_char.quest_dict.get(
            "Main", {}
        ):
            return
        if not all(
            story[key]
            for key in (
                "joffrey_tavern_scene_seen",
                "joffrey_patrol_briefing_seen",
                "joffrey_route_review_seen",
                "hexagonum_report_seen",
            )
        ):
            return
        scene = StorySceneScreen(
            self.presenter,
            "The Thirsty Dog — The Missing Patrol",
            participants=("Joffrey", "Liora", "Tavin"),
            background_image="tavern.jpg",
            player_char=self.player_char,
        )
        scene.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "Joffrey has spread a patrol map across two place settings. A slip of paper lies beside it, still wet at the edges.",
                ),
                StoryBeat(
                    "Joffrey",
                    "The fourth-floor patrol missed both bells. They took my survey. Look where somebody put the return mark.",
                ),
                StoryBeat("Liora", "At the fork. Is that blood?"),
                StoryBeat(
                    "Joffrey",
                    "Red survey ink. But I rubbed that fork out before I gave them the map.",
                ),
                StoryBeat(
                    "Liora",
                    "Then let Caedmon have a look. His watch is changing. You could take two of them with you.",
                ),
                StoryBeat(
                    "Tavin", "How long would it take them to walk from that fork to the pens?"
                ),
                StoryBeat(
                    "Narrator",
                    "Joffrey measures the distance with his thumb. He leaves his supper where it is.",
                ),
                StoryBeat(
                    "Joffrey", "Less than a change of watch. I can catch them at the lower steps."
                ),
                StoryBeat(
                    "Liora",
                    "I'd sooner you waited. Give me the slip, at least. I'll see the others get the right map.",
                ),
                StoryBeat(
                    "Joffrey",
                    "Tell them to look for my chalk low on the wall. The lamps throw a shadow over the high marks.",
                ),
                StoryBeat(
                    "Narrator",
                    "Liora folds the slip into her apron. Joffrey takes the chalk from her pencil cup and goes.",
                ),
            )
        )
        story["joffrey_departed"] = True

    def _random_patron_comment(self, patron: str) -> str | None:
        # Gather patron-specific dialogues eligible for the player's level
        combined_pool: list[str] = []
        dialogues = PATRON_DIALOGUES.get(patron)
        player_level = self.player_char.player_level()
        if dialogues:
            eligible_levels = [lvl for lvl in dialogues if player_level >= lvl]
            if dialogues and eligible_levels:
                # Drunkard uses only the high-tier messages once level 65 is reached
                if patron == "Drunkard" and player_level >= 65:
                    eligible_levels = [lvl for lvl in eligible_levels if lvl == 65]
                chosen_level = random.choice(eligible_levels)
                combined_pool.extend(dialogues[chosen_level])

        # Always include general tavern flavor comments in the random pool
        combined_pool.extend(TAVERN_FLAVOR_DIALOGUES)

        return random.choice(combined_pool) if combined_pool else None

    def _build_patron_list(self):
        """Build the list of available patrons based on quest state."""
        options = ["Oren"]
        if "A Bad Dream" in self.player_char.quest_dict.get("Main", {}):
            if not self.player_char.quest_dict["Main"]["A Bad Dream"].get("Turned In"):
                options.append("Liora")
            else:
                options.append("Tavin")
        else:
            options.append("Liora")
        # Pell is present in the arrival scene, so he remains available from
        # the player's first deliberate tavern visit onward.
        options.append("Pell")
        if self.player_char.player_level() >= 10:
            gone = main_story.ensure_state(self.player_char)[
                "joffrey_departed"
            ] or "A Bad Dream" in self.player_char.quest_dict.get("Main", {})
            options.append("Duty Soldier" if gone else "Joffrey")
            if self.player_char.player_level() >= 25:
                if "Red Dragon" in self.player_char.quest_dict.get("Main", {}):
                    if not self.player_char.quest_dict["Main"]["Red Dragon"].get("Turned In"):
                        options.append("Hooded Figure")
                else:
                    options.append("Hooded Figure")
        options.append("Back")
        return options

    def talk_to_patrons(self):
        """Talk to tavern patrons and access their quests."""
        patrons_screen = LocationMenuScreen(
            self.presenter,
            "The Thirsty Dog - Patrons",
            background_image="tavern.jpg",
        )

        while True:
            # Rebuild patron list each iteration to reflect quest state changes
            options = self._build_patron_list()
            patrons_screen.set_option_portraits(
                [
                    "Soldier" if patron == "Duty Soldier" else patron if patron != "Back" else None
                    for patron in options
                ]
            )
            choice = patrons_screen.navigate(
                options,
                reset_cursor=False,
                flush_events=True,
                require_key_release=True,
            )
            if choice is None or (choice is not None and options[choice] == "Back"):
                return

            patron = options[choice]
            patron_role = self.PATRON_ROLES[patron]
            # Route to quest manager for applicable quest givers
            if patron_role in (
                "Barkeep",
                "Waitress",
                "Soldier",
                "Busboy",
                "Hooded Figure",
                "Drunkard",
            ):
                from .quest_manager import QuestManager

                qm = QuestManager(
                    self.presenter,
                    self.player_char,
                    quest_text_renderer=lambda text, patron=patron: patrons_screen.display_quest_text(
                        text, npc_name=patron
                    ),
                    renderer_preserve_formatting=True,
                )
                did_action, showed_message = qm.check_and_offer(
                    patron_role, show_help=False, suppress_no_quests_message=True
                )
                if not did_action and not showed_message:
                    # Mix a random patron comment with a random quest help hint
                    pool = []
                    hint = qm.get_random_help_hint(patron_role)
                    if hint:
                        pool.append(hint)
                    comment = self._random_patron_comment(patron_role)
                    if comment:
                        pool.append(comment)
                    if pool:
                        selection = random.choice(pool)
                        qm.quest_text_renderer(selection)
            else:
                # This branch is not used since all patrons are handled above,
                # but keep a fallback to show a general tavern flavor comment.
                patron_dialogue = random.choice(TAVERN_FLAVOR_DIALOGUES)
                popup = ConfirmationPopup(self.presenter, patron_dialogue, show_buttons=False)
                popup.show(**self.popup_show_kwargs())

    def show_bounty_board(self):
        """Show and manage bounty quests from the tavern."""
        # Check for completable bounties
        bounty_dict = self.player_char.quest_dict.get("Bounty", {})

        bounty_screen = LocationMenuScreen(
            self.presenter, "Bounty Board", background_image="tavern.jpg"
        )
        previous_background_draw_func = self._popup_background_draw_func
        self._popup_background_draw_func = lambda: bounty_screen.draw_frame(do_flip=False)

        try:
            while True:
                game = getattr(self.presenter, "game", None)
                update_bounties = getattr(game, "update_bounties", None)
                if callable(update_bounties):
                    update_bounties()

                bounty_options = ["Accept Bounty", "View Active Bounties", "Leave"]

                # Check if any bounties are complete
                completable = [name for name, data in bounty_dict.items() if data[2]]
                if completable:
                    bounty_options.insert(1, "Turn In Bounty")
                if bounty_dict:
                    abandon_idx = len(bounty_options) - 1
                    bounty_options.insert(abandon_idx, "Abandon Bounty")

                choice_idx = bounty_screen.navigate(
                    bounty_options,
                    reset_cursor=False,
                    flush_events=True,
                    require_key_release=True,
                )

                if choice_idx is None or bounty_options[choice_idx] == "Leave":
                    break

                if bounty_options[choice_idx] == "Accept Bounty":
                    self.accept_bounty()

                elif bounty_options[choice_idx] == "Turn In Bounty":
                    self.turn_in_bounty(completable)

                elif bounty_options[choice_idx] == "Abandon Bounty":
                    self.abandon_bounty()

                elif bounty_options[choice_idx] == "View Active Bounties":
                    self.view_active_bounties()
        finally:
            self._popup_background_draw_func = previous_background_draw_func

    def accept_bounty(self):
        """Accept a bounty from the board."""
        bounty_dict = self.player_char.quest_dict.get("Bounty", {})
        bounty_screen = LocationMenuScreen(
            self.presenter, "Accept Bounty", background_image="tavern.jpg"
        )

        while True:
            if active_bounty_count(self.player_char) >= MAX_ACTIVE_BOUNTIES:
                popup = ConfirmationPopup(
                    self.presenter,
                    f"You can hold at most {MAX_ACTIVE_BOUNTIES} active bounties.",
                    show_buttons=False,
                )
                popup.show(**self.popup_show_kwargs())
                return

            # Get available bounties
            bounties_available = []
            if hasattr(self.presenter, "game") and hasattr(self.presenter.game, "bounties"):
                game_bounties = self.presenter.game.bounties
                # Only offer bounties the player doesn't already have
                for bounty_name in game_bounties.keys():
                    if bounty_name not in bounty_dict:
                        bounties_available.append(bounty_name)

            if not bounties_available:
                popup = ConfirmationPopup(
                    self.presenter, "No new bounties available at this time.", show_buttons=False
                )
                popup.show(**self.popup_show_kwargs())
                return

            # Build display list
            bounty_display = [(name, 0) for name in bounties_available]
            bounty_display.append(("Back", 0))

            choice = bounty_screen.navigate_with_content(
                bounty_display,
                flush_events=True,
                require_key_release=True,
            )

            if choice is None or bounty_display[choice][0] == "Back":
                return

            bounty_name = bounty_display[choice][0]
            bounty_data = self.presenter.game.bounties[bounty_name]
            enemy_obj = bounty_data.get("enemy")
            enemy_name = getattr(enemy_obj, "name", bounty_data.get("enemy_name", "Unknown"))
            if enemy_name == "Unknown" and isinstance(enemy_obj, str):
                enemy_name = enemy_obj
            required = self._bounty_required_count(bounty_data)

            # Add bounty to player's quest dict
            self.player_char.quest_dict["Bounty"][bounty_name] = [
                bounty_data,
                0,
                False,
            ]
            self._remove_board_bounty(bounty_name)

            # Show bounty info
            info_msg = (
                f"Bounty Accepted: {bounty_name}\n"
                f"Target: {enemy_name}\n"
                f"Enemies to defeat: {required}\n"
                f"Reward: {bounty_data.get('gold', 0)} Gold, {bounty_data.get('exp', 0)} Experience"
            )
            popup = ConfirmationPopup(self.presenter, info_msg, show_buttons=False)
            popup.show(**self.popup_show_kwargs())

    @staticmethod
    def _bounty_required_count(bounty_data):
        try:
            return max(1, int(bounty_data.get("num", 1) or 1))
        except (AttributeError, TypeError, ValueError):
            return 1

    def turn_in_bounty(self, completable):
        """Turn in completed bounties using the inn UI."""
        if not completable:
            popup = ConfirmationPopup(self.presenter, "No bounties to turn in.", show_buttons=False)
            popup.show(**self.popup_show_kwargs())
            return

        bounty_screen = LocationMenuScreen(
            self.presenter, "Turn In Bounty", background_image="tavern.jpg"
        )
        remaining = list(completable)
        while remaining:
            bounty_options = [(name, 0) for name in remaining]
            bounty_options.append(("Back", 0))
            choice_idx = bounty_screen.navigate_with_content(
                bounty_options,
                flush_events=True,
                require_key_release=True,
            )

            if choice_idx is None or bounty_options[choice_idx][0] == "Back":
                return

            bounty_name = bounty_options[choice_idx][0]
            bounty_data = self.player_char.quest_dict["Bounty"].get(bounty_name)
            if not bounty_data:
                remaining.remove(bounty_name)
                continue

            bounty = bounty_data[0]
            gold = bounty.get("gold", 0)
            exp = bounty.get("exp", 0)
            self.player_char.gold += gold
            from src.core.progression import award_experience

            level_result = award_experience(self.player_char, exp)
            self.player_char._pending_level_up_result = (
                level_result if level_result.new_level > level_result.old_level else None
            )
            reward_lines = [
                f"Bounty Complete: {bounty_name}",
                "",
                "Rewards:",
                f"• {gold} Gold",
                f"• {exp} Experience",
            ]
            if bounty.get("reward"):
                reward_item = bounty["reward"]()
                self.player_char.modify_inventory(reward_item)
                reward_lines.append(f"• {reward_item.name}")
            reward_msg = "\n".join(reward_lines)
            previous_background_draw_func = self._popup_background_draw_func
            self._popup_background_draw_func = (
                lambda options=bounty_options: bounty_screen.draw_content_selection_frame(
                    options,
                    do_flip=False,
                )
            )
            try:
                popup = ConfirmationPopup(self.presenter, reward_msg, show_buttons=False)
                popup.show(**self.popup_show_kwargs())
            finally:
                self._popup_background_draw_func = previous_background_draw_func

            # Remove completed bounty and retain the selector for remaining entries.
            del self.player_char.quest_dict["Bounty"][bounty_name]
            self._remove_board_bounty(bounty_name)
            remaining.remove(bounty_name)

            if level_result.new_level > level_result.old_level:
                self.level_up()

    def _remove_board_bounty(self, bounty_name):
        """Remove an accepted or completed bounty from the current board."""
        game = getattr(self.presenter, "game", None)
        bounties = getattr(game, "bounties", None)
        if isinstance(bounties, dict):
            bounties.pop(bounty_name, None)

    def abandon_bounty(self):
        """Abandon an active bounty without returning it to the current board."""
        bounty_dict = self.player_char.quest_dict.get("Bounty", {})

        if not bounty_dict:
            popup = ConfirmationPopup(
                self.presenter, "No active bounties to abandon.", show_buttons=False
            )
            popup.show(**self.popup_show_kwargs())
            return

        bounty_screen = LocationMenuScreen(
            self.presenter, "Abandon Bounty", background_image="tavern.jpg"
        )
        while bounty_dict:
            bounty_options = [(name, 0) for name in bounty_dict]
            bounty_options.append(("Back", 0))
            choice_idx = bounty_screen.navigate_with_content(
                bounty_options,
                flush_events=True,
                require_key_release=True,
            )

            if choice_idx is None or bounty_options[choice_idx][0] == "Back":
                return

            bounty_name = bounty_options[choice_idx][0]
            previous_background_draw_func = self._popup_background_draw_func
            self._popup_background_draw_func = (
                lambda options=bounty_options: bounty_screen.draw_content_selection_frame(
                    options,
                    do_flip=False,
                )
            )
            try:
                popup = ConfirmationPopup(
                    self.presenter,
                    f"Are you sure you want to abandon the {bounty_name} bounty?",
                    show_buttons=True,
                )
                if popup.show(**self.popup_show_kwargs()):
                    del bounty_dict[bounty_name]
                    notice = ConfirmationPopup(
                        self.presenter,
                        f"Abandoned bounty: {bounty_name}",
                        show_buttons=False,
                    )
                    notice.show(**self.popup_show_kwargs())
            finally:
                self._popup_background_draw_func = previous_background_draw_func

    def view_active_bounties(self):
        """View all active bounty quests."""
        bounty_dict = self.player_char.quest_dict.get("Bounty", {})

        if not bounty_dict:
            popup = ConfirmationPopup(
                self.presenter,
                "No active bounties.\n\nCheck back later for new opportunities!",
                show_buttons=False,
            )
            popup.show(**self.popup_show_kwargs())
            return

        bounty_screen = LocationMenuScreen(
            self.presenter, "Active Bounties", background_image="tavern.jpg"
        )

        # Build display list
        bounty_display = []
        for name, data in bounty_dict.items():
            bounty = data[0]
            killed = data[1]
            complete = data[2]
            status = "✓ Complete" if complete else f"{killed}/{bounty['num']} killed"
            display_text = f"{name} - {status}"
            bounty_display.append((display_text, 0))

        bounty_display.append(("Back", 0))

        choice = bounty_screen.navigate_with_content(
            bounty_display,
            flush_events=True,
            require_key_release=True,
        )

        if choice is None or bounty_display[choice][0] == "Back":
            return

    def level_up(self):
        """Handle level up with GUI interface."""
        # show_level_up already displays all level-up information
        self.level_up_screen.show_level_up(self.player_char, None)
