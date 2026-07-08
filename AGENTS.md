# Reverse HH — Agent Guide

Сервис обратного поиска работы: соискатели публикуют резюме, работодатели откликаются непубличными вакансиями.

## Source of truth

- **PRD**: `docs/prd/reverse-hh-prd.md`
- **Domain glossary**: `CONTEXT.md`
- **ADRs**: `docs/adr/`

## Working rules

1. Читай PRD и `CONTEXT.md` перед изменениями доменной логики.
2. Не добавляй фичи из раздела Out of Scope PRD без явного запроса.
3. Центральная доменная модель — отклик (`Application`), права доступа, snapshots и статусы. Не размазывай эту логику по UI-слоям.
4. Любое изменение бизнес-правил должно сопровождаться тестами на внешнее поведение (см. PRD → Testing Decisions).
5. Коммиты — только по запросу пользователя.

## Agent skills

### Issue tracker

Issues and PRDs live in GitHub Issues for this repo. See `docs/agents/issue-tracker.md`.

### Triage labels

Default triage vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo: `CONTEXT.md` + `docs/adr/`. See `docs/agents/domain.md`.

## Repo layout

```
reverse-hh/
├── AGENTS.md              # This file
├── CONTEXT.md             # Domain glossary
├── README.md
├── docs/
│   ├── prd/               # Product requirements
│   ├── adr/               # Architecture decision records
│   └── agents/            # Agent workflow config
└── src/                   # Application code (to be scaffolded)
```

## MVP focus

Первый этап разработки — доменный контур:

- аккаунт с ролями соискателя и работодателя;
- резюме, тесты, непубличные вакансии;
- отклик работодателя на резюме;
- принятие/отклонение, чат, модерация, audit log.
