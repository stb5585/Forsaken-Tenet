"""Constants behavior for the combat manager package."""

from src.paths import PYGAME_ASSETS_DIR

_DISPLAY_TO_ENGINE = {
    "Spells": "Cast Spell",
    "Skills": "Use Skill",
    "Resolve": "Use Skill",
    "Bursts": "Use Skill",
    "Hold the Line": "Defend",
    "Defensive Release": "Defend",
    "Items": "Use Item",
}

SLOT_SYMBOL_ATLAS = PYGAME_ASSETS_DIR / "ui" / "slot_machine_symbols.png"
SLOT_CARD_RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
SLOT_CARD_SUITS = ("S", "H", "D", "C")
SLOT_CARD_DECK = [f"{rank}{suit}" for suit in SLOT_CARD_SUITS for rank in SLOT_CARD_RANKS]
SLOT_CARD_ORDER = {card: index for index, card in enumerate(SLOT_CARD_DECK)}
SLOT_CARD_VALUES = {
    "A": 14,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
}
VESPERION_FALSE_FINAL_HP_RATIO = 0.70
VESPERION_FALSE_FINAL_ENEMY_TURNS = 3
# Hold the opening combat frame briefly so encounters have a readable handoff.
COMBAT_START_TRANSITION_FRAMES = 12
# Keep automatic turns legible without making rapid enemies feel sluggish.
ENEMY_PRE_ACTION_HOLD_FRAMES = 6
ENEMY_RESULT_HOLD_FRAMES = 10
POST_TURN_DELAY_FRAMES = 1
DEFEAT_PAUSE_MS = 250
FLEE_PAUSE_MS = 200
