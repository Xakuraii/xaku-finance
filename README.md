# XakuFinance

Personal finance management for people who want their numbers to be *right*.

Track your money. Control your spending. Build your savings. Understand your financial future.

> **Status: planning complete, implementation not started.** This repository currently contains the
> approved planning package (requirements, architecture, schema, accounting rules, API contracts,
> security model, roadmap, and the Phase 1 implementation plan). No application code exists yet.
> Nothing in this repository should be read as a shipped feature.

---

## What XakuFinance is

A single-user, private financial workspace for individuals. It combines:

- A double-entry ledger that every balance and report derives from.
- Multi-account, multi-currency tracking (USD and KHR first).
- Income/expense transactions with splits, tags, and audited edits.
- Internal transfers, including explicit cross-currency transfers.
- Category budgets with positive-only rollover and custom financial periods.
- Savings goals backed by real money movements, not virtual wishlists.
- Debt tracking that separates principal from interest.
- Historical net worth, Safe-to-Spend, daily allowance, and an emergency fund planner.
- Reports, on-demand insights, notifications, imports/exports, backups, and privacy controls.

It is **not** an expense tracker with a dashboard bolted on, and it is **not** a multi-tenant
accounting suite. One user, one workspace, one ledger.

## Stack

| Layer | Choice |
|---|---|
| Frontend | React 19 + TypeScript + Vite, Tailwind CSS v4, Radix primitives, TanStack Query, React Router, React Hook Form + Zod, Recharts |
| Backend | Python 3.12+, Django 5.2 LTS, Django REST Framework, drf-spectacular |
| Database | PostgreSQL 16+ |
| Auth | JWT (SimpleJWT) with rotating refresh tokens, Argon2id, optional TOTP 2FA |
| Async | Celery + Redis (only for work that must not block a request) |
| Infra | Docker Compose, GitHub Actions, S3-compatible object storage for exports/backups |

Rationale and rejected alternatives: `docs/adr/`.

## Documentation map

| Document | Contents |
|---|---|
| [`docs/SRS.md`](docs/SRS.md) | Software Requirements Specification, requirement IDs, assumptions, gaps |
| [`docs/FEATURE_MATRIX.md`](docs/FEATURE_MATRIX.md) | V1 required / V1 optional / deferred, with complexity and risk |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System, ledger, reporting, auth, background, backup, deployment architecture + Mermaid |
| [`docs/DATABASE.md`](docs/DATABASE.md) | Entity specification, constraints, indexes, ERD |
| [`docs/ACCOUNTING_RULES.md`](docs/ACCOUNTING_RULES.md) | Ledger model, posting recipes, money rules, reconciliation |
| [`docs/API_SPECIFICATION.md`](docs/API_SPECIFICATION.md) | Endpoints, payloads, errors, pagination, idempotency |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Threat model, controls, privacy, deletion, backups |
| [`docs/TESTING.md`](docs/TESTING.md) | Test pyramid, financial-integrity suite, gates |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Six phases, milestones, dependencies, exit criteria |
| [`docs/RISKS.md`](docs/RISKS.md) | Risks, dependencies, mitigations |
| [`docs/ACCEPTANCE_CRITERIA.md`](docs/ACCEPTANCE_CRITERIA.md) | V1.0 release checklist |
| [`docs/PLANNING_REVIEW.md`](docs/PLANNING_REVIEW.md) | Consistency, arithmetic, double-counting, and feasibility review |
| [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) | Golden brand system, tokens, typography, charts, motion |
| [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md) | Full planned tree and ownership boundaries |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | Dated record of real changes |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |
| [`GLOSSARY.md`](GLOSSARY.md) | Canonical domain vocabulary |
| [`.AGENT.md`](.AGENT.md) | Operating instructions for coding agents |
| [`.agent/`](.agent/) | Agent context, standards, workflows, checklists |

Phase 1 implementation plan:
[`docs/superpowers/plans/2026-11-17-phase-1-foundation.md`](docs/superpowers/plans/2026-11-17-phase-1-foundation.md)

## Planned local setup

These commands describe the intended developer experience; they will only work once Phase 1 lands.

```bash
cp .env.example .env
docker compose up --build
# API      http://localhost:8000/api/v1/
# API docs http://localhost:8000/api/docs/
# Web      http://localhost:5173
```

Backend checks, run inside the `api` container:

```bash
python manage.py migrate
python manage.py seed_currencies
python manage.py check --deploy
pytest
python manage.py spectacular --file docs/openapi.yaml --validate
```

Frontend checks:

```bash
cd frontend
npm ci
npm run typecheck
npm run lint
npm run test
npm run build
npx playwright test
```

## Non-negotiable invariants

1. Money is never a float. Integer minor units in the database, `Decimal` in Python, strings in JSON.
2. Every balance derives from ledger postings. No mutable `balance` column is authoritative.
3. Every journal entry balances to zero per currency.
4. Completed ≠ pending ≠ cancelled. Only completed entries affect balances.
5. Transfers, opening balances, and savings earmarks are never income or expense.
6. Financial writes are atomic (`ATOMIC_REQUESTS` + `select_for_update` on affected accounts).
7. Every row is workspace-scoped; every query is workspace-scoped.
8. Financial history is append-only: edits create audit rows, corrections create reversing entries.
9. AI never computes or invents a number. It explains server-computed summaries.
10. A feature is not done because a page renders. See `docs/ACCEPTANCE_CRITERIA.md`.

## License

Proprietary. All rights reserved unless a `LICENSE` file says otherwise.
