# Local development setup

## Prerequisites

- Docker and Docker Compose
- Python 3.12+ (optional, for running backend outside Docker)
- Git

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000

- API docs: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/v1/health

## Local backend (without Docker)

```bash
# Start PostgreSQL (or use docker compose up db -d)
cp .env.example .env

cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend is served from `frontend/` by FastAPI static mount.

## Commands (Makefile)

| Command | Description |
|---------|-------------|
| `make dev` | Start docker compose |
| `make test` | Run pytest |
| `make lint` | Run ruff |
| `make migrate` | Run alembic upgrade head (after Foundation epic) |

## Project structure

```
backend/app/domain/   — business logic (start here for features)
backend/app/api/      — thin HTTP layer
frontend/js/api.js    — fetch wrapper with credentials: 'include'
docs/api/openapi.yaml — API contract
docs/domain/          — entity model, state machine
docs/adr/             — architecture decisions
```

## First development issue

Start with GitHub issue **Foundation** (`ready-for-agent`):
- PostgreSQL models + Alembic
- JWT cookie auth dependency (`/auth/me`)
- Replace in-memory auth stub

## Documentation

- [PRD](../prd/reverse-hh-prd.md)
- [Entity model](../domain/entity-model.md)
- [Application state machine](../domain/application-state-machine.md)
- [UX flows](../ux/flows.md)
- [OpenAPI](../api/openapi.yaml)
