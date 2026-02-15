"""Character and character item API endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.auth import get_authenticated_inventory
from app.database import get_db
from app.models import (
    Character,
    CharacterCreate,
    CharacterItem,
    CharacterItemCreate,
    CharacterItemRead,
    CharacterItemUpdate,
    CharacterRead,
    CharacterUpdate,
)

router = APIRouter(prefix="/api/inventories", tags=["characters"])


async def _get_character_or_404(
    slug: str,
    character_id: UUID,
    db: AsyncSession,
    x_passphrase: str | None,
) -> tuple:
    """Authenticate and get a character, raising 404 if not found."""
    inventory = await get_authenticated_inventory(slug, db, x_passphrase)

    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.inventory_id == inventory.id,
        )
    )
    character = result.scalar_one_or_none()

    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    return inventory, character


# --- Character CRUD ---


@router.get("/{slug}/characters", response_model=list[CharacterRead])
async def list_characters(
    slug: str,
    db: AsyncSession = Depends(get_db),
    x_passphrase: str | None = Header(default=None),
) -> list[CharacterRead]:
    """List all characters in the party."""
    inventory = await get_authenticated_inventory(slug, db, x_passphrase)

    result = await db.execute(
        select(Character)
        .where(Character.inventory_id == inventory.id)
        .order_by(Character.created_at)
    )
    characters = result.scalars().all()

    reads = []
    for char in characters:
        read = CharacterRead.model_validate(char)
        read.build_ability_scores()
        reads.append(read)
    return reads


@router.post("/{slug}/characters", response_model=CharacterRead)
async def create_character(
    slug: str,
    data: CharacterCreate,
    db: AsyncSession = Depends(get_db),
    x_passphrase: str | None = Header(default=None),
) -> CharacterRead:
    """Create a new character in the party."""
    inventory = await get_authenticated_inventory(slug, db, x_passphrase)

    char_data = data.model_dump()
    character = Character(inventory_id=inventory.id, **char_data)

    db.add(character)
    await db.commit()
    await db.refresh(character)

    read = CharacterRead.model_validate(character)
    read.build_ability_scores()
    return read


@router.get("/{slug}/characters/{character_id}", response_model=CharacterRead)
async def get_character(
    slug: str,
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_passphrase: str | None = Header(default=None),
) -> CharacterRead:
    """Get a character with computed stats."""
    _, character = await _get_character_or_404(slug, character_id, db, x_passphrase)

    read = CharacterRead.model_validate(character)
    read.build_ability_scores()
    return read


@router.patch("/{slug}/characters/{character_id}", response_model=CharacterRead)
async def update_character(
    slug: str,
    character_id: UUID,
    data: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
    x_passphrase: str | None = Header(default=None),
) -> CharacterRead:
    """Update a character (partial update)."""
    _, character = await _get_character_or_404(slug, character_id, db, x_passphrase)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(character, key, value)

    character.updated_at = datetime.now(UTC)

    db.add(character)
    await db.commit()
    await db.refresh(character)

    read = CharacterRead.model_validate(character)
    read.build_ability_scores()
    return read


@router.delete("/{slug}/characters/{character_id}", status_code=204)
async def delete_character(
    slug: str,
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_passphrase: str | None = Header(default=None),
) -> None:
    """Delete a character and all its items."""
    _, character = await _get_character_or_404(slug, character_id, db, x_passphrase)

    # Delete all character items first
    items_result = await db.execute(
        select(CharacterItem).where(CharacterItem.character_id == character.id)
    )
    for item in items_result.scalars().all():
        await db.delete(item)

    await db.delete(character)
    await db.commit()


# --- Character Items ---


@router.get(
    "/{slug}/characters/{character_id}/items",
    response_model=list[CharacterItemRead],
)
async def list_character_items(
    slug: str,
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_passphrase: str | None = Header(default=None),
) -> list[CharacterItem]:
    """List all items belonging to a character."""
    _, character = await _get_character_or_404(slug, character_id, db, x_passphrase)

    result = await db.execute(
        select(CharacterItem)
        .where(CharacterItem.character_id == character.id)
        .order_by(CharacterItem.created_at)
    )
    return list(result.scalars().all())


@router.post(
    "/{slug}/characters/{character_id}/items",
    response_model=CharacterItemRead,
)
async def create_character_item(
    slug: str,
    character_id: UUID,
    data: CharacterItemCreate,
    db: AsyncSession = Depends(get_db),
    x_passphrase: str | None = Header(default=None),
) -> CharacterItem:
    """Add an item to a character's inventory."""
    _, character = await _get_character_or_404(slug, character_id, db, x_passphrase)

    item_data = data.model_dump()
    item = CharacterItem(character_id=character.id, **item_data)

    db.add(item)
    await db.commit()
    await db.refresh(item)

    return item


@router.patch(
    "/{slug}/characters/{character_id}/items/{item_id}",
    response_model=CharacterItemRead,
)
async def update_character_item(
    slug: str,
    character_id: UUID,
    item_id: UUID,
    data: CharacterItemUpdate,
    db: AsyncSession = Depends(get_db),
    x_passphrase: str | None = Header(default=None),
) -> CharacterItem:
    """Update a character's item (partial update)."""
    _, character = await _get_character_or_404(slug, character_id, db, x_passphrase)

    result = await db.execute(
        select(CharacterItem).where(
            CharacterItem.id == item_id,
            CharacterItem.character_id == character.id,
        )
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=404, detail="Character item not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    item.updated_at = datetime.now(UTC)

    db.add(item)
    await db.commit()
    await db.refresh(item)

    return item


@router.delete(
    "/{slug}/characters/{character_id}/items/{item_id}",
    status_code=204,
)
async def delete_character_item(
    slug: str,
    character_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_passphrase: str | None = Header(default=None),
) -> None:
    """Remove an item from a character's inventory."""
    _, character = await _get_character_or_404(slug, character_id, db, x_passphrase)

    result = await db.execute(
        select(CharacterItem).where(
            CharacterItem.id == item_id,
            CharacterItem.character_id == character.id,
        )
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=404, detail="Character item not found")

    await db.delete(item)
    await db.commit()


@router.post(
    "/{slug}/characters/{character_id}/items/{item_id}/equip",
    response_model=CharacterItemRead,
)
async def equip_item(
    slug: str,
    character_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_passphrase: str | None = Header(default=None),
) -> CharacterItem:
    """Equip a character item."""
    _, character = await _get_character_or_404(slug, character_id, db, x_passphrase)

    result = await db.execute(
        select(CharacterItem).where(
            CharacterItem.id == item_id,
            CharacterItem.character_id == character.id,
        )
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=404, detail="Character item not found")

    item.is_equipped = True
    item.updated_at = datetime.now(UTC)

    db.add(item)
    await db.commit()
    await db.refresh(item)

    return item


@router.post(
    "/{slug}/characters/{character_id}/items/{item_id}/unequip",
    response_model=CharacterItemRead,
)
async def unequip_item(
    slug: str,
    character_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_passphrase: str | None = Header(default=None),
) -> CharacterItem:
    """Unequip a character item."""
    _, character = await _get_character_or_404(slug, character_id, db, x_passphrase)

    result = await db.execute(
        select(CharacterItem).where(
            CharacterItem.id == item_id,
            CharacterItem.character_id == character.id,
        )
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=404, detail="Character item not found")

    item.is_equipped = False
    item.updated_at = datetime.now(UTC)

    db.add(item)
    await db.commit()
    await db.refresh(item)

    return item
