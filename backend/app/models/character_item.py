"""SQLModel-based CharacterItem models.

This module contains the CharacterItem model and related schemas for character inventory items.
Mirrors the Item model but belongs to a character instead of an inventory,
with additional is_equipped, stat_modifiers, and stat_overrides fields.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, SQLModel

from app.models.item import ItemRarity, ItemType


class CharacterItemBase(SQLModel):
    """Base fields shared across all CharacterItem schemas."""

    name: str = Field(min_length=1, description="Item name")
    type: ItemType = Field(default=ItemType.misc, description="Item type")
    category: str | None = Field(default=None, description="Item category (e.g., Weapon, Armor)")
    rarity: ItemRarity = Field(default=ItemRarity.common, description="Item rarity")
    description: str | None = Field(default=None, description="Item description")
    quantity: int = Field(default=1, ge=1, description="Number of this item")
    weight: float | None = Field(default=None, ge=0, description="Weight in pounds")
    estimated_value: float | None = Field(default=None, ge=0, description="Estimated value in gold")


class CharacterItem(CharacterItemBase, table=True):
    """Character inventory item model - ORM table."""

    __tablename__ = "character_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    character_id: UUID = Field(foreign_key="characters.id", index=True)

    # Additional fields
    notes: str | None = Field(default=None, description="User notes about this item")
    thumbnail_url: str | None = Field(default=None, description="URL to item thumbnail image")
    is_standard_item: bool = Field(default=False, description="Whether this is from the SRD")
    standard_item_id: str | None = Field(default=None, description="ID in SRD if standard item")

    # JSON column for type-specific properties
    properties: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    # Equipment
    is_equipped: bool = Field(default=False, description="Whether the item is equipped")

    # Stat effects (JSON columns)
    stat_modifiers: dict[str, int] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additive bonuses e.g. {'strength': 2, 'ac': 2}",
    )
    stat_overrides: dict[str, int] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Fixed value sets e.g. {'strength': 19}",
    )

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CharacterItemCreate(CharacterItemBase):
    """Schema for creating a new character item."""

    notes: str | None = Field(default=None, description="User notes about this item")
    properties: dict[str, Any] | None = Field(default=None, description="Type-specific properties")
    is_standard_item: bool = Field(default=False)
    standard_item_id: str | None = Field(default=None)
    is_equipped: bool = Field(default=False)
    stat_modifiers: dict[str, int] | None = Field(default=None)
    stat_overrides: dict[str, int] | None = Field(default=None)


class CharacterItemRead(CharacterItemBase):
    """Schema for character item response."""

    id: UUID
    character_id: UUID
    notes: str | None
    thumbnail_url: str | None
    is_standard_item: bool
    standard_item_id: str | None
    properties: dict[str, Any] | None
    is_equipped: bool
    stat_modifiers: dict[str, int] | None
    stat_overrides: dict[str, int] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CharacterItemUpdate(SQLModel):
    """Schema for updating a character item (all fields optional for partial update)."""

    name: str | None = Field(default=None, min_length=1)
    type: ItemType | None = None
    category: str | None = None
    rarity: ItemRarity | None = None
    description: str | None = None
    notes: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    weight: float | None = Field(default=None, ge=0)
    estimated_value: float | None = Field(default=None, ge=0)
    thumbnail_url: str | None = None
    properties: dict[str, Any] | None = None
    is_equipped: bool | None = None
    stat_modifiers: dict[str, int] | None = None
    stat_overrides: dict[str, int] | None = None
