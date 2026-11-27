"""Main storyline progression state helpers."""

from __future__ import annotations

from copy import deepcopy

from . import opening_story

GUARDIAN_TRIALS = (
    "Triangulus",
    "Quadrata",
    "Hexagonum",
    "Luna",
    "Polaris",
    "Infinitas",
)

GUARDIAN_TRIAL_CHOICES = {
    "Triangulus": ("Name", "Body", "Memory"),
    "Quadrata": ("Obey", "Resist", "Rewrite"),
    "Hexagonum": ("Root", "Fang", "River"),
    "Luna": ("Protect", "Release", "Share"),
    "Polaris": ("Trust", "Question", "Remember"),
    "Infinitas": ("Endure", "Break", "Rest"),
}

GUARDIAN_CLUE_MEANINGS = {
    "Triangulus": "selfhood is chosen, not assigned",
    "Quadrata": "order without consent becomes tyranny",
    "Hexagonum": "instinct begins life, but does not define meaning",
    "Luna": "love without freedom becomes possession or obligation",
    "Polaris": "guidance must invite, not command",
    "Infinitas": "endurance only has meaning when stopping or continuing is a choice",
}

GUARDIAN_VIGNETTE_SUMMARIES = {
    "Triangulus": "identity chosen through name, body, and memory",
    "Quadrata": "order worthy only when consent can resist or rewrite it",
    "Hexagonum": "root, fang, and river become meaning through choice",
    "Luna": "love protects, releases, or shares without possession",
    "Polaris": "guidance permits trust, questioning, and remembered direction",
    "Infinitas": "endurance matters because stopping and continuing remain choices",
}

CLASS_VOLUNTAS_ARCHETYPES = {
    "martial": ("Grandmaster of Arms", "Berserker", "Dragoon", "Stalwart Defender", "Master Monk"),
    "mystic": ("Wizard", "Archbishop", "Astromancer", "Archdruid"),
    "hybrid": (
        "Crusader",
        "Knight Enchanter",
        "Seeker",
        "Arcane Trickster",
        "Templar",
        "Hierophant",
    ),
    "companion": ("Thaumaturgist", "Troubadour", "Beast Master"),
    "shadow": ("Demonologist", "Shadowcaster", "Rogue", "Ninja", "Lycan", "Soulcatcher"),
}

CLASS_VOLUNTAS_BRIDGE_CLASSES = (
    "Grandmaster of Arms",
    "Demonologist",
    "Archdruid",
    "Berserker",
    "Crusader",
    "Dragoon",
    "Stalwart Defender",
    "Wizard",
    "Shadowcaster",
    "Knight Enchanter",
    "Thaumaturgist",
    "Rogue",
    "Seeker",
    "Ninja",
    "Arcane Trickster",
    "Templar",
    "Hierophant",
    "Master Monk",
    "Archbishop",
    "Troubadour",
    "Lycan",
    "Astromancer",
    "Soulcatcher",
    "Beast Master",
)

REFLECTION_VOLUNTAS_ANSWERS = ("Claim", "Carry", "ChooseAgain")

REFLECTION_VOLUNTAS_ANSWER_SUMMARIES = {
    "Claim": "Reflection answer: claimed the chosen path",
    "Carry": "Reflection answer: carried the untaken paths without surrendering the chosen one",
    "ChooseAgain": "Reflection answer: kept choosing as the proof of self",
}

GUARDIAN_TRIAL_DEFINITIONS = {
    "Triangulus": {
        "kind": "combat",
        "question": "What proves the self?",
        "intro_event": "Triangulus Trial Intro",
        "complete_event": "Triangulus Trial Complete",
        "defeat_event": "Triangulus Trial Defeat",
    },
    "Quadrata": {
        "kind": "puzzle",
        "question": "What should order do?",
        "intro_event": "Quadrata Trial Intro",
        "complete_event": "Quadrata Trial Complete",
        "defeat_event": None,
    },
    "Hexagonum": {
        "kind": "choice",
        "question": "How does nature answer?",
        "intro_event": "Hexagonum Trial Intro",
        "complete_event": "Hexagonum Trial Complete",
        "defeat_event": None,
    },
    "Luna": {
        "kind": "choice",
        "question": "What does love choose?",
        "intro_event": "Luna Trial Intro",
        "complete_event": "Luna Trial Complete",
        "defeat_event": None,
    },
    "Polaris": {
        "kind": "puzzle",
        "question": "How do you follow guidance?",
        "intro_event": "Polaris Trial Intro",
        "complete_event": "Polaris Trial Complete",
        "defeat_event": None,
    },
    "Infinitas": {
        "kind": "combat",
        "question": "How do you face the endless?",
        "intro_event": "Infinitas Trial Intro",
        "complete_event": "Infinitas Trial Complete",
        "defeat_event": "Infinitas Trial Defeat",
    },
}

for _guardian, _definition in GUARDIAN_TRIAL_DEFINITIONS.items():
    _definition["choices"] = GUARDIAN_TRIAL_CHOICES[_guardian]
    _definition["choice_events"] = {
        choice: f"{_guardian} Trial {choice}" for choice in GUARDIAN_TRIAL_CHOICES[_guardian]
    }

ROUTE_ORDERS = ("Escort", "Exception", "SignOut")

ACT_TWO_ANSWERS = {
    "liora_reply": ("burial", "tracks", "map"),
    "polaris_advice": ("inspect", "refuse"),
    "infinitas_return": ("rest", "help", "continue"),
}

# Memories belong to the choices the player actually witnessed in Silvana.
GUARDIAN_MEMORIES = {
    "Quadrata": (
        "route_order",
        {
            "Escort": "A key knocks against a litter pole. You put its bearer at the head of the crew.",
            "Exception": "You remember the key dropping into the soldier's palm. His sister knew his voice.",
            "SignOut": "You can see the landing written beside his name. Someone knew where to send the blanket.",
        },
    ),
    "Hexagonum": (
        "hexagonum_report_seen",
        {
            True: "White threads cling to a jar. You hear Mara asking what the people in the queue are supposed to drink."
        },
    ),
    "Luna": (
        "liora_reply",
        {
            "burial": "For an instant the weight in your hands is the last stone you laid by the pen.",
            "tracks": "You see two boot prints beyond the bent bars. Liora wanted to know where they went.",
            "map": "You remember Liora's fingertip resting on the spot you showed her.",
        },
    ),
    "Polaris": (
        "polaris_advice",
        {
            "inspect": "You unfold the survey again in memory. An ink doorway. Solid stone under your palm.",
            "refuse": "Your fingers find the button you fastened over your map. The Figure moved aside when you asked.",
        },
    ),
    "Infinitas": (
        "infinitas_return",
        {
            "rest": "A hinge turns without a sound. Oren kept his word and let you sleep.",
            "help": "You remember Pell holding the lamp while Oren checked the strap on your pack.",
            "continue": "The smell of the supper you stayed for comes back before you can recall the road.",
        },
    ),
}


def guardian_memory(story, guardian):
    """Recall a witnessed scene, leaving missing or migrated answers unspoken."""
    if guardian == "Triangulus":
        answer = opening_story.TRIANGULUS_ANSWER_TEXT.get(story.get("triangulus_identity_answer"))
        return f"Your own voice comes back from the first altar. ‘{answer}’" if answer else None
    key, memories = GUARDIAN_MEMORIES[guardian]
    return memories.get(story.get(key))


DEFAULT_MAIN_STORY_STATE = {
    "route_order": None,
    "joffrey_departed": False,
    "joffrey_found": False,
    "liora_letter_read": False,
    "luna_report_seen": False,
    "closing_tavern_seen": False,
    "epilogue_choice": None,
    "liora_reply": None,
    "polaris_advice": None,
    "infinitas_return": None,
    "joffrey_chalk_seen": False,
    "quadrata_report_seen": False,
    "hexagonum_report_seen": False,
    **opening_story.copied_defaults(),
    "vesperion_false_final_triggered": False,
    "pending_liminal_gap_entry": False,
    "liminal_gap_entered": False,
    "liminal_gap_guide_revealed": False,
    "liminal_gap_guide_save_used": False,
    "liminal_gap_clues_reviewed": False,
    "guardian_trials_started": {guardian: False for guardian in GUARDIAN_TRIALS},
    "guardian_trials_completed": {guardian: False for guardian in GUARDIAN_TRIALS},
    "guardian_trial_choices": {guardian: None for guardian in GUARDIAN_TRIALS},
    "voluntas_clues_found": {guardian: False for guardian in GUARDIAN_TRIALS},
    "guardian_trial_vignettes_seen": {guardian: False for guardian in GUARDIAN_TRIALS},
    "liminal_trial_v2_reviewed": False,
    "voluntas_revealed": False,
    "seventh_seat_revealed": False,
    "acolyte_liminal_seen": False,
    "reflection_attempts": 0,
    "reflection_failures": 0,
    "reflection_defeated": False,
    "returned_from_liminal_gap": False,
    "hooded_figure_witness_revealed": False,
    "hooded_figure_angelic_confirmed": False,
    "class_voluntas_affirmed": False,
    "class_voluntas_affirmed_class": None,
    "class_voluntas_affirmed_ring_awakened": False,
    "class_voluntas_affirmed_archetype": None,
    "reflection_voluntas_answer": None,
    "hooded_figure_witness_farewell_seen": False,
    "class_voluntas_followup_seen": False,
    "class_voluntas_bridge_seen": False,
    "reflection_path_mirror_seen": False,
    "vesperion_choice_argument_seen": False,
    "true_final_unlocked": False,
    "vesperion_true_final_defeated": False,
    "main_story_complete": False,
}


def default_state() -> dict[str, object]:
    """Return a fresh main-story state dictionary."""
    return deepcopy(DEFAULT_MAIN_STORY_STATE)


def normalize_state(state: object = None) -> dict[str, object]:
    """Return a backward-compatible main-story progression dictionary."""
    normalized = default_state()
    if isinstance(state, dict):
        for key in DEFAULT_MAIN_STORY_STATE:
            if key in {
                "guardian_trials_started",
                "guardian_trials_completed",
                "voluntas_clues_found",
                "guardian_trial_vignettes_seen",
            }:
                saved_trials = state.get(key, {})
                if isinstance(saved_trials, dict):
                    normalized[key] = {
                        guardian: bool(saved_trials.get(guardian, False))
                        for guardian in GUARDIAN_TRIALS
                    }
                continue
            if key == "guardian_trial_choices":
                saved_choices = state.get(key, {})
                if isinstance(saved_choices, dict):
                    normalized[key] = {
                        guardian: (
                            saved_choices.get(guardian)
                            if saved_choices.get(guardian) in GUARDIAN_TRIAL_CHOICES[guardian]
                            else None
                        )
                        for guardian in GUARDIAN_TRIALS
                    }
                continue
            if key in {"reflection_attempts", "reflection_failures"}:
                try:
                    normalized[key] = max(0, int(state.get(key, normalized[key])))
                except (TypeError, ValueError):
                    normalized[key] = 0
                continue
            if key == "class_voluntas_affirmed_class":
                saved_class = state.get(key)
                normalized[key] = str(saved_class).strip() if saved_class else None
                continue
            if key == "class_voluntas_affirmed_archetype":
                saved_archetype = state.get(key)
                normalized_archetype = str(saved_archetype).strip() if saved_archetype else ""
                normalized[key] = (
                    normalized_archetype
                    if normalized_archetype in {*CLASS_VOLUNTAS_ARCHETYPES, "wanderer"}
                    else None
                )
                continue
            if key in ACT_TWO_ANSWERS:
                answer = state.get(key)
                normalized[key] = answer if answer in ACT_TWO_ANSWERS[key] else None
                continue
            if key == "epilogue_choice":
                choice = state.get(key)
                normalized[key] = choice if choice in ("chair", "bread", "coat") else None
                continue
            if key == "route_order":
                order = state.get(key)
                normalized[key] = order if order in ROUTE_ORDERS else None
                continue
            if key == "reflection_voluntas_answer":
                saved_answer = state.get(key)
                normalized[key] = (
                    saved_answer if saved_answer in REFLECTION_VOLUNTAS_ANSWERS else None
                )
                continue
            if key in opening_story.OPENING_STATE_DEFAULTS:
                normalized[key] = state.get(key, normalized[key])
                continue
            normalized[key] = bool(state.get(key, normalized[key]))
    if (
        normalized.get("class_voluntas_affirmed")
        and not normalized.get("class_voluntas_affirmed_archetype")
        and normalized.get("class_voluntas_affirmed_class")
    ):
        normalized["class_voluntas_affirmed_archetype"] = class_voluntas_archetype(
            normalized.get("class_voluntas_affirmed_class")
        )
    opening_story.normalize_opening_fields(normalized)
    return normalized


def ensure_state(player) -> dict[str, object]:
    """Attach normalized main-story state to a player and return it."""
    player.main_story = normalize_state(getattr(player, "main_story", None))
    return player.main_story


def all_guardian_trials_completed(story_state: dict[str, object]) -> bool:
    """Return whether every Guardian trial has been completed."""
    completed = story_state.get("guardian_trials_completed", {})
    return isinstance(completed, dict) and all(
        completed.get(guardian) for guardian in GUARDIAN_TRIALS
    )


def all_voluntas_clues_found(story_state: dict[str, object]) -> bool:
    """Return whether every Guardian Voluntas clue has been found."""
    clues = story_state.get("voluntas_clues_found", {})
    return isinstance(clues, dict) and all(clues.get(guardian) for guardian in GUARDIAN_TRIALS)


def completed_guardian_count(story_state: dict[str, object]) -> int:
    """Return how many Guardian trials have been completed."""
    completed = story_state.get("guardian_trials_completed", {})
    if not isinstance(completed, dict):
        return 0
    return sum(1 for guardian in GUARDIAN_TRIALS if completed.get(guardian))


def guardian_clue_summary(story_state: dict[str, object]) -> list[str]:
    """Return readable summaries for each awakened Guardian clue."""
    clues = story_state.get("voluntas_clues_found", {})
    choices = story_state.get("guardian_trial_choices", {})
    if not isinstance(clues, dict):
        clues = {}
    if not isinstance(choices, dict):
        choices = {}

    summaries: list[str] = []
    for guardian in GUARDIAN_TRIALS:
        if not clues.get(guardian):
            continue
        choice = choices.get(guardian)
        choice_text = f" ({choice})" if choice else ""
        summaries.append(f"{guardian}{choice_text}: {GUARDIAN_CLUE_MEANINGS[guardian]}.")
    return summaries


def guardian_trial_vignette_seen(story_state: dict[str, object], guardian_name: str) -> bool:
    """Return whether a Guardian's deeper trial vignette has been seen."""
    if guardian_name not in GUARDIAN_TRIALS:
        return False
    seen = story_state.get("guardian_trial_vignettes_seen", {})
    return isinstance(seen, dict) and bool(seen.get(guardian_name))


def record_guardian_trial_vignette(story_state: dict[str, object], guardian_name: str) -> bool:
    """Record a Guardian's deeper trial vignette once."""
    if guardian_name not in GUARDIAN_TRIALS:
        return False

    seen = story_state.get("guardian_trial_vignettes_seen")
    if not isinstance(seen, dict):
        seen = {}
    normalized_seen = {guardian: bool(seen.get(guardian, False)) for guardian in GUARDIAN_TRIALS}
    already_seen = normalized_seen[guardian_name]
    normalized_seen[guardian_name] = True
    story_state["guardian_trial_vignettes_seen"] = normalized_seen
    return not already_seen


def completed_guardian_vignette_count(story_state: dict[str, object]) -> int:
    """Return how many deeper Guardian trial vignettes have been seen."""
    seen = story_state.get("guardian_trial_vignettes_seen", {})
    if not isinstance(seen, dict):
        return 0
    return sum(1 for guardian in GUARDIAN_TRIALS if seen.get(guardian))


def guardian_vignette_summary(story_state: dict[str, object]) -> list[str]:
    """Return readable summaries for each seen deeper Guardian vignette."""
    seen = story_state.get("guardian_trial_vignettes_seen", {})
    choices = story_state.get("guardian_trial_choices", {})
    if not isinstance(seen, dict):
        seen = {}
    if not isinstance(choices, dict):
        choices = {}

    summaries: list[str] = []
    for guardian in GUARDIAN_TRIALS:
        if not seen.get(guardian):
            continue
        choice = choices.get(guardian)
        choice_text = f" ({choice})" if choice in GUARDIAN_TRIAL_CHOICES[guardian] else ""
        summaries.append(f"{guardian}{choice_text}: {GUARDIAN_VIGNETTE_SUMMARIES[guardian]}.")
    return summaries


def guardian_trial_definition(guardian_name: str) -> dict[str, object]:
    """Return the configured Guardian trial definition."""
    return GUARDIAN_TRIAL_DEFINITIONS[guardian_name]


def guardian_trial_choices(guardian_name: str) -> tuple[str, ...]:
    """Return valid player answers for a Guardian trial."""
    return tuple(GUARDIAN_TRIAL_DEFINITIONS[guardian_name]["choices"])


def guardian_trial_question(guardian_name: str) -> str:
    """Return the prompt shown for a Guardian trial choice."""
    return str(GUARDIAN_TRIAL_DEFINITIONS[guardian_name]["question"])


def guardian_trial_event(
    guardian_name: str, answer: str | None = None, *, event: str | None = None
) -> str | None:
    """Return the special-event key for a Guardian trial beat."""
    definition = GUARDIAN_TRIAL_DEFINITIONS[guardian_name]
    if answer is not None:
        choice_events = definition.get("choice_events", {})
        return choice_events.get(answer) if isinstance(choice_events, dict) else None
    if event is None:
        return None
    value = definition.get(event)
    return str(value) if value else None


def is_guardian_trial_choice(guardian_name: str, answer: object) -> bool:
    """Return whether an answer belongs to the Guardian's valid choices."""
    return answer in GUARDIAN_TRIAL_CHOICES[guardian_name]


def record_guardian_trial_completion(
    story_state: dict[str, object], guardian_name: str, answer: str
) -> bool:
    """Record a completed Guardian trial and awakened clue."""
    if guardian_name not in GUARDIAN_TRIALS or not is_guardian_trial_choice(guardian_name, answer):
        return False
    story_state["guardian_trials_started"][guardian_name] = True
    story_state["guardian_trial_choices"][guardian_name] = answer
    story_state["guardian_trials_completed"][guardian_name] = True
    story_state["voluntas_clues_found"][guardian_name] = True
    return True


def should_confirm_hooded_figure_angelic(story_state: dict[str, object]) -> bool:
    """Return whether the post-Reflection Hooded Figure confirmation should play."""
    return bool(
        story_state.get("reflection_defeated")
        and story_state.get("hooded_figure_witness_revealed")
        and not story_state.get("hooded_figure_angelic_confirmed")
    )


def class_voluntas_archetype(class_name: object) -> str:
    """Return the story archetype for a class's Voluntas affirmation."""
    normalized_class = str(class_name).strip() if class_name else ""
    for archetype, class_names in CLASS_VOLUNTAS_ARCHETYPES.items():
        if normalized_class in class_names:
            return archetype
    return "wanderer"


def record_class_voluntas_affirmation(
    story_state: dict[str, object],
    class_name: object,
    ring_awakened: object,
) -> bool:
    """Record the optional Class Ring/Voluntas affirmation once."""
    if story_state.get("class_voluntas_affirmed"):
        return False

    normalized_class = str(class_name).strip() if class_name else ""
    if not normalized_class:
        return False

    story_state["class_voluntas_affirmed"] = True
    story_state["class_voluntas_affirmed_class"] = normalized_class
    story_state["class_voluntas_affirmed_ring_awakened"] = bool(ring_awakened)
    story_state["class_voluntas_affirmed_archetype"] = class_voluntas_archetype(normalized_class)
    return True


def record_reflection_voluntas_answer(story_state: dict[str, object], answer: object) -> bool:
    """Record the optional Reflection Voluntas answer once."""
    if story_state.get("reflection_voluntas_answer"):
        return False
    if answer not in REFLECTION_VOLUNTAS_ANSWERS:
        return False
    story_state["reflection_voluntas_answer"] = answer
    return True


def should_show_class_voluntas_followup(story_state: dict[str, object]) -> bool:
    """Return whether the optional class-path follow-up can be shown."""
    return bool(
        story_state.get("class_voluntas_affirmed")
        and not story_state.get("class_voluntas_followup_seen")
    )


def record_class_voluntas_followup(story_state: dict[str, object]) -> bool:
    """Record the optional class-path follow-up once."""
    if not should_show_class_voluntas_followup(story_state):
        return False
    story_state["class_voluntas_followup_seen"] = True
    return True


def should_show_class_voluntas_bridge(story_state: dict[str, object]) -> bool:
    """Return whether the optional per-class Voluntas bridge can be shown."""
    return bool(
        story_state.get("class_voluntas_affirmed")
        and story_state.get("class_voluntas_followup_seen")
        and not story_state.get("class_voluntas_bridge_seen")
    )


def record_class_voluntas_bridge(story_state: dict[str, object]) -> bool:
    """Record the optional per-class Voluntas bridge once."""
    if not should_show_class_voluntas_bridge(story_state):
        return False
    story_state["class_voluntas_bridge_seen"] = True
    return True


def class_voluntas_bridge_event_key(class_name: object) -> str:
    """Return the special-event key for a class-specific Voluntas bridge."""
    normalized_class = str(class_name).strip() if class_name else ""
    if normalized_class in CLASS_VOLUNTAS_BRIDGE_CLASSES:
        return f"Class Voluntas Bridge {normalized_class}"
    return "Class Voluntas Bridge Wanderer"


def should_show_reflection_path_mirror(story_state: dict[str, object]) -> bool:
    """Return whether the Reflection path mirror scene can be shown."""
    return bool(
        story_state.get("voluntas_revealed")
        and story_state.get("acolyte_liminal_seen")
        and not story_state.get("reflection_defeated")
        and not story_state.get("reflection_path_mirror_seen")
    )


def record_reflection_path_mirror(story_state: dict[str, object]) -> bool:
    """Record the Reflection path mirror once."""
    if not should_show_reflection_path_mirror(story_state):
        return False
    story_state["reflection_path_mirror_seen"] = True
    return True


def should_show_vesperion_choice_argument(story_state: dict[str, object]) -> bool:
    """Return whether the true-final Vesperion choice argument can be shown."""
    return bool(
        story_state.get("true_final_unlocked")
        and not story_state.get("vesperion_choice_argument_seen")
        and not story_state.get("main_story_complete")
    )


def record_vesperion_choice_argument(story_state: dict[str, object]) -> bool:
    """Record the true-final Vesperion choice argument once."""
    if not should_show_vesperion_choice_argument(story_state):
        return False
    story_state["vesperion_choice_argument_seen"] = True
    return True


def voluntas_path_summary(story_state: dict[str, object]) -> list[str]:
    """Return compact story-only summaries of the player's Voluntas path."""
    summaries: list[str] = []

    class_name = story_state.get("class_voluntas_affirmed_class")
    if story_state.get("class_voluntas_affirmed") and class_name:
        ring_state = (
            "awakened" if story_state.get("class_voluntas_affirmed_ring_awakened") else "dormant"
        )
        archetype = story_state.get(
            "class_voluntas_affirmed_archetype"
        ) or class_voluntas_archetype(class_name)
        summaries.append(f"Class path: {class_name} ({archetype}, {ring_state} ring).")
    else:
        summaries.append("Class path: no Class Ring affirmation recorded.")

    answer = story_state.get("reflection_voluntas_answer")
    if answer in REFLECTION_VOLUNTAS_ANSWER_SUMMARIES:
        summaries.append(f"{REFLECTION_VOLUNTAS_ANSWER_SUMMARIES[answer]}.")
    else:
        summaries.append("Reflection answer: not yet recorded.")

    clue_summaries = guardian_clue_summary(story_state)
    if clue_summaries:
        summaries.extend(clue_summaries)
    else:
        summaries.append("Guardian clues: none awakened.")

    vignette_count = completed_guardian_vignette_count(story_state)
    summaries.append(f"Guardian trial depths witnessed: {vignette_count}/{len(GUARDIAN_TRIALS)}.")
    return summaries


def should_show_hooded_witness_farewell(story_state: dict[str, object]) -> bool:
    """Return whether the Hooded Figure witness farewell can be shown."""
    return bool(
        story_state.get("reflection_defeated")
        and not story_state.get("returned_from_liminal_gap")
        and not story_state.get("hooded_figure_witness_farewell_seen")
    )


def can_reveal_voluntas(story_state: dict[str, object]) -> bool:
    """Return whether the Seventh Seat can reveal Voluntas."""
    return all_guardian_trials_completed(story_state) and all_voluntas_clues_found(story_state)


def can_unlock_true_final(story_state: dict[str, object]) -> bool:
    """Return whether the true final path has all narrative prerequisites."""
    return bool(story_state.get("voluntas_revealed") and story_state.get("reflection_defeated"))
