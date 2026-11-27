"""
GUI Quest Manager: offers and turns in quests using Pygame presenter.
Adapts core quest data from town.quest_dict for Pygame presentation.
"""

from __future__ import annotations

import copy
import random
import textwrap
from typing import Any

from src.core import items, main_story, quest_progress
from src.core.player.combat import has_special_power_reward
from src.core.town import (
    RESPONSE_MAP,
    already_defeated_enemy,
    get_reactive_town_hints,
    quest_dict,
)

from .confirmation_popup import ConfirmationPopup, RewardSelectionPopup
from .level_up import LevelUpScreen
from .story_scene import PLAYER_PORTRAIT_KEY, StoryBeat, StorySceneScreen


class QuestManager:
    def __init__(
        self,
        presenter,
        player_char,
        quest_text_renderer=None,
        quest_choice_renderer=None,
        wrap_width=50,
        renderer_preserve_formatting: bool = False,
        story_background_draw_func=None,
    ):
        self.presenter = presenter
        self.screen = presenter.screen
        self.player_char = player_char
        self.quest_text_renderer = quest_text_renderer
        self.quest_choice_renderer = quest_choice_renderer
        self.wrap_width = wrap_width  # characters
        self.renderer_preserve_formatting = renderer_preserve_formatting
        self.story_background_draw_func = story_background_draw_func

    @staticmethod
    def _popup_show_kwargs() -> dict[str, bool]:
        return {"flush_events": True, "require_key_release": True}

    def _show_popup(self, popup):
        return popup.show(**self._popup_show_kwargs())

    def _format_for_renderer(self, text: str) -> str:
        if self.renderer_preserve_formatting:
            return text

        wrapped_lines: list[str] = []
        for raw_line in text.split("\n"):
            if not raw_line.strip():
                wrapped_lines.append("")
                continue
            wrapped = textwrap.wrap(raw_line, width=self.wrap_width)
            if wrapped:
                wrapped_lines.extend(wrapped)
            else:
                wrapped_lines.append(raw_line)
        return "\n".join(wrapped_lines)

    def _ensure_chalice_progress(self, quest_data: dict | None) -> dict | None:
        if not quest_data:
            return None
        progress = quest_data.setdefault("Chalice Progress", {})
        for key in ("Hooded", "Map", "Sergeant", "Adventurer", "Revealed", "Spawned"):
            progress.setdefault(key, False)
        return progress

    def _show_hint(self, message: str) -> None:
        if self.quest_text_renderer:
            self.quest_text_renderer(self._format_for_renderer(message))
        else:
            wrapped = "\n".join(textwrap.wrap(message, width=self.wrap_width))
            popup = ConfirmationPopup(self.presenter, wrapped, show_buttons=False)
            self._show_popup(popup)

    def _handle_chalice_giver_hint(self, giver: str) -> bool:
        quest_data = self.player_char.quest_dict.get("Side", {}).get("The Holy Grail of Quests")
        if not quest_data or quest_data.get("Completed") or quest_data.get("Turned In"):
            return False
        progress = self._ensure_chalice_progress(quest_data)
        if not progress:
            return False

        if giver == "Hooded Figure" and not progress.get("Hooded"):
            self._show_hint(
                "The Hooded Figure whispers that a map to the Golden Chalice was last seen with an adventurer carrying an ugly sword."
            )
            progress["Hooded"] = True
            quest_data["Help Text"] = (
                "Revisit the boulder where you found Excaliper; the map may be hidden there."
            )
            return True

        if giver == "Sergeant" and not progress.get("Sergeant"):
            if "Chalice Map" in self.player_char.special_inventory or progress.get("Map"):
                progress["Map"] = True
                self._show_hint(
                    "The Sergeant studies your map and mutters, 'There's a hidden route somewhere on the third floor. Find the adventurer there.'"
                )
                progress["Sergeant"] = True
                quest_data["Help Text"] = (
                    "Search the third floor for a secret path; an adventurer there can help decipher the map."
                )
                return True

        return False

    def get_random_help_hint(self, giver: str) -> str | None:
        """Return a single random help hint for active quests from the given giver.
        Does not render anything; returns None if no applicable hints.
        """

        def flatten(lst):
            out = []
            for d in lst:
                for name, q in d.items():
                    out.append((name, q))
            return out

        mains, sides = self._eligible_quests(giver)
        hints: list[str] = []
        for name, _ in flatten(mains):
            category = self._quest_category(giver, name, "Main")
            pdata = self.player_char.quest_dict.get(category, {}).get(name)
            if pdata and not pdata.get("Turned In"):
                ht = pdata.get("Help Text", "")
                if isinstance(ht, str) and ht.strip():
                    hints.append(ht)
        for name, _ in flatten(sides):
            pdata = self.player_char.quest_dict.get("Side", {}).get(name)
            if pdata and not pdata.get("Turned In"):
                ht = pdata.get("Help Text", "")
                if isinstance(ht, str) and ht.strip():
                    hints.append(ht)
        hints.extend(get_reactive_town_hints(self.player_char, giver))
        return random.choice(hints) if hints else None

    def _eligible_quests(self, giver: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        data = quest_dict.get(giver, {"Main": {}, "Side": {}})
        level = self.player_char.player_level()
        main_list: list[dict[str, Any]] = []
        side_list: list[dict[str, Any]] = []
        for lvl, q in data.get("Main", {}).items():
            if level >= int(lvl):
                main_list.append(q)
        for lvl, q in data.get("Progression", {}).items():
            if level >= int(lvl):
                main_list.append(q)
        for lvl, q in data.get("Side", {}).items():
            if level >= int(lvl):
                if (
                    getattr(self.player_char, "main_story", {}).get("liora_reply")
                    and "Where's the Beef?" in q
                ):
                    q = dict(q)
                    beef = q.pop("Where's the Beef?")
                    if giver == "Waitress":
                        q["Where's the Beef?"] = {**beef, **quest_progress.CHURCH_PROVISIONS}
                side_list.append(q)
        return main_list, side_list

    def _quest_category(self, giver: str, quest_name: str, fallback: str) -> str:
        """Return the authored/runtime category for one named quest."""
        giver_data = quest_dict.get(giver, {})
        player_quests = getattr(self.player_char, "quest_dict", {})
        for category in quest_progress.AUTHORED_QUEST_CATEGORIES:
            for quests_at_level in giver_data.get(category, {}).values():
                if quest_name in quests_at_level:
                    return category
            if quest_name in player_quests.get(category, {}):
                return category
        return fallback

    def has_available_or_active_quest(self, giver: str) -> bool:
        """Return whether a giver merits a Quests menu entry for this player."""
        mains, sides = self._eligible_quests(giver)
        for default_type, groups in (("Main", mains), ("Side", sides)):
            for group in groups:
                for name, definition in group.items():
                    quest_type = self._quest_category(giver, name, default_type)
                    player_quests = getattr(self.player_char, "quest_dict", {})
                    if not isinstance(player_quests, dict):
                        player_quests = {}
                    active = player_quests.get(quest_type, {}).get(name)
                    if isinstance(active, dict) and not active.get("Turned In", False):
                        return True
                    if active is None and self._can_offer_quest(name, definition, quest_type):
                        return True
        return False

    def has_pending_conversation(self, npc_name: str) -> bool:
        """Return whether an active objective requires speaking with this NPC."""
        return quest_progress.has_pending_conversation(self.player_char, npc_name)

    def _can_offer_quest(self, quest_name: str, q: dict[str, Any], typ: str) -> bool:
        """Check if quest can be offered based on prerequisites."""
        if not quest_progress.can_offer_authored_quest(self.player_char, quest_name):
            return False
        # Check if quest requires another quest to be turned in first
        required_quest = q.get("Requires")
        if required_quest:
            # Look for the required quest in both Main and Side
            for quest_type in quest_progress.AUTHORED_QUEST_CATEGORIES:
                if required_quest in self.player_char.quest_dict.get(quest_type, {}):
                    req_data = self.player_char.quest_dict[quest_type][required_quest]
                    if not req_data.get("Turned In", False):
                        return False
                    # Required quest is turned in, can proceed
                    return True
            # Required quest not found in player's quest dict - cannot offer
            return False
        # No requirements, can offer
        return True

    def get_quest_status_summary(self) -> dict[str, Any]:
        """Return compact quest completion/turn-in counts for diagnostics."""
        categories: dict[str, dict[str, int]] = {}
        totals = {
            "quests": 0,
            "completed": 0,
            "turned_in": 0,
            "ready_to_turn_in": 0,
            "active": 0,
        }

        for category, quests in getattr(self.player_char, "quest_dict", {}).items():
            category_counts = {
                "quests": 0,
                "completed": 0,
                "turned_in": 0,
                "ready_to_turn_in": 0,
                "active": 0,
            }
            if not isinstance(quests, dict):
                categories[category] = category_counts
                continue

            for quest_data in quests.values():
                if not isinstance(quest_data, dict):
                    continue
                completed = bool(quest_data.get("Completed", False))
                turned_in = bool(quest_data.get("Turned In", False))
                category_counts["quests"] += 1
                category_counts["completed"] += int(completed)
                category_counts["turned_in"] += int(turned_in)
                category_counts["ready_to_turn_in"] += int(completed and not turned_in)
                category_counts["active"] += int(not turned_in)

            categories[category] = category_counts
            for key in totals:
                totals[key] += category_counts[key]

        return {"categories": categories, "totals": totals}

    def _show_uncertain_reports_completion(self) -> None:
        """Resolve the first relic report as an authored multi-speaker scene."""
        player_name = str(getattr(self.player_char, "name", None) or "You")
        scene = StorySceneScreen(
            self.presenter,
            "Barracks — The First Relic",
            participants=("Caedmon", "Edrin", "Joffrey"),
            participant_anchors={"Joffrey": "Caedmon"},
            background_image="barracks.jpg",
            player_char=self.player_char,
        )
        scene.show_dialogue(
            (
                StoryBeat("Edrin", "Tomas?"),
                StoryBeat(
                    player_name, "I found him under the stone. He was dead.", PLAYER_PORTRAIT_KEY
                ),
                StoryBeat("Edrin", "Was Mira with him?"),
                StoryBeat(
                    player_name,
                    "I found her chalk marks past the door. That's as far as I could follow them.",
                    PLAYER_PORTRAIT_KEY,
                ),
                StoryBeat("Caedmon", "I'll leave her name on the board."),
                StoryBeat(
                    "Narrator",
                    "Caedmon takes three ledgers down from the shelf. Each has a sketch in the margin.",
                ),
                StoryBeat(
                    "Caedmon", "Three different patrols drew these. Joffrey, lay the relic here."
                ),
                StoryBeat(
                    "Joffrey",
                    "See where this line breaks off? There's the rest of it on the next page. The points fit.",
                ),
                StoryBeat("Edrin", "Mira kept trying to tell me about the space in the middle."),
                StoryBeat(
                    "Caedmon",
                    "Have a look at this older sheet. Torn clean across, but you can still count six places round the middle.",
                ),
                StoryBeat("Joffrey", "Six rooms like the one you found?"),
                StoryBeat(
                    "Caedmon",
                    "Could be. If you find anything else that fits these marks, bring it back. We'll lay it beside this one.",
                ),
            )
        )

    def turn_in_completed_quest(
        self,
        quest_name: str,
        typ: str,
        *,
        show_end_text: bool = True,
    ) -> bool:
        """Turn in one known completed quest without opening the giver menu."""
        qdata = self.player_char.quest_dict.get(typ, {}).get(quest_name)
        if not qdata or not qdata.get("Completed") or qdata.get("Turned In"):
            return False
        self._turn_in(quest_name, typ, show_end_text=show_end_text)
        return bool(qdata.get("Turned In"))

    def _turn_in(self, quest_name: str, typ: str, *, show_end_text: bool = True) -> None:
        qdata = self.player_char.quest_dict[typ][quest_name]
        reward = qdata.get("Reward", [])
        reward_num = qdata.get("Reward Number", 1)
        if reward == ["Power Up"] and not has_special_power_reward(self.player_char):
            self._show_hint("Complete your second promotion before claiming the Power Core reward.")
            return

        # Narrative resolutions belong to the quest outcome itself. Stage them before any
        # settlement mutates inventory, experience, level, or the Turned In flag.
        self._handle_pre_turn_in_quest_events(quest_name)

        # Show end-of-quest text from quest giver if available
        end_text = qdata.get("End Text", "")
        if quest_name == "Uncertain Reports":
            self._show_uncertain_reports_completion()
        if quest_name in (
            "Uncertain Reports",
            "Bring Him Home",
            "Rookie Mistake",
            "Lapidation",
            "The Holy Relics",
        ):
            end_text = ""
        if quest_name == "A Bad Dream" and getattr(self.player_char, "main_story", {}).get(
            "joffrey_found"
        ):
            end_text = ""
        if end_text and show_end_text:
            if self.quest_text_renderer:
                if self.renderer_preserve_formatting:
                    self.quest_text_renderer(f"Quest Complete: {quest_name}\n\n{end_text}")
                else:
                    header_text = f"====== {quest_name} ======\n\n"
                    wrapped_end = "\n".join(textwrap.wrap(end_text, width=self.wrap_width))
                    self.quest_text_renderer(header_text + wrapped_end)
            else:
                header_text = f"====== {quest_name} ======\n\n"
                wrapped_end = "\n".join(textwrap.wrap(end_text, width=self.wrap_width))
                header_text += wrapped_end
                wrapped_end = "\n".join(textwrap.wrap(header_text, width=self.wrap_width))
                popup = ConfirmationPopup(self.presenter, wrapped_end, show_buttons=False)
                self._show_popup(popup)

        # Rewards
        exp = qdata.get("Experience", 0)

        def format_item_info(item) -> str:
            info_lines = []
            info_lines.append(f"Type: {getattr(item, 'typ', 'Item')}")
            if hasattr(item, "subtyp"):
                info_lines.append(f"Subtype: {item.subtyp}")
            info_lines.append("")
            if getattr(item, "damage", 0):
                info_lines.append(f"Damage: {item.damage}")
            if getattr(item, "armor", 0):
                info_lines.append(f"Armor: {item.armor}")
            if getattr(item, "magic", 0):
                info_lines.append(f"Magic: {item.magic:+d}")
            if getattr(item, "magic_defense", 0):
                info_lines.append(f"Magic Defense: {item.magic_defense:+d}")
            if getattr(item, "description", ""):
                info_lines.append("")
                wrapped_desc = textwrap.wrap(item.description, width=self.wrap_width)
                info_lines.extend(wrapped_desc)
            info_lines.append("")
            info_lines.append(f"Value: {getattr(item, 'value', 0)}g")
            return "\n".join(info_lines)

        def ensure_item_instance(reward_entry):
            if isinstance(reward_entry, type):
                return reward_entry()
            if hasattr(reward_entry, "name"):
                return reward_entry
            return None

        def new_item_copy(reward_entry):
            if isinstance(reward_entry, type):
                return reward_entry()
            if hasattr(reward_entry, "name"):
                return reward_entry.__class__()
            return None

        # Gold or items
        reward_str = ""
        if reward == ["Gold"]:
            self.player_char.gold += reward_num
            reward_str = f"{reward_num} gold"
        elif reward == ["Power Up"]:
            grant_message = self.player_char.special_power()
            reward_str = grant_message.strip()
            reward_str = reward_str.removeprefix("You gain the skill ").removesuffix(".")
        elif reward == ["Warp Point"]:
            # Special flag for warp point access
            setattr(self.player_char, "warp_point", True)
            reward_str = "Warp Point access"
        elif reward and isinstance(reward, list) and len(reward) == 1:
            # Single item reward: can be either [ItemClass] or [ItemInstance]
            item_or_cls = reward[0]

            # Check if it's a class or an instance
            if isinstance(item_or_cls, type):
                # It's a class, instantiate it Reward Number times
                for _ in range(reward_num):
                    item = item_or_cls()
                    self.player_char.modify_inventory(item)
                    if not reward_str:
                        reward_str = f"{item.name} x{reward_num}"
            else:
                # It's an instance, grant Reward Number copies of the same type
                for _ in range(reward_num):
                    item = item_or_cls.__class__()
                    self.player_char.modify_inventory(item)
                    if not reward_str:
                        reward_str = f"{item.name} x{reward_num}"
        else:
            # If multiple reward choices, let player pick one (with inspect) instead of granting all
            chosen_names = []
            if (
                reward
                and len(reward) > 1
                and all(isinstance(r, type) or hasattr(r, "name") for r in reward)
            ):
                reward_items = []
                for entry in reward:
                    item = ensure_item_instance(entry)
                    if item is not None:
                        reward_items.append(item)
                if reward_items:
                    while True:
                        popup = RewardSelectionPopup(
                            self.presenter,
                            "Choose your reward",
                            reward_items,
                            format_item_info,
                        )
                        choice = popup.show(**self._popup_show_kwargs())
                        if choice is None:
                            # If user backs out of menu, keep asking until a choice is made
                            continue
                        item = reward_items[choice]
                        for _ in range(reward_num):
                            granted = new_item_copy(item)
                            if granted is not None:
                                self.player_char.modify_inventory(granted)
                                chosen_names.append(granted.name)
                        break
                reward_str = ", ".join(chosen_names)
            else:
                names = []
                for _ in range(reward_num):
                    for cls in reward:
                        item = new_item_copy(cls)
                        if item is not None:
                            self.player_char.modify_inventory(item)
                            names.append(item.name)
                reward_str = ", ".join(names) if names else ""

        # Show quest completion and rewards first
        message = [f"Quest turned in: {quest_name}"]
        if exp:
            message.append(f"Experience: {exp}")
        if reward_str:
            message.append(f"Reward: {reward_str}")
        combined_msg = "\n".join(message)
        if self.quest_text_renderer:
            self.quest_text_renderer(self._format_for_renderer(combined_msg))
        else:
            popup = ConfirmationPopup(self.presenter, combined_msg, show_buttons=False)
            self._show_popup(popup)

        # Then apply experience through the shared flat progression service.
        from src.core.progression import award_experience

        level_result = award_experience(self.player_char, exp)
        self.player_char._pending_level_up_result = (
            level_result if level_result.new_level > level_result.old_level else None
        )

        # Remove collected items if this is a Collect type quest
        if qdata.get("Type") == "Collect":
            quest_item = qdata.get("What")
            if quest_item:
                try:
                    target_names = set()
                    target_classes = set()

                    # Handle both string and class/instance quest-item representations
                    if isinstance(quest_item, str):
                        target_names.add(quest_item)
                        target_classes.add(quest_item)
                        try:
                            quest_item_cls = getattr(items, quest_item, None)
                            if quest_item_cls and callable(quest_item_cls):
                                quest_item_obj = quest_item_cls()
                                target_names.add(getattr(quest_item_obj, "name", quest_item))
                                target_classes.add(quest_item_cls.__name__)
                        except Exception:
                            pass
                    elif callable(quest_item):
                        quest_item_obj = quest_item()
                        target_names.add(getattr(quest_item_obj, "name", ""))
                        target_classes.add(quest_item.__name__)
                    else:
                        target_names.add(getattr(quest_item, "name", ""))
                        target_classes.add(quest_item.__class__.__name__)

                    # Remove only the required amount when possible.
                    try:
                        remaining_to_remove = int(qdata.get("Total", 0))
                    except (TypeError, ValueError):
                        remaining_to_remove = 0

                    for inventory_name in ("special_inventory", "inventory"):
                        inventory = getattr(self.player_char, inventory_name, {})
                        for key in list(inventory.keys()):
                            item_list = inventory.get(key, [])
                            if not item_list:
                                continue

                            sample = item_list[0]
                            sample_name = getattr(sample, "name", key)
                            sample_class = sample.__class__.__name__
                            is_match = (
                                key in target_names
                                or sample_name in target_names
                                or sample_class in target_classes
                            )
                            if not is_match:
                                continue

                            if remaining_to_remove > 0:
                                remove_count = min(remaining_to_remove, len(item_list))
                                for _ in range(remove_count):
                                    item_list.pop(0)
                                remaining_to_remove -= remove_count
                                if not item_list:
                                    del inventory[key]
                                if remaining_to_remove <= 0:
                                    break
                            else:
                                del inventory[key]
                        if remaining_to_remove <= 0:
                            break
                except Exception:
                    pass

        level_up_screen = LevelUpScreen(self.presenter.screen, self.presenter)
        if level_result.new_level > level_result.old_level:
            level_up_screen.show_level_up(self.player_char, None)
        qdata["Turned In"] = True

        quest_progress.handle_quest_turn_in(self.player_char, quest_name)

    def _remove_lucky_locket_for_bad_dream(self) -> None:
        """Remove Joffrey's locket when the Waitress takes it during turn-in."""
        try:
            self.player_char.modify_inventory(items.LuckyLocket(), subtract=True, rare=True)
        except Exception:
            special_inventory = getattr(self.player_char, "special_inventory", {})
            special_inventory.pop("Lucky Locket", None)

    def _handle_quest_events(self, quest_name: str) -> None:
        """Handle narrative and special events before a quest is settled."""

        def show_special_event_text(event_name: str) -> None:
            from src.core.data.data_loader import get_special_events

            event_text = get_special_events().get(event_name, {}).get("Text", [])
            if not event_text:
                return
            formatted_text = "\n".join(event_text)
            if self.quest_text_renderer:
                self.quest_text_renderer(self._format_for_renderer(formatted_text))
            else:
                wrapped_text = "\n".join(textwrap.wrap(formatted_text, width=self.wrap_width))
                popup = ConfirmationPopup(self.presenter, wrapped_text, show_buttons=False)
                self._show_popup(popup)

        if quest_name == "A Bad Dream":
            self._remove_lucky_locket_for_bad_dream()

            if getattr(self.player_char, "main_story", {}).get("joffrey_found"):
                scene = StorySceneScreen(
                    self.presenter,
                    "The Thirsty Dog — The Locket",
                    participants=("Liora", "Tavin"),
                    background_image="tavern.jpg",
                    player_char=self.player_char,
                )
                scene.show_dialogue(
                    (
                        StoryBeat(
                            "Narrator",
                            "Liora reaches across the counter. The chain slides into her palm.",
                        ),
                        StoryBeat(
                            "Liora",
                            "It still catches. Here, you have to lift the clasp a little. Where was he?",
                        ),
                    )
                )
                answer = scene.choose(
                    "What do you tell her?",
                    [
                        "By the pens. I covered him with stones.",
                        "He reached the bars. Someone made it out the other side.",
                        "Show her his last chalk mark on the map.",
                    ],
                    allow_cancel=False,
                )
                scene.show_dialogue(
                    (
                        StoryBeat(
                            "Liora",
                            (
                                "Thank you for staying with him.",
                                "You saw tracks? Show Caedmon where they went.",
                                "Right down there? I kept looking at the fork.",
                            )[answer],
                        ),
                        StoryBeat(
                            "Tavin", "I could have stood in the doorway. Do you ever wish I had?"
                        ),
                        StoryBeat("Liora", "I wish he'd come home. Give me a minute, Tav."),
                        StoryBeat(
                            "Narrator",
                            "She threads the chain through her apron tie and counts three old keys onto the counter. A little brass one follows.",
                        ),
                        StoryBeat(
                            "Liora",
                            "The brass one's for his locker. Bring me anything with my name on it.",
                        ),
                    )
                )
                self.player_char.main_story["liora_reply"] = ("burial", "tracks", "map")[answer]
                self.player_char.modify_inventory(items.BrassKey(), rare=True)
                beef = self.player_char.quest_dict.get("Side", {}).get("Where's the Beef?")
                if beef and not beef.get("Turned In"):
                    beef.update(quest_progress.CHURCH_PROVISIONS)
                return

            # Show Busboy special event
            show_special_event_text("Busboy")

            # Transfer "Where's the Beef?" quest to Busboy if it exists
            if "Where's the Beef?" in self.player_char.quest_dict.get("Side", {}):
                beef_quest = self.player_char.quest_dict["Side"]["Where's the Beef?"]
                if not beef_quest.get("Turned In"):
                    beef_quest["Who"] = "Busboy"
                    beef_quest["End Text"] = (
                        "Thanks, this will help feed a lot of people. Here's something for your time."
                    )
                    beef_quest["Help Text"] = (
                        "You can get meat from pretty much any animal. Not really a time to be picky..."
                    )

                    transfer_msg = (
                        "I know the waitress asked you to get her some meat for her wedding.\n"
                        "She obviously doesn't need them anymore, so I can take them if you get them."
                    )
                    if self.quest_text_renderer:
                        self.quest_text_renderer(self._format_for_renderer(transfer_msg))
                    else:
                        wrapped_transfer = "\n".join(
                            textwrap.wrap(transfer_msg, width=self.wrap_width)
                        )
                        popup = ConfirmationPopup(
                            self.presenter, wrapped_transfer, show_buttons=False
                        )
                        self._show_popup(popup)
        elif quest_name == "The Wizard's Folly":
            show_special_event_text("Nimue After Merzhin")
        elif quest_name == "This Thing's Nuclear":
            show_special_event_text("Power Up")

    def _handle_pre_turn_in_quest_events(self, quest_name: str) -> None:
        """Show quest-resolution scenes before rewards and completion settlement."""
        if quest_name == "The Holy Relics":
            scene = StorySceneScreen(
                self.presenter,
                "Barracks — The Last Rubbing",
                participants=("Caedmon", "Soldier"),
                background_image="barracks.jpg",
                player_char=self.player_char,
            )
            scene.show_dialogue(
                (
                    StoryBeat(
                        "Narrator",
                        "Caedmon unpicks the stitches in six ledgers. He lays the chamber rubbings edge to edge. Every page has a thumb-wide strip of clean paper in the same place.",
                    ),
                    StoryBeat(
                        "Soldier",
                        "I went back for that bit. Look, you can see where I tore the paper the second time.",
                    ),
                    StoryBeat("Caedmon", "I know. Mine came out the same. Leave the space."),
                    StoryBeat(
                        "Soldier", "Can I tell the watch we're done? My brother wants to come home."
                    ),
                    StoryBeat("Caedmon", "Tell him to come. I'll keep the lamp here."),
                )
            )
        elif quest_name == "Bring Him Home":
            self._show_timmy_home_scene()
        elif quest_name == "Rookie Mistake":
            self._show_rookie_burial_scenes()
        if quest_name == "Lapidation":
            scene = StorySceneScreen(
                self.presenter,
                "The Thirsty Dog — Rutger’s Necklace",
                participants=("Pell",),
                background_image="tavern.jpg",
                player_char=self.player_char,
            )
            scene.show_dialogue(
                (
                    StoryBeat("Pell", "You saw the bird fall? All the way down?"),
                    StoryBeat(
                        "Narrator",
                        "Pell undoes his necklace. He starts to slip it over his head again, catches himself and holds it out to you.",
                    ),
                    StoryBeat("Pell", "Clasp sticks. Here, let me."),
                )
            )
        self._handle_quest_events(quest_name)

    def _show_rookie_burial_scenes(self) -> None:
        """Receive the fallen recruit in the courtyard, then hold his burial."""
        player_name = str(getattr(self.player_char, "name", "Hero") or "Hero")
        courtyard = StorySceneScreen(
            self.presenter,
            "Silvana Courtyard — A Rookie Returns",
            participants=("Caedmon", "Soldier"),
            participant_anchors={"Soldier": "Caedmon"},
            background_image="town.png",
            player_char=self.player_char,
        )
        courtyard.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "The gate watch falls silent when you enter Silvana carrying the fallen "
                    "recruit. Caedmon crosses the courtyard before anyone can call for him.",
                    portrait_name="",
                ),
                StoryBeat("Caedmon", "Clear the gate. Give them room."),
                StoryBeat(
                    player_name,
                    "First level. I carried him up from there.",
                    portrait_name=PLAYER_PORTRAIT_KEY,
                ),
                StoryBeat(
                    "Caedmon",
                    "He asked me if he was ready. I told him he was.",
                ),
                StoryBeat(
                    "Narrator",
                    "Caedmon takes the recruit's patrol clasp and closes his hand around it. "
                    "The Priest is waiting at the graveyard.",
                    portrait_name="",
                ),
            ),
            fade_in_ms=900,
            fade_hold_ms=250,
        )

        graveyard = StorySceneScreen(
            self.presenter,
            "Silvana Graveyard — The Last Watch",
            participants=("Priest", "Caedmon"),
            participant_anchors={"Soldier": "Caedmon"},
            background_image="graveyard.jpg",
            player_char=self.player_char,
        )
        graveyard.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "At the graveyard, the Priest waits beside an open grave. Soldiers, "
                    "Joffrey, Liora, and townspeople stand together in the rain.",
                    portrait_name="",
                ),
                StoryBeat("Priest", "Take the foot, Caedmon. Easy now."),
                StoryBeat(
                    "Narrator",
                    "You and Caedmon lower the recruit into the grave. Caedmon opens his hand. The patrol clasp has left a mark in his palm.",
                ),
                StoryBeat("Soldier", "We should have gone with him."),
                StoryBeat(
                    "Narrator",
                    "The soldier takes the clasp from Caedmon and pins it to the wooden marker. The Priest waits beside him until he steps back.",
                ),
            ),
            fade_in_ms=1000,
            fade_hold_ms=300,
        )

        if "Dead Soldier" in getattr(self.player_char, "special_inventory", {}):
            self.player_char.modify_inventory(items.DeadSoldier(), subtract=True, rare=True)

    def _show_timmy_home_scene(self) -> None:
        """Stage Timmy's reunion without changing quest settlement."""
        scene = StorySceneScreen(
            self.presenter,
            "Silvana — Timmy Comes Home",
            participants=("Timmy's Mother", "Timmy's Father", "Timmy"),
            participant_anchors={"Timmy": "Timmy's Mother"},
            background_image="town.png",
            player_char=self.player_char,
        )
        scene.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "Timmy's parents come running across the barracks yard. Caedmon steps out of their way.",
                ),
                StoryBeat("Timmy's Mother", "Timmy."),
                StoryBeat(
                    "Narrator",
                    "She drops to her knees and pulls him close. His father stops beside them, one hand over his mouth.",
                ),
                StoryBeat("Timmy", "Dad? I lost my lamp."),
                StoryBeat("Timmy's Father", "That's all right, son. Come here."),
                StoryBeat(
                    "Narrator",
                    "His father kneels in the mud. Timmy gets one arm free and pulls him in too.",
                ),
            )
        )

    def _already_killed(self, enemy_name: str) -> bool:
        return already_defeated_enemy(self.player_char, enemy_name)

    def _offer_barghest_briefing(self) -> bool:
        """Ask for the assignment in the barracks, shortening subsequent visits."""
        story = main_story.ensure_state(self.player_char)
        scene = StorySceneScreen(
            self.presenter,
            "Barracks — Cry Havoc!",
            participants=("Joffrey", "Edrin", "Caedmon"),
            participant_anchors={"Caedmon": "Joffrey"},
            background_image="barracks.jpg",
            player_char=self.player_char,
        )
        if not story["barghest_briefing_seen"]:
            scene.show_dialogue(
                (
                    StoryBeat(
                        "Narrator", "Joffrey props the bestiary open so Edrin can see the drawing."
                    ),
                    StoryBeat("Joffrey", "The hound on this page. Does it look familiar?"),
                    StoryBeat("Edrin", "The eyes do. It was taller when it came after me."),
                    StoryBeat("Joffrey", "Barghest. Turn the page. That's still the same beast."),
                    StoryBeat(
                        "Caedmon",
                        "I've got two other reports of those eyes. Both by the sealed chamber.",
                    ),
                )
            )
            story["barghest_briefing_seen"] = True
        if self._already_killed("Barghest"):
            prompt = "You've been to that chamber. Will you give me your account?"
            answers = ["I'll make my report.", "Another time."]
        else:
            prompt = "Will you take the Barghest and have a look inside that chamber?"
            answers = ["I'll go.", "Not yet."]
        return scene.choose(prompt, answers, speaker="Caedmon") == 0

    def _confirm_standard_offer(self, quest_name: str, text: str) -> bool:
        """Show a quest giver's offer and ask whether to accept it."""
        # Display quest text - use renderer if available, otherwise the standard confirmation popup
        if self.quest_text_renderer:
            if self.renderer_preserve_formatting:
                intro = text.strip()
                if intro:
                    self.quest_text_renderer(f"Quest: {quest_name}\n\n{intro}")
                else:
                    self.quest_text_renderer(f"Quest: {quest_name}")
            else:
                header_text = f"====== {quest_name} ======\n\n"
                wrapped_text = "\n".join(textwrap.wrap(text, width=self.wrap_width))
                self.quest_text_renderer(header_text + wrapped_text)
        else:
            header_text = f"{quest_name}\n\n"
            wrapped_text = "\n".join(textwrap.wrap(text, width=self.wrap_width))
            wrapped_text = header_text + wrapped_text
            popup = ConfirmationPopup(self.presenter, wrapped_text, show_buttons=False)
            self._show_popup(popup)

        # Separate Accept/Decline menu
        if self.quest_choice_renderer:
            choice = self.quest_choice_renderer("Accept this quest?", ["Accept", "Decline"])
            return choice == 0
        popup = ConfirmationPopup(self.presenter, "Accept this quest?")
        return bool(self._show_popup(popup))

    def _offer(self, giver: str, quest_name: str, q: dict[str, Any], typ: str) -> bool:
        barghest_briefing = quest_name == "Cry Havoc!"
        if barghest_briefing:
            accepted = self._offer_barghest_briefing()
        else:
            accepted = self._confirm_standard_offer(quest_name, q.get("Start Text", ""))

        if accepted:
            # Add a copy of quest to player quest log
            if typ not in self.player_char.quest_dict:
                self.player_char.quest_dict[typ] = {}
            self.player_char.quest_dict[typ][quest_name] = copy.deepcopy(q)

            if (
                quest_name == "A Bad Dream"
                and main_story.ensure_state(self.player_char)["joffrey_found"]
            ):
                self.player_char.quest_dict[typ][quest_name]["Completed"] = True

            if quest_name == "The Holy Grail of Quests":
                self._ensure_chalice_progress(self.player_char.quest_dict[typ][quest_name])

            # If it's a defeat quest and player already killed the target, mark complete
            if q.get("Type") == "Defeat" and isinstance(q.get("What"), str):
                if self._already_killed(q["What"]):
                    self.player_char.quest_dict[typ][quest_name]["Completed"] = True

            # If it's the Relics collection quest and player already has all relics,
            # mark as completed immediately so it can be turned in.
            if q.get("Type") == "Collect" and q.get("What") == "Relics":
                if quest_progress.has_all_relics(
                    self.player_char
                ) and not self.player_char.quest_dict[typ][quest_name].get("Completed"):
                    self.player_char.quest_dict[typ][quest_name]["Completed"] = True

            # If the quest grants an initial item (for example Naivete's empty vial),
            # replicate minimal cases here if needed.
            if quest_name == "Naivete":
                try:
                    self.player_char.modify_inventory(items.EmptyVial(), rare=True)
                except Exception:
                    pass

            if barghest_briefing:
                return True

            # Use personalized response from RESPONSE_MAP
            response = RESPONSE_MAP.get(
                giver, ["Quest accepted! Check your quest log for details.", "Maybe next time."]
            )[0]
            # Special case for Sergeant's Relics quest
            if giver == "Sergeant" and quest_name == "The Holy Relics":
                response += "\n\nMake sure to grab the health potions out of your storage locker if you haven't already."

            if self.quest_text_renderer:
                self.quest_text_renderer(self._format_for_renderer(response))
            else:
                popup = ConfirmationPopup(
                    self.presenter,
                    response,
                    show_buttons=False,
                )
                self._show_popup(popup)
            return True
        else:
            if barghest_briefing:
                return False

            # Use personalized rejection response from RESPONSE_MAP
            response = RESPONSE_MAP.get(
                giver, ["Quest accepted! Check your quest log for details.", "Maybe next time."]
            )[1]
            if self.quest_text_renderer:
                self.quest_text_renderer(self._format_for_renderer(response))
            else:
                popup = ConfirmationPopup(self.presenter, response, show_buttons=False)
                self._show_popup(popup)
            return False

    def check_and_offer(
        self, giver: str, show_help: bool = True, suppress_no_quests_message: bool = False
    ) -> tuple[bool, bool]:
        """Return (did_action, showed_message).

        did_action: quest turned in or accepted.
        showed_message: any popup/help/no-quest message was shown.
        """
        conversation_message = quest_progress.record_conversation(self.player_char, giver)
        quest_progress.sync_relic_story_progress(self.player_char)
        quest_progress.sync_collection_progress(self.player_char)
        did_action = False
        showed_message = False
        quest_was_offered = False
        if conversation_message:
            self._show_hint(conversation_message.rstrip())
            return True, True
        mains, sides = self._eligible_quests(giver)

        # Turn-in checks, then offers
        # Build flat (name, data) lists
        def flatten(lst):
            out = []
            for d in lst:
                for name, q in d.items():
                    out.append((name, q))
            return out

        for name, q in flatten(mains):
            category = self._quest_category(giver, name, "Main")
            pdata = self.player_char.quest_dict.get(category, {}).get(name)
            if (
                pdata
                and not pdata.get("Completed")
                and q.get("Type") == "Defeat"
                and isinstance(q.get("What"), str)
            ):
                if self._already_killed(q["What"]):
                    pdata["Completed"] = True
            # Safety: auto-complete Relics collect quest if already fulfilled but not marked
            pdata = self.player_char.quest_dict.get(category, {}).get(name)
            if (
                pdata
                and not pdata.get("Completed")
                and q.get("Type") == "Collect"
                and q.get("What") == "Relics"
            ):
                if quest_progress.has_all_relics(self.player_char):
                    pdata["Completed"] = True
            pdata = self.player_char.quest_dict.get(category, {}).get(name)
            if pdata and pdata.get("Completed") and not pdata.get("Turned In"):
                self._turn_in(name, category)
                did_action = True
                showed_message = True
                return did_action, showed_message
        for name, q in flatten(sides):
            pdata = self.player_char.quest_dict.get("Side", {}).get(name)
            if (
                pdata
                and not pdata.get("Completed")
                and q.get("Type") == "Defeat"
                and isinstance(q.get("What"), str)
            ):
                if self._already_killed(q["What"]):
                    pdata["Completed"] = True
            pdata = self.player_char.quest_dict.get("Side", {}).get(name)
            if pdata and pdata.get("Completed") and not pdata.get("Turned In"):
                self._turn_in(name, "Side")
                did_action = True
                showed_message = True
                return did_action, showed_message

        # Offer new quests, main first then side
        for name, q in flatten(mains):
            category = self._quest_category(giver, name, "Main")
            if name not in self.player_char.quest_dict.get(category, {}):
                # Check prerequisites before offering
                if not self._can_offer_quest(name, q, category):
                    continue
                quest_was_offered = True
                if self._offer(giver, name, q, category):
                    return True, True
                showed_message = True  # declined quest still showed a popup
        for name, q in flatten(sides):
            # Skip debug-only pandora/ultima style special cases
            if name == "Pandora's Box" and "Photon Sphere" not in self.player_char.spellbook.get(
                "Spells", {}
            ):
                continue

            if name not in self.player_char.quest_dict.get("Side", {}):
                # Check prerequisites before offering
                if not self._can_offer_quest(name, q, "Side"):
                    continue
                quest_was_offered = True
                if self._offer(giver, name, q, "Side"):
                    return True, True
                showed_message = True  # declined quest still showed a popup

        # Quest-specific hint handling (e.g., Golden Chalice progression)
        if self._handle_chalice_giver_hint(giver):
            return did_action, True

        # If no actions, show help text from active quests for this giver if any
        help_texts = []
        for name, q in flatten(mains):
            category = self._quest_category(giver, name, "Main")
            pdata = self.player_char.quest_dict.get(category, {}).get(name)
            if pdata and not pdata.get("Turned In"):
                help_texts.append(pdata.get("Help Text", ""))
        for name, q in flatten(sides):
            pdata = self.player_char.quest_dict.get("Side", {}).get(name)
            if pdata and not pdata.get("Turned In"):
                help_texts.append(pdata.get("Help Text", ""))
        help_texts.extend(get_reactive_town_hints(self.player_char, giver))
        if help_texts and show_help:
            # Show a single random hint per interaction instead of all at once
            candidates = [ht for ht in help_texts if isinstance(ht, str) and ht.strip()]
            if candidates:
                hint = random.choice(candidates)
                if self.quest_text_renderer:
                    self.quest_text_renderer(self._format_for_renderer(hint))
                else:
                    wrapped_hint = "\n".join(textwrap.wrap(hint, width=self.wrap_width))
                    popup = ConfirmationPopup(self.presenter, wrapped_hint, show_buttons=False)
                    self._show_popup(popup)
                showed_message = True
        elif not quest_was_offered and not suppress_no_quests_message:
            # Only show "no quests" if no quest was offered at all and not suppressed
            popup = ConfirmationPopup(
                self.presenter, "I have no new quests for you at this time.", show_buttons=False
            )
            self._show_popup(popup)
            showed_message = True
        return did_action, showed_message
