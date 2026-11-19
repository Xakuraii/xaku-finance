# Repository Structure — XakuFinance

**Status:** backend scaffold exists (Phase 1, Task 1). Frontend and application domains are planned.

```
XakuFinance/
├── .AGENT.md
├── .agent/
│   ├── context/
│   │   ├── product.md
│   │   ├── glossary.md
│   │   └── decisions.md
│   ├── standards/
│   │   ├── backend.md
│   │   ├── frontend.md
│   │   ├── database.md
│   │   └── security.md
│   ├── workflows/
│   │   ├── feature-delivery.md
│   │   ├── financial-change.md
│   │   └── release.md
│   └── checklists/
│       ├── definition-of-done.md
│       └── financial-integrity.md
├── .env.example
├── .gitignore
├── .dockerignore
├── .editorconfig
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── nightly.yml
│       └── deploy.yml
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile
├── README.md
├── GLOSSARY.md
├── docs/
│   ├── SRS.md
│   ├── FEATURE_MATRIX.md
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── ACCOUNTING_RULES.md
│   ├── API_SPECIFICATION.md
│   ├── SECURITY.md
│   ├── TESTING.md
│   ├── ROADMAP.md
│   ├── RISKS.md
│   ├── ACCEPTANCE_CRITERIA.md
│   ├── DESIGN_SYSTEM.md
│   ├── REPOSITORY_STRUCTURE.md
│   ├── CHANGELOG.md
│   ├── openapi.yaml                  # generated, committed
│   ├── adr/
│   │   ├── 0001-double-entry-ledger.md
│   │   ├── 0002-integer-minor-units.md
│   │   ├── 0003-transaction-aggregate-and-reversal.md
│   │   ├── 0004-authentication-and-sessions.md
│   │   ├── 0005-django-monolith-and-celery.md
│   │   └── 0006-react-spa-and-generated-client.md
│   └── superpowers/
│       └── plans/
│           └── 2026-11-17-phase-1-foundation.md
├── backend/
│   ├── manage.py
│   ├── pyproject.toml
│   ├── pytest.ini
│   ├── mypy.ini
│   ├── Dockerfile
│   ├── config/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── wsgi.py
│   │   ├── urls.py
│   │   ├── celery.py
│   │   └── settings/
│   │       ├── base.py
│   │       ├── local.py
│   │       ├── test.py
│   │       └── production.py
│   ├── apps/
│   │   ├── common/
│   │   │   ├── money.py              # Money value object, parsing, quantization
│   │   │   ├── periods.py            # calendar/custom period resolution
│   │   │   ├── models.py             # UuidModel, TimestampedModel, ArchivedModel
│   │   │   ├── managers.py           # WorkspaceScopedManager
│   │   │   ├── permissions.py
│   │   │   ├── pagination.py
│   │   │   ├── errors.py
│   │   │   ├── idempotency.py
│   │   │   └── middleware.py
│   │   ├── identity/
│   │   │   ├── models.py             # User, UserProfile, UserSession, 2FA, recovery, social
│   │   │   ├── services/
│   │   │   │   ├── registration.py
│   │   │   │   ├── sessions.py
│   │   │   │   ├── two_factor.py
│   │   │   │   ├── passwords.py
│   │   │   │   └── google.py
│   │   │   ├── api/                 # serializers, views, urls
│   │   │   ├── migrations/
│   │   │   └── tests/
│   │   ├── workspaces/
│   │   ├── accounts/
│   │   ├── ledger/
│   │   │   ├── models.py             # LedgerAccount, JournalEntry, Posting
│   │   │   ├── services/
│   │   │   │   ├── posting.py        # the only posting entry point
│   │   │   │   ├── reversal.py
│   │   │   │   ├── accounts.py       # system account provisioning
│   │   │   │   └── reconciliation.py
│   │   │   ├── selectors.py          # balances, as-of sums
│   │   │   ├── management/commands/check_ledger.py
│   │   │   └── tests/
│   │   ├── categories/
│   │   ├── tags/
│   │   ├── transactions/
│   │   │   ├── models.py             # Transaction, Split, Audit, Transfer, OpeningBalance
│   │   │   ├── services/
│   │   │   │   ├── create.py
│   │   │   │   ├── update.py
│   │   │   │   ├── archive.py
│   │   │   │   ├── status.py
│   │   │   │   ├── splits.py
│   │   │   │   └── transfers.py
│   │   │   ├── selectors.py
│   │   │   ├── api/
│   │   │   └── tests/
│   │   ├── budgets/
│   │   ├── savings/
│   │   ├── debts/
│   │   ├── analytics/
│   │   │   ├── net_worth.py
│   │   │   ├── safe_to_spend.py
│   │   │   ├── daily_allowance.py
│   │   │   ├── emergency_fund.py
│   │   │   ├── snapshots.py
│   │   │   └── tests/
│   │   ├── reports/
│   │   ├── insights/
│   │   ├── notifications/
│   │   ├── datamanagement/
│   │   │   ├── importers/            # csv, xlsx
│   │   │   ├── duplicates.py
│   │   │   ├── exporters/
│   │   │   ├── backups.py
│   │   │   ├── restore.py
│   │   │   └── tests/
│   │   ├── privacy/
│   │   └── audit/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── factories/
│   │   ├── property/
│   │   ├── security/
│   │   └── performance/
│   └── scripts/
│       ├── seed_dev.py
│       └── check_openapi.sh
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── playwright.config.ts
│   ├── index.html
│   ├── Dockerfile
│   ├── public/
│   ├── e2e/
│   └── src/
│       ├── main.tsx
│       ├── app/
│       │   ├── router.tsx
│       │   ├── providers.tsx
│       │   ├── authenticated-layout.tsx
│       │   └── error-boundary.tsx
│       ├── components/
│       │   ├── money.tsx
│       │   ├── metric.tsx
│       │   ├── statement-sheet.tsx
│       │   ├── data-table.tsx
│       │   ├── progress-rule.tsx
│       │   ├── chart-frame.tsx
│       │   ├── period-picker.tsx
│       │   ├── split-editor.tsx
│       │   ├── confirm-dialog.tsx
│       │   ├── empty-state.tsx
│       │   └── ...
│       ├── features/
│       │   ├── auth/
│       │   ├── dashboard/
│       │   ├── accounts/
│       │   ├── transactions/
│       │   ├── transfers/
│       │   ├── budgets/
│       │   ├── savings/
│       │   ├── debts/
│       │   ├── net-worth/
│       │   ├── reports/
│       │   ├── emergency-fund/
│       │   ├── notifications/
│       │   ├── imports/
│       │   └── settings/
│       ├── lib/
│       │   ├── api/
│       │   │   ├── client.ts
│       │   │   ├── generated/        # generated from OpenAPI, never hand-edited
│       │   │   └── queries/
│       │   ├── money.ts
│       │   ├── dates.ts
│       │   ├── format.ts
│       │   └── query-keys.ts
│       ├── styles/
│       │   ├── tokens.css
│       │   ├── base.css
│       │   └── tailwind.css
│       └── test/
│           ├── setup.ts
│           └── msw/
├── infra/
│   ├── nginx/
│   ├── postgres/
│   │   └── init.sql
│   ├── backup/
│   │   ├── backup.sh
│   │   └── restore-drill.sh
│   └── terraform/                    # only if infrastructure is codified
└── scripts/
    ├── generate-api-client.sh
    └── verify-ledger.sh
```

---

## 1. Ownership boundaries

| Area | Owns | Must not |
|---|---|---|
| `apps/ledger` | Posting, balancing, reversal, reconciliation | Know about HTTP, budgets, goals |
| `apps/transactions` | Transaction lifecycle, splits, audit, transfer detail | Compute balances directly |
| `apps/accounts` | Account metadata and lifecycle | Write postings outside ledger services |
| `apps/budgets` | Budget plans, periods, rollover | Read today's category totals without period filters |
| `apps/analytics` | Derived figures (net worth, Safe-to-Spend, allowance) | Mutate financial records |
| `apps/reports` | Aggregation and export shapes | Redefine accounting meanings |
| `apps/datamanagement` | Import/export/backup/restore orchestration | Bypass transaction services on commit |
| `frontend/features/*` | UI composition per domain | Compute financial truth |
| `frontend/lib/money.ts` | Parse/format/display only | Convert currencies or decide sufficiency |

## 2. Naming conventions

- Python modules/functions `snake_case`; classes `PascalCase`; constants `UPPER_SNAKE`.
- Services are verbs: `create_transaction`, `post_entry`, `allocate_earmark`.
- Selectors are nouns: `account_balances`, `period_expense_totals`.
- React components `PascalCase.tsx`; hooks `useThing.ts`; query keys centralized in `lib/query-keys.ts`.
- API paths plural nouns, kebab-case for multiword (`/savings-goals/`, `/notification-preferences/`).
- Migration names describe intent (`0007_add_rollover_cap.py`), never `auto`.
- Branch names `feat/…`, `fix/…`, `chore/…`; commits Conventional Commits.

## 3. Generated and vendored code

| Path | Source | Rule |
|---|---|---|
| `docs/openapi.yaml` | drf-spectacular | Committed; CI fails if regeneration differs |
| `frontend/src/lib/api/generated/` | OpenAPI generator | Never hand-edited; regenerate in the same commit as API changes |
| Fonts in `frontend/public/fonts/` | Self-hosted, licensed | Include license files |

## 4. Root files

- `Makefile` wraps common commands (`make up`, `make test`, `make check`) so agents do not guess.
- `.env.example` lists every variable with a safe placeholder and a comment; no real values.
- `docker-compose.yml` includes `db`, `redis`, `api`, `worker`, `beat`, `web`, `mailpit`.
- CI uses the same Python/Node/Postgres majors as production, pinned in `.github/workflows/ci.yml`.
