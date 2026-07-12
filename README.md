# Reverse HH

Сервис обратного поиска работы: соискатели публикуют резюме, верифицированные работодатели откликаются непубличными вакансиями. Соискатель принимает или отклоняет предложение.

**Репозиторий:** https://github.com/antibenzin/reverse-hh

## Стек

| Слой | Технология |
|------|------------|
| Frontend | Vanilla JS + HTML + CSS |
| Backend | Python 3.12 + FastAPI |
| БД | PostgreSQL 16 |
| Auth | JWT в httpOnly cookie |

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build
```

Открыть http://localhost:8000 · API docs: http://localhost:8000/api/docs

Подробнее: [docs/development/setup.md](docs/development/setup.md)

## Документация

| Документ | Описание |
|----------|----------|
| [PRD](docs/prd/reverse-hh-prd.md) | Продуктовые требования MVP |
| [CONTEXT.md](CONTEXT.md) | Доменный словарь |
| [AGENTS.md](AGENTS.md) | Правила для AI-агентов |
| [Entity model](docs/domain/entity-model.md) | Схема БД и сущности |
| [State machine](docs/domain/application-state-machine.md) | Жизненный цикл отклика |
| [OpenAPI](docs/api/openapi.yaml) | REST API контракт |
| [UX flows](docs/ux/flows.md) | Экраны и флоу |
| [Backlog](docs/backlog/epics.md) | 10 эпиков разработки |
| [ADRs](docs/adr/) | Архитектурные решения |

## Структура проекта

```
backend/app/
  domain/     — бизнес-логика (начинать здесь)
  api/        — HTTP-роутеры
  models/     — SQLAlchemy
frontend/     — статический UI
docs/         — PRD, ADR, domain, API
```

## Разработка

1. Взять issue **[Epic] Foundation** (`ready-for-agent`) — или см. [backlog](docs/backlog/epics.md)
2. Опубликовать issues на GitHub: `python scripts/create_github_issues.py`
3. Доменная логика → тесты → API → UI

```bash
make test    # pytest
make lint    # ruff
```
