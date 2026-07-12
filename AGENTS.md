# Reverse HH — Agent Guide

Сервис обратного поиска работы: соискатели публикуют резюме, работодатели откликаются непубличными вакансиями.

## Source of truth

- **PRD**: `docs/prd/reverse-hh-prd.md`
- **Domain glossary**: `CONTEXT.md`
- **Entity model**: `docs/domain/entity-model.md`
- **State machine**: `docs/domain/application-state-machine.md`
- **API contract**: `docs/api/openapi.yaml`
- **UX flows**: `docs/ux/flows.md`
- **ADRs**: `docs/adr/`
- **Backlog**: `docs/backlog/epics.md`

## Stack

- Backend: FastAPI + PostgreSQL + SQLAlchemy + Alembic
- Frontend: vanilla JS/HTML/CSS, `fetch` with `credentials: 'include'`
- Auth: JWT in httpOnly cookie (ADR-0005)

## Working rules

1. Читай PRD, `CONTEXT.md` и релевантные ADR перед изменениями доменной логики.
2. Не добавляй фичи из раздела Out of Scope PRD без явного запроса.
3. Центральная доменная модель — **Application** (отклик работодателя). Логика в `backend/app/domain/`, не в роутерах и не в JS.
4. Любое изменение бизнес-правил — тесты на внешнее поведение (см. PRD → Testing Decisions).
5. Коммиты — только по запросу пользователя.
6. Следуй `docs/api/openapi.yaml` для контракта API.

## Agent skills

### Issue tracker

GitHub Issues. See `docs/agents/issue-tracker.md`. Backlog: `docs/backlog/epics.md`.

### Triage labels

`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` + `docs/domain/`. See `docs/agents/domain.md`.

## Repo layout

```
reverse-hh/
├── backend/app/
│   ├── domain/          # Business logic — implement features here first
│   ├── api/             # Thin HTTP layer
│   ├── models/          # SQLAlchemy
│   └── services/        # email, notifications, audit
├── frontend/
│   ├── js/api.js        # fetch + credentials: 'include'
│   └── pages/           # HTML per screen
├── docs/
│   ├── prd/
│   ├── adr/
│   ├── domain/
│   ├── api/
│   ├── ux/
│   └── backlog/
├── AGENTS.md
├── CONTEXT.md
└── docker-compose.yml
```

## First task

**Epic Foundation** (`ready-for-agent`): DB models, Alembic, JWT cookie auth dependency, replace auth stub.

See `docs/backlog/epics.md` for acceptance criteria.
