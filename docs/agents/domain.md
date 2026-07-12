# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root
- **`docs/adr/`** — read ADRs that touch the area you're about to work in
- **`docs/prd/reverse-hh-prd.md`** — product requirements for MVP

If any of these files don't exist, proceed silently.

Also read `docs/prd/reverse-hh-prd.md`, `docs/domain/entity-model.md`, and `docs/domain/application-state-machine.md` when working on domain features.

## File structure

Single-context repo:

```
/
├── CONTEXT.md
├── docs/adr/
├── docs/prd/
└── src/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0001 — but worth reopening because…_
