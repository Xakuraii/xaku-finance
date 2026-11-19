# XakuFinance

Personal finance management for people who want their numbers to be *right*.

Track your money. Control your spending. Build your savings. Understand your financial future.

> **Status: Phase 1 in progress.** The backend scaffold, money and period primitives, identity
> models, atomic registration, rotating refresh sessions, email verification, password reset, and
> Google sign-in exist and are tested. Accounts, transactions, and reports are not implemented yet.
> Nothing in this repository should be read as a shipped feature until its acceptance criteria are
> met.

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

The full documentation index is available at [`docs/README.md`](docs/README.md).

| Document | Contents |
|---|---|
| [`docs/specifications/SRS.md`](docs/specifications/SRS.md) | Software Requirements Specification, requirement IDs, assumptions, gaps |
| [`docs/specifications/FEATURE_MATRIX.md`](docs/specifications/FEATURE_MATRIX.md) | V1 required / V1 optional / deferred, with complexity and risk |
| [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) | System, ledger, reporting, auth, background, backup, deployment architecture + Mermaid |
| [`docs/architecture/DATABASE.md`](docs/architecture/DATABASE.md) | Entity specification, constraints, indexes, ERD |
| [`docs/architecture/ACCOUNTING_RULES.md`](docs/architecture/ACCOUNTING_RULES.md) | Ledger model, posting recipes, money rules, reconciliation |
| [`docs/api/API_SPECIFICATION.md`](docs/api/API_SPECIFICATION.md) | Endpoints, payloads, errors, pagination, idempotency |
| [`docs/architecture/SECURITY.md`](docs/architecture/SECURITY.md) | Threat model, controls, privacy, deletion, backups |
| [`docs/specifications/TESTING.md`](docs/specifications/TESTING.md) | Test pyramid, financial-integrity suite, gates |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Delivery roadmap, milestones, dependencies, exit criteria |
| [`docs/specifications/RISKS.md`](docs/specifications/RISKS.md) | Risks, dependencies, mitigations |
| [`docs/specifications/ACCEPTANCE_CRITERIA.md`](docs/specifications/ACCEPTANCE_CRITERIA.md) | V1.0 release checklist |
| [`docs/specifications/PLANNING_REVIEW.md`](docs/specifications/PLANNING_REVIEW.md) | Consistency, arithmetic, double-counting, and feasibility review |
| [`docs/architecture/DESIGN_SYSTEM.md`](docs/architecture/DESIGN_SYSTEM.md) | Golden brand system, tokens, typography, charts, motion |
| [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md) | Full planned tree and ownership boundaries |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | Dated record of real changes |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |
| [`docs/reports/`](docs/reports/) | Milestone and verification reports |
| [`GLOSSARY.md`](GLOSSARY.md) | Canonical domain vocabulary |
| [`.AGENT.md`](.AGENT.md) | Operating instructions for coding agents |
| [`.agent/`](.agent/) | Agent context, standards, workflows, checklists |

Phase 1 implementation plan:
[`docs/superpowers/plans/2026-11-17-phase-1-foundation.md`](docs/superpowers/plans/2026-11-17-phase-1-foundation.md)

## Local setup

Phase 1 backend work is runnable now. The frontend is not built yet.

```bash
cp .env.example .env
docker compose up -d postgres redis
cd backend
python -m venv .venv
# Windows: .venv\Scripts\python -m pip install -e ".[dev]"
python -m pip install -e ".[dev]"
python manage.py migrate
pytest
```

On Windows the venv executables live in `.venv\Scripts\`. The database is exposed on host port
**55432** to avoid colliding with a locally installed PostgreSQL. CI uses PostgreSQL 16; the schema
targets 16+.

Email uses Django's console backend locally, so verification and reset links are printed to the
API log. To read them in a browser, start Mailpit (`docker compose up -d mailpit`), set
`EMAIL_BACKEND`, `EMAIL_HOST`, and `EMAIL_PORT` as shown in `.env.example`, then open
`http://localhost:56381`.

Backend checks:

```bash
cd backend
python -m ruff check .
python -m mypy apps
pytest
python manage.py spectacular --file ../docs/openapi.yaml --validate
```

Frontend checks (once the SPA lands):

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
