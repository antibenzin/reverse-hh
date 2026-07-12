# ADR-0003: Application State Machine

## Status

Accepted

## Context

Application (employer response to a resume) is the central domain entity. PRD defines nine statuses and multiple transitions with side effects (chat open, limit debit, read-only).

## Decision

Implement a formal state machine in `backend/app/domain/applications.py`. Status enum and allowed transitions are the single source of truth.

### Statuses

| Status | Meaning |
|--------|---------|
| `sent` | Submitted; candidate has not opened |
| `viewed` | Candidate opened the application |
| `accepted` | Candidate accepted; chat open |
| `rejected` | Candidate rejected |
| `auto_rejected` | Auto-reject rules (salary/format/location) |
| `expired` | System timeout without response |
| `reactivation_requested` | Candidate asked if expired offer is still valid |
| `reactivated` | Employer confirmed; candidate can decide again |
| `closed_after_acceptance` | Candidate closed chat after accepting |

### Key rules

- `UNIQUE(resume_id, vacancy_id)` — one application per pair forever.
- Limit debited on transition to `sent` (or `auto_rejected` if employer confirmed send).
- Employer cannot withdraw after `sent`.
- Chat created only on `accepted`.
- `closed_after_acceptance` sets chat read-only.

Full transition table: see [application-state-machine.md](../domain/application-state-machine.md).

### Implementation

```python
# Conceptual shape — not final code
class ApplicationStatus(str, Enum):
    sent = "sent"
    viewed = "viewed"
    # ...

ALLOWED_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = { ... }

def transition(app: Application, to: ApplicationStatus, actor: Actor) -> Application:
    if to not in ALLOWED_TRANSITIONS[app.status]:
        raise InvalidTransition(...)
    # side effects: chat, audit, notifications
```

## Consequences

**Positive:**
- Invalid states impossible if all changes go through `transition()`.
- Easy to test each transition in isolation.

**Negative:**
- Background jobs needed for `expired` (cron or scheduled task).
- Reactivation flow adds complexity.

## Alternatives considered

- **Status as free string in DB**: rejected — no guard against invalid transitions.
- **Separate tables per status**: rejected — unnecessary normalization.
