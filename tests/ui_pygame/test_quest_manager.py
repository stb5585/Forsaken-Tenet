#!/usr/bin/env python3
"""Focused coverage for pygame quest-manager helpers and flows."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from src.core import items as core_items
from src.core import quest_progress
from src.core.data.data_loader import get_quests
from src.ui_pygame.gui import quest_manager
from tests.test_framework import TestGameState


class BarghestBossRoom:
    defeated = True
    enemy = None


class DummyItem:
    def __init__(
        self,
        name="Reward Blade",
        *,
        typ="Weapon",
        subtyp="Sword",
        value=100,
        description="Reward item description.",
        damage=3,
        armor=0,
        magic=0,
        magic_defense=0,
    ):
        self.name = name
        self.typ = typ
        self.subtyp = subtyp
        self.value = value
        self.description = description
        self.damage = damage
        self.armor = armor
        self.magic = magic
        self.magic_defense = magic_defense


class EmptyVial:
    def __init__(self):
        self.name = "Empty Vial"


class ShieldReward(DummyItem):
    def __init__(self):
        super().__init__("Shield Reward", typ="OffHand", subtyp="Shield")


class FakePopup:
    messages = []
    responses = []
    show_kwargs = []

    def __init__(self, _presenter, message, show_buttons=True):
        self.message = message
        self.show_buttons = show_buttons
        FakePopup.messages.append((message, show_buttons))

    def show(self, **kwargs):
        FakePopup.show_kwargs.append(kwargs)
        if FakePopup.responses:
            return FakePopup.responses.pop(0)
        return None


class FakeRewardSelectionPopup:
    responses = []
    show_kwargs = []

    def __init__(self, _presenter, _title, items, detail_provider):
        self.items = items
        self.detail_provider = detail_provider

    def show(self, **kwargs):
        FakeRewardSelectionPopup.show_kwargs.append(kwargs)
        return FakeRewardSelectionPopup.responses.pop(0)


class FakeLevelUpScreen:
    calls = []

    def __init__(self, _screen, _presenter):
        pass

    def show_level_up(self, player_char, _arg):
        FakeLevelUpScreen.calls.append(player_char.level.exp)
        player_char.level.exp_to_gain = 1


def _make_presenter():
    return SimpleNamespace(screen=object())


def _make_player(level=12):
    inventory_calls = []

    def modify_inventory(item, num=1, subtract=False, rare=False):
        inventory_calls.append((item.name, num, subtract, rare))

    player = SimpleNamespace(
        gold=0,
        level=SimpleNamespace(level=level, pro_level=2, exp=0, exp_to_gain=0),
        quest_dict={"Main": {}, "Side": {}},
        inventory={},
        special_inventory={},
        spellbook={"Spells": {}},
        kill_dict={},
        warp_point=False,
        modify_inventory=modify_inventory,
        player_level=lambda: level,
        max_level=lambda: False,
        has_relics=lambda: False,
    )
    player.inventory_calls = inventory_calls
    return player


def _manager(player=None, **kwargs):
    return quest_manager.QuestManager(_make_presenter(), player or _make_player(), **kwargs)


def _content_quest(giver: str, category: str, quest_name: str) -> dict:
    for quest_by_level in get_quests()[giver][category].values():
        if quest_name in quest_by_level:
            quest_data = deepcopy(quest_by_level[quest_name])
            quest_data["Completed"] = True
            quest_data["Turned In"] = False
            return quest_data
    raise AssertionError(f"Missing quest fixture: {giver} {category} {quest_name}")


def test_sergeant_starts_with_uncertain_reports_not_holy_relics():
    player = _make_player(level=1)
    rendered = []
    manager = _manager(
        player,
        quest_text_renderer=lambda text: rendered.append(text),
        quest_choice_renderer=lambda _prompt, _options: 0,
    )

    acted, showed = manager.check_and_offer("Sergeant")

    assert (acted, showed) == (True, True)
    assert quest_progress.UNCERTAIN_REPORTS in player.quest_dict["Main"]
    assert quest_progress.HOLY_RELICS not in player.quest_dict["Main"]
    offered_text = "\n".join(rendered)
    assert "six relics" not in offered_text.lower()
    assert "vesperion" not in offered_text.lower()
    assert "voluntas" not in offered_text.lower()


def test_first_relic_report_turn_in_creates_holy_relics(monkeypatch):
    player = _make_player(level=20)
    player.quest_dict["Main"][quest_progress.UNCERTAIN_REPORTS] = _content_quest(
        "Sergeant", "Main", quest_progress.UNCERTAIN_REPORTS
    )
    player.quest_dict["Main"][quest_progress.UNCERTAIN_REPORTS]["Completed"] = False
    player.special_inventory["Triangulus"] = [core_items.Relic1()]
    rendered = []
    manager = _manager(player, quest_text_renderer=lambda text: rendered.append(text))
    scenes = []
    scene_kwargs = []

    class FakeStoryScene:
        def __init__(self, _presenter, title, **kwargs):
            self.title = title
            self.kwargs = kwargs
            scene_kwargs.append(kwargs)

        def show_dialogue(self, beats):
            scenes.append(tuple(beats))

    FakeLevelUpScreen.calls = []
    monkeypatch.setattr(quest_manager, "LevelUpScreen", FakeLevelUpScreen)
    monkeypatch.setattr(quest_manager, "StorySceneScreen", FakeStoryScene)

    acted, showed = manager.check_and_offer("Sergeant")

    assert (acted, showed) == (True, True)
    assert player.quest_dict["Main"][quest_progress.UNCERTAIN_REPORTS]["Turned In"] is True
    holy = player.quest_dict["Main"][quest_progress.HOLY_RELICS]
    assert holy["Completed"] is False
    assert holy["Stage"] == "collecting"
    assert "Recovered 1/6 relics" in holy["Help Text"]
    assert [beat.speaker for beat in scenes[0][:5]] == [
        "Caedmon",
        "Edrin",
        "Caedmon",
        "Edrin",
        "Caedmon",
    ]
    assert scenes[0][5].speaker == "Narrator"
    assert "ledgers" in scenes[0][5].text
    assert scene_kwargs[0]["background_image"] == "town.png"
    assert "background_draw_func" not in scene_kwargs[0]
    assert all("Quest Complete: Uncertain Reports" not in message for message in rendered)


def test_formatting_and_chalice_hint_helpers(monkeypatch):
    player = _make_player()
    player.quest_dict["Side"]["The Holy Grail of Quests"] = {
        "Completed": False,
        "Turned In": False,
        "Help Text": "",
    }
    rendered = []
    manager = _manager(
        player, quest_text_renderer=lambda text: rendered.append(text), wrap_width=12
    )

    assert manager._format_for_renderer("alpha beta gamma") == "alpha beta\ngamma"
    preserved = _manager(player, renderer_preserve_formatting=True)
    assert preserved._format_for_renderer("a\nb") == "a\nb"

    progress = manager._ensure_chalice_progress(
        player.quest_dict["Side"]["The Holy Grail of Quests"]
    )
    assert progress["Hooded"] is False
    assert progress["Spawned"] is False

    assert manager._handle_chalice_giver_hint("Hooded Figure") is True
    assert progress["Hooded"] is True
    assert "ugly sword" in rendered[-1]

    player.special_inventory["Chalice Map"] = [DummyItem("Chalice Map", typ="Misc", subtyp="Key")]
    assert manager._handle_chalice_giver_hint("Sergeant") is True
    assert progress["Sergeant"] is True
    assert "third" in rendered[-1]
    assert "floor" in rendered[-1]


def test_show_hint_eligible_quests_and_random_help(monkeypatch):
    player = _make_player(level=10)
    player.quest_dict = {
        "Main": {"Quest A": {"Help Text": "Find the key.", "Turned In": False}},
        "Side": {"Quest B": {"Help Text": "Visit the ruins.", "Turned In": False}},
    }
    rendered = []
    manager = _manager(
        player, quest_text_renderer=lambda text: rendered.append(text), wrap_width=15
    )

    monkeypatch.setattr(
        quest_manager,
        "quest_dict",
        {
            "Guide": {
                "Main": {"5": [{"Quest A": {"Type": "Talk"}}][0]},
                "Side": {"10": [{"Quest B": {"Type": "Collect"}}][0]},
            }
        },
    )
    monkeypatch.setattr(
        quest_manager, "get_reactive_town_hints", lambda _player, _giver: ["Secret grail hint"]
    )
    monkeypatch.setattr(quest_manager.random, "choice", lambda seq: seq[0])

    mains, sides = manager._eligible_quests("Guide")
    assert list(mains[0].keys()) == ["Quest A"]
    assert list(sides[0].keys()) == ["Quest B"]
    assert manager.get_random_help_hint("Guide") == "Find the key."

    monkeypatch.setattr(quest_manager, "ConfirmationPopup", FakePopup)
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    manager_no_renderer = _manager(player, wrap_width=10)
    manager_no_renderer._show_hint("This is a popup hint")
    assert "This is a" in FakePopup.messages[-1][0]
    assert FakePopup.show_kwargs[-1] == {
        "flush_events": True,
        "require_key_release": True,
    }


def test_random_help_hint_uses_reactive_town_hints_when_no_quest_help(monkeypatch):
    player = _make_player(level=10)
    player.quest_dict = {"Main": {}, "Side": {}}
    manager = _manager(player)

    monkeypatch.setattr(
        quest_manager,
        "quest_dict",
        {"Guide": {"Main": {}, "Side": {}}},
    )
    monkeypatch.setattr(
        quest_manager, "get_reactive_town_hints", lambda _player, _giver: ["Reactive warning"]
    )
    monkeypatch.setattr(quest_manager.random, "choice", lambda seq: seq[0])

    assert manager.get_random_help_hint("Guide") == "Reactive warning"


def test_random_help_hint_exposes_postgame_tavern_dialogue(monkeypatch):
    player = _make_player(level=10)
    player.main_story = {"main_story_complete": True}
    manager = _manager(player)

    monkeypatch.setattr(quest_manager.random, "choice", lambda seq: seq[0])

    hint = manager.get_random_help_hint("Barkeep")

    assert hint is not None
    assert "ordinary days" in hint


def test_can_offer_and_already_killed_helpers():
    player = _make_player()
    player.quest_dict["Main"]["Earlier"] = {"Turned In": True}
    player.quest_dict["Side"]["Blocked"] = {"Turned In": False}
    player.kill_dict = {"Boss": {"Dragon": 1}}
    player.world_dict = {(0, 0, 1): BarghestBossRoom()}
    manager = _manager(player)

    assert manager._can_offer_quest("Any", {}, "Main") is True
    assert manager._can_offer_quest("Later", {"Requires": "Earlier"}, "Main") is True
    assert manager._can_offer_quest("Later", {"Requires": "Blocked"}, "Main") is False
    assert manager._can_offer_quest("Later", {"Requires": "Missing"}, "Main") is False
    assert manager._already_killed("Dragon") is True
    assert manager._already_killed("Barghest") is True
    assert manager._already_killed("Slime") is False


def test_barghest_briefing_remembers_deferral_and_recognizes_an_early_kill(monkeypatch):
    manager = _manager(_make_player(level=20))
    player = manager.player_char
    quest = get_quests()["Sergeant"]["Main"]["20"]["Cry Havoc!"]
    beats = []
    prompts = []
    choices = iter([1, 0])

    class Briefing:
        def __init__(self, _presenter, _title, **kwargs):
            assert kwargs["background_image"] == "barracks.jpg"

        def show_dialogue(self, lines):
            beats.extend(lines)

        def choose(self, prompt, _options, **kwargs):
            assert kwargs["speaker"] == "Caedmon"
            prompts.append(prompt)
            return next(choices)

    monkeypatch.setattr(quest_manager, "StorySceneScreen", Briefing)
    assert manager._offer("Sergeant", "Cry Havoc!", quest, "Main") is False
    assert "Cry Havoc!" not in player.quest_dict["Main"]
    assert player.main_story["barghest_briefing_seen"] is True
    assert [beat.speaker for beat in beats].count("Edrin") == 1

    beats.clear()
    player.world_dict = {(18, 2, 1): BarghestBossRoom()}
    assert manager._offer("Sergeant", "Cry Havoc!", quest, "Main") is True
    assert not beats
    assert "Barghest" in prompts[0]
    assert "give me your account" in prompts[1]
    accepted = player.quest_dict["Main"]["Cry Havoc!"]
    assert accepted["Completed"] and not accepted["Turned In"]
    assert accepted["Reward"] == [core_items.PowerRing]


def test_check_and_offer_autocompletes_defeated_boss_room_without_kill_entry(monkeypatch):
    player = _make_player(level=12)
    player.world_dict = {(5, 5, 1): BarghestBossRoom()}
    player.quest_dict["Main"]["Cry Havoc!"] = {
        "Type": "Defeat",
        "What": "Barghest",
        "Completed": False,
        "Turned In": False,
    }
    manager = _manager(player)

    monkeypatch.setattr(
        manager,
        "_eligible_quests",
        lambda giver: ([{"Cry Havoc!": {"Type": "Defeat", "What": "Barghest"}}], []),
    )
    turnins = []
    monkeypatch.setattr(manager, "_turn_in", lambda name, typ: turnins.append((name, typ)))

    acted, showed = manager.check_and_offer("Sergeant")

    assert (acted, showed) == (True, True)
    assert player.quest_dict["Main"]["Cry Havoc!"]["Completed"] is True
    assert turnins == [("Cry Havoc!", "Main")]


def test_offer_accept_covers_kill_check_relics_naivete_and_decline(monkeypatch):
    player = _make_player()
    player.kill_dict = {"Boss": {"Goblin King": 1}}
    player.has_relics = lambda: True
    rendered = []
    choices = iter([0, 0, 0, 1])
    manager = _manager(
        player,
        quest_text_renderer=lambda text: rendered.append(text),
        quest_choice_renderer=lambda _prompt, _options: next(choices),
    )

    monkeypatch.setattr(quest_manager, "RESPONSE_MAP", {"Guide": ["Accepted!", "Declined!"]})
    monkeypatch.setattr(quest_manager.items, "EmptyVial", EmptyVial, raising=False)

    assert (
        manager._offer("Guide", "Defeat Quest", {"Type": "Defeat", "What": "Goblin King"}, "Main")
        is True
    )
    assert player.quest_dict["Main"]["Defeat Quest"]["Completed"] is True

    assert (
        manager._offer("Guide", "The Holy Relics", {"Type": "Collect", "What": "Relics"}, "Main")
        is True
    )
    assert player.quest_dict["Main"]["The Holy Relics"]["Completed"] is True

    assert manager._offer("Guide", "Naivete", {"Type": "Collect", "What": "Vial"}, "Side") is True
    assert ("Empty Vial", 1, False, True) in player.inventory_calls
    assert manager._offer("Guide", "Declined Quest", {"Type": "Talk"}, "Side") is False
    assert any("Accepted!" in text for text in rendered)
    assert any("Declined!" in text for text in rendered)


def test_turn_in_handles_gold_collect_cleanup_and_levelup(monkeypatch):
    player = _make_player()
    player.level.exp_to_gain = -5
    player.quest_dict["Main"]["Collect Quest"] = {
        "End Text": "You did it.",
        "Experience": 5,
        "Reward": ["Gold"],
        "Reward Number": 30,
        "Type": "Collect",
        "What": "QuestGem",
        "Total": 2,
        "Completed": True,
        "Turned In": False,
    }
    player.inventory["QuestGem"] = [
        DummyItem("QuestGem", typ="Misc", subtyp="Gem"),
        DummyItem("QuestGem", typ="Misc", subtyp="Gem"),
    ]
    rendered = []
    manager = _manager(player, quest_text_renderer=lambda text: rendered.append(text))

    FakeLevelUpScreen.calls = []
    monkeypatch.setattr(quest_manager, "LevelUpScreen", FakeLevelUpScreen)

    events = []
    monkeypatch.setattr(
        manager, "_handle_quest_events", lambda quest_name: events.append(quest_name)
    )

    manager._turn_in("Collect Quest", "Main")

    assert player.gold == 30
    assert player.level.exp == 5
    assert FakeLevelUpScreen.calls == []
    assert "QuestGem" not in player.inventory
    assert player.quest_dict["Main"]["Collect Quest"]["Turned In"] is True
    assert events == ["Collect Quest"]
    assert any("Quest turned in: Collect Quest" in text for text in rendered)


def test_power_core_turn_in_grants_terminal_class_power(monkeypatch):
    player = TestGameState.create_player(class_name="Master Monk", level=60)
    player.quest_dict["Side"]["This Thing's Nuclear"] = _content_quest(
        "Griswold",
        "Side",
        "This Thing's Nuclear",
    )
    player.special_inventory["Power Core"] = [core_items.PowerCore()]
    rendered = []
    manager = _manager(player, quest_text_renderer=rendered.append)
    monkeypatch.setattr(quest_manager, "LevelUpScreen", FakeLevelUpScreen)
    monkeypatch.setattr(
        "src.core.data.data_loader.get_special_events",
        lambda: {"Power Up": {"Text": ["The Power Core awakens your hidden art."]}},
    )

    manager._turn_in("This Thing's Nuclear", "Side")

    assert player.quest_dict["Side"]["This Thing's Nuclear"]["Turned In"] is True
    assert "Dim Mak" in player.spellbook["Skills"]
    assert player.power_up is True
    assert "Power Core" not in player.special_inventory
    assert any("Reward: Dim Mak" in message for message in rendered)
    assert any("Power Core awakens" in message for message in rendered)


def test_power_core_turn_in_waits_for_second_promotion():
    player = _make_player(level=60)
    player.quest_dict["Side"]["This Thing's Nuclear"] = {
        "Reward": ["Power Up"],
        "Completed": True,
        "Turned In": False,
    }
    rendered = []
    manager = _manager(player, quest_text_renderer=rendered.append)

    manager._turn_in("This Thing's Nuclear", "Side")

    assert player.quest_dict["Side"]["This Thing's Nuclear"]["Turned In"] is False
    assert any("second promotion" in message for message in rendered)


def test_turn_in_handles_reward_selection_and_bad_dream_event(monkeypatch):
    player = _make_player()
    player.quest_dict["Side"]["A Bad Dream"] = {
        "End Text": "Nightmare solved.",
        "Experience": 0,
        "Reward": [DummyItem, ShieldReward],
        "Reward Number": 1,
        "Type": "Talk",
        "Completed": True,
        "Turned In": False,
    }
    player.quest_dict["Side"]["Where's the Beef?"] = {"Turned In": False}
    player.special_inventory["Lucky Locket"] = [DummyItem("Lucky Locket", typ="Misc", subtyp="Key")]

    FakeRewardSelectionPopup.responses = [None, 1]
    FakeRewardSelectionPopup.show_kwargs = []
    monkeypatch.setattr(quest_manager, "RewardSelectionPopup", FakeRewardSelectionPopup)
    monkeypatch.setattr(quest_manager, "LevelUpScreen", FakeLevelUpScreen)
    monkeypatch.setattr(
        "src.core.data.data_loader.get_special_events",
        lambda: {"Busboy": {"Text": ["Busboy event line 1", "Busboy event line 2"]}},
    )
    rendered = []
    manager = _manager(player, quest_text_renderer=lambda text: rendered.append(text))

    manager._turn_in("A Bad Dream", "Side")

    assert any(call[0] == "Shield Reward" for call in player.inventory_calls)
    assert ("Lucky Locket", 1, True, True) in player.inventory_calls
    assert all(kwargs["flush_events"] is True for kwargs in FakeRewardSelectionPopup.show_kwargs)
    assert all(
        kwargs["require_key_release"] is True for kwargs in FakeRewardSelectionPopup.show_kwargs
    )
    beef = player.quest_dict["Side"]["Where's the Beef?"]
    assert beef["Who"] == "Busboy"
    assert "help feed a lot of people" in beef["End Text"]
    assert any("Busboy event line 1" in text for text in rendered)


def test_content_old_key_rewards_turn_in_through_pygame_manager(monkeypatch):
    player = _make_player()
    player.quest_dict["Progression"] = {
        "The Butcher": _content_quest("Barkeep", "Progression", "The Butcher")
    }
    player.quest_dict["Main"]["A Bad Dream"] = _content_quest("Waitress", "Main", "A Bad Dream")
    rendered = []
    manager = _manager(player, quest_text_renderer=lambda text: rendered.append(text))
    monkeypatch.setattr(quest_manager, "LevelUpScreen", FakeLevelUpScreen)
    monkeypatch.setattr(manager, "_handle_quest_events", lambda _quest_name: None)

    manager._turn_in("The Butcher", "Progression")
    manager._turn_in("A Bad Dream", "Main")

    assert [call[0] for call in player.inventory_calls].count("Old Key") == 5
    assert any("Reward: Old Key x2" in text for text in rendered)
    assert any("Reward: Old Key x3" in text for text in rendered)
    assert player.quest_dict["Progression"]["The Butcher"]["Turned In"] is True
    assert player.quest_dict["Main"]["A Bad Dream"]["Turned In"] is True


def test_bring_him_home_turn_in_shows_timmy_home_event(monkeypatch):
    player = _make_player(level=5)
    player.quest_dict["Side"]["Bring Him Home"] = _content_quest(
        "Sergeant", "Side", "Bring Him Home"
    )
    rendered = []
    manager = _manager(player, quest_text_renderer=lambda text: rendered.append(text))
    monkeypatch.setattr(quest_manager, "LevelUpScreen", FakeLevelUpScreen)
    scenes = []

    class FakeStoryScene:
        def __init__(self, _presenter, title, **kwargs):
            self.title = title
            self.kwargs = kwargs
            self.beats = ()
            scenes.append(self)

        def show_dialogue(self, beats):
            assert player.inventory_calls == []
            assert player.quest_dict["Side"]["Bring Him Home"]["Turned In"] is False
            self.beats = tuple(beats)

    monkeypatch.setattr(quest_manager, "StorySceneScreen", FakeStoryScene)

    manager._turn_in("Bring Him Home", "Side")

    assert player.quest_dict["Side"]["Bring Him Home"]["Turned In"] is True
    assert any("Quest turned in: Bring Him Home" in text for text in rendered)
    assert len(scenes) == 1
    assert scenes[0].title == "Silvana — Timmy Comes Home"
    assert scenes[0].kwargs["background_image"] == "town.png"
    assert scenes[0].kwargs["participants"] == (
        "Timmy's Mother",
        "Timmy's Father",
        "Timmy",
        "Caedmon",
    )
    assert [beat.speaker for beat in scenes[0].beats] == [
        "Narrator",
        "Timmy's Mother",
        "Narrator",
        "Timmy",
        "Timmy's Father",
        "Timmy's Mother",
        "Caedmon",
    ]
    assert "family back together" in scenes[0].beats[-1].text


def test_rookie_mistake_arrival_scenes_precede_rewards_and_consume_body(monkeypatch):
    player = _make_player(level=12)
    player.name = "Mara"
    player.quest_dict["Side"]["Rookie Mistake"] = _content_quest(
        "Sergeant", "Side", "Rookie Mistake"
    )
    player.special_inventory["Dead Soldier"] = [core_items.DeadSoldier()]
    original_modify_inventory = player.modify_inventory

    def modify_inventory(item, num=1, subtract=False, rare=False):
        original_modify_inventory(item, num=num, subtract=subtract, rare=rare)
        if subtract and rare and item.name == "Dead Soldier":
            del player.special_inventory[item.name]

    player.modify_inventory = modify_inventory
    rendered = []
    manager = _manager(player, quest_text_renderer=rendered.append)
    scenes = []

    class FakeStoryScene:
        def __init__(self, _presenter, title, **kwargs):
            self.title = title
            self.kwargs = kwargs
            self.beats = ()
            self.show_kwargs = {}
            scenes.append(self)

        def show_dialogue(self, beats, **kwargs):
            assert player.quest_dict["Side"]["Rookie Mistake"]["Turned In"] is False
            assert all(call[0] != "Mana Potion" for call in player.inventory_calls)
            self.beats = tuple(beats)
            self.show_kwargs = kwargs

    monkeypatch.setattr(quest_manager, "LevelUpScreen", FakeLevelUpScreen)
    monkeypatch.setattr(quest_manager, "StorySceneScreen", FakeStoryScene)

    assert manager.turn_in_completed_quest("Rookie Mistake", "Side", show_end_text=False) is True

    assert [scene.title for scene in scenes] == [
        "Silvana Courtyard — A Rookie Returns",
        "Silvana Graveyard — The Last Watch",
    ]
    assert scenes[0].kwargs["background_image"] == "town.png"
    assert scenes[1].kwargs["background_image"] == "graveyard.jpg"
    assert scenes[1].kwargs["participants"] == ("Priest", "Caedmon")
    hero_beats = [
        beat
        for scene in scenes
        for beat in scene.beats
        if beat.portrait_name == quest_manager.PLAYER_PORTRAIT_KEY
    ]
    assert [beat.speaker for beat in hero_beats] == ["Mara", "Mara"]
    assert "Dead Soldier" not in player.special_inventory
    assert player.quest_dict["Side"]["Rookie Mistake"]["Turned In"] is True
    assert sum(call[0] == "Mana Potion" for call in player.inventory_calls) == 4
    assert all("This death belongs in my ledger" not in message for message in rendered)


def test_check_and_offer_covers_turnin_offer_help_and_noquest(monkeypatch):
    player = _make_player(level=12)
    player.quest_dict["Main"]["Done Quest"] = {"Completed": True, "Turned In": False}
    player.quest_dict["Main"]["Help Quest"] = {"Help Text": "Need help here.", "Turned In": False}
    manager = _manager(player)

    monkeypatch.setattr(
        manager,
        "_eligible_quests",
        lambda giver: ([{"Done Quest": {"Type": "Talk"}}, {"New Quest": {"Type": "Talk"}}], []),
    )

    turnins = []
    offers = []
    monkeypatch.setattr(manager, "_turn_in", lambda name, typ: turnins.append((name, typ)))
    monkeypatch.setattr(
        manager, "_offer", lambda giver, name, q, typ: offers.append((giver, name, typ)) or False
    )
    monkeypatch.setattr(manager, "_handle_chalice_giver_hint", lambda giver: False)
    monkeypatch.setattr(quest_manager, "get_reactive_town_hints", lambda _player, _giver: [])
    monkeypatch.setattr(quest_manager.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(quest_manager, "ConfirmationPopup", FakePopup)
    FakePopup.messages = []

    acted, showed = manager.check_and_offer("Guide")
    assert (acted, showed) == (True, True)
    assert turnins == [("Done Quest", "Main")]

    player.quest_dict["Main"]["Done Quest"]["Turned In"] = True
    monkeypatch.setattr(
        manager,
        "_eligible_quests",
        lambda giver: (
            [
                {"Done Quest": {"Type": "Talk"}},
                {"Help Quest": {"Type": "Talk"}},
                {"New Quest": {"Type": "Talk"}},
            ],
            [],
        ),
    )
    acted, showed = manager.check_and_offer("Guide")
    assert (acted, showed) == (False, True)
    assert offers == [("Guide", "New Quest", "Main")]
    assert "Need help here." in FakePopup.messages[-1][0]

    player.quest_dict["Main"]["Help Quest"]["Turned In"] = True
    monkeypatch.setattr(manager, "_eligible_quests", lambda giver: ([], []))
    FakePopup.messages = []
    acted, showed = manager.check_and_offer("Guide", show_help=False)
    assert (acted, showed) == (False, True)
    assert "no new quests" in FakePopup.messages[-1][0].lower()


def test_quest_status_summary_counts_completion_and_turnin_state():
    player = _make_player()
    player.quest_dict = {
        "Main": {
            "Ready": {"Completed": True, "Turned In": False},
            "Done": {"Completed": True, "Turned In": True},
            "Active": {"Completed": False, "Turned In": False},
        },
        "Side": {
            "Legacy Missing Completed": {"Turned In": False},
            "Malformed": "not-a-dict",
        },
        "Bounty": {},
    }
    manager = _manager(player)

    assert manager.get_quest_status_summary() == {
        "categories": {
            "Main": {
                "quests": 3,
                "completed": 2,
                "turned_in": 1,
                "ready_to_turn_in": 1,
                "active": 2,
            },
            "Side": {
                "quests": 1,
                "completed": 0,
                "turned_in": 0,
                "ready_to_turn_in": 0,
                "active": 1,
            },
            "Bounty": {
                "quests": 0,
                "completed": 0,
                "turned_in": 0,
                "ready_to_turn_in": 0,
                "active": 0,
            },
        },
        "totals": {
            "quests": 4,
            "completed": 2,
            "turned_in": 1,
            "ready_to_turn_in": 1,
            "active": 3,
        },
    }


def test_turn_in_popup_reward_variants_and_collect_cleanup(monkeypatch):
    player = _make_player()
    player.max_level = lambda: True
    player.quest_dict["Side"]["Warp Trial"] = {
        "End Text": "Warp unlocked.",
        "Experience": 2,
        "Reward": ["Warp Point"],
        "Reward Number": 1,
        "Type": "Collect",
        "What": DummyItem,
        "Total": 1,
        "Completed": True,
        "Turned In": False,
    }
    player.inventory["Reward Blade"] = [DummyItem()]
    player.special_inventory["Reward Blade"] = [DummyItem()]
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    monkeypatch.setattr(quest_manager, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(quest_manager, "LevelUpScreen", FakeLevelUpScreen)

    manager = _manager(player)
    manager._handle_quest_events = lambda _name: None
    manager._turn_in("Warp Trial", "Side")

    assert player.warp_point is True
    assert "Reward Blade" not in player.special_inventory
    assert "Reward Blade" in player.inventory
    assert any("Warp Point access" in message for message, _buttons in FakePopup.messages)
    assert all(kwargs["flush_events"] is True for kwargs in FakePopup.show_kwargs)
    assert all(kwargs["require_key_release"] is True for kwargs in FakePopup.show_kwargs)

    player.quest_dict["Side"]["Gold Trial"] = {
        "End Text": "",
        "Experience": 0,
        "Reward": ["Gold"],
        "Reward Number": 25,
        "Type": "Talk",
        "Completed": True,
        "Turned In": False,
    }
    manager._turn_in("Gold Trial", "Side")
    assert player.gold == 25


def test_offer_without_renderer_and_check_and_offer_side_branches(monkeypatch):
    player = _make_player(level=20)
    FakePopup.messages = []
    FakePopup.responses = [None, True, None, False]
    FakePopup.show_kwargs = []
    monkeypatch.setattr(quest_manager, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        quest_manager, "RESPONSE_MAP", {"Priest": ["Blessings.", "Come back later."]}
    )

    manager = _manager(player)
    accepted = manager._offer(
        "Priest", "Popup Quest", {"Start Text": "A popup intro.", "Type": "Talk"}, "Main"
    )
    declined = manager._offer(
        "Priest", "Declined Popup Quest", {"Start Text": "Second intro.", "Type": "Talk"}, "Main"
    )

    assert accepted is True
    assert declined is False
    assert all(kwargs["flush_events"] is True for kwargs in FakePopup.show_kwargs)
    assert all(kwargs["require_key_release"] is True for kwargs in FakePopup.show_kwargs)
    assert "Popup Quest" in player.quest_dict["Main"]
    assert any("Blessings." in message for message, _buttons in FakePopup.messages)
    assert any("Come back later." in message for message, _buttons in FakePopup.messages)

    player.quest_dict["Main"] = {"Relic Quest": {"Completed": False, "Turned In": False}}
    player.has_relics = lambda: True
    monkeypatch.setattr(
        manager,
        "_eligible_quests",
        lambda giver: (
            [{"Relic Quest": {"Type": "Collect", "What": "Relics"}}],
            [{"Pandora's Box": {"Type": "Talk"}}],
        ),
    )
    turnins = []
    monkeypatch.setattr(manager, "_turn_in", lambda name, typ: turnins.append((name, typ)))
    monkeypatch.setattr(
        manager,
        "_offer",
        lambda giver, name, q, typ: (_ for _ in ()).throw(AssertionError("should not offer")),
    )
    monkeypatch.setattr(manager, "_handle_chalice_giver_hint", lambda giver: True)
    acted, showed = manager.check_and_offer("Priest", show_help=False)
    assert (acted, showed) == (True, True)
    assert player.quest_dict["Main"]["Relic Quest"]["Completed"] is True
    assert turnins == [("Relic Quest", "Main")]

    monkeypatch.setattr(manager, "_eligible_quests", lambda giver: ([], []))
    monkeypatch.setattr(manager, "_handle_chalice_giver_hint", lambda giver: False)
    FakePopup.messages = []
    acted, showed = manager.check_and_offer("Priest", suppress_no_quests_message=True)
    assert (acted, showed) == (False, False)


def test_handle_quest_events_popup_fallback(monkeypatch):
    player = _make_player()
    player.quest_dict["Side"]["Where's the Beef?"] = {"Turned In": False}
    FakePopup.messages = []
    FakePopup.show_kwargs = []
    monkeypatch.setattr(quest_manager, "ConfirmationPopup", FakePopup)
    monkeypatch.setattr(
        "src.core.data.data_loader.get_special_events",
        lambda: {"Busboy": {"Text": ["Busboy popup line"]}},
    )

    manager = _manager(player)
    manager._handle_quest_events("A Bad Dream")

    assert any("Busboy popup line" in message for message, _buttons in FakePopup.messages)
    assert all(kwargs["flush_events"] is True for kwargs in FakePopup.show_kwargs)
    assert all(kwargs["require_key_release"] is True for kwargs in FakePopup.show_kwargs)
    assert player.quest_dict["Side"]["Where's the Beef?"]["Who"] == "Busboy"


def test_wizards_folly_turn_in_shows_nimue_followup_with_renderer(monkeypatch):
    player = _make_player()
    rendered = []
    monkeypatch.setattr(
        "src.core.data.data_loader.get_special_events",
        lambda: {"Nimue After Merzhin": {"Text": ["The water settles.", "Nimue remembers."]}},
    )

    manager = _manager(
        player, quest_text_renderer=lambda text: rendered.append(text), wrap_width=18
    )
    manager._handle_quest_events("The Wizard's Folly")

    assert rendered
    assert "The water settles." in rendered[-1]
    assert "Nimue remembers." in rendered[-1]
