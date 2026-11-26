"""
Barracks system for GUI - handles quests and storage.
Implements the core barracks logic from town.py adapted for Pygame presenter.
"""

from src.core import enemies, items, main_story, map_tiles, opening_story
from src.core.classes import class_rings, grandmaster
from src.core.data.data_loader import get_special_events

from .confirmation_popup import ConfirmationPopup
from .location_menu import LocationMenuScreen
from .story_scene import StoryBeat, StorySceneScreen
from .town_base import TownScreenBase


class GrandmasterTrialTile(map_tiles.MapTile):
    """Concrete combat tile for Secret Master bouts."""

    def modify_player(self, game):
        self.visited = True

    def available_actions(self, player_char):
        return []


class BarracksManager(TownScreenBase):
    """Manages barracks interactions with pygame presenter."""

    LEGACY_BARRACKS_TRIALS = {
        "Dragoon": {
            "label": "Guard The Fall",
            "enemy_name": "Skybreak Veteran",
            "intro": (
                "The Sergeant leads you to the high training platform. A Skybreak Veteran "
                "tests whether you can land, endure, and keep fighting."
            ),
            "failure": "The fall is guarded another day. The veteran waits for your next attempt.",
            "scale": 1.15,
            "stats": {
                "health": 105,
                "mana": 20,
                "strength": 23,
                "intel": 8,
                "wisdom": 12,
                "con": 18,
                "charisma": 10,
                "dex": 20,
                "attack": 25,
                "defense": 16,
                "magic": 6,
                "magic_def": 13,
            },
        },
        "Stalwart Defender": {
            "label": "Siege Trial",
            "enemy_name": "Ironwall Captain",
            "intro": (
                "The old shield line forms around the sparring floor. The Ironwall Captain "
                "tests whether your guard can hold under siege pressure."
            ),
            "failure": "The shield line breaks. The captain resets the Siege Trial.",
            "scale": 1.20,
            "stats": {
                "health": 125,
                "mana": 10,
                "strength": 21,
                "intel": 6,
                "wisdom": 12,
                "con": 23,
                "charisma": 10,
                "dex": 14,
                "attack": 22,
                "defense": 24,
                "magic": 4,
                "magic_def": 16,
            },
        },
    }

    MILESTONE_STORAGE_REWARDS = (
        (
            "Rookie Mistake",
            (
                (items.HealthPotion, 2),
                (items.ManaPotion, 1),
            ),
        ),
        (
            "The Butcher",
            (
                (items.HealthPotion, 3),
                (items.ManaPotion, 1),
            ),
        ),
        (
            "A Bad Dream",
            (
                (items.GreatHealthPotion, 2),
                (items.GreatManaPotion, 1),
            ),
        ),
        (
            "No Laughing Matter",
            (
                (items.Remedy, 2),
                (items.Elixir, 1),
            ),
        ),
        (
            "The Wizard's Folly",
            (
                (items.Elixir, 2),
                (items.Megalixir, 1),
            ),
        ),
    )

    def __init__(self, presenter, player_char, game=None):
        super().__init__(presenter)
        self.player_char = player_char
        self.game = game

    def visit_barracks(self):
        """Visit the barracks for quests and storage."""
        barracks_options = ["Quests", "Storage Locker"]
        story_state = main_story.ensure_state(self.player_char)
        quest_dict = getattr(self.player_char, "quest_dict", {})
        uncertain = quest_dict.get("Main", {}).get("Uncertain Reports")
        if isinstance(uncertain, dict) and not story_state.get("opening_ledger_seen"):
            barracks_options.insert(1, "Review Patrol Ledgers")
        if self._berserker_duel_available():
            barracks_options.append("No Healing Duel")
        if self._legacy_barracks_trial_available():
            barracks_options.append(self._legacy_barracks_trial_label())
        if self._grandmaster_hall_available():
            barracks_options.append("Secret Hall")
        barracks_options.append("Leave")

        barracks_screen = LocationMenuScreen(
            self.presenter,
            "Barracks",
            background_image="barracks.jpg",
        )
        barracks_screen.options_list = barracks_options
        barracks_screen.set_location_portrait("Caedmon Varr")

        # Pre-render barracks frame so entry popups draw over the proper background.
        barracks_screen.draw_all()
        barracks_background = self.presenter.screen.copy()

        def draw_barracks_background():
            return self.presenter.screen.blit(barracks_background, (0, 0))

        self._grant_milestone_storage_rewards(draw_barracks_background)

        # If the player has the Brass Key, resolve Joffrey's Key handoff.
        if "Brass Key" in self.player_char.special_inventory:
            # Show special event text over barracks background.
            try:
                lines = get_special_events().get("Joffrey's Key", {}).get("Text", [])
            except (OSError, TypeError, ValueError):
                lines = []
            event_message = (
                " ".join(line.strip() for line in lines if line is not None).strip()
                or "Joffrey's Key"
            )
            event_popup = ConfirmationPopup(
                self.presenter, event_message, show_buttons=False, slow_print=True
            )
            event_popup.show(
                background_draw_func=draw_barracks_background,
                flush_events=True,
                require_key_release=True,
                min_display_ms=300,
            )

            self.player_char.modify_inventory(items.BrassKey(), subtract=True, rare=True)
            self.player_char.modify_inventory(items.JoffreysLetter(), rare=True)
            self.player_char.modify_inventory(items.GreatHealthPotion(), num=5)

            reward_popup = ConfirmationPopup(
                self.presenter,
                "You gain 5 Great Health Potions and Joffrey's Letter.",
                show_buttons=False,
            )
            reward_popup.show(
                background_draw_func=draw_barracks_background,
                flush_events=True,
                require_key_release=True,
            )

        while True:
            choice_idx = barracks_screen.navigate(
                barracks_options,
                reset_cursor=False,
                flush_events=True,
                require_key_release=True,
            )

            if choice_idx is None:
                choice_label = "Leave"
            else:
                choice_label = barracks_options[choice_idx]

            if choice_label == "Leave":
                popup = ConfirmationPopup(self.presenter, "Take care, soldier.", show_buttons=False)
                popup.show(
                    background_draw_func=draw_barracks_background,
                    flush_events=True,
                    require_key_release=True,
                )
                break

            elif choice_label == "Quests":
                from .quest_manager import QuestManager

                qm = QuestManager(
                    self.presenter,
                    self.player_char,
                    quest_text_renderer=lambda text: barracks_screen.display_quest_text(
                        text, npc_name="Caedmon Varr"
                    ),
                    renderer_preserve_formatting=True,
                    story_background_draw_func=draw_barracks_background,
                )
                qm.check_and_offer("Sergeant")

            elif choice_label == "Review Patrol Ledgers":
                self._review_opening_ledgers(draw_barracks_background)
                barracks_options.remove("Review Patrol Ledgers")

            elif choice_label == "Storage Locker":
                self.manage_storage()
                if self._berserker_duel_available() and "No Healing Duel" not in barracks_options:
                    barracks_options.insert(-1, "No Healing Duel")
                elif not self._berserker_duel_available() and "No Healing Duel" in barracks_options:
                    barracks_options.remove("No Healing Duel")
                trial_label = self._legacy_barracks_trial_label()
                if self._legacy_barracks_trial_available() and trial_label not in barracks_options:
                    barracks_options.insert(-1, trial_label)
                elif (
                    not self._legacy_barracks_trial_available() and trial_label in barracks_options
                ):
                    barracks_options.remove(trial_label)
                if self._grandmaster_hall_available() and "Secret Hall" not in barracks_options:
                    barracks_options.insert(-1, "Secret Hall")
                elif not self._grandmaster_hall_available() and "Secret Hall" in barracks_options:
                    barracks_options.remove("Secret Hall")

            elif choice_label == "No Healing Duel":
                self.visit_berserker_no_healing_duel(draw_barracks_background)

            elif choice_label == self._legacy_barracks_trial_label():
                self.visit_legacy_barracks_class_ring_trial(draw_barracks_background)

            elif choice_label == "Secret Hall":
                self.visit_grandmaster_secret_hall(draw_barracks_background)

    def _review_opening_ledgers(self, background_draw_func=None) -> None:
        """Let the player inspect the three contradictory patrol entries in any order."""
        entries = {
            "Route entry": (
                "North passage, fourteen turns. The returning scout remembers nine. "
                "Both maps bear the same hand."
            ),
            "Time entry": (
                "Patrol absent two nights. Every survivor insists they were below for less "
                "than an hour."
            ),
            "Threshold entry": (
                "Sealed stone, three marks around an empty center. Witnesses disagree whether "
                "the marks stood above, below, or behind the door."
            ),
        }
        scene = StorySceneScreen(
            self.presenter,
            "Barracks — Patrol Ledgers",
            participants=("Caedmon", "Edrin", "Joffrey"),
            participant_anchors={"Joffrey": "Caedmon"},
            background_image="barracks.jpg",
            player_char=self.player_char,
        )
        scene.show_dialogue(
            (
                StoryBeat(
                    "Narrator",
                    "Caedmon places three patrol ledgers on the table and opens each to a "
                    "marked entry.",
                    portrait_name="",
                ),
            )
        )
        while entries:
            labels = list(entries)
            choice = scene.choose(
                "Which patrol entry do you inspect?",
                labels,
                speaker="Caedmon",
                record_selection=False,
            )
            if choice is None:
                continue
            label = labels[choice]
            scene.show_dialogue((StoryBeat("Patrol Ledger", entries.pop(label), portrait_name=""),))

        opening_story.record_ledger_review(main_story.ensure_state(self.player_char))
        scene.show_dialogue(
            (
                StoryBeat("Edrin", "I know what I saw. I just do not know when I saw it."),
                StoryBeat(
                    "Joffrey",
                    "Bad maps can drift. They don't repeat the same mistake in three different "
                    "hands.",
                ),
                StoryBeat("Caedmon", "Then find what is repeating."),
            )
        )

    def _grandmaster_hall_available(self):
        return grandmaster.is_grandmaster(
            self.player_char
        ) and grandmaster.ring_visible_for_sergeant(self.player_char)

    def _berserker_duel_available(self):
        return (
            class_rings.class_name(self.player_char) == "Berserker"
            and class_rings.has_visible_class_ring(self.player_char)
            and not class_rings.is_awakened(self.player_char, "Berserker")
        )

    def _legacy_barracks_trial_config(self):
        return self.LEGACY_BARRACKS_TRIALS.get(class_rings.class_name(self.player_char))

    def _legacy_barracks_trial_label(self):
        config = self._legacy_barracks_trial_config()
        return config["label"] if config else "Class Ring Trial"

    def _legacy_barracks_trial_available(self):
        class_name = class_rings.class_name(self.player_char)
        return (
            class_name in self.LEGACY_BARRACKS_TRIALS
            and class_rings.has_visible_class_ring(self.player_char)
            and not class_rings.is_awakened(self.player_char, class_name)
        )

    def _show_message(self, message, background_draw_func=None):
        popup = ConfirmationPopup(self.presenter, message, show_buttons=False)
        popup.show(
            background_draw_func=background_draw_func,
            flush_events=True,
            require_key_release=True,
        )

    def _choose_grandmaster_weapon(self, rebind=False):
        title = "Rebind Discipline" if rebind else "Awaken Discipline"
        screen = LocationMenuScreen(self.presenter, title)
        options = list(grandmaster.WEAPON_TYPES) + ["Back"]
        choice = screen.navigate(
            options,
            reset_cursor=True,
            flush_events=True,
            require_key_release=True,
        )
        if choice is None or options[choice] == "Back":
            return None
        return options[choice]

    def _trial_enemy(self, weapon_type, round_number, rebind=False):
        level = max(1, int(getattr(getattr(self.player_char, "level", None), "level", 1)))
        pro_level = max(1, int(getattr(getattr(self.player_char, "level", None), "pro_level", 1)))
        difficulty = 1.25 if rebind else 1.0
        round_scale = 1 + (round_number * 0.15)
        scale = difficulty * round_scale
        enemy = enemies.Enemy(
            name=f"Secret Master {weapon_type} Adept {round_number}",
            health=int((80 + level * 8 + pro_level * 25) * scale),
            mana=int((20 + level * 2) * scale),
            strength=int((18 + level // 2) * scale),
            intel=int((10 + level // 4) * scale),
            wisdom=int((12 + level // 4) * scale),
            con=int((16 + level // 3) * scale),
            charisma=10,
            dex=int((16 + level // 3) * scale),
            attack=int((20 + level // 2) * scale),
            defense=int((14 + level // 3) * scale),
            magic=8,
            magic_def=int((12 + level // 4) * scale),
            exp=0,
        )
        enemy.gold = 0
        enemy.inventory = {}
        enemy.enemy_typ = "Trial"
        enemy.grandmaster_trial_enemy = True
        return enemy

    def _apply_trial_recovery_floor(self):
        self.player_char.health.current = max(
            self.player_char.health.current,
            self.player_char.health.max // 2,
        )
        self.player_char.mana.current = max(
            self.player_char.mana.current,
            self.player_char.mana.max // 2,
        )

    def _run_grandmaster_gauntlet(self, weapon_type, rebind=False):
        combat_manager = getattr(
            getattr(self.game, "dungeon_manager", None), "combat_manager", None
        )
        if combat_manager is None:
            return False

        for round_number in range(1, 4):
            if grandmaster.get_weapon_type(self.player_char, "Weapon") != weapon_type:
                self._show_message(
                    f"The trial requires {weapon_type} in your main hand. The gauntlet resets."
                )
                return False
            self._apply_trial_recovery_floor()
            tile = GrandmasterTrialTile(0, 0, 0)
            tile.enemy = None
            won = combat_manager.start_combat(
                self.player_char,
                self._trial_enemy(weapon_type, round_number, rebind=rebind),
                tile,
            )
            if not won:
                return False
        return True

    def visit_grandmaster_secret_hall(self, background_draw_func=None):
        state = grandmaster.normalize_state(
            getattr(self.player_char, "grandmaster_discipline", None)
        )
        rebind = bool(state["activated"])
        intro = (
            "The Sergeant studies the Class Ring and unlocks a narrow door behind the old banners. "
            "Master Varric waits in the hidden hall, ready to test the weapon you choose."
        )
        if rebind:
            intro = (
                "Master Varric nods toward the training floor. The ring can be rebound, but only "
                "if you prove the new discipline against a harder trial."
            )
        self._show_message(intro, background_draw_func=background_draw_func)

        weapon_type = self._choose_grandmaster_weapon(rebind=rebind)
        if weapon_type is None:
            return False
        if grandmaster.get_weapon_type(self.player_char, "Weapon") != weapon_type:
            self._show_message(
                f"Equip a {weapon_type} in your main hand before beginning the trial."
            )
            return False

        if not self._run_grandmaster_gauntlet(weapon_type, rebind=rebind):
            self._show_message("The gauntlet resets. Master Varric waits for your next attempt.")
            return False

        grandmaster.bind_weapon(self.player_char, weapon_type)
        ring = self.player_char.equipment.get("Ring")
        if getattr(ring, "name", None) == "Class Ring":
            ring.class_mod(self.player_char)
        self._show_message(
            f"The Class Ring awakens to {weapon_type} Discipline."
            if not rebind
            else f"The Class Ring is rebound to {weapon_type} Discipline."
        )
        return True

    def _berserker_duel_enemy(self):
        level = max(1, int(getattr(getattr(self.player_char, "level", None), "level", 1)))
        pro_level = max(1, int(getattr(getattr(self.player_char, "level", None), "pro_level", 1)))
        scale = 1 + (pro_level * 0.20)
        enemy = enemies.Enemy(
            name="Scarred Barracks Champion",
            health=int((95 + level * 10 + pro_level * 28) * scale),
            mana=0,
            strength=int((22 + level // 2 + pro_level * 4) * scale),
            intel=6,
            wisdom=8,
            con=int((18 + level // 3 + pro_level * 3) * scale),
            charisma=10,
            dex=int((16 + level // 3 + pro_level * 2) * scale),
            attack=int((24 + level // 2 + pro_level * 4) * scale),
            defense=int((16 + level // 3 + pro_level * 3) * scale),
            magic=0,
            magic_def=int((10 + level // 4) * scale),
            exp=0,
        )
        enemy.gold = 0
        enemy.inventory = {}
        enemy.enemy_typ = "Trial"
        enemy.class_ring_trial_enemy = True
        enemy.class_ring_trial_name = "No Healing Duel"
        enemy.class_ring_no_healing_duel = True
        return enemy

    def _run_berserker_duel(self):
        combat_manager = getattr(
            getattr(self.game, "dungeon_manager", None), "combat_manager", None
        )
        if combat_manager is None:
            return False

        self._apply_trial_recovery_floor()
        tile = GrandmasterTrialTile(0, 0, 0)
        tile.enemy = None
        return combat_manager.start_combat(
            self.player_char,
            self._berserker_duel_enemy(),
            tile,
        )

    def visit_berserker_no_healing_duel(self, background_draw_func=None):
        self._show_message(
            "The Sergeant clears the sparring floor. A scarred champion waits with no healer, "
            "no mercy, and one rule: win without restoring your wounds.",
            background_draw_func=background_draw_func,
        )

        if not self._run_berserker_duel():
            self._show_message("The duel ends. The champion waits for a cleaner victory.")
            return False

        success, message = self.player_char.awaken_class_ring("Berserker")
        ring = self.player_char.equipment.get("Ring")
        if success and getattr(ring, "name", None) == "Class Ring":
            ring.class_mod(self.player_char)
        self._show_message(message.strip() or "The Class Ring awakens through the No Healing Duel.")
        return success

    def _legacy_barracks_trial_enemy(self):
        config = self._legacy_barracks_trial_config()
        if not config:
            return None
        level = max(1, int(getattr(getattr(self.player_char, "level", None), "level", 1)))
        pro_level = max(1, int(getattr(getattr(self.player_char, "level", None), "pro_level", 1)))
        scale = float(config.get("scale", 1.0)) * (1 + (pro_level * 0.18))
        stats = config["stats"]
        enemy = enemies.Enemy(
            name=config["enemy_name"],
            health=int((stats["health"] + level * 9 + pro_level * 24) * scale),
            mana=int((stats["mana"] + level * 2) * scale),
            strength=int((stats["strength"] + level // 2 + pro_level * 3) * scale),
            intel=int((stats["intel"] + level // 4) * scale),
            wisdom=int((stats["wisdom"] + level // 4) * scale),
            con=int((stats["con"] + level // 3 + pro_level * 3) * scale),
            charisma=stats["charisma"],
            dex=int((stats["dex"] + level // 3 + pro_level * 2) * scale),
            attack=int((stats["attack"] + level // 2 + pro_level * 3) * scale),
            defense=int((stats["defense"] + level // 3 + pro_level * 3) * scale),
            magic=int((stats["magic"] + level // 5) * scale),
            magic_def=int((stats["magic_def"] + level // 4) * scale),
            exp=0,
        )
        enemy.gold = 0
        enemy.inventory = {}
        enemy.enemy_typ = "Trial"
        enemy.class_ring_trial_enemy = True
        enemy.class_ring_trial_name = config["label"]
        return enemy

    def _run_legacy_barracks_trial(self):
        combat_manager = getattr(
            getattr(self.game, "dungeon_manager", None), "combat_manager", None
        )
        if combat_manager is None:
            return False
        enemy = self._legacy_barracks_trial_enemy()
        if enemy is None:
            return False

        self._apply_trial_recovery_floor()
        tile = GrandmasterTrialTile(0, 0, 0)
        tile.enemy = None
        return combat_manager.start_combat(self.player_char, enemy, tile)

    def visit_legacy_barracks_class_ring_trial(self, background_draw_func=None):
        class_name = class_rings.class_name(self.player_char)
        config = self._legacy_barracks_trial_config()
        if not config:
            return False

        self._show_message(config["intro"], background_draw_func=background_draw_func)
        if not self._run_legacy_barracks_trial():
            self._show_message(config["failure"])
            return False

        success, message = self.player_char.awaken_class_ring(class_name)
        ring = self.player_char.equipment.get("Ring")
        if success and getattr(ring, "name", None) == "Class Ring":
            ring.class_mod(self.player_char)
        self._show_message(message.strip() or f"The Class Ring awakens through {config['label']}.")
        return success

    def _quest_turned_in(self, quest_name):
        quest_dict = getattr(self.player_char, "quest_dict", {})
        for quest_type in ("Main", "Progression", "Side"):
            quest_data = quest_dict.get(quest_type, {}).get(quest_name)
            if isinstance(quest_data, dict) and quest_data.get("Turned In"):
                return True
        return False

    def _deposit_storage_reward(self, item_factory, quantity: int) -> str | None:
        """Add milestone reward items directly to storage without moving inventory."""
        if quantity <= 0:
            return None

        storage = getattr(self.player_char, "storage", None)
        if not isinstance(storage, dict):
            self.player_char.storage = {}
            storage = self.player_char.storage

        sample_item = item_factory()
        item_list = storage.setdefault(sample_item.name, [])
        item_list.extend(item_factory() for _ in range(quantity))
        return f"{quantity}x {sample_item.name}"

    def _grant_milestone_storage_rewards(self, background_draw_func=None):
        """Deposit one-time milestone supplies in the player's storage locker."""
        quest_dict = getattr(self.player_char, "quest_dict", None)
        if not isinstance(quest_dict, dict):
            return []

        claimed = quest_dict.setdefault("Milestone Storage Rewards", {})
        granted = []
        for quest_name, rewards in self.MILESTONE_STORAGE_REWARDS:
            if claimed.get(quest_name) or not self._quest_turned_in(quest_name):
                continue

            for item_factory, quantity in rewards:
                grant_text = self._deposit_storage_reward(item_factory, quantity)
                if grant_text:
                    granted.append(grant_text)
            claimed[quest_name] = True

        if granted:
            reward_text = ", ".join(granted)
            popup = ConfirmationPopup(
                self.presenter,
                f"The quartermaster stocked your storage locker with milestone supplies: {reward_text}.",
                show_buttons=False,
            )
            popup.show(
                background_draw_func=background_draw_func,
                flush_events=True,
                require_key_release=True,
            )

        return granted

    def manage_storage(self):
        """Access storage system."""
        storage_options = ["Store Items", "Leave"]

        # Add retrieve option if storage has items
        if self.player_char.storage:
            storage_options.insert(1, "Retrieve Items")

        storage_screen = LocationMenuScreen(self.presenter, "Storage Locker")

        while True:
            choice = storage_screen.navigate(
                storage_options,
                reset_cursor=False,
                flush_events=True,
                require_key_release=True,
            )

            if choice is None or (choice is not None and storage_options[choice] == "Leave"):
                break

            if storage_options[choice] == "Store Items":
                self.store_items()
                # Update menu if storage now has items
                if self.player_char.storage and "Retrieve Items" not in storage_options:
                    storage_options.insert(1, "Retrieve Items")

            elif storage_options[choice] == "Retrieve Items":
                self.retrieve_items()
                # Update menu if storage is now empty
                if not self.player_char.storage and "Retrieve Items" in storage_options:
                    storage_options.remove("Retrieve Items")

    def store_items(self):
        """Store items in storage locker."""
        if not self.player_char.inventory:
            popup = ConfirmationPopup(
                self.presenter, "You have no items to store.", show_buttons=False
            )
            popup.show(flush_events=True, require_key_release=True)
            return

        from .confirmation_popup import QuantityPopup

        store_screen = LocationMenuScreen(self.presenter, "Store Items")

        while True:
            # Build item list
            item_options = []
            item_data_list = []
            items_display = []

            for name, items_list in self.player_char.inventory.items():
                if items_list:
                    count = len(items_list)
                    item = items_list[0]  # Get first item as representative
                    item_options.append(name)
                    item_data_list.append((item, count))
                    items_display.append((item.name, count))

            if not item_options:
                popup = ConfirmationPopup(
                    self.presenter, "You have no items to store.", show_buttons=False
                )
                popup.show(flush_events=True, require_key_release=True)
                return

            item_options.append("Back")
            items_display.append(("Back", 0))

            # Show items list in right panel and navigate on right
            choice = store_screen.navigate_with_content(
                items_display,
                flush_events=True,
                require_key_release=True,
            )

            if choice is None or items_display[choice][0] == "Back":
                return

            item, count = item_data_list[choice]

            # Use QuantityPopup for quantity selection
            qty_popup = QuantityPopup(
                self.presenter, item.name, unit_cost=0, max_quantity=count, action="store"
            )
            quantity = qty_popup.show(flush_events=True, require_key_release=True)

            if quantity is None or quantity == 0:
                continue

            # Move to storage
            self.player_char.modify_inventory(item, num=quantity, storage=True, subtract=True)
            popup = ConfirmationPopup(
                self.presenter, f"Stored {quantity}x {item.name}", show_buttons=False
            )
            popup.show(flush_events=True, require_key_release=True)

    def retrieve_items(self):
        """Retrieve items from storage locker."""
        if not self.player_char.storage:
            popup = ConfirmationPopup(self.presenter, "Your storage is empty.", show_buttons=False)
            popup.show(flush_events=True, require_key_release=True)
            return

        from .confirmation_popup import QuantityPopup

        storage_screen = LocationMenuScreen(self.presenter, "Retrieve Items")

        while True:
            # Build storage list
            storage_options = []
            storage_data_list = []
            storage_display = []

            for name, item_list in self.player_char.storage.items():
                if item_list:
                    count = len(item_list)
                    storage_options.append(name)
                    storage_data_list.append((item_list[0], count))
                    storage_display.append((item_list[0].name, count))

            if not storage_options:
                popup = ConfirmationPopup(
                    self.presenter, "Your storage is empty.", show_buttons=False
                )
                popup.show(flush_events=True, require_key_release=True)
                return

            storage_options.append("Back")
            storage_display.append(("Back", 0))

            # Show items list in right panel and navigate on right
            choice = storage_screen.navigate_with_content(
                storage_display,
                flush_events=True,
                require_key_release=True,
            )

            if choice is None or storage_display[choice][0] == "Back":
                return

            item, count = storage_data_list[choice]

            # Use QuantityPopup for quantity selection
            qty_popup = QuantityPopup(
                self.presenter,
                item.name,
                unit_cost=0,
                max_quantity=count,
                action="retrieve",
                default_quantity=count,
            )
            quantity = qty_popup.show(flush_events=True, require_key_release=True)

            if quantity is None or quantity == 0:
                continue

            # Move from storage to inventory (subtract=False means add to inventory, remove from storage)
            self.player_char.modify_inventory(item, num=quantity, storage=True, subtract=False)
            popup = ConfirmationPopup(
                self.presenter, f"Retrieved {quantity}x {item.name}", show_buttons=False
            )
            popup.show(flush_events=True, require_key_release=True)
