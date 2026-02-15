"""SQLModel-based Character models.

This module contains the Character model and related schemas for character sheets.
"""

import math
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import computed_field
from sqlmodel import Field, SQLModel

# D&D 5e XP thresholds for each level
XP_THRESHOLDS: list[tuple[int, int]] = [
    (355000, 20),
    (305000, 19),
    (265000, 18),
    (225000, 17),
    (195000, 16),
    (165000, 15),
    (140000, 14),
    (120000, 13),
    (100000, 12),
    (85000, 11),
    (64000, 10),
    (48000, 9),
    (34000, 8),
    (23000, 7),
    (14000, 6),
    (6500, 5),
    (2700, 4),
    (900, 3),
    (300, 2),
    (0, 1),
]

# XP needed for each level (indexed by level, 0 unused)
XP_FOR_LEVEL: list[int] = [
    0,  # placeholder for index 0
    0,
    300,
    900,
    2700,
    6500,
    14000,
    23000,
    34000,
    48000,
    64000,
    85000,
    100000,
    120000,
    140000,
    165000,
    195000,
    225000,
    265000,
    305000,
    355000,
]


def xp_to_level(xp: int) -> int:
    """Compute level from XP using 5e thresholds."""
    for threshold, level in XP_THRESHOLDS:
        if xp >= threshold:
            return level
    return 1


def level_to_proficiency_bonus(level: int) -> int:
    """Compute proficiency bonus from level."""
    return (level - 1) // 4 + 2


def ability_modifier(score: int) -> int:
    """Compute ability modifier: floor((score - 10) / 2)."""
    return math.floor((score - 10) / 2)


class CharacterBase(SQLModel):
    """Base fields shared across all Character schemas."""

    name: str = Field(min_length=1, description="Character name")
    race: str | None = Field(default=None, description="Character race")
    char_class: str | None = Field(default=None, description="Character class")
    hp_max: int = Field(default=10, ge=0, description="Maximum hit points")
    hp_current: int = Field(default=10, ge=0, description="Current hit points")
    ac: int = Field(default=10, ge=0, description="Base armor class")
    speed: int = Field(default=30, ge=0, description="Movement speed in feet")
    xp: int = Field(default=0, ge=0, description="Experience points")

    # Base ability scores (default 10)
    strength: int = Field(default=10, ge=1, le=30)
    dexterity: int = Field(default=10, ge=1, le=30)
    constitution: int = Field(default=10, ge=1, le=30)
    intelligence: int = Field(default=10, ge=1, le=30)
    wisdom: int = Field(default=10, ge=1, le=30)
    charisma: int = Field(default=10, ge=1, le=30)


class Character(CharacterBase, table=True):
    """Character model - ORM table."""

    __tablename__ = "characters"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    inventory_id: UUID = Field(foreign_key="inventories.id", index=True)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CharacterCreate(SQLModel):
    """Schema for creating a new character."""

    name: str = Field(min_length=1, description="Character name")
    race: str | None = Field(default=None)
    char_class: str | None = Field(default=None)
    hp_max: int = Field(default=10, ge=0)
    hp_current: int = Field(default=10, ge=0)
    ac: int = Field(default=10, ge=0)
    speed: int = Field(default=30, ge=0)
    xp: int = Field(default=0, ge=0)
    strength: int = Field(default=10, ge=1, le=30)
    dexterity: int = Field(default=10, ge=1, le=30)
    constitution: int = Field(default=10, ge=1, le=30)
    intelligence: int = Field(default=10, ge=1, le=30)
    wisdom: int = Field(default=10, ge=1, le=30)
    charisma: int = Field(default=10, ge=1, le=30)


class CharacterRead(CharacterBase):
    """Schema for character response with computed fields."""

    id: UUID
    inventory_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def level(self) -> int:
        return xp_to_level(self.xp)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def proficiency_bonus(self) -> int:
        return level_to_proficiency_bonus(self.level)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def xp_to_next_level(self) -> int | None:
        lvl = self.level
        if lvl >= 20:
            return None
        return XP_FOR_LEVEL[lvl + 1] - self.xp

    @computed_field  # type: ignore[prop-decorator]
    @property
    def strength_modifier(self) -> int:
        return ability_modifier(self.strength)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dexterity_modifier(self) -> int:
        return ability_modifier(self.dexterity)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def constitution_modifier(self) -> int:
        return ability_modifier(self.constitution)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def intelligence_modifier(self) -> int:
        return ability_modifier(self.intelligence)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def wisdom_modifier(self) -> int:
        return ability_modifier(self.wisdom)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def charisma_modifier(self) -> int:
        return ability_modifier(self.charisma)


class CharacterUpdate(SQLModel):
    """Schema for updating a character (all fields optional)."""

    name: str | None = Field(default=None, min_length=1)
    race: str | None = None
    char_class: str | None = None
    hp_max: int | None = Field(default=None, ge=0)
    hp_current: int | None = Field(default=None, ge=0)
    ac: int | None = Field(default=None, ge=0)
    speed: int | None = Field(default=None, ge=0)
    xp: int | None = Field(default=None, ge=0)
    strength: int | None = Field(default=None, ge=1, le=30)
    dexterity: int | None = Field(default=None, ge=1, le=30)
    constitution: int | None = Field(default=None, ge=1, le=30)
    intelligence: int | None = Field(default=None, ge=1, le=30)
    wisdom: int | None = Field(default=None, ge=1, le=30)
    charisma: int | None = Field(default=None, ge=1, le=30)
