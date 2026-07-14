# D&D Party Inventory Manager - Agent Instructions

## Project Overview

Web app for D&D 5e party inventory management. Slug + passphrase access (no user accounts). Real-time sync via SSE.

## Key Documents

- **Full Spec:** `tasks/prd-inventory-manager.md` — Complete product specification
- **Implementation:** `IMPLEMENTATION.md` — Ordered user stories with acceptance criteria
- **Status:** `PROJECT_STATUS.md` — Current progress across all workstreams
- **PRDs:** `tasks/phase1/*.json` — Machine-readable story lists for Ralph

## Tech Stack

- **Frontend:** React 18 + Vite + Bun + Tailwind + TanStack Query + Zustand
- **Backend:** Python 3.11+ + FastAPI + UV + SQLModel + Pydantic v2
- **Database:** SQLite (async via aiosqlite)
- **Real-time:** Server-Sent Events (SSE)

## Project Structure

```
dnd-inventory-manager/                    # Main repo (on main branch)
├── backend/
│   └── app/
│       ├── main.py           # FastAPI app
│       ├── config.py         # Pydantic settings
│       ├── database.py       # SQLModel/SQLAlchemy async setup
│       ├── models/           # SQLModel models (ORM + schemas)
│       │   └── inventory.py  # Inventory model + Create/Read/Update schemas
│       ├── routers/          # API endpoints
│       ├── services/         # Business logic
│       ├── core/             # Auth, encryption, SSE manager
│       └── data/             # SRD item database
├── frontend/
│   └── src/
│       ├── api/              # API client
│       ├── components/       # React components
│       ├── hooks/            # Custom hooks
│       ├── pages/            # Route pages
│       ├── stores/           # Zustand stores
│       └── types/            # TypeScript types
├── tasks/                    # PRDs and specs
│   ├── prd-inventory-manager.md
│   └── phase1/               # Phase 1 story lists
└── scripts/
    └── ralph.sh              # Agent loop script

# Worktrees (sibling directories) - generic workers
dnd-inventory-manager-wt-1/              # Can work on any branch/PRD
dnd-inventory-manager-wt-2/              # Can work on any branch/PRD
dnd-inventory-manager-wt-3/              # Can work on any branch/PRD
```

## SQLModel Patterns

SQLModel combines SQLAlchemy ORM and Pydantic validation into a single model. This eliminates the old pattern of separate `db/*.py` (ORM) and `models/*.py` (schemas).

### Creating a New Model

```python
from datetime import UTC, datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel

# Base schema with shared fields
class ItemBase(SQLModel):
    name: str = Field(min_length=1)
    description: str | None = None

# ORM model (table=True makes it a database table)
class Item(ItemBase, table=True):
    __tablename__ = "items"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

# Create schema (for POST requests)
class ItemCreate(SQLModel):
    name: str = Field(min_length=1)
    description: str | None = None

# Read schema (for responses - excludes sensitive fields)
class ItemRead(ItemBase):
    id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}

# Update schema (all fields optional)
class ItemUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
```

### Key Points

1. **`table=True`** — Makes the class an ORM model (creates database table)
2. **Without `table=True`** — Just a Pydantic schema for validation
3. **`from_attributes=True`** — Allows creating from ORM instances
4. **Use Read schemas for responses** — Exclude sensitive fields like password hashes

### Query Pattern

```python
from sqlmodel import select

# Using SQLModel select (works with async sessions)
result = await db.execute(select(Item).where(Item.slug == slug))
item = result.scalar_one_or_none()
```

### When to Use Custom Endpoints vs CRUDRouter

**Custom endpoints** (preferred when):
- Custom authentication logic (passphrase headers)
- Slug generation or other preprocessing
- Non-standard response shapes
- Complex business logic

**CRUDRouter** (useful when):
- Simple CRUD with no auth
- Standard REST patterns
- Admin/internal APIs

## Development

### Quick Start (Recommended)

Run the full stack with a single command:

```bash
./scripts/dev.sh
```

This will:
- Auto-detect available ports (no conflicts with other worktrees)
- Create `.env.local` files if missing
- Start backend and frontend together
- Clean up both processes on Ctrl+C

### First-Time Setup

To configure your environment without starting servers:

```bash
./scripts/dev-setup.sh
```

This creates:
- `backend/.env.local` with `PORT=XXXX`
- `frontend/.env.local` with `VITE_PORT=XXXX` and `VITE_API_URL=...`

### Manual Workflow

After running setup, you can start services individually:

```bash
# Terminal 1 - Backend
cd backend
source .env.local
uv run uvicorn app.main:app --reload --port $PORT

# Terminal 2 - Frontend
cd frontend
source .env.local
bun run dev --port $VITE_PORT
```

### Port Assignment

Ports are dynamically assigned to avoid conflicts:
- **Backend:** First available port in 8000-8099
- **Frontend:** First available port in 5173-5199

The `.env.local` files are **gitignored** and auto-generated. Each worktree gets its own ports.

**Production uses fixed ports:**
| Service | Port |
|---------|------|
| Docker app | 8080 |

### Troubleshooting

**Ports seem stuck or conflicting?**
```bash
rm backend/.env.local frontend/.env.local
./scripts/dev-setup.sh
```

**Check which ports are in use:**
```bash
./scripts/dev-ports.sh
```

## Production Deployment (Docker)

### Production Safety for Agents

Treat any running container named `dnd-inventory-manager` as live production unless the user explicitly says otherwise. Do not use the production Docker container, production data mount, production port, or existing Tailscale Serve config as a test environment.

Before running Docker or Tailscale commands for this app, check what is already running:

```bash
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
docker inspect dnd-inventory-manager --format '{{json .Mounts}}'
tailscale serve status
```

If the container uses `/home/sbolgert/workspace/dnd-inventory-manager/data` or another real data directory, stop and treat it as production. Do not run `docker compose up`, `docker compose down`, or `tailscale serve` from a Codex worktree against that container.

Preferred dev environments:
- Use `./scripts/dev.sh` for local worktree development; it assigns non-production ports automatically.
- For Tailscale device testing, use the README "Tailnet Dev Testing" workflow with Vite on `--host 0.0.0.0` and a worktree-specific frontend port.
- If Docker is required for dev testing, use a separate Compose project, separate container name, separate data volume, and a non-production host port. Never reuse port `8080` or the `dnd-inventory-manager` container name for dev testing.

### Quick Start
```bash
docker compose up -d --build    # Build and start
docker compose down             # Stop
docker compose logs -f app      # View logs
```

### Access URLs
- **Local:** http://localhost:8080
- **Tailscale:** http://<tailscale-ip>:8080 (from phone/other devices)

### Architecture
```
Phone/Device (Tailscale) → Host port 8080 → nginx in container → uvicorn on 127.0.0.1:8000
                                                    ↓
                                           /api/* proxy to backend
```

### Key Files
- `docker-compose.yml` — Service definitions
- `Dockerfile` — Bun frontend build + Python/nginx runtime
- `data/` — production SQLite data when using the default Compose bind mount

### Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| Command | `./scripts/dev.sh` | `docker compose up -d --build` |
| Backend | uvicorn with --reload | Docker container |
| Frontend | Vite dev server | nginx serving built files |
| Ports | 8000-8099, 5173-5199 | 8080 |
| Hot reload | Yes | No (rebuild required) |

### Data Persistence
SQLite database is stored in `./data/` and mounted as a Docker volume. Data persists across container restarts.

## Code Conventions

### Backend (Python)
- Use SQLModel for all models (ORM + schemas in one)
- Async everywhere (async def, await)
- Type hints on all functions
- SQLModel select() for queries
- UV for package management

### Frontend (TypeScript/React)
- Functional components with hooks
- TanStack Query for server state
- Zustand for client state
- Tailwind for styling (mobile-first)
- Bun for package management

## Key Patterns

### API Authentication
Passphrase sent via `X-Passphrase` header. Verified against bcrypt hash.

### SSE Events
Broadcast via `ConnectionManager`. Events: `item_added`, `item_updated`, `item_removed`, `currency_updated`.

### Item Type Handling
Base `Item` model with `properties: dict` for type-specific fields. Use discriminated unions in Pydantic.

## Testing Guidelines

### Backend Tests

**Assert database persistence for create/update operations:**

Tests should verify that data was actually persisted to the database, not just that the API returned a successful response. This catches issues where the response looks correct but the database transaction failed or wasn't committed.

```python
async def test_create_item_success(
    self, client: AsyncClient, test_inventory: tuple[Inventory, str], test_db: AsyncSession
) -> None:
    """Test creating an item persists to database."""
    inventory, passphrase = test_inventory
    response = await client.post(
        f"/api/inventories/{inventory.slug}/items",
        json={"name": "Magic Sword", "type": "equipment"},
        headers={"X-Passphrase": passphrase},
    )
    assert response.status_code == 200
    
    # Verify persistence to database
    data = response.json()
    from uuid import UUID
    from sqlmodel import select
    
    item_id = UUID(data["id"])
    result = await test_db.execute(select(Item).where(Item.id == item_id))
    db_item = result.scalar_one_or_none()
    assert db_item is not None
    assert db_item.name == "Magic Sword"
```

**For update tests, refresh the fixture object:**

```python
async def test_update_item_success(
    self, client: AsyncClient, inventory_with_items: tuple, test_db: AsyncSession
) -> None:
    inventory, passphrase, items = inventory_with_items
    item = items[0]
    response = await client.patch(...)
    
    # Refresh and verify database state
    await test_db.refresh(item)
    result = await test_db.execute(select(Item).where(Item.id == item.id))
    db_item = result.scalar_one_or_none()
    assert db_item.name == "Updated Name"
```

## Quality Checks (REQUIRED)

**At the end of every turn, run the CI checks before committing:**

```bash
# Backend (from backend/ directory)
uv run ruff check app/ tests/
uv run pytest tests/ -v

# Frontend (from frontend/ directory)
bun run typecheck
bun run lint
```

These same checks run in GitHub Actions CI on every PR. **Do not commit if any check fails.**

### Full Commands (if needed)

```bash
# Backend - also format
cd backend
uv run ruff check .
uv run ruff format .
uv run ty check app/
uv run pytest -v

# Frontend
cd frontend
bun run typecheck
bun run lint
```

## Full Spec

See `tasks/prd-inventory-manager.md` for complete product specification.
