# D&D Party Inventory Manager

A collaborative web app for managing shared party inventory in D&D 5e campaigns. Players join via a unique slug link — no accounts needed. Changes sync in real-time across all connected devices.

**🎮 Try it now at [dndinventorymanager.com](https://dndinventorymanager.com)**

![D&D Party Inventory Manager](docs/screenshot.png)

## Features

- **Slug-based party access** — share a link, no sign-ups required
- **Real-time sync** — instant updates for all viewers via Server-Sent Events (SSE)
- **SRD 5e integration** — auto-populate item stats from the official SRD via [dnd5eapi.co](https://www.dnd5eapi.co/) GraphQL API
- **Currency tracking** — manage party gold with full transaction history
- **Full history & undo** — every change is logged; rollback to any point
- **Dark mode** — easy on the eyes for late-night sessions
- **Mobile-friendly** — responsive design, works great on phones and tablets

## Quick Start (Self-Hosting)

### Docker (recommended)

```bash
docker run -d -p 8080:80 -v dnd-data:/app/data linuxlewis/dnd-inventory-manager
```

Open **http://localhost:8080** — that's it!

Your data persists in the `dnd-data` volume across restarts and upgrades.

### Docker Compose

```bash
git clone https://github.com/linuxlewis/dnd-inventory-manager.git
cd dnd-inventory-manager
docker compose up -d
```

Access at **http://localhost:8080**.

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/dnd_inventory.db` | Database connection string |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |

Override via environment in `docker-compose.yml` or `docker run -e`:

```bash
docker run -d -p 8080:80 \
  -v dnd-data:/app/data \
  -e 'CORS_ORIGINS=["https://yourdomain.com"]' \
  linuxlewis/dnd-inventory-manager
```

## Development

**Prerequisites:** [Bun](https://bun.sh/) (frontend) · [UV](https://github.com/astral-sh/uv) + Python 3.11+ (backend)

### Local Dev Server

The easiest local workflow is:

```bash
./scripts/dev.sh
```

This assigns available backend/frontend ports for the current worktree and starts both servers. It avoids the production Docker container and the fixed self-hosting port.

### Tailnet Dev Testing

For testing from a phone or another device over Tailscale, do not reuse the production Docker container on port `8080`. Start the dev servers on worktree-specific ports instead:

```bash
./scripts/dev-setup.sh

# Terminal 1 - backend
source backend/.env.local
cd backend
uv run uvicorn app.main:app --reload --port "$PORT"

# Terminal 2 - frontend, from the repo root
BACKEND_PORT=$(grep '^PORT=' backend/.env.local | cut -d= -f2)
FRONTEND_PORT=$(grep '^VITE_PORT=' frontend/.env.local | cut -d= -f2)
cd frontend
VITE_API_URL="http://127.0.0.1:$BACKEND_PORT" bun run dev --host 0.0.0.0 --port "$FRONTEND_PORT"
```

Then open `http://<tailscale-ip>:$FRONTEND_PORT`. The frontend serves `/api` through the Vite proxy, so the backend can stay bound to localhost on the dev machine.

### Manual Dev Servers

```bash
# Backend
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000

# Frontend (in another terminal)
cd frontend && bun install && bun run dev
```

The frontend dev server proxies `/api` requests to `localhost:8000`.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 · TypeScript · Vite · Bun |
| Backend | Python 3.12 · FastAPI · SQLAlchemy |
| Database | SQLite (async via aiosqlite) |
| Real-time | Server-Sent Events (SSE) |
| SRD Data | GraphQL ([dnd5eapi.co](https://www.dnd5eapi.co/)) |
| Container | nginx + uvicorn · supervisord |

## Disclaimer

This project is not affiliated with, endorsed by, or associated with Wizards of the Coast, Hasbro, or any of their subsidiaries. Dungeons & Dragons, D&D, and all related trademarks are property of Wizards of the Coast LLC. Game data provided via the [D&D 5e SRD API](https://www.dnd5eapi.co/) under the Open Gaming License (OGL).

## License

MIT
