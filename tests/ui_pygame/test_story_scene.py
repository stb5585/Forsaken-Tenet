"""Focused coverage for authored storyline scene presentation."""

from types import SimpleNamespace

import pygame

from src.ui_pygame.gui import story_scene


def _presenter(width=900, height=700):
    pygame.font.init()
    return SimpleNamespace(
        screen=pygame.Surface((width, height)),
        width=width,
        height=height,
        title_font=pygame.font.Font(None, 34),
        large_font=pygame.font.Font(None, 30),
        normal_font=pygame.font.Font(None, 24),
        small_font=pygame.font.Font(None, 18),
        clock=SimpleNamespace(tick=lambda _fps: None),
        debug_mode=False,
        story_dialogue_cps=35,
    )


def test_choice_popup_wraps_responses_into_non_overlapping_hitboxes():
    popup = story_scene.StoryChoicePopup(
        _presenter(),
        "What remains yours when every inherited title falls silent?",
        [
            "A deliberately long response that must wrap without colliding with the next choice.",
            "A shorter response.",
        ],
    )

    rects = popup.option_rects()

    assert len(popup.option_lines[0]) > 1
    assert rects[0].bottom < rects[1].top
    assert rects[0].height > rects[1].height


def test_required_choice_ignores_escape(monkeypatch):
    monkeypatch.setattr(story_scene, "prepare_guarded_input", lambda **_kwargs: True)
    monkeypatch.setattr(story_scene, "release_guard_allows_input", lambda _required, armed: armed)
    monkeypatch.setattr(
        story_scene,
        "update_input_armed_from_event",
        lambda _event, _required, armed: armed,
    )
    events = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)],
        ]
    )
    monkeypatch.setattr(story_scene, "get_events", lambda: next(events))
    monkeypatch.setattr(story_scene.StoryChoicePopup, "draw", lambda _self: None)
    popup = story_scene.StoryChoicePopup(
        _presenter(),
        "Required choice",
        ["Continue"],
        allow_cancel=False,
    )

    assert popup.show() == 0


def test_story_dialogue_wraps_full_words_before_revealing(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    scene = story_scene.StorySceneScreen(_presenter(), "Stable wrapping")
    beat = story_scene.StoryBeat("Narrator", "Alpha beta gamma")

    wrapped = scene._wrapped_beat_text(beat, 90)

    assert wrapped == "Alpha beta\ngamma"
    assert wrapped[:12].splitlines() == ["Alpha beta", "g"]


def test_dialogue_fade_flushes_input_before_slow_print(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    prepare_calls = []
    monkeypatch.setattr(
        story_scene,
        "prepare_guarded_input",
        lambda **kwargs: prepare_calls.append(kwargs) or True,
    )
    monkeypatch.setattr(story_scene, "release_guard_allows_input", lambda _required, armed: armed)
    monkeypatch.setattr(
        story_scene,
        "update_input_armed_from_event",
        lambda _event, _required, armed: armed,
    )
    monkeypatch.setattr(
        story_scene,
        "get_events",
        lambda: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)],
    )
    presenter = _presenter()
    presenter.debug_mode = True
    scene = story_scene.StorySceneScreen(presenter, "Fade")
    fades = []
    scene._fade_in_dialogue = lambda beat, duration: fades.append((beat, duration))
    scene.draw_frame = lambda *_args, **_kwargs: None
    beat = story_scene.StoryBeat("Narrator", "The room comes into view.")

    scene.show_dialogue((beat,), fade_in_ms=900)

    assert fades == [(beat, 900)]
    assert prepare_calls == [
        {"flush_events": True, "require_key_release": True},
        {"flush_events": True, "require_key_release": True},
    ]


def test_story_scene_choice_keeps_context_and_uses_popup(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    calls = []

    class FakeChoicePopup:
        def __init__(self, presenter, prompt, options, **kwargs):
            calls.append((presenter, prompt, options, kwargs))

        def show(self, **kwargs):
            calls.append(kwargs)
            return 1

    monkeypatch.setattr(story_scene, "StoryChoicePopup", FakeChoicePopup)
    player = SimpleNamespace(
        name="Ada",
        race="Elf",
        sex="Female",
        cls="Mage",
        portrait_variant=2,
    )
    scene = story_scene.StorySceneScreen(
        _presenter(),
        "A Story Scene",
        participants=("Caedmon", "Edrin"),
        player_char=player,
    )
    drawn = []
    scene.draw_frame = lambda beat, **kwargs: drawn.append((beat, kwargs))
    selected_dialogue = []
    scene.show_dialogue = lambda beats: selected_dialogue.extend(beats)

    choice = scene.choose("What do you say?", ["First", "Second"], speaker="You")

    assert choice == 1
    assert drawn[0][0] == story_scene.StoryBeat("You", "What do you say?", None)
    assert calls[-1] == {"flush_events": True, "require_key_release": True}
    assert selected_dialogue == [
        story_scene.StoryBeat("Ada", "Second", story_scene.PLAYER_PORTRAIT_KEY)
    ]


def test_selected_response_uses_matching_player_dialogue_art(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    portrait = pygame.Surface((225, 400), pygame.SRCALPHA)
    requests = []

    class RecordingDialogueArtManager:
        def get_portrait(self, race, sex, *, variant):
            requests.append((race, sex, variant))
            return portrait

    player = SimpleNamespace(
        name="Ada",
        race=SimpleNamespace(name="Elf"),
        sex="Female",
        cls=SimpleNamespace(name="Mage"),
        portrait_variant=2,
    )
    scene = story_scene.StorySceneScreen(
        _presenter(),
        "A Story Scene",
        player_char=player,
        player_dialogue_art_manager=RecordingDialogueArtManager(),
    )

    result = scene._player_portrait_surface()

    assert result is portrait
    assert requests == [(player.race, "Female", 2)]


def test_player_uses_same_three_character_rotation_as_npcs(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    portrait = pygame.Surface((512, 768), pygame.SRCALPHA)
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "npc_portrait_surface",
        lambda _self, **_kwargs: portrait,
    )

    class DialogueArtManager:
        def get_portrait(self, _race, _sex, *, variant):
            assert variant == 4
            return portrait

    player = SimpleNamespace(
        name="Hero",
        race="Human",
        sex="Male",
        portrait_variant=4,
    )
    scene = story_scene.StorySceneScreen(
        _presenter(),
        "Player Stage",
        participants=("Edrin", "Caedmon", "Joffrey"),
        participant_anchors={"Caedmon": "Edrin"},
        player_char=player,
        player_dialogue_art_manager=DialogueArtManager(),
    )

    assert len(scene._staged_portraits) == 3
    assert all(
        staged.portrait_name != story_scene.PLAYER_PORTRAIT_KEY
        for staged in scene._staged_portraits.values()
    )

    hero_beat = story_scene.StoryBeat(
        "Hero",
        "People are missing. If I can help, I should.",
        story_scene.PLAYER_PORTRAIT_KEY,
    )
    scene._stage_for_beat(
        hero_beat,
        (
            story_scene.StoryBeat("Edrin", "I saw it move.", "Edrin"),
            story_scene.StoryBeat("Joffrey", "The route is marked.", "Joffrey"),
        ),
    )

    assert len(scene._staged_portraits) == 3
    assert scene._staged_portraits["right"] == story_scene.StagedPortrait(
        "Hero", story_scene.PLAYER_PORTRAIT_KEY, "right"
    )

    scene._stage_for_beat(
        story_scene.StoryBeat("Liora", "Keep the door clear.", "Liora"),
        (
            story_scene.StoryBeat("Edrin", "I saw it move.", "Edrin"),
            story_scene.StoryBeat("Joffrey", "The route is marked.", "Joffrey"),
        ),
    )

    assert len(scene._staged_portraits) == 3
    assert scene._staged_portraits["right"] == story_scene.StagedPortrait(
        "Liora", "Liora", "right"
    )
    assert {staged.speaker for staged in scene._staged_portraits.values()} == {
        "Liora",
        "Edrin",
        "Joffrey",
    }


def test_portraits_are_mirrored_when_native_facing_points_outward(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    portrait = pygame.Surface((128, 256), pygame.SRCALPHA)

    class DialogueArtManager:
        def get_portrait(self, _race, _sex, *, variant):
            assert variant == 4
            return portrait

        def should_mirror(self, _race, _sex, *, variant, stage_side):
            assert variant == 4
            return stage_side == "right"

    player = SimpleNamespace(
        name="Hero",
        race="Human",
        sex="Male",
        portrait_variant=4,
    )
    scene = story_scene.StorySceneScreen(
        _presenter(),
        "Player Facing",
        player_char=player,
        player_dialogue_art_manager=DialogueArtManager(),
    )
    flip_calls = []
    original_flip = pygame.transform.flip

    def recording_flip(surface, flip_x, flip_y):
        flip_calls.append((flip_x, flip_y))
        return original_flip(surface, flip_x, flip_y)

    monkeypatch.setattr(pygame.transform, "flip", recording_flip)
    npc_manager = SimpleNamespace(
        should_mirror=lambda npc_name, *, stage_side: (
            npc_name == "Caedmon" and stage_side == "left"
        )
    )
    monkeypatch.setattr(story_scene, "get_npc_art_manager", lambda: npc_manager)

    scene._draw_staged_portrait(
        story_scene.StagedPortrait("Hero", story_scene.PLAYER_PORTRAIT_KEY, "right"),
        pygame.Rect(500, 100, 300, 600),
        active_speaker="Hero",
    )
    monkeypatch.setattr(
        scene,
        "npc_portrait_surface",
        lambda **_kwargs: portrait,
    )
    scene._draw_staged_portrait(
        story_scene.StagedPortrait("Caedmon", "Caedmon", "left"),
        pygame.Rect(50, 100, 300, 600),
        active_speaker="Caedmon",
    )

    assert flip_calls == [(True, False), (True, False)]


def test_listener_portrait_is_darker_without_becoming_translucent(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    portrait = pygame.Surface((128, 256), pygame.SRCALPHA)
    portrait.fill((220, 180, 140, 255))
    scene = story_scene.StorySceneScreen(_presenter(), "Opaque listeners")
    monkeypatch.setattr(scene, "npc_portrait_surface", lambda **_kwargs: portrait)
    monkeypatch.setattr(scene, "_portrait_should_mirror", lambda _staged: False)
    rect = pygame.Rect(50, 50, 256, 512)

    scene._draw_staged_portrait(
        story_scene.StagedPortrait("Liora", "Liora", "left"),
        rect,
        active_speaker="Oren",
    )

    pixel = scene.screen.get_at(rect.center)
    assert pixel.a == 255
    assert pixel.r < 220
    assert pixel.g < 180
    assert pixel.b < 140


def test_story_scene_picture_panel_has_no_cast_name_strip(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    scene = story_scene.StorySceneScreen(
        _presenter(),
        "Crowded Tavern",
        participants=("Oren", "Liora", "Joffrey", "Pell", "Tavin"),
    )

    rendered_text = []

    class RecordingFont:
        def __init__(self, original):
            self.original = original

        def render(self, text, antialias, color):
            rendered_text.append(text)
            return self.original.render(text, antialias, color)

        def size(self, text):
            return self.original.size(text)

        def get_height(self):
            return self.original.get_height()

    scene.normal_font = RecordingFont(scene.normal_font)
    scene.draw_frame(story_scene.StoryBeat("Oren", "The tavern is listening."), do_flip=False)

    assert "Oren" in rendered_text
    assert not {"Liora", "Joffrey", "Pell", "Tavin"}.intersection(rendered_text)


def test_story_scene_narrator_leaves_portrait_blank(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    scene = story_scene.StorySceneScreen(_presenter(), "Narration")
    portrait_names = []
    scene.npc_portrait_surface = lambda *, npc_name=None, **_kwargs: portrait_names.append(npc_name)

    scene.draw_frame(story_scene.StoryBeat("Narrator", "Rain strikes the glass."), do_flip=False)

    assert portrait_names == []


def test_story_scene_stages_three_portraits_and_replaces_only_one(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    portrait = pygame.Surface((512, 768), pygame.SRCALPHA)
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_portrait_surface",
        lambda _self, _portrait_name: portrait,
    )
    scene = story_scene.StorySceneScreen(
        _presenter(),
        "Stable Cast",
        participants=("Edrin", "Caedmon", "Joffrey", "Liora"),
        participant_anchors={"Joffrey": "Edrin", "Liora": "Edrin"},
    )

    assert {
        slot: staged.speaker for slot, staged in scene._staged_portraits.items()
    } == {"left": "Edrin", "right": "Caedmon", "left_support": "Joffrey"}

    scene._stage_for_beat(
        story_scene.StoryBeat("Liora", "Hold still."),
        (
            story_scene.StoryBeat("Edrin", "I am trying."),
            story_scene.StoryBeat("Caedmon", "Give her room."),
        ),
    )

    assert {
        slot: staged.speaker for slot, staged in scene._staged_portraits.items()
    } == {"left": "Edrin", "right": "Caedmon", "left_support": "Liora"}


def test_narration_does_not_change_portrait_staging(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    portrait = pygame.Surface((512, 768), pygame.SRCALPHA)
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_portrait_surface",
        lambda _self, _portrait_name: portrait,
    )
    scene = story_scene.StorySceneScreen(
        _presenter(),
        "Narrated Exchange",
        participants=("Oren", "Caedmon"),
    )
    before = dict(scene._staged_portraits)

    scene._stage_for_beat(story_scene.StoryBeat("Narrator", "The room falls quiet."))

    assert scene._staged_portraits == before


def test_story_frame_renders_only_current_beat_but_history_keeps_prior_lines(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    scene = story_scene.StorySceneScreen(_presenter(), "One Beat")
    prior = story_scene.StoryBeat("Edrin", "The route changed.", portrait_name="")
    current = story_scene.StoryBeat("Caedmon", "Then we verify it.", portrait_name="")
    rendered_text = []

    class RecordingFont:
        def __init__(self, original):
            self.original = original

        def render(self, text, antialias, color):
            rendered_text.append(text)
            return self.original.render(text, antialias, color)

        def size(self, text):
            return self.original.size(text)

        def get_height(self):
            return self.original.get_height()

    scene.normal_font = RecordingFont(scene.normal_font)
    scene.draw_frame(current, transcript=[prior, current], do_flip=False)

    assert "Caedmon" in rendered_text
    assert "Then we verify it." in rendered_text
    assert "Edrin" not in rendered_text
    assert "The route changed." not in rendered_text
    history = scene._history_render_lines([prior, current], 700)
    assert ("Edrin", scene.colors.GOLD) in history
    assert ("The route changed.", scene.colors.LIGHT_GRAY) in history


def test_story_layout_fits_supported_landscape_resolutions(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    for width, height in ((900, 700), (1920, 1080), (1080, 1920)):
        scene = story_scene.StorySceneScreen(_presenter(width, height), "Responsive Scene")
        title_rect, dialogue_rect, portrait_rects = scene._layout()
        viewport = pygame.Rect(0, 0, width, height)

        assert viewport.contains(title_rect)
        assert viewport.contains(dialogue_rect)
        assert all(viewport.contains(rect) for rect in portrait_rects.values())
        assert portrait_rects["left"].left < portrait_rects["right"].left
        assert dialogue_rect.width >= int(width * 0.9)


def test_history_toggle_does_not_advance_dialogue(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    monkeypatch.setattr(story_scene, "prepare_guarded_input", lambda **_kwargs: True)
    monkeypatch.setattr(story_scene, "release_guard_allows_input", lambda _required, armed: armed)
    monkeypatch.setattr(
        story_scene,
        "update_input_armed_from_event",
        lambda _event, _required, armed: armed,
    )
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
    events = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h)],
            [click],
        ]
    )
    monkeypatch.setattr(story_scene, "get_events", lambda: next(events))
    presenter = _presenter()
    presenter.story_dialogue_cps = 0
    scene = story_scene.StorySceneScreen(presenter, "History")
    history_states = []
    scene.draw_frame = lambda *_args, **_kwargs: history_states.append(scene._history_open)

    scene.show_dialogue((story_scene.StoryBeat("Oren", "Listen first."),))

    assert history_states == [False, True, False]


def test_first_click_completes_slow_print_and_second_advances(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    monkeypatch.setattr(story_scene, "prepare_guarded_input", lambda **_kwargs: True)
    monkeypatch.setattr(story_scene, "release_guard_allows_input", lambda _required, armed: armed)
    monkeypatch.setattr(
        story_scene,
        "update_input_armed_from_event",
        lambda _event, _required, armed: armed,
    )
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
    events = iter([[click, click], [click]])
    monkeypatch.setattr(story_scene, "get_events", lambda: next(events))
    monkeypatch.setattr(story_scene.pygame.time, "get_ticks", lambda: 0)
    scene = story_scene.StorySceneScreen(_presenter(), "Protected Dialogue")
    draws = []
    scene.draw_frame = lambda _beat, **kwargs: draws.append(
        {**kwargs, "transcript": list(kwargs["transcript"])}
    )
    beat = story_scene.StoryBeat("Caedmon", "This line should reveal slowly.")

    scene.show_dialogue((beat,))

    assert [draw["visible_characters"] for draw in draws] == [0, len(beat.text)]
    assert draws[-1]["transcript"] == [beat]


def test_each_speaker_appends_to_the_same_transcript(monkeypatch):
    monkeypatch.setattr(
        story_scene.StorySceneScreen,
        "_load_background",
        lambda self: setattr(self, "background", None),
    )
    monkeypatch.setattr(story_scene, "prepare_guarded_input", lambda **_kwargs: True)
    monkeypatch.setattr(story_scene, "release_guard_allows_input", lambda _required, armed: armed)
    monkeypatch.setattr(
        story_scene,
        "update_input_armed_from_event",
        lambda _event, _required, armed: armed,
    )
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
    monkeypatch.setattr(story_scene, "get_events", lambda: [click])
    presenter = _presenter()
    presenter.story_dialogue_cps = 0
    scene = story_scene.StorySceneScreen(presenter, "Shared Transcript")
    draws = []
    scene.draw_frame = lambda _beat, **kwargs: draws.append(
        {**kwargs, "transcript": list(kwargs["transcript"])}
    )
    beats = (
        story_scene.StoryBeat("Edrin", "The route changed."),
        story_scene.StoryBeat("Joffrey", "Then we correct the map."),
    )

    scene.show_dialogue(beats)

    assert [len(draw["transcript"]) for draw in draws] == [1, 2]
    assert draws[-1]["transcript"] == list(beats)
