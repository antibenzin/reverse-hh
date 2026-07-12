# ADR-0005: Auth and Notifications

## Status

Accepted

## Context

Users have one account with candidate and/or employer roles. Frontend is vanilla JS without token management libraries. MVP needs email + in-app notifications, no push.

## Decision

### Authentication

- **Method**: email + password registration and login.
- **Session**: JWT stored in **httpOnly cookie** (`access_token`), not Bearer in localStorage.
- **Cookie flags**: `HttpOnly`, `SameSite=Lax`, `Secure` in production.
- **JWT payload**: `sub` (user id), `exp`, optional `iat`. No sensitive data in claims.
- **Session check**: `GET /api/v1/auth/me` returns current user or 401.

### Frontend integration

```javascript
fetch('/api/v1/resumes', { credentials: 'include' })
```

On 401, redirect to `/pages/login.html`. JS never reads or stores the JWT.

### Logout

`POST /api/v1/auth/logout` clears cookie (`Max-Age=0`).

### Password

- Hashed with bcrypt (passlib or bcrypt directly).
- Minimum length enforced in Pydantic schema.

### Notifications (MVP)

| Channel | Scope |
|---------|-------|
| In-app | `notifications` table; `GET /api/v1/notifications` |
| Email | Async send on key events (new application, accept/reject, chat message, verification result) |

Email provider: configurable SMTP via env (`SMTP_HOST`, etc.). Dev: log to console or Mailhog in docker-compose optional later.

**Not in MVP**: push, Telegram, WebSocket for notifications. Chat polling or simple refresh acceptable for MVP.

### Admin

Platform admins: `users.is_admin` boolean. Admin routes under `/api/v1/admin/` with separate dependency check.

## Consequences

**Positive:**
- XSS cannot steal JWT from localStorage.
- Vanilla JS auth is trivial (`credentials: 'include'`).
- Same-origin static + API simplifies cookie auth.

**Negative:**
- CSRF: mitigated by `SameSite=Lax` + JSON API (no simple form POST). Consider CSRF token if forms added later.
- JWT in cookie still needs short expiry + refresh strategy (MVP: 24h access token acceptable).

## Alternatives considered

- **Bearer in localStorage**: rejected — worse XSS exposure; more JS boilerplate.
- **Session table server-side**: acceptable future upgrade; JWT cookie sufficient for MVP.
