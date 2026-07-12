# ADR-0001: Monolith FastAPI + Vanilla JS

## Status

Accepted

## Context

MVP requires a job-search platform with complex domain logic (applications, snapshots, RBAC, moderation). We need a stack that supports agent-driven development, opens in any browser without build tooling, and keeps deployment simple.

## Decision

- **Monolithic backend**: single FastAPI application serving REST API and static frontend files.
- **Frontend**: vanilla HTML, CSS, and JavaScript — no frameworks, no bundlers, no plugins.
- **Single origin**: FastAPI serves `frontend/` as static files and API at `/api/v1/`. This enables httpOnly cookie auth without CORS complexity.
- **Database**: PostgreSQL 16 with SQLAlchemy 2 + Alembic migrations.
- **Deployment unit**: one Docker image for API + static; separate PostgreSQL container.

## Structure

```
backend/app/     — FastAPI, domain logic, models
frontend/        — static HTML/CSS/JS
docker-compose   — postgres + api
```

## Consequences

**Positive:**
- No frontend build step; pages open directly in browser.
- One deployable unit; simpler local dev.
- Same-origin cookie auth works out of the box.

**Negative:**
- No component framework; UI duplication possible across pages.
- Scaling frontend and API independently is not needed for MVP but harder later.
- Type safety only on backend (Pydantic); frontend relies on OpenAPI contract.

## Alternatives considered

- **NestJS + React**: rejected — user requirement for vanilla JS.
- **Separate frontend server (nginx)**: rejected for MVP — adds deployment complexity without benefit at this scale.
