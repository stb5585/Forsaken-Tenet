"""Story behavior for the dungeon manager package."""

from src.core import enemies, main_story
from src.core.classes import class_rings

from .core import get_special_events


class DungeonStoryMixin:
    def _enter_liminal_gap_stub(self, return_location, vesperion=None):
        """Resolve the scripted false-final transition into the Liminal Gap hub."""
        self._show_special_event_dialogue(
            "Vesperion False Final",
            title="Vesperion",
        )

        enter_stub = getattr(self.player_char, "enter_liminal_gap_stub", None)
        if callable(enter_stub):
            enter_stub(return_location)

        self._show_special_event_dialogue("Liminal Gap Arrival", title="The Liminal Gap")
        self.add_message("You wake in the Liminal Gap, wounded but alive.")
        self._cached_view = None
        self._cached_frame = None
        self._mark_view_dirty()

    def _interact_liminal_guide(self, guide_tile):
        """Handle the Hooded Figure's Liminal Gap guide interaction."""
        story_state = self.player_char.ensure_main_story_state()
        if not story_state.get("liminal_gap_guide_revealed"):
            self._show_special_event_dialogue(
                "Hooded Figure Liminal Reveal", title="The Hooded Figure"
            )
            story_state["liminal_gap_guide_revealed"] = True

        options = ["Save Game", "Review Guardian Clues"]
        if main_story.completed_guardian_vignette_count(story_state) > 0:
            options.append("Review Trial Depths")
        if self._class_voluntas_affirmation_available(story_state):
            options.append("Affirm Class Path")
        if main_story.should_show_class_voluntas_followup(story_state):
            options.append("Revisit Class Path")
        if main_story.should_show_class_voluntas_bridge(story_state):
            options.append("Bridge Class Identity")
        if main_story.should_show_hooded_witness_farewell(story_state):
            options.append("Ask About the Witness")
        options.append("Leave")

        choice = self._popup_menu(
            "The Hooded Figure",
            options,
            flush_events=True,
            require_key_release=True,
        )
        selected = (
            options[choice] if isinstance(choice, int) and 0 <= choice < len(options) else "Leave"
        )
        if selected == "Review Guardian Clues":
            self._review_liminal_guardian_clues(story_state)
            guide_tile.read = True
            return
        if selected == "Review Trial Depths":
            self._review_liminal_trial_vignettes(story_state)
            guide_tile.read = True
            return
        if selected == "Affirm Class Path":
            self._affirm_class_voluntas_path(story_state, guide_tile)
            return
        if selected == "Revisit Class Path":
            self._revisit_class_voluntas_path(story_state, guide_tile)
            return
        if selected == "Bridge Class Identity":
            self._bridge_class_voluntas_identity(story_state, guide_tile)
            return
        if selected == "Ask About the Witness":
            self._show_hooded_witness_farewell(story_state, guide_tile)
            return
        if selected != "Save Game":
            self.add_message("The Hooded Figure waits in silence.")
            return

        self._show_special_event_dialogue("Liminal Guide Save", title="The Hooded Figure")
        save_game = getattr(self.game, "save_game", None)
        if callable(save_game):
            save_game()
            story_state["liminal_gap_guide_save_used"] = True
            guide_tile.read = True
            self.add_message("The Hooded Figure anchors your progress.")
        else:
            self.add_message("The Hooded Figure reaches for an anchor that is not there.")

    def _class_voluntas_affirmation_available(self, story_state):
        """Return whether the guide can offer the optional class-path affirmation."""
        identity = class_rings.class_voluntas_identity(self.player_char)
        return bool(
            story_state.get("voluntas_revealed")
            and not story_state.get("class_voluntas_affirmed")
            and identity.get("visible")
            and identity.get("class_name")
        )

    def _affirm_class_voluntas_path(self, story_state, guide_tile):
        """Play and record the optional Class Ring/Voluntas affirmation."""
        identity = class_rings.class_voluntas_identity(self.player_char)
        self._show_special_event_dialogue("Class Voluntas Affirmation", title="Voluntas")
        ring_event = (
            "Class Voluntas Awakened Ring"
            if identity.get("awakened")
            else "Class Voluntas Dormant Ring"
        )
        self._show_special_event_dialogue(ring_event, title="Class Ring")
        recorded = main_story.record_class_voluntas_affirmation(
            story_state,
            identity.get("class_name"),
            identity.get("awakened"),
        )
        archetype = story_state.get(
            "class_voluntas_affirmed_archetype"
        ) or main_story.class_voluntas_archetype(identity.get("class_name"))
        self._show_special_event_dialogue(
            f"Class Voluntas Archetype {str(archetype).title()}",
            title="Class Ring",
        )
        guide_tile.read = True
        if recorded:
            ring_state = "awakened" if identity.get("awakened") else "dormant"
            self.add_message(
                f"{identity.get('class_name')} is affirmed through a {ring_state} Class Ring."
            )
        else:
            self.add_message("The Class Ring has already answered Voluntas.")

    def _revisit_class_voluntas_path(self, story_state, guide_tile):
        """Play and record the optional Class Ring/Voluntas follow-up."""
        class_name = story_state.get("class_voluntas_affirmed_class") or "The chosen class"
        archetype = story_state.get(
            "class_voluntas_affirmed_archetype"
        ) or main_story.class_voluntas_archetype(class_name)
        self._show_special_event_dialogue("Class Voluntas Followup", title="Voluntas")
        self._show_special_event_dialogue(
            f"Class Voluntas Followup {str(archetype).title()}",
            title="Class Ring",
        )
        recorded = main_story.record_class_voluntas_followup(story_state)
        guide_tile.read = True
        if recorded:
            ring_state = (
                "awakened"
                if story_state.get("class_voluntas_affirmed_ring_awakened")
                else "dormant"
            )
            self.add_message(f"{class_name} is remembered through a {ring_state} Class Ring.")
        else:
            self.add_message("The Class Ring follow-up has already been remembered.")

    def _bridge_class_voluntas_identity(self, story_state, guide_tile):
        """Play and record the optional per-class Voluntas bridge."""
        class_name = story_state.get("class_voluntas_affirmed_class") or "The chosen class"
        event_key = main_story.class_voluntas_bridge_event_key(class_name)
        self._show_special_event_dialogue("Class Voluntas Bridge", title="Voluntas")
        self._show_special_event_dialogue(event_key, title="Class Ring")
        recorded = main_story.record_class_voluntas_bridge(story_state)
        guide_tile.read = True
        if recorded:
            self.add_message(f"{class_name} bridges its chosen path to Voluntas.")
        else:
            self.add_message("The Class Ring bridge has already been remembered.")

    def _show_hooded_witness_farewell(self, story_state, guide_tile):
        """Play the optional unnamed Hooded Figure witness farewell."""
        self._show_special_event_dialogue(
            "Hooded Figure Witness Farewell", title="The Hooded Figure"
        )
        story_state["hooded_figure_witness_farewell_seen"] = True
        guide_tile.read = True
        self.add_message("The Hooded Figure remains unnamed, but their witness is given freely.")

    def _review_liminal_guardian_clues(self, story_state):
        """Show the Hooded Figure's current summary of awakened Guardian clues."""
        self._show_special_event_dialogue("Liminal Clue Review", title="The Hooded Figure")
        story_state["liminal_gap_clues_reviewed"] = True
        summaries = main_story.guardian_clue_summary(story_state)
        completed_count = main_story.completed_guardian_count(story_state)
        self.add_message(
            f"Guardian clues awakened: {completed_count}/{len(main_story.GUARDIAN_TRIALS)}."
        )
        if not summaries:
            self.add_message("No Guardian clue has awakened yet.")
            return
        for summary in summaries:
            self.add_message(summary)

    def _review_liminal_trial_vignettes(self, story_state):
        """Show the Hooded Figure's summary of deeper Guardian trial vignettes."""
        self._show_special_event_dialogue("Liminal Trial V2 Review", title="The Hooded Figure")
        story_state["liminal_trial_v2_reviewed"] = True
        summaries = main_story.guardian_vignette_summary(story_state)
        completed_count = main_story.completed_guardian_vignette_count(story_state)
        self.add_message(
            f"Guardian trial depths witnessed: {completed_count}/{len(main_story.GUARDIAN_TRIALS)}."
        )
        if not summaries:
            self.add_message("No deeper Guardian trial has been witnessed yet.")
            return
        for summary in summaries:
            self.add_message(summary)

    def _interact_liminal_guardian_gate(self, gate_tile):
        """Run or report the selected Guardian trial gate."""
        guardian_name = getattr(gate_tile, "guardian_name", "Guardian")
        if guardian_name in main_story.GUARDIAN_TRIALS:
            self._interact_guardian_trial(gate_tile, guardian_name)
            return

        event_name = getattr(gate_tile, "liminal_gate_event", "Liminal No Exit")
        self._show_special_event_dialogue(event_name, title=guardian_name)
        gate_tile.read = True
        self.add_message(f"The gate of {guardian_name} remains sealed.")

    def _interact_guardian_trial(self, gate_tile, guardian_name):
        """Run a lightweight Guardian trial and record its Voluntas clue."""
        story_state = self.player_char.ensure_main_story_state()
        completed = story_state["guardian_trials_completed"]
        if completed.get(guardian_name):
            if not main_story.guardian_trial_vignette_seen(story_state, guardian_name):
                choice = self._popup_menu(
                    guardian_name,
                    ["Recall Deeper Trial", "Leave"],
                    flush_events=True,
                    require_key_release=True,
                )
                if choice == 0:
                    self._recall_guardian_trial_vignette(gate_tile, story_state, guardian_name)
                else:
                    self.add_message(f"You step back from the quiet gate of {guardian_name}.")
                return
            self._show_special_event_dialogue(
                f"{guardian_name} Trial Complete", title=guardian_name
            )
            self.add_message(f"The gate of {guardian_name} is quiet. Its trial is complete.")
            gate_tile.read = True
            return

        if not story_state.get("liminal_gap_guide_revealed"):
            event_name = getattr(gate_tile, "liminal_gate_event", f"{guardian_name} Gate")
            self._show_special_event_dialogue(event_name, title=guardian_name)
            self.add_message("The gate waits for the Hooded Figure to name the path.")
            return

        choice = self._popup_menu(
            guardian_name,
            ["Begin Trial", "Leave"],
            flush_events=True,
            require_key_release=True,
        )
        if choice != 0:
            self.add_message(f"You step back from the gate of {guardian_name}.")
            return

        trial_definition = main_story.guardian_trial_definition(guardian_name)
        story_state["guardian_trials_started"][guardian_name] = True
        intro_event = main_story.guardian_trial_event(guardian_name, event="intro_event")
        if intro_event:
            self._show_special_event_dialogue(intro_event, title=guardian_name)
        self._show_guardian_trial_v2_threshold(guardian_name)
        memory = main_story.guardian_memory(story_state, guardian_name)
        if memory:
            self._show_dungeon_dialogue(memory, title=guardian_name)
        answer_options = list(main_story.guardian_trial_choices(guardian_name))
        answer_choice = self._popup_menu(
            main_story.guardian_trial_question(guardian_name),
            answer_options,
            flush_events=True,
            require_key_release=True,
        )
        if answer_choice is None:
            self.add_message(f"The gate of {guardian_name} dims, awaiting a clearer answer.")
            return

        answer = answer_options[answer_choice]
        if trial_definition.get("kind") == "combat":
            combat_won = self._run_guardian_trial_echo(gate_tile, guardian_name, answer)
            if not combat_won:
                defeat_event = main_story.guardian_trial_event(guardian_name, event="defeat_event")
                if defeat_event:
                    self._show_special_event_dialogue(defeat_event, title=guardian_name)
                self.add_message(f"The gate of {guardian_name} remains open for another attempt.")
                return

        self._show_guardian_trial_v2_choice(guardian_name, answer)
        main_story.record_guardian_trial_vignette(story_state, guardian_name)

        if not main_story.record_guardian_trial_completion(story_state, guardian_name, answer):
            self.add_message(f"The gate of {guardian_name} dims, rejecting an impossible answer.")
            return
        gate_tile.read = True

        answer_event = main_story.guardian_trial_event(guardian_name, answer)
        if answer_event:
            self._show_special_event_dialogue(answer_event, title=guardian_name)
        for message in self._apply_guardian_trial_consequence(guardian_name, answer):
            self.add_message(message)
        complete_event = main_story.guardian_trial_event(guardian_name, event="complete_event")
        if complete_event:
            self._show_special_event_dialogue(complete_event, title=guardian_name)
        self.add_message(f"{guardian_name} answers. A clue of Voluntas awakens.")
        if main_story.can_reveal_voluntas(story_state) and not story_state.get("voluntas_revealed"):
            self._show_special_event_dialogue("Voluntas Pattern Complete", title="Voluntas")
            self.add_message("The six clues form a path toward the empty Seventh Seat.")

    def _show_guardian_trial_v2_threshold(self, guardian_name: str):
        """Show the deeper threshold vignette for a Guardian trial."""
        self._show_special_event_dialogue(
            f"{guardian_name} Trial V2 Threshold", title=guardian_name
        )

    def _show_guardian_trial_v2_choice(self, guardian_name: str, answer: str):
        """Show the deeper choice-specific vignette for a Guardian trial."""
        self._show_special_event_dialogue(f"{guardian_name} Trial V2 {answer}", title=guardian_name)

    def _recall_guardian_trial_vignette(self, gate_tile, story_state, guardian_name: str):
        """Replay a completed Guardian's deeper vignette without re-awarding progress."""
        self._show_guardian_trial_v2_threshold(guardian_name)
        choices = story_state.get("guardian_trial_choices", {})
        stored_answer = choices.get(guardian_name) if isinstance(choices, dict) else None
        answer = (
            stored_answer
            if main_story.is_guardian_trial_choice(guardian_name, stored_answer)
            else main_story.guardian_trial_choices(guardian_name)[0]
        )
        self._show_guardian_trial_v2_choice(guardian_name, answer)
        main_story.record_guardian_trial_vignette(story_state, guardian_name)
        gate_tile.read = True
        self.add_message(
            f"{guardian_name}'s deeper trial memory settles without changing the path already chosen."
        )

    def _run_guardian_trial_echo(self, gate_tile, guardian_name: str, answer: str) -> bool:
        """Run a combat-heavy Guardian trial and return whether it was won."""
        echo = enemies.GuardianTrialEcho(guardian_name, profile=answer)
        self.player_char.state = "fight"
        self.combat_manager.player_world_dict = self.player_char.world_dict
        self._refresh_cached_frame()
        combat_won = self.combat_manager.start_combat(
            self.player_char,
            echo,
            gate_tile,
        )
        self._cached_view = None
        self._cached_frame = None
        self._mark_view_dirty()
        return bool(combat_won)

    def _apply_guardian_trial_consequence(self, guardian_name: str, answer: str) -> list[str]:
        """Apply a small one-time Liminal trial consequence to the player."""
        del answer
        player = self.player_char
        if guardian_name == "Triangulus":
            restored = self._restore_resource(player.mana, 0.10)
            return [f"Triangulus steadies the chosen self, restoring {restored} MP."]
        if guardian_name == "Quadrata":
            status_effects = getattr(player, "status_effects", {})
            defend = status_effects.get("Defend")
            if defend is not None:
                defend.active = True
                defend.duration = max(getattr(defend, "duration", 0), 2)
                defend.extra = max(getattr(defend, "extra", 0), 0.25)
            return ["Quadrata sets a chosen order around you."]
        if guardian_name == "Hexagonum":
            restored = self._restore_resource(player.health, 0.15, minimum=1)
            return [f"Hexagonum answers through living endurance, restoring {restored} HP."]
        if guardian_name == "Luna":
            hp_restored = self._restore_resource(player.health, 0.08, minimum=1)
            mp_restored = self._restore_resource(player.mana, 0.08)
            return [
                f"Luna returns mercy freely chosen, restoring {hp_restored} HP and {mp_restored} MP."
            ]
        if guardian_name == "Polaris":
            status_effects = getattr(player, "status_effects", {})
            for status_name in ("Blind", "Silence"):
                effect = status_effects.get(status_name)
                if effect is not None:
                    effect.active = False
                    effect.duration = 0
            return ["Polaris fixes true north, clearing blindness and silence."]
        if guardian_name == "Infinitas":
            hp_restored = self._restore_to_half(player.health, minimum=1)
            mp_restored = self._restore_to_half(player.mana)
            return [
                f"Infinitas makes another step possible, restoring {hp_restored} HP and {mp_restored} MP."
            ]
        return []

    @staticmethod
    def _restore_resource(resource, fraction: float, *, minimum: int = 0) -> int:
        maximum = int(getattr(resource, "max", 0) or 0)
        before = int(getattr(resource, "current", 0) or 0)
        amount = max(minimum, int(maximum * fraction)) if maximum else 0
        resource.current = min(maximum, before + amount)
        return max(0, int(resource.current) - before)

    @staticmethod
    def _restore_to_half(resource, *, minimum: int = 0) -> int:
        maximum = int(getattr(resource, "max", 0) or 0)
        before = int(getattr(resource, "current", 0) or 0)
        target = max(minimum, maximum // 2)
        resource.current = max(before, min(maximum, target))
        return max(0, int(resource.current) - before)

    def _interact_liminal_exit_blocker(self, blocker_tile):
        """Explain why the player cannot leave the Liminal Gap yet."""
        story_state = self.player_char.ensure_main_story_state()
        if story_state.get("true_final_unlocked"):
            self._show_special_event_dialogue("Return From Liminal Gap", title="The Liminal Gap")
            returned = False
            return_from_liminal = getattr(self.player_char, "return_from_liminal_gap", None)
            if callable(return_from_liminal):
                returned = bool(return_from_liminal())
            blocker_tile.read = True
            self._cached_view = None
            self._cached_frame = None
            self._mark_view_dirty()
            if returned:
                self.add_message("You return to the final threshold with Voluntas awakened.")
            else:
                self.add_message("The path opens, but no return anchor remains.")
            return

        self._show_special_event_dialogue("Liminal No Exit", title="The Liminal Gap")
        blocker_tile.read = True
        self.add_message("There is no way back until the Guardian path is resolved.")

    def _interact_liminal_seventh_seat(self, seat_tile):
        """Reveal Voluntas after all six Guardian clues are complete."""
        story_state = self.player_char.ensure_main_story_state()
        if story_state.get("voluntas_revealed"):
            self._show_special_event_dialogue("Seventh Seat Reveal", title="Voluntas")
            self.add_message(
                "The empty Seventh Seat is quiet. Voluntas has already been remembered."
            )
            seat_tile.read = True
            return

        if not main_story.can_reveal_voluntas(story_state):
            self._show_special_event_dialogue("Seventh Seat Sealed", title="The Seventh Seat")
            self.add_message("The empty Seventh Seat waits for all six Guardian clues.")
            return

        self._show_special_event_dialogue("Seventh Seat Reveal", title="Voluntas")
        self._show_special_event_dialogue("Hooded Figure Witness Reveal", title="The Hooded Figure")
        story_state["seventh_seat_revealed"] = True
        story_state["voluntas_revealed"] = True
        story_state["hooded_figure_witness_revealed"] = True
        seat_tile.read = True
        self.add_message("Voluntas is remembered. The Reflection waits beyond the Acolyte.")

    def _interact_liminal_acolyte(self, acolyte_tile):
        """Show the non-combat Acolyte tragic mirror scene."""
        story_state = self.player_char.ensure_main_story_state()
        if not story_state.get("voluntas_revealed"):
            self._show_special_event_dialogue("Acolyte Liminal Waiting", title="The Acolyte")
            self.add_message("The Acolyte says nothing while Voluntas remains hidden.")
            return

        self._show_special_event_dialogue("Acolyte Liminal Mirror", title="The Acolyte")
        story_state["acolyte_liminal_seen"] = True
        acolyte_tile.read = True
        self.add_message("The Acolyte remains behind, emptied by the peace they accepted.")

    def _interact_liminal_reflection(self, reflection_tile):
        """Start or report the Reflection/Psychopomp encounter."""
        story_state = self.player_char.ensure_main_story_state()
        if not story_state.get("voluntas_revealed"):
            self._show_special_event_dialogue("Reflection Locked", title="Reflection")
            self.add_message("The Reflection will not form until Voluntas is remembered.")
            return
        if not story_state.get("acolyte_liminal_seen"):
            self._show_special_event_dialogue("Reflection Locked", title="Reflection")
            self.add_message("The Acolyte's warning must be faced before the Reflection.")
            return
        if story_state.get("reflection_defeated"):
            self._show_special_event_dialogue("Reflection Victory", title="Reflection")
            self._show_hooded_angelic_confirmation_if_ready(story_state)
            self.add_message("The Reflection is still. The way back is open.")
            reflection_tile.read = True
            return

        prior_attempts = int(story_state.get("reflection_attempts", 0))
        show_class_echo = bool(story_state.get("class_voluntas_affirmed") and prior_attempts == 0)
        story_state["reflection_attempts"] = prior_attempts + 1
        reflection = enemies.ReflectionPsychopomp()
        mirror_player = getattr(reflection, "mirror_player", None)
        if callable(mirror_player):
            mirror_player(self.player_char)
        prelude_event = self._reflection_profile_event(reflection, "Prelude")
        self._show_special_event_dialogue(prelude_event, title="Reflection")
        if show_class_echo:
            self._show_special_event_dialogue("Class Voluntas Reflection Echo", title="Voluntas")
        if not story_state.get("reflection_voluntas_answer"):
            self._ask_reflection_voluntas_answer(story_state)
        elif prior_attempts > 0:
            self._show_special_event_dialogue("Reflection Voluntas Retry", title="Voluntas")
        if main_story.should_show_reflection_path_mirror(story_state):
            self._show_special_event_dialogue("Reflection Path Mirror", title="Reflection")
            main_story.record_reflection_path_mirror(story_state)
            self._add_voluntas_path_summary_messages(story_state)
        self.player_char.state = "fight"
        self.combat_manager.player_world_dict = self.player_char.world_dict
        self._refresh_cached_frame()
        combat_won = self.combat_manager.start_combat(
            self.player_char,
            reflection,
            reflection_tile,
        )
        if combat_won:
            victory_event = self._reflection_profile_event(reflection, "Victory")
            self._show_special_event_dialogue(victory_event, title="Reflection")
            if story_state.get("reflection_voluntas_answer"):
                self._show_special_event_dialogue(
                    "Reflection Voluntas Victory Echo", title="Voluntas"
                )
            if story_state.get("reflection_path_mirror_seen"):
                self._show_special_event_dialogue(
                    "Reflection Path Victory Echo", title="Reflection"
                )
            self._show_hooded_angelic_confirmation_if_ready(story_state)
            reflection_tile.read = True
            self.add_message("The chosen self holds. The way back to Vesperion opens.")
        else:
            story_state["reflection_failures"] = int(story_state.get("reflection_failures", 0)) + 1
            defeat_event = self._reflection_profile_event(reflection, "Defeat")
            self._show_special_event_dialogue(defeat_event, title="Reflection")
            self.add_message("The Reflection returns you to the Liminal hub to choose again.")
        self._cached_view = None
        self._cached_frame = None
        self._mark_view_dirty()

    def _ask_reflection_voluntas_answer(self, story_state):
        """Ask the optional Reflection Voluntas presentation choice."""
        answer_options = ["Claim This Path", "Carry The Untaken", "Choose Again"]
        answer_values = ["Claim", "Carry", "ChooseAgain"]
        choice = self._popup_menu(
            "What does Voluntas ask of the self you chose?",
            answer_options,
            flush_events=True,
            require_key_release=True,
        )
        if not isinstance(choice, int) or choice < 0 or choice >= len(answer_values):
            self.add_message("Voluntas waits for an answer only you can give.")
            return False
        answer = answer_values[choice]
        if not main_story.record_reflection_voluntas_answer(story_state, answer):
            return False
        event_answer = "Choose Again" if answer == "ChooseAgain" else answer
        self._show_special_event_dialogue(
            f"Reflection Voluntas Choice {event_answer}",
            title="Voluntas",
        )
        return True

    @staticmethod
    def _reflection_profile_event(reflection, beat: str) -> str:
        """Return a profile-specific Reflection event key."""
        mirrored_path = getattr(reflection, "mirrored_path", {})
        profile = mirrored_path.get("profile") if isinstance(mirrored_path, dict) else None
        profile_suffix = (
            str(profile).title() if profile in {"martial", "mystic", "hybrid"} else "Hybrid"
        )
        event_name = f"Reflection {beat} {profile_suffix}"
        try:
            if event_name in get_special_events():
                return event_name
        except Exception:
            pass
        return f"Reflection {beat}"

    def _show_hooded_angelic_confirmation_if_ready(self, story_state) -> bool:
        """Play the one-time post-Reflection Hooded Figure confirmation."""
        if not main_story.should_confirm_hooded_figure_angelic(story_state):
            return False
        self._show_special_event_dialogue(
            "Hooded Figure Angelic Confirmation", title="The Hooded Figure"
        )
        story_state["hooded_figure_angelic_confirmed"] = True
        self.add_message("The Hooded Figure's hidden light answers Voluntas one last time.")
        return True

    def _show_vesperion_choice_argument_if_ready(self, story_state) -> bool:
        """Play the one-time true-final Vesperion choice argument."""
        if not main_story.record_vesperion_choice_argument(story_state):
            return False
        self._show_special_event_dialogue("Vesperion Choice Argument", title="Vesperion")
        self._show_special_event_dialogue("Vesperion Tragedy Reframing", title="Vesperion")
        answer = {
            "burial": "You remember Liora asking where he lay. She wanted to know someone stayed with him. Vesperion remembers the question he asked. You remember hers.",
            "tracks": "You told Liora about the footprints. The first thing she wanted was for Caedmon to find whoever had made it out.",
            "map": "You remember Liora leaning across the counter to see the place for herself. Vesperion talks straight over that part.",
        }.get(story_state.get("liora_reply"))
        if answer:
            self._show_dungeon_dialogue(answer, title="The Lower Pens")
        self._add_voluntas_path_summary_messages(story_state)
        return True

    def _add_voluntas_path_summary_messages(self, story_state) -> None:
        """Add compact Voluntas path summary lines to the message log."""
        for summary in main_story.voluntas_path_summary(story_state):
            self.add_message(summary)

    def _interact_incubus_lair(self, incubus_tile):
        """Handle Incubus lair interaction - spawn Incubus if quest is active."""
        # Check if quest is active
        if "Oedipal Complex" not in self.player_char.quest_dict.get("Side", {}):
            self.add_message("The oppressive atmosphere fades as you approach.")
            return

        quest_data = self.player_char.quest_dict["Side"]["Oedipal Complex"]

        # If quest already completed, show victory message
        if quest_data["Completed"]:
            self.add_message("Only ash remains of the once mighty Incubus.")
            return

        # If already defeated in this encounter, don't respawn
        if hasattr(incubus_tile, "defeated") and incubus_tile.defeated:
            self.add_message("The Incubus has been vanquished.")
            return

        # Spawn Incubus for battle
        self.add_message("A demonic figure materializes before you!")
        self.add_message("The Incubus: 'You dare challenge ME, the father of Merzhin?'")

        incubus_tile.enter_combat(self.player_char)
        enemy = incubus_tile.enemy

        self.player_char.state = "fight"
        self._refresh_cached_frame()

        combat_won = self.combat_manager.start_combat(self.player_char, enemy, incubus_tile)

        if combat_won:
            # Complete quest
            if incubus_tile.defeat_incubus(self.game):
                self.add_message("Quest completed: Oedipal Complex")
                self.add_message("You have proven your worthiness to Nimue!")
        elif not self.player_char.is_alive():
            self.add_message("You were defeated by the Incubus...")
        else:
            self.add_message("You escaped from the Incubus.")

    def _interact_golden_chalice_room(self, chalice_tile):
        """Handle Golden Chalice room interaction."""
        # Check if quest is active
        if "The Holy Grail of Quests" not in self.player_char.quest_dict.get("Side", {}):
            self.add_message("An invisible force prevents you from approaching the chalice.")
            return

        quest_data = self.player_char.quest_dict["Side"]["The Holy Grail of Quests"]

        # If quest already completed, show empty pedestal message
        if quest_data["Completed"]:
            self.add_message("An empty pedestal stands where the chalice once rested.")
            return

        # Prompt player to take the chalice
        from ..confirmation_popup import ConfirmationPopup

        popup = ConfirmationPopup(
            self.presenter,
            "A golden chalice rests on the pedestal, radiating holy light.\n\n"
            "Do you wish to take it?",
            show_buttons=True,
        )

        if popup.show(
            background_draw_func=self._dungeon_dialog_background,
            flush_events=True,
            require_key_release=True,
            min_display_ms=300,
        ):
            if chalice_tile.pickup_chalice_action(self.game):
                self.add_message("You obtain the Golden Chalice!")
                self.add_message("Quest completed: The Holy Grail of Quests")
                self.add_message("You can feel its blessing preparing you for the trials ahead.")
            else:
                self.add_message("Something prevents you from taking the chalice.")
        else:
            self.add_message("You decide to leave the chalice for now.")
