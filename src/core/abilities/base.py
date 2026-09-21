"""Shared ability types and YAML-backed ability construction."""

from __future__ import annotations

from textwrap import wrap
from typing import TYPE_CHECKING

from src.paths import CORE_DATA_DIR

from ..combat.combat_result import CombatResult
from ..combat.targeting import TargetLossPolicy, TargetScope
from ..identity import ABILITY_TYPES

if TYPE_CHECKING:
    from typing import Any

    from ..character import Character


# ── YAML ability loader helper ──────────────────────────────────────────
_YAML_DIR = CORE_DATA_DIR / "abilities"


def _load_yaml_ability(filename: str, cls_name: str | None = None) -> Ability:
    """Load a combat-ready ability from a YAML file.

    If *cls_name* is provided it is stored on the returned instance as
    ``_class_name`` so the save-system serialiser can round-trip the
    original Python class name.
    """
    from ..data.ability_loader import AbilityFactory

    ability = AbilityFactory.create_from_yaml(_YAML_DIR / filename, combat_ready=True)
    if cls_name:
        ability._class_name = cls_name
        ability.aliases = tuple(dict.fromkeys((*getattr(ability, "aliases", ()), cls_name)))
    return ability


class Ability:
    """
    Base class for all abilities

    Attributes:
        name: name of the ability
        description: description of the ability that explains what it does in so many words
        cost: amount of mana required to cast spell; default is 0
        combat: boolean indicating whether the ability can only be cast in combat
        passive: boolean indicating whether the ability is passively active
        typ: the type of the ability
        subtyp: the subtype of the ability
        dmg_mod: damage modifier for the ability
        result: the result of the ability
    -----------------------------------------------------------
    Methods:
        __init__: initializes the ability with the given attributes
        __str__: returns a string representation of the ability
        special_effect: applies a special effect to the ability
    """

    ability_type_id: str

    def __init_subclass__(cls, *, ability_id: str | None = None, **kwargs: object) -> None:
        """Register runtime ability types for strict persistence."""
        super().__init_subclass__(**kwargs)
        cls.ability_type_id = ABILITY_TYPES.register(cls, ability_id)

    def __init__(
        self,
        name: str,
        description: str,
        cost: int = 0,
        combat: bool = True,
        passive: bool = False,
        typ: str = "",
        subtyp: str = "",
        dmg_mod: float = 1.0,
        target_scope: TargetScope = TargetScope.SINGLE_ENEMY,
        target_loss_policy: TargetLossPolicy = TargetLossPolicy.RETARGET_FOCUS,
    ) -> None:
        """
        Args:
            name (str): name of the ability
            description (str): description of the ability that explains what it does in so many words
            cost (int): amount of mana required to cast spell; default is 0
            combat (bool): boolean indicating whether the ability can only be cast in combat
            passive (bool): boolean indicating whether the ability is passively active
            typ (str): the type of the ability
            subtyp (str): the subtype of the ability
            dmg_mod (float): damage modifier for the ability
            result (CombatResult): the result of the ability
        """
        self.name = name
        self.description = description
        self.cost = cost
        self.combat = combat
        self.passive = passive
        self.typ = typ
        self.subtyp = subtyp
        self.dmg_mod = dmg_mod
        self.target_scope = target_scope
        self.target_loss_policy = target_loss_policy
        self._ability_id: str | None = None
        self.result = CombatResult(
            action=name, extra={"cost": cost, "type": self.typ, "subtype": self.subtyp}
        )

    @property
    def ability_id(self) -> str | None:
        """Return the immutable YAML slug when this ability is data-backed."""
        return getattr(self, "_ability_id", None)

    @ability_id.setter
    def ability_id(self, value: str) -> None:
        """Set a data-backed slug once, permitting idempotent loader reuse."""
        if not value:
            raise ValueError("ability_id must not be empty")
        existing = getattr(self, "_ability_id", None)
        if existing is not None and existing != value:
            raise AttributeError("ability_id is immutable")
        self._ability_id = value

    def _ensure_result(self) -> None:
        """
        Ensure self.result exists (for backward compatibility with old save files).
        Creates a new CombatResult if the attribute is missing.
        """
        if not hasattr(self, "result"):
            self.result = CombatResult(
                action=self.name,
                extra={"cost": self.cost, "type": self.typ, "subtype": self.subtyp},
            )

    def is_available(self, user: Character, target: Character | None = None) -> bool:
        """Return whether current combat state permits selecting the ability."""
        del user, target
        return True

    def _reset_result(
        self,
        *,
        actor: Character | None = None,
        target: Character | None = None,
    ) -> CombatResult:
        """
        Reset the reusable result object to per-cast defaults.

        Many ability instances are reused across turns (enemy spellbooks),
        so this clears transient fields (messages, effects, extra context)
        to prevent cross-cast leakage.
        """
        self._ensure_result()
        result = self.result
        result.action = self.name
        result.actor = actor
        result.target = target
        result.hit = None
        result.crit = None
        result.dodge = None
        result.block = None
        result.block_amount = None
        result.damage = 0
        result.healing = 0
        result.effects_applied = {
            "Status": [],
            "Physical": [],
            "Stat": [],
            "Magic": [],
            "Class": [],
        }
        result.extra = {"cost": self.cost, "type": self.typ, "subtype": self.subtyp}
        result.message = ""
        result.actor_id = None
        result.target_id = None
        return result

    def __str__(self) -> str:
        """
        Returns:
            str: string representation of the ability

        Example:
            >>> ability = Ability("Fireball", "A powerful fire spell.")
            >>> print(ability)
            ================================
            Fireball
            A powerful fire spell.
            -----------------------------------
            Type: Spell
            Sub-Type: Offensive
            Mana Cost: 10
            ===================================
        """
        wrapped_description = wrap(self.description, 35, break_on_hyphens=False)
        description_text = "\n".join(wrapped_description)
        str_text = (
            f"{'=' * ((35 - len(self.name)) // 2)}{self.name}{'=' * ((36 - len(self.name)) // 2)}\n"
            f"{description_text}\n"
            f"{35*'-'}\n"
            f"Type: {self.typ}\n"
            f"Sub-Type: {self.subtyp}\n"
        )
        if not self.passive:
            str_text += f"Mana Cost: {self.cost}\n"
        else:
            str_text += "Passive\n"
        str_text += "==================================="
        return str_text

    def special_effect(self, *args: Any, **kwargs: Any) -> CombatResult:
        """
        Applies a special effect to the ability.
        Args:
            *args: variable length argument list
            **kwargs: variable length keyword argument list
        Returns:
            CombatResult: the result of the special effect
        Raises:
            NotImplementedError: if the special effect is not implemented
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement special_effect method."
        )


class Skill(Ability):
    """
    Child class of Ability that handles skills

    Attributes:
        name: name of the ability
        description: description of the ability that explains what it does in so many words
        cost: amount of mana required to cast spell; default is 0
        combat: boolean indicating whether the ability can only be cast in combat
        passive: boolean indicating whether the ability is passively active
        typ: the type of these abilities is 'Skill'
        subtyp: the subtype of the ability; the options are:
            'Offensive', 'Defensive', 'Stealth', 'Enhance', 'Drain', 'Class', 'Truth',
            'Martial Arts', 'Luck', or 'PowerUp'
        dmg_mod: damage modifier for the ability
        result: the result of the ability
        weapon: boolean indicating whether the ability is a weapon skill
    ------------------------------------------------------------
    Methods:
        __init__: initializes the ability with the given attributes
        __str__: returns a string representation of the ability
        special_effect: applies a special effect to the ability
        use: applies the skill to the target
    ------------------------------------------------------------
    Example:
        >>> skill = Skill("Double Strike", "Perform two melee attacks at normal damage.")
        >>> print(skill)
        ================================
        Double Strike
        Perform two melee attacks at normal damage.
        -----------------------------------
        Type: Skill
        Sub-Type: Offensive
        Mana Cost: 10
        ===================================
    """

    def __init__(self, name: str, description: str, weapon: bool = False) -> None:
        """
        Args:
            name (str): name of the ability
            description (str): description of the ability that explains what it does in so many words
            weapon (bool): boolean indicating whether the ability is a weapon skill
        """
        super().__init__(name, description)
        self.typ = "Skill"
        self.weapon = weapon

    def use(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> CombatResult:
        """
        Applies the skill to the target.
        Ensures self.result exists and sets up basic properties.
        Subclasses should call super().use(user, target, **kwargs) first,
        then add their specific logic.

        Args:
            user: The character using the skill
            target: The target of the skill (optional)
            **kwargs: Additional keyword arguments
        Returns:
            CombatResult: the result of the skill
        """
        return self._reset_result(actor=user, target=target)


class CallContract(Skill):
    """Demonologist class skill for bargaining with the active fiend patron."""

    def __init__(self) -> None:
        super().__init__(
            name="Call Contract",
            description="Call on the active fiend patron and bargain for aid.",
        )
        self.subtyp = "Class"
        self.cost = 0

    def use(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        from ..classes import demonologist

        super().use(user, target, **kwargs)
        intent = kwargs.get("intent") or getattr(self, "pending_intent", None) or "Harm"
        if hasattr(self, "pending_intent"):
            self.pending_intent = None
        return demonologist.resolve_contract(user, target, intent)


class Redeem(Skill):
    """Vow of Redemption skill that attempts a mercy victory."""

    def __init__(self) -> None:
        super().__init__(
            name="Redeem",
            description="Attempt a mercy victory against a wounded non-boss foe.",
        )
        self.subtyp = "Class"
        self.cost = 0

    def use(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        from ..classes import paladin

        super().use(user, target, **kwargs)
        if target is None:
            return "There is no foe to redeem.\n"
        return paladin.attempt_redeem(user, target, rng=kwargs.get("rng"))


class Challenge(Skill):
    """Vow of Conquest skill that names a challenged foe."""

    def __init__(self) -> None:
        super().__init__(
            name="Challenge",
            description="Mark the current enemy as your Challenged Foe for 3 turns.",
        )
        self.subtyp = "Class"
        self.cost = 0

    def use(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        from ..classes import paladin

        super().use(user, target, **kwargs)
        if target is None:
            return "There is no foe to challenge.\n"
        return paladin.start_challenge(user, target)


class Interpose(Skill):
    """Vow of Protection skill that prepares a guarded block."""

    def __init__(self) -> None:
        super().__init__(
            name="Interpose",
            description="Enter a guarded stance for 2 turns and strengthen the next block.",
        )
        self.subtyp = "Class"
        self.cost = 0

    def use(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        from ..classes import paladin

        super().use(user, target, **kwargs)
        return paladin.start_interpose(user)


class JudgmentRiposte(Skill):
    """Vow of Retribution skill that prepares a retaliatory strike."""

    def __init__(self) -> None:
        super().__init__(
            name="Judgment Riposte",
            description="Prepare a Holy counterattack against the next enemy attack.",
        )
        self.subtyp = "Class"
        self.cost = 0

    def use(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> str:
        from ..classes import paladin

        super().use(user, target, **kwargs)
        return paladin.start_riposte(user)


class Spell(Ability):
    """
    Child class of Ability that handles spell casting

    Attributes:
        name: name of the ability
        description: description of the ability that explains what it does in so many words
        cost: amount of mana required to cast spell; default is 0
        combat: boolean indicating whether the ability can only be cast in combat
        passive: boolean indicating whether the ability is passively active
        typ: the type of the abilities is 'Spell'
        subtyp: the subtype of the ability; the options are:
            'Fire', 'Ice', 'Lightning', 'Earth', 'Water', 'Wind', 'Holy', 'Shadow', 'Poison',
            'Heal', 'Death', 'Support', 'Status', 'Movement', 'Illusion', or 'Non-elemental'
        dmg_mod: damage modifier for the ability
        result: the result of the ability
        school: the school of magic to which this spell belongs
    ------------------------------------------------------------
    Methods:
        __init__: initializes the ability with the given attributes
        __str__: returns a string representation of the ability
        special_effect: applies a special effect to the ability
        cast: applies the spell to the target
    ------------------------------------------------------------
    Example:
        >>> spell = Spell("Fireball", "A powerful fire spell.")
        >>> print(spell)
        ================================
        Fireball
        A powerful fire spell.
        -----------------------------------
        Type: Spell
        Sub-Type: Fire
        Mana Cost: 10
        ===================================
    """

    def __init__(
        self,
        name: str,
        description: str,
        school: str | None = None,
    ) -> None:
        """
        Args:
            name (str): name of the ability
            description (str): description of the ability that explains what it does in so many words
            school (str | None): the school of magic to which this spell belongs
        """
        super().__init__(name, description)
        self.typ: str = "Spell"
        self.school = school

    def cast(
        self,
        user: Character,
        target: Character | None = None,
        **kwargs: Any,
    ) -> CombatResult:
        """
        Applies the spell to the target.
        Ensures self.result exists and sets up basic properties.
        Subclasses should call super().cast(user, target, **kwargs) first,
        then add their specific logic.

        Args:
            user: The character casting the spell
            target: The target of the spell (optional)
            **kwargs: Additional keyword arguments
        Returns:
            CombatResult: the result of the spell
        """
        return self._reset_result(actor=user, target=target)


"""
Skill section
"""


def _skill_subtype(cls_name: str, subtyp: str, description: str) -> type:
    """Generate a Skill subclass whose only distinction is *subtyp*."""

    def _init(self, name: str = "", description: str = "", **kwargs: Any) -> None:
        Skill.__init__(self, name, description, **kwargs)
        self.subtyp = subtyp

    return type(
        cls_name,
        (Skill,),
        {
            "__init__": _init,
            "__doc__": description,
        },
    )


Offensive = _skill_subtype(
    "Offensive", "Offensive", "Skill subtype for offensive skills that work to damage the enemy."
)
Defensive = _skill_subtype(
    "Defensive", "Defensive", "Skill subtype for defensive skills that work to protect the user."
)
Stealth = _skill_subtype(
    "Stealth",
    "Stealth",
    "Skill subtype for stealth skills that use subterfuge to surprise the enemy.",
)
Enhance = _skill_subtype(
    "Enhance",
    "Enhance",
    "Skill subtype for enhance skills that enhance the user's abilities or equipment.",
)
Drain = _skill_subtype(
    "Drain", "Drain", "Skill subtype for drain skills that drain the enemy's health or mana."
)
Class = _skill_subtype("Class", "Class", "Skill subtype for class-specific skills.")
Truth = _skill_subtype(
    "Truth", "Truth", "Skill subtype for truth skills that reveal secrets or hidden truths."
)
MartialArts = _skill_subtype(
    "MartialArts",
    "Martial Arts",
    "Skill subtype for martial arts skills specific to hand-to-hand combat.",
)
Luck = _skill_subtype("Luck", "Luck", "Skill subtype for luck-based skills.")
PowerUp = _skill_subtype(
    "PowerUp", "Power Up", "Skill subtype for power-up skills obtained through training."
)
