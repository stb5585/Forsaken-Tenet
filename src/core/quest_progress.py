"""Shared quest progression helpers for staged story quests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from . import items, main_story, opening_story

UNCERTAIN_REPORTS = "Uncertain Reports"
HOLY_RELICS = "The Holy Relics"
RELIC_NAMES = (
    "Triangulus",
    "Quadrata",
    "Hexagonum",
    "Luna",
    "Polaris",
    "Infinitas",
)
AUTHORED_QUEST_CATEGORIES = ("Main", "Progression", "Side")
QUEST_CATEGORIES = (*AUTHORED_QUEST_CATEGORIES, "Bounty")


@dataclass(frozen=True)
class RelicCollectionResult:
    """Outcome of the shared relic acquisition transition."""

    collected: bool
    relic: object | None = None
    quest_message: str = ""
    threshold_revealed: bool = False


def ensure_quest_categories(player) -> dict[str, dict]:
    """Return a normalized quest dictionary with core categories present."""
    quest_dict = getattr(player, "quest_dict", None)
    if not isinstance(quest_dict, dict):
        quest_dict = {}
        player.quest_dict = quest_dict
    for category in QUEST_CATEGORIES:
        if not isinstance(quest_dict.get(category), dict):
            quest_dict[category] = {}
    return quest_dict


def _activate_quest_stage(quest_data: dict[str, Any], stage_name: str) -> None:
    """Make one declarative quest stage the active top-level objective."""
    stage = quest_data.get("Stages", {}).get(stage_name, {})
    quest_data["Stage"] = stage_name
    for key in ("Type", "What", "Total", "Target Position", "Help Text"):
        if key in stage:
            quest_data[key] = deepcopy(stage[key])
        elif key == "Target Position":
            quest_data.pop(key, None)


def _complete_matching_side_quests(player, quest_type: str, predicate) -> str:
    """Advance active side quests of ``quest_type`` accepted by ``player``."""
    messages: list[str] = []
    for quest_name, quest_data in ensure_quest_categories(player)["Side"].items():
        if (
            isinstance(quest_data, dict)
            and quest_data.get("Type") == quest_type
            and not quest_data.get("Completed")
            and not quest_data.get("Turned In")
            and predicate(quest_data)
        ):
            messages.append(_advance_or_complete_quest(quest_name, quest_data))
    return "\n".join(messages) + ("\n" if messages else "")


def _advance_or_complete_quest(quest_name: str, quest_data: dict[str, Any]) -> str:
    """Advance a staged quest or return its final completion text."""
    stage = quest_data.get("Stages", {}).get(quest_data.get("Stage"), {})
    next_stage = stage.get("Next Stage") if isinstance(stage, dict) else None
    if isinstance(next_stage, str) and next_stage in quest_data.get("Stages", {}):
        _activate_quest_stage(quest_data, next_stage)
        progress_text = stage.get("Progress Text", "")
        if isinstance(progress_text, str) and progress_text.strip():
            return progress_text.rstrip()
        return ""
    quest_data["Completed"] = True
    completion_text = stage.get("Completion Text", "")
    if isinstance(completion_text, str) and completion_text.strip():
        return completion_text.rstrip()
    return f"You have completed the quest {quest_name}."


def record_location(player, position: tuple[int, int, int]) -> str:
    """Record arrival at a location for active data-driven locate quests."""
    normalized_position = tuple(position)

    def matches(quest_data: dict[str, Any]) -> bool:
        target = quest_data.get("Target Position")
        return isinstance(target, (list, tuple)) and tuple(target) == normalized_position

    message = _complete_matching_side_quests(player, "Locate", matches)
    ensure_story = getattr(player, "ensure_main_story_state", None)
    if callable(ensure_story):
        descent_text = opening_story.record_first_descent(ensure_story(), normalized_position)
        if descent_text:
            message += f"{descent_text}\n"
    return message


def record_conversation(player, npc_name: str) -> str:
    """Record a conversation for active data-driven town dialogue quests."""
    return _complete_matching_side_quests(
        player,
        "Talk",
        lambda quest_data: quest_data.get("What") == npc_name,
    )


def has_pending_conversation(player, npc_name: str) -> bool:
    """Return whether an active quest currently asks the player to speak to an NPC."""
    return any(
        isinstance(quest_data, dict)
        and quest_data.get("Type") == "Talk"
        and quest_data.get("What") == npc_name
        and not quest_data.get("Completed")
        and not quest_data.get("Turned In")
        for category in AUTHORED_QUEST_CATEGORIES
        for quest_data in ensure_quest_categories(player)[category].values()
    )


def record_defeat(player, enemy_name: str) -> str:
    """Record a defeated enemy against active side-quest objectives."""
    messages: list[str] = []
    for quest_name, quest_data in ensure_quest_categories(player)["Side"].items():
        if (
            not isinstance(quest_data, dict)
            or quest_data.get("Type") != "Defeat"
            or quest_data.get("What") != enemy_name
            or quest_data.get("Completed")
            or quest_data.get("Turned In")
        ):
            continue
        total = max(1, int(quest_data.get("Total", 1) or 1))
        defeated = min(total, int(quest_data.get("Killed", 0) or 0) + 1)
        quest_data["Killed"] = defeated
        if defeated >= total:
            message = _advance_or_complete_quest(quest_name, quest_data)
            if message:
                messages.append(message)
    return "\n".join(messages) + ("\n" if messages else "")


def record_collection(player, item) -> str:
    """Record an item obtained against active side-quest collection objectives."""
    messages: list[str] = []
    for quest_name, quest_data in ensure_quest_categories(player)["Side"].items():
        if not isinstance(quest_data, dict) or quest_data.get("Type", "Collect") != "Collect":
            continue
        if not _collection_target_matches(quest_data.get("What"), item):
            continue
        if quest_data.get("Completed") or quest_data.get("Turned In"):
            continue
        total = max(1, int(quest_data.get("Total", 1) or 1))
        prior_collected = int(quest_data.get("Collected", 0) or 0)
        collected = min(
            total,
            max(prior_collected + 1, _collection_inventory_count(player, quest_data.get("What"))),
        )
        quest_data["Collected"] = collected
        if collected >= total and prior_collected < total:
            message = _advance_or_complete_quest(quest_name, quest_data)
            if message:
                messages.append(message)
    return "\n".join(messages) + ("\n" if messages else "")


def sync_collection_progress(player) -> None:
    """Reconcile active collection quests with items already in inventory.

    This repairs progress from saves created before ordinary enemy loot notified
    the quest system, and prevents a display count from exceeding its target.
    """
    for category in AUTHORED_QUEST_CATEGORIES:
        for quest_data in ensure_quest_categories(player)[category].values():
            if (
                not isinstance(quest_data, dict)
                or quest_data.get("Type", "Collect") != "Collect"
                or quest_data.get("Completed")
                or quest_data.get("Turned In")
            ):
                continue
            total = max(1, int(quest_data.get("Total", 1) or 1))
            collected = min(total, _collection_inventory_count(player, quest_data.get("What")))
            quest_data["Collected"] = collected
            if collected >= total:
                _advance_or_complete_quest("", quest_data)


def _collection_target_matches(quest_what, item) -> bool:
    """Return whether one inventory item satisfies a collection target."""
    item_name = getattr(item, "name", None)
    item_class_name = type(item).__name__
    if isinstance(quest_what, str):
        return quest_what in {item_name, item_class_name}
    if callable(quest_what):
        return quest_what.__name__ == item_class_name
    return getattr(quest_what, "name", None) == item_name


def _collection_inventory_count(player, quest_what) -> int:
    """Count matching inventory stacks across regular and special inventory."""
    count = 0
    for inventory_name in ("inventory", "special_inventory"):
        inventory = getattr(player, inventory_name, {}) or {}
        for stack in inventory.values():
            for item in stack:
                if _collection_target_matches(quest_what, item):
                    count += 1
    return count


def relic_count(player) -> int:
    """Return how many of the six major relics the player currently carries."""
    inventory = getattr(player, "special_inventory", {}) or {}
    return sum(1 for relic_name in RELIC_NAMES if relic_name in inventory)


def has_all_relics(player) -> bool:
    """Return whether the player currently carries all six major relics."""
    if relic_count(player) == len(RELIC_NAMES):
        return True
    has_relics = getattr(player, "has_relics", None)
    if callable(has_relics):
        try:
            return bool(has_relics())
        except (AttributeError, TypeError, ValueError):
            return False
    return False


def _sergeant_main_template(quest_name: str) -> dict[str, Any] | None:
    from src.core.data.data_loader import get_quests

    sergeant_mains = get_quests().get("Sergeant", {}).get("Main", {})
    for quests_at_level in sergeant_mains.values():
        if quest_name in quests_at_level:
            return deepcopy(quests_at_level[quest_name])
    return None


def ensure_uncertain_reports_quest(player) -> dict[str, Any]:
    """Create or return the staged opening investigation quest."""
    main_quests = ensure_quest_categories(player)["Main"]
    quest = main_quests.get(UNCERTAIN_REPORTS)
    if not isinstance(quest, dict):
        quest = _copy_template_or_minimal(UNCERTAIN_REPORTS)
        main_quests[UNCERTAIN_REPORTS] = quest
    return quest


def can_offer_authored_quest(player, quest_name: str) -> bool:
    """Apply story-state prerequisites not expressible as a turned-in quest."""
    if quest_name != "Cry Havoc!":
        return True
    uncertain = ensure_quest_categories(player)["Main"].get(UNCERTAIN_REPORTS)
    if not isinstance(uncertain, dict) or uncertain.get("Turned In"):
        return False
    ensure_story = getattr(player, "ensure_main_story_state", None)
    story = ensure_story() if callable(ensure_story) else main_story.ensure_state(player)
    return bool(story.get("opening_ledger_seen"))


def relic_for_floor(floor: int):
    """Return the authored relic instance for floors one through six."""
    relic_types = (
        items.Relic1,
        items.Relic2,
        items.Relic3,
        items.Relic4,
        items.Relic5,
        items.Relic6,
    )
    if not 1 <= floor <= len(relic_types):
        return None
    return relic_types[floor - 1]()


def collect_relic(
    player, floor: int, *, triangulus_answer: str | None = None
) -> RelicCollectionResult:
    """Grant one relic, restore resources, and synchronize its story quest."""
    relic = relic_for_floor(floor)
    if relic is None:
        return RelicCollectionResult(False)
    inventory = getattr(player, "special_inventory", {}) or {}
    if relic.name in inventory:
        return RelicCollectionResult(False, relic=relic)

    ensure_story = getattr(player, "ensure_main_story_state", None)
    story = ensure_story() if callable(ensure_story) else main_story.ensure_state(player)
    threshold_revealed = False
    if floor == 1:
        if triangulus_answer not in opening_story.TRIANGULUS_IDENTITY_ANSWERS:
            return RelicCollectionResult(False, relic=relic)
        threshold_revealed = opening_story.record_triangulus_threshold(story)
        opening_story.record_triangulus_answer(story, triangulus_answer)

    player.modify_inventory(relic, rare=True, quest=True)
    player.health.current = player.health.max
    player.mana.current = player.mana.max
    quest_message = sync_relic_story_progress(player)
    return RelicCollectionResult(
        True,
        relic=relic,
        quest_message=quest_message,
        threshold_revealed=threshold_revealed,
    )


def _stage_help(quest_data: dict[str, Any]) -> str | None:
    stage = quest_data.get("Stage")
    stages = quest_data.get("Stages", {})
    if isinstance(stages, dict) and stage in stages:
        help_text = stages[stage].get("Help Text")
        if isinstance(help_text, str) and help_text.strip():
            return help_text
    return None


def _holy_relics_help(count: int) -> str:
    if count <= 0:
        return (
            "The first relic report proved there may be related sealed chambers. "
            "Recover each relic you find and bring proof back to the Sergeant."
        )
    if count < len(RELIC_NAMES):
        return (
            f"Recovered {count}/{len(RELIC_NAMES)} relics. The Sergeant is comparing their markings "
            "against old patrol reports while you search the remaining sealed chambers."
        )
    return (
        "All six relics have been recovered. Return to the Sergeant before pressing toward "
        "the final threshold."
    )


def _copy_template_or_minimal(quest_name: str) -> dict[str, Any]:
    template = _sergeant_main_template(quest_name)
    if template is not None:
        return template
    if quest_name == UNCERTAIN_REPORTS:
        return {
            "Who": "Sergeant",
            "Type": "Story",
            "What": "First Relic Report",
            "Total": 1,
            "Stage": "investigate",
            "Stages": {},
            "Start Text": "",
            "End Text": "",
            "Help Text": "",
            "Reward": [],
            "Reward Number": 1,
            "Experience": 0,
            "Completed": False,
            "Turned In": False,
        }
    return {
        "Who": "Sergeant",
        "Type": "Collect",
        "What": "Relics",
        "Total": len(RELIC_NAMES),
        "Stage": "collecting",
        "Stages": {},
        "Start Text": "",
        "End Text": "",
        "Help Text": _holy_relics_help(0),
        "Reward": [],
        "Reward Number": 1,
        "Experience": 0,
        "Completed": False,
        "Turned In": False,
    }


def update_staged_help_text(quest_data: dict[str, Any]) -> None:
    """Copy the current staged objective help into the standard Help Text slot."""
    help_text = _stage_help(quest_data)
    if help_text:
        quest_data["Help Text"] = help_text


def ensure_holy_relics_quest(
    player, *, completed: bool | None = None, turned_in: bool = False
) -> dict[str, Any]:
    """Ensure the staged Holy Relics quest exists in the player's main log."""
    quest_dict = ensure_quest_categories(player)
    main_quests = quest_dict["Main"]
    quest_data = main_quests.get(HOLY_RELICS)
    if not isinstance(quest_data, dict):
        quest_data = _copy_template_or_minimal(HOLY_RELICS)
        main_quests[HOLY_RELICS] = quest_data

    quest_data.setdefault("Stage", "collecting")
    quest_data.setdefault("Total", len(RELIC_NAMES))
    quest_data["Help Text"] = _holy_relics_help(relic_count(player))

    if completed is None:
        completed = has_all_relics(player)
    quest_data["Completed"] = bool(completed)
    if turned_in:
        quest_data["Turned In"] = True
        quest_data["Completed"] = True
    else:
        quest_data.setdefault("Turned In", False)
    return quest_data


def sync_relic_story_progress(player) -> str:
    """Synchronize staged relic quest state and return any completion message."""
    quest_dict = ensure_quest_categories(player)
    main_quests = quest_dict["Main"]
    count = relic_count(player)
    message = ""

    uncertain = main_quests.get(UNCERTAIN_REPORTS)
    if isinstance(uncertain, dict):
        update_staged_help_text(uncertain)
        if count >= 1 and not uncertain.get("Turned In"):
            uncertain["Stage"] = "report_first_relic"
            update_staged_help_text(uncertain)
            if not uncertain.get("Completed"):
                uncertain["Completed"] = True
                message += f"You have completed the quest {UNCERTAIN_REPORTS}.\n"

    holy = main_quests.get(HOLY_RELICS)
    if isinstance(holy, dict):
        was_completed = bool(holy.get("Completed"))
        ensure_holy_relics_quest(
            player, completed=has_all_relics(player), turned_in=bool(holy.get("Turned In"))
        )
        if has_all_relics(player) and not was_completed:
            message += f"You have completed the quest {HOLY_RELICS}!\n"

    return message


def handle_quest_turn_in(player, quest_name: str) -> None:
    """Apply story quest side effects after a quest is turned in."""
    if quest_name == UNCERTAIN_REPORTS:
        ensure_holy_relics_quest(player)


def migrate_relic_story_quests(player) -> None:
    """Replace old immediate Holy Relics quest state with the staged chain."""
    quest_dict = ensure_quest_categories(player)
    main_quests = quest_dict["Main"]
    progression_quests = quest_dict["Progression"]
    legacy_butcher = main_quests.pop("The Butcher", None)
    if isinstance(legacy_butcher, dict) and "The Butcher" not in progression_quests:
        progression_quests["The Butcher"] = legacy_butcher
    holy = main_quests.get(HOLY_RELICS)
    if isinstance(holy, dict) and "Stage" not in holy:
        old_turned_in = bool(holy.get("Turned In"))
        old_completed = bool(holy.get("Completed"))
        main_quests.pop(HOLY_RELICS, None)
        count = relic_count(player)
        if old_turned_in:
            ensure_holy_relics_quest(player, completed=True, turned_in=True)
        elif count <= 0:
            uncertain = _copy_template_or_minimal(UNCERTAIN_REPORTS)
            uncertain["Completed"] = old_completed
            main_quests[UNCERTAIN_REPORTS] = uncertain
            sync_relic_story_progress(player)
        else:
            ensure_holy_relics_quest(player, completed=count == len(RELIC_NAMES))
        return

    sync_relic_story_progress(player)
