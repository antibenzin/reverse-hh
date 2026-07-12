# ADR-0004: RBAC — Company and Vacancy

## Status

Accepted

## Context

Companies have multiple members (owner, recruiter). Recruiters can be assigned to vacancies. Visibility of applications and chats depends on role and assignment. PRD defines granular rules.

## Decision

### Company-level roles

| Role | Permissions |
|------|-------------|
| `owner` | Full company control: verification, members, all vacancies, all applications, all chats |
| `recruiter` | Own applications + applications/chats for assigned vacancies; edit assigned vacancies; cannot change vacancy status or member roster |

### Vacancy assignment

- `vacancy_recruiters` junction table: `(vacancy_id, user_id)`.
- Creator of vacancy is auto-assigned and can add other recruiters.
- Owner can assign any recruiter to any vacancy.

### Visibility matrix

| Resource | Owner | Recruiter (creator) | Recruiter (assigned) | Recruiter (other) |
|----------|-------|---------------------|----------------------|-------------------|
| All company applications | yes | — | — | no |
| Own applications | yes | yes | yes | yes |
| Assigned vacancy applications | yes | yes | yes | no |
| All company chats | yes | — | — | no |
| Related chats | yes | yes | yes | no |

### Multi-company users

- User can belong to multiple companies via `company_members`.
- Active company workspace selected in UI; API requests include `X-Company-Id` header or path prefix `/companies/{id}/`.

### Candidate-side blocks

- **Hide from company**: company cannot see specific resume in catalog.
- **Block company**: company cannot see any resume or send applications; existing chats read-only.

Block is at **company** level, not individual recruiter.

### Enforcement

`backend/app/domain/access.py` centralizes checks. Every API endpoint that reads applications, resumes, or chats calls access helpers before returning data.

## Consequences

**Positive:**
- Clear permission model matches PRD grilling decisions.
- Owner not a bottleneck for day-to-day recruiting on assigned vacancies.

**Negative:**
- `X-Company-Id` header adds client responsibility.
- Permission checks on every read path — must not forget in new endpoints.

## Alternatives considered

- **Flat recruiter = full company access**: rejected — too permissive.
- **Per-application assignment**: rejected — PRD uses vacancy-level assignment.
