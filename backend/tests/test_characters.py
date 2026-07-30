"""Tests for character and character item API endpoints."""

import math
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import Character, CharacterItem, Inventory
from app.models.character import xp_to_level
from app.routers.inventories import hash_passphrase


@pytest.fixture
async def char_inventory(test_db: AsyncSession) -> tuple[Inventory, str]:
    """Create an inventory for character tests."""
    passphrase = "test-passphrase-123"
    inventory = Inventory(
        slug="char-test-party",
        name="Character Test Party",
        passphrase_hash=hash_passphrase(passphrase),
    )
    test_db.add(inventory)
    await test_db.commit()
    await test_db.refresh(inventory)
    return inventory, passphrase


@pytest.fixture
async def char_with_items(
    test_db: AsyncSession,
) -> tuple[Inventory, str, Character, list[CharacterItem]]:
    """Create an inventory with a character that has items."""
    passphrase = "test-passphrase-123"
    inventory = Inventory(
        slug="char-items-party",
        name="Character Items Party",
        passphrase_hash=hash_passphrase(passphrase),
    )
    test_db.add(inventory)
    await test_db.commit()
    await test_db.refresh(inventory)

    character = Character(
        inventory_id=inventory.id,
        name="Thorin",
        race="Dwarf",
        character_class="Fighter",
        strength=16,
        dexterity=12,
        constitution=14,
        intelligence=10,
        wisdom=10,
        charisma=8,
        base_ac=10,
        max_hp=30,
        current_hp=30,
        xp=900,
    )
    test_db.add(character)
    await test_db.commit()
    await test_db.refresh(character)

    items = [
        CharacterItem(
            character_id=character.id,
            name="Gauntlets of Ogre Power",
            type="equipment",
            rarity="uncommon",
            is_equipped=True,
            stat_overrides={"strength": 19},
        ),
        CharacterItem(
            character_id=character.id,
            name="Ring of Strength",
            type="equipment",
            rarity="rare",
            is_equipped=True,
            stat_modifiers={"strength": 1},
        ),
        CharacterItem(
            character_id=character.id,
            name="Shield +1",
            type="equipment",
            rarity="uncommon",
            is_equipped=True,
            stat_modifiers={"ac": 2},
        ),
        CharacterItem(
            character_id=character.id,
            name="Healing Potion",
            type="potion",
            rarity="common",
            is_equipped=False,
        ),
    ]
    for item in items:
        test_db.add(item)
    await test_db.commit()
    for item in items:
        await test_db.refresh(item)

    return inventory, passphrase, character, items


class TestCreateCharacter:
    """Tests for POST /api/inventories/{slug}/characters."""

    async def test_create_character_success(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
        test_db: AsyncSession,
    ) -> None:
        inventory, passphrase = char_inventory
        response = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Gandalf", "race": "Human", "character_class": "Wizard"},
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Gandalf"
        assert data["race"] == "Human"
        assert data["character_class"] == "Wizard"
        assert data["level"] == 1
        assert data["proficiency_bonus"] == 2

        # Verify persistence
        char_id = UUID(data["id"])
        result = await test_db.execute(select(Character).where(Character.id == char_id))
        db_char = result.scalar_one_or_none()
        assert db_char is not None
        assert db_char.name == "Gandalf"

    async def test_create_character_defaults(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        response = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Default Hero"},
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["xp"] == 0
        assert data["strength"] == 10
        assert data["base_ac"] == 10
        assert data["speed"] == 30
        assert data["max_hp"] == 10

    async def test_create_character_with_ability_scores(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        response = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={
                "name": "Strong Hero",
                "strength": 20,
                "dexterity": 14,
                "constitution": 16,
                "intelligence": 8,
                "wisdom": 12,
                "charisma": 10,
            },
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()
        scores = data["ability_scores"]
        assert scores["strength"]["base"] == 20
        assert scores["strength"]["effective"] == 20
        assert scores["strength"]["modifier"] == 5
        assert scores["intelligence"]["modifier"] == -1

    async def test_create_character_no_auth_returns_401(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, _ = char_inventory
        response = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Test"},
        )
        assert response.status_code == 401


class TestGetCharacter:
    """Tests for GET /api/inventories/{slug}/characters/{id}."""

    async def test_get_character_success(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        # Create first
        create_resp = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Legolas", "race": "Elf", "character_class": "Ranger", "xp": 6500},
            headers={"X-Passphrase": passphrase},
        )
        char_id = create_resp.json()["id"]

        # Get
        response = await client.get(
            f"/api/inventories/{inventory.slug}/characters/{char_id}",
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Legolas"
        assert data["level"] == 5
        assert data["proficiency_bonus"] == 3
        assert "ability_scores" in data
        assert "effective_ac" in data

    async def test_get_character_not_found(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(
            f"/api/inventories/{inventory.slug}/characters/{fake_id}",
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 404

    async def test_get_character_no_auth_returns_401(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        create_resp = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Test"},
            headers={"X-Passphrase": passphrase},
        )
        char_id = create_resp.json()["id"]

        response = await client.get(
            f"/api/inventories/{inventory.slug}/characters/{char_id}",
        )
        assert response.status_code == 401


class TestListCharacters:
    """Tests for GET /api/inventories/{slug}/characters."""

    async def test_list_characters_success(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        # Create two characters
        await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Char A"},
            headers={"X-Passphrase": passphrase},
        )
        await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Char B"},
            headers={"X-Passphrase": passphrase},
        )

        response = await client.get(
            f"/api/inventories/{inventory.slug}/characters",
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_list_characters_no_auth_returns_401(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, _ = char_inventory
        response = await client.get(
            f"/api/inventories/{inventory.slug}/characters",
        )
        assert response.status_code == 401


class TestUpdateCharacter:
    """Tests for PATCH /api/inventories/{slug}/characters/{id}."""

    async def test_update_character_success(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
        test_db: AsyncSession,
    ) -> None:
        inventory, passphrase = char_inventory
        create_resp = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Old Name"},
            headers={"X-Passphrase": passphrase},
        )
        char_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/inventories/{inventory.slug}/characters/{char_id}",
            json={"name": "New Name", "xp": 300},
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["xp"] == 300
        assert data["level"] == 2

        # Verify persistence
        result = await test_db.execute(select(Character).where(Character.id == UUID(char_id)))
        db_char = result.scalar_one_or_none()
        assert db_char is not None
        assert db_char.name == "New Name"
        assert db_char.xp == 300

    async def test_update_character_no_auth_returns_401(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        create_resp = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Test"},
            headers={"X-Passphrase": passphrase},
        )
        char_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/inventories/{inventory.slug}/characters/{char_id}",
            json={"name": "Updated"},
        )
        assert response.status_code == 401


class TestDeleteCharacter:
    """Tests for DELETE /api/inventories/{slug}/characters/{id}."""

    async def test_delete_character_success(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        create_resp = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Doomed"},
            headers={"X-Passphrase": passphrase},
        )
        char_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/inventories/{inventory.slug}/characters/{char_id}",
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 204

        # Verify gone
        get_resp = await client.get(
            f"/api/inventories/{inventory.slug}/characters/{char_id}",
            headers={"X-Passphrase": passphrase},
        )
        assert get_resp.status_code == 404

    async def test_delete_character_cascades_items(
        self,
        client: AsyncClient,
        char_with_items: tuple[Inventory, str, Character, list[CharacterItem]],
        test_db: AsyncSession,
    ) -> None:
        inventory, passphrase, character, items = char_with_items

        response = await client.delete(
            f"/api/inventories/{inventory.slug}/characters/{character.id}",
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 204

        # Verify all items are deleted
        result = await test_db.execute(
            select(CharacterItem).where(CharacterItem.character_id == character.id)
        )
        remaining = result.scalars().all()
        assert len(remaining) == 0

    async def test_delete_character_no_auth_returns_401(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        create_resp = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Test"},
            headers={"X-Passphrase": passphrase},
        )
        char_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/inventories/{inventory.slug}/characters/{char_id}",
        )
        assert response.status_code == 401


class TestCharacterItems:
    """Tests for character item CRUD endpoints."""

    async def test_add_item_to_character(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
        test_db: AsyncSession,
    ) -> None:
        inventory, passphrase = char_inventory
        create_resp = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Hero"},
            headers={"X-Passphrase": passphrase},
        )
        char_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/inventories/{inventory.slug}/characters/{char_id}/items",
            json={"name": "Longsword", "type": "equipment"},
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Longsword"
        assert data["is_equipped"] is False
        assert data["character_id"] == char_id

        # Verify persistence
        item_id = UUID(data["id"])
        result = await test_db.execute(select(CharacterItem).where(CharacterItem.id == item_id))
        db_item = result.scalar_one_or_none()
        assert db_item is not None
        assert db_item.name == "Longsword"

    async def test_list_character_items(
        self,
        client: AsyncClient,
        char_with_items: tuple[Inventory, str, Character, list[CharacterItem]],
    ) -> None:
        inventory, passphrase, character, items = char_with_items
        response = await client.get(
            f"/api/inventories/{inventory.slug}/characters/{character.id}/items",
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    async def test_update_character_item(
        self,
        client: AsyncClient,
        char_with_items: tuple[Inventory, str, Character, list[CharacterItem]],
        test_db: AsyncSession,
    ) -> None:
        inventory, passphrase, character, items = char_with_items
        item = items[0]
        response = await client.patch(
            f"/api/inventories/{inventory.slug}/characters/{character.id}/items/{item.id}",
            json={"name": "Upgraded Gauntlets"},
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Upgraded Gauntlets"

        # Verify persistence
        await test_db.refresh(item)
        result = await test_db.execute(select(CharacterItem).where(CharacterItem.id == item.id))
        db_item = result.scalar_one_or_none()
        assert db_item is not None
        assert db_item.name == "Upgraded Gauntlets"

    async def test_delete_character_item(
        self,
        client: AsyncClient,
        char_with_items: tuple[Inventory, str, Character, list[CharacterItem]],
    ) -> None:
        inventory, passphrase, character, items = char_with_items
        item = items[0]
        response = await client.delete(
            f"/api/inventories/{inventory.slug}/characters/{character.id}/items/{item.id}",
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 204

    async def test_character_items_no_auth_returns_401(
        self,
        client: AsyncClient,
        char_with_items: tuple[Inventory, str, Character, list[CharacterItem]],
    ) -> None:
        inventory, _, character, _ = char_with_items
        response = await client.get(
            f"/api/inventories/{inventory.slug}/characters/{character.id}/items",
        )
        assert response.status_code == 401


class TestEquipUnequip:
    """Tests for equip/unequip endpoints."""

    async def test_equip_item(
        self,
        client: AsyncClient,
        char_with_items: tuple[Inventory, str, Character, list[CharacterItem]],
    ) -> None:
        inventory, passphrase, character, items = char_with_items
        unequipped_item = items[3]  # Healing Potion is unequipped
        assert unequipped_item.is_equipped is False

        response = await client.post(
            f"/api/inventories/{inventory.slug}/characters/{character.id}/items/{unequipped_item.id}/equip",
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_equipped"] is True

    async def test_unequip_item(
        self,
        client: AsyncClient,
        char_with_items: tuple[Inventory, str, Character, list[CharacterItem]],
    ) -> None:
        inventory, passphrase, character, items = char_with_items
        equipped_item = items[0]  # Gauntlets are equipped
        assert equipped_item.is_equipped is True

        response = await client.post(
            f"/api/inventories/{inventory.slug}/characters/{character.id}/items/{equipped_item.id}/unequip",
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_equipped"] is False


class TestComputedStats:
    """Tests for computed stats with equipment modifiers."""

    async def test_stat_override_and_modifier(
        self,
        client: AsyncClient,
        char_with_items: tuple[Inventory, str, Character, list[CharacterItem]],
    ) -> None:
        """Base STR 16, override 19 (gauntlets), +1 modifier (ring) = effective 20."""
        inventory, passphrase, character, _ = char_with_items
        response = await client.get(
            f"/api/inventories/{inventory.slug}/characters/{character.id}",
            headers={"X-Passphrase": passphrase},
        )
        assert response.status_code == 200
        data = response.json()

        str_scores = data["ability_scores"]["strength"]
        assert str_scores["base"] == 16
        # Override 19 > base 16, so effective = 19 + 1 (modifier) = 20
        assert str_scores["effective"] == 20
        assert str_scores["modifier"] == math.floor((20 - 10) / 2)  # +5

    async def test_effective_ac_with_modifier(
        self,
        client: AsyncClient,
        char_with_items: tuple[Inventory, str, Character, list[CharacterItem]],
    ) -> None:
        """Base AC 10 + Shield +1 (ac modifier +2) = effective AC 12."""
        inventory, passphrase, character, _ = char_with_items
        response = await client.get(
            f"/api/inventories/{inventory.slug}/characters/{character.id}",
            headers={"X-Passphrase": passphrase},
        )
        data = response.json()
        assert data["base_ac"] == 10
        assert data["effective_ac"] == 12

    async def test_unequipped_items_dont_affect_stats(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        # Create character with base STR 10
        create_resp = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Weakling", "strength": 10},
            headers={"X-Passphrase": passphrase},
        )
        char_id = create_resp.json()["id"]

        # Add item with stat_modifiers but don't equip it
        await client.post(
            f"/api/inventories/{inventory.slug}/characters/{char_id}/items",
            json={
                "name": "Belt of Giant Strength",
                "type": "equipment",
                "stat_overrides": {"strength": 25},
                "is_equipped": False,
            },
            headers={"X-Passphrase": passphrase},
        )

        # Get character - STR should still be 10
        response = await client.get(
            f"/api/inventories/{inventory.slug}/characters/{char_id}",
            headers={"X-Passphrase": passphrase},
        )
        data = response.json()
        assert data["ability_scores"]["strength"]["effective"] == 10

    async def test_no_modifiers_items_dont_affect_stats(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        create_resp = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Normal Hero", "strength": 14},
            headers={"X-Passphrase": passphrase},
        )
        char_id = create_resp.json()["id"]

        # Add equipped item with no stat modifiers
        await client.post(
            f"/api/inventories/{inventory.slug}/characters/{char_id}/items",
            json={
                "name": "Regular Sword",
                "type": "equipment",
                "is_equipped": True,
            },
            headers={"X-Passphrase": passphrase},
        )

        response = await client.get(
            f"/api/inventories/{inventory.slug}/characters/{char_id}",
            headers={"X-Passphrase": passphrase},
        )
        data = response.json()
        assert data["ability_scores"]["strength"]["effective"] == 14
        assert data["ability_scores"]["strength"]["base"] == 14


class TestXPLevelComputation:
    """Tests for XP to level computation at boundaries."""

    @pytest.mark.parametrize(
        ("xp", "expected_level"),
        [
            (0, 1),
            (299, 1),
            (300, 2),
            (899, 2),
            (900, 3),
            (2699, 3),
            (2700, 4),
            (6500, 5),
            (14000, 6),
            (23000, 7),
            (34000, 8),
            (48000, 9),
            (64000, 10),
            (85000, 11),
            (100000, 12),
            (120000, 13),
            (140000, 14),
            (165000, 15),
            (195000, 16),
            (225000, 17),
            (265000, 18),
            (305000, 19),
            (355000, 20),
            (999999, 20),
        ],
    )
    def test_xp_to_level_boundaries(self, xp: int, expected_level: int) -> None:
        assert xp_to_level(xp) == expected_level

    async def test_xp_to_next_level_via_api(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        create_resp = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Leveler", "xp": 300},
            headers={"X-Passphrase": passphrase},
        )
        data = create_resp.json()
        assert data["level"] == 2
        assert data["xp_to_next_level"] == 600  # 900 - 300

    async def test_xp_to_next_level_at_max(
        self,
        client: AsyncClient,
        char_inventory: tuple[Inventory, str],
    ) -> None:
        inventory, passphrase = char_inventory
        create_resp = await client.post(
            f"/api/inventories/{inventory.slug}/characters",
            json={"name": "Max Level", "xp": 355000},
            headers={"X-Passphrase": passphrase},
        )
        data = create_resp.json()
        assert data["level"] == 20
        assert data["proficiency_bonus"] == 6
        assert data["xp_to_next_level"] is None
