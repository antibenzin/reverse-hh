# ADR-0002: Domain Layer and Snapshots

## Status

Accepted

## Context

PRD defines complex business rules: application state machine, visibility, auto-reject, limits, and immutable history when resume/vacancy/test change after an application is sent. Logic must not leak into FastAPI routers or frontend JS.

## Decision

### Domain layer

All business rules live in `backend/app/domain/`:

- `applications.py` — submit, accept, reject, expire, reactivate
- `resumes.py` — publish, visibility, draft sync
- `tests.py` — validation, hide-on-edit
- `companies.py` — verification, membership
- `vacancies.py` — status transitions
- `access.py` — who can see what (catalog, applications, chats)

API routers (`backend/app/api/`) are thin: validate input, call domain, return response. No business logic in routers.

### Snapshots

When an employer submits an application, freeze immutable copies:

| Snapshot | Storage |
|----------|---------|
| Resume (published version) | `applications.resume_snapshot` JSONB |
| Vacancy (active version) | `applications.vacancy_snapshot` JSONB |
| Test (version at submit time) | `applications.test_snapshot` JSONB |
| Test answers | `application_test_answers` table |

Snapshots are never updated when source entities change. Old applications always show what was sent.

### Testing seam

Primary test boundary: `backend/app/domain/` — unit and integration tests call domain functions directly with test DB session. Routers tested only for HTTP contract smoke tests.

## Consequences

**Positive:**
- Business rules in one place; PRD changes map to domain modules.
- Snapshots prevent disputes about "what was offered."
- Agents can implement features by editing domain + tests without touching UI first.

**Negative:**
- JSONB snapshots are harder to query than normalized history tables.
- Domain layer must receive DB session and dependencies explicitly (no hidden globals).

## Alternatives considered

- **Event sourcing**: rejected — overkill for MVP.
- **Separate snapshot tables per entity**: rejected — JSONB sufficient for MVP read patterns.
