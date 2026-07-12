# Development Backlog (Epics)

Run `python scripts/create_github_issues.py` to publish these as GitHub Issues (requires `gh auth`).

Until then, use this file as the backlog source of truth.

---

## Epic 1: Foundation `P0` `ready-for-agent`

**Title:** [Epic] Foundation: Docker, DB schema, auth skeleton, CI

- SQLAlchemy models for core entities (see [entity-model.md](domain/entity-model.md))
- Alembic migrations initial revision
- DB session dependency for FastAPI
- JWT httpOnly cookie auth dependency; working `GET /auth/me`
- Replace in-memory auth stub in `backend/app/api/auth.py`
- CI passes (ruff + pytest)

**Refs:** ADR-0001, ADR-0005, [setup.md](development/setup.md)

---

## Epic 2: Auth & accounts `P0`

**Title:** [Epic] Auth & accounts: registration, dual role

- Persistent DB users; register/login/logout
- Create candidate profile endpoint
- Company membership table; multi-company users
- Password hashing bcrypt

**Refs:** PRD US 1, 23-25; ADR-0005

---

## Epic 3: Resumes `P0`

**Title:** [Epic] Resumes: CRUD, draft/publish, visibility, contacts

- Draft + publish flow; visibility public/link_only/hidden
- Hide from company/domain/tax_id; block company
- Per-channel contact visibility; work experience modes
- Archive + permanent delete with snapshot anonymization

**Refs:** [entity-model.md](domain/entity-model.md), [flows.md](ux/flows.md) §2

---

## Epic 4: Tests `P1`

**Title:** [Epic] Tests: constructor, resume binding, hide on edit

- Max 10 questions; types single/multi/text/scale
- Hide resume while editing test; publish restores visibility
- Delete test with confirmation

**Refs:** [flows.md](ux/flows.md) §3, ADR-0002

---

## Epic 5: Companies `P0`

**Title:** [Epic] Companies: verification, owner/recruiter, invites

- Company CRUD; verification flow
- Owner/recruiter; invite + join requests
- Manual review for 2nd+ company; `X-Company-Id` header

**Refs:** ADR-0004, [flows.md](ux/flows.md) §8

---

## Epic 6: Vacancies `P1`

**Title:** [Epic] Vacancies: CRUD, statuses, required fields, recruiters

- Statuses draft/active/archived; mandatory salary
- Vacancy recruiter assignment; edit permissions

**Refs:** [entity-model.md](domain/entity-model.md)

---

## Epic 7: Applications `P0`

**Title:** [Epic] Applications: отклик, state machine, snapshots, auto-reject

- Submit with snapshots; UNIQUE(resume_id, vacancy_id)
- Full state machine; auto-reject; limit debit on send
- Expiry, extend once, reactivation; rejection reasons

**Refs:** [application-state-machine.md](domain/application-state-machine.md), ADR-0003

---

## Epic 8: Chat `P1`

**Title:** [Epic] Chat: text + links, read-only on block

- Chat on accept; text/links only
- Read-only on close/block; share contacts button

**Refs:** [flows.md](ux/flows.md) §7

---

## Epic 9: Moderation `P2`

**Title:** [Epic] Moderation: complaints, sanctions, audit log

- Complaints on 4 target types; admin sanctions
- Audit log; violation warnings on company profile

---

## Epic 10: Notifications `P2`

**Title:** [Epic] Notifications: email + in-app

- `GET /notifications`; email on key events
- SMTP via env; console fallback in dev

**Refs:** ADR-0005
