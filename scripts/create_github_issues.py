#!/usr/bin/env python3
"""Create GitHub labels and epic issues for reverse-hh. Run once: python scripts/create_github_issues.py"""

import json
import subprocess
import sys

REPO = "antibenzin/reverse-hh"
GH = r"C:\Program Files\GitHub CLI\gh.exe"

LABELS = [
    ("needs-triage", "d4c5f9", "Maintainer needs to evaluate"),
    ("needs-info", "fbca04", "Waiting on reporter"),
    ("ready-for-agent", "0e8a16", "Ready for AFK agent"),
    ("ready-for-human", "1d76db", "Requires human implementation"),
    ("wontfix", "ffffff", "Will not be actioned"),
    ("epic:foundation", "5319e7", "Foundation epic"),
    ("epic:auth", "1d76db", "Auth epic"),
    ("epic:resumes", "0e8a16", "Resumes epic"),
    ("epic:tests", "bfd4f2", "Tests epic"),
    ("epic:companies", "d93f0b", "Companies epic"),
    ("epic:vacancies", "fbca04", "Vacancies epic"),
    ("epic:applications", "b60205", "Applications epic"),
    ("epic:chat", "006b75", "Chat epic"),
    ("epic:moderation", "e99695", "Moderation epic"),
    ("epic:notifications", "c5def5", "Notifications epic"),
    ("P0", "b60205", "Priority 0"),
    ("P1", "fbca04", "Priority 1"),
    ("P2", "0e8a16", "Priority 2"),
]

EPICS = [
    {
        "title": "[Epic] Foundation: Docker, DB schema, auth skeleton, CI",
        "labels": ["epic:foundation", "ready-for-agent", "P0"],
        "body": """## Summary
Bootstrap infrastructure for MVP development.

## Acceptance criteria
- [ ] SQLAlchemy models for core entities (see docs/domain/entity-model.md)
- [ ] Alembic migrations initial revision
- [ ] DB session dependency for FastAPI
- [ ] JWT httpOnly cookie auth dependency; working GET /auth/me
- [ ] Replace in-memory auth stub
- [ ] CI passes (ruff + pytest)

## References
- docs/adr/0001-monolith-fastapi-vanilla-js.md
- docs/adr/0005-auth-and-notifications.md
- docs/development/setup.md
""",
    },
    {
        "title": "[Epic] Auth & accounts: registration, dual role",
        "labels": ["epic:auth", "P0"],
        "body": """## User stories
- US-1: Single account for candidate and employer roles

## Acceptance criteria
- [ ] Register/login/logout with persistent DB users
- [ ] Create candidate profile endpoint
- [ ] User can belong to multiple companies (membership table)
- [ ] Password hashing bcrypt

## References
- docs/prd/reverse-hh-prd.md US 1, 23-25
- docs/adr/0005-auth-and-notifications.md
""",
    },
    {
        "title": "[Epic] Resumes: CRUD, draft/publish, visibility, contacts",
        "labels": ["epic:resumes", "P0"],
        "body": """## User stories
- US 2-8: Multiple resumes, visibility, hide from companies, block, contacts

## Acceptance criteria
- [ ] Resume draft + publish flow
- [ ] Visibility: public / link_only / hidden
- [ ] Hide from company/domain/tax_id rules
- [ ] Block company
- [ ] Contact visibility per channel
- [ ] Work experience modes (has / no / NDA)
- [ ] Archive and permanent delete with snapshot anonymization

## References
- docs/domain/entity-model.md
- docs/ux/flows.md §2
""",
    },
    {
        "title": "[Epic] Tests: constructor, resume binding, hide on edit",
        "labels": ["epic:tests", "P1"],
        "body": """## User stories
- US 9-12: Test per resume, question types, expected answers

## Acceptance criteria
- [ ] Max 10 questions, all required
- [ ] Question types: single, multi, text, scale
- [ ] Hide resume from catalog while test editing
- [ ] Save draft / publish and restore visibility
- [ ] Delete test with confirmation

## References
- docs/ux/flows.md §3
- docs/adr/0002-domain-layer-and-snapshots.md
""",
    },
    {
        "title": "[Epic] Companies: verification, owner/recruiter, invites",
        "labels": ["epic:companies", "P0"],
        "body": """## User stories
- US 23-25: Company roles, invites, multi-company workspace

## Acceptance criteria
- [ ] Company CRUD and archive
- [ ] Verification flow (email, website, tax_id, domain match or manual)
- [ ] Owner/recruiter roles
- [ ] Invite + join request flow
- [ ] Second+ company manual review flag
- [ ] X-Company-Id workspace header

## References
- docs/adr/0004-rbac-company-vacancy.md
- docs/ux/flows.md §8
""",
    },
    {
        "title": "[Epic] Vacancies: CRUD, statuses, required fields, recruiters",
        "labels": ["epic:vacancies", "P1"],
        "body": """## Acceptance criteria
- [ ] Vacancy statuses: draft, active, archived
- [ ] All required fields enforced (salary fixed or range mandatory)
- [ ] Assign recruiters to vacancies
- [ ] Edit permissions per ADR-0004

## References
- docs/domain/entity-model.md
- docs/ux/flows.md §8
""",
    },
    {
        "title": "[Epic] Applications: отклик, state machine, snapshots, auto-reject",
        "labels": ["epic:applications", "P0"],
        "body": """## User stories
- US 14-19, 30: Employer applies, candidate accepts/rejects

## Acceptance criteria
- [ ] Submit application with snapshots (resume, vacancy, test)
- [ ] UNIQUE(resume_id, vacancy_id) forever
- [ ] Full state machine (docs/domain/application-state-machine.md)
- [ ] Auto-reject salary/format/location with employer confirm
- [ ] Limit debit on send
- [ ] Expiry + extend once + reactivation flow
- [ ] Optional rejection reasons shared with employer

## References
- docs/adr/0003-application-state-machine.md
- docs/ux/flows.md §5-6
""",
    },
    {
        "title": "[Epic] Chat: text + links, read-only on block",
        "labels": ["epic:chat", "P1"],
        "body": """## User stories
- US 20-21: Chat after accept, manual contact sharing

## Acceptance criteria
- [ ] Chat created on accepted application
- [ ] Text and links only, no files
- [ ] Read-only on closed_after_acceptance, company block, admin action
- [ ] Share contacts button for candidate

## References
- docs/ux/flows.md §7
- docs/adr/0005-auth-and-notifications.md
""",
    },
    {
        "title": "[Epic] Moderation: complaints, sanctions, audit log",
        "labels": ["epic:moderation", "P2"],
        "body": """## User stories
- US 28-30: Complaints on 4 types, admin sanctions, audit

## Acceptance criteria
- [ ] Complaints: company, message, application, resume
- [ ] Admin sanctions per PRD list
- [ ] Audit log events per docs/domain/entity-model.md
- [ ] Serious violation warning on company profile for candidates

## References
- docs/adr/0004-rbac-company-vacancy.md
""",
    },
    {
        "title": "[Epic] Notifications: email + in-app",
        "labels": ["epic:notifications", "P2"],
        "body": """## Acceptance criteria
- [ ] notifications table + GET /notifications
- [ ] Email on key events (new application, accept/reject, chat, verification)
- [ ] SMTP configurable via env; console fallback in dev

## References
- docs/adr/0005-auth-and-notifications.md
""",
    },
]


def run(args: list[str]) -> None:
    result = subprocess.run([GH, *args], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        raise SystemExit(result.returncode)
    if result.stdout.strip():
        print(result.stdout.strip())


def main() -> None:
    for name, color, desc in LABELS:
        subprocess.run(
            [GH, "label", "create", name, "--repo", REPO, "--color", color, "--description", desc, "--force"],
            capture_output=True,
        )
    print(f"Labels ensured on {REPO}")

    for epic in EPICS:
        labels = ",".join(epic["labels"])
        run([
            "issue", "create",
            "--repo", REPO,
            "--title", epic["title"],
            "--body", epic["body"],
            "--label", labels,
        ])


if __name__ == "__main__":
    main()
