# Changelog — XakuFinance

All notable changes to this project are recorded here. Format loosely follows Keep a Changelog.
**Nothing in this file may claim a feature is implemented when it is not.**

## [Unreleased]

### Added
- 2026-11-18 — Phase 3 Financial Planning:
  - Savings Goals & Earmarks: Multi-strategy savings (`linked_account` and `earmark`), row-locked allocation capacity constraints ($\sum \text{allocated} \le \text{account available balance}$), 4 contribution kinds (`transfer_in`, `earmark`, `adjustment`, `withdrawal`), goal archiving with automatic earmark release, timeline projections, REST API at `/api/v1/savings-goals/`, and interactive UI (`SavingsGoalCard`, `CreateGoalDialog`, `ContributeDialog`).
  - Debts & Liabilities: Dedicated 1:1 `LedgerAccount` per liability, double-entry disbursement (asset debit, liability credit), split repayments (principal debit to liability, interest/fee debits to expense, credit to asset), strictly ledger-derived outstanding balance (`-SUM(postings)`), accrued interest recording, payoff amortization projections, REST API at `/api/v1/debts/`, and interactive UI (`DebtCard`, `CreateDebtDialog`, `RepaymentDialog`, `DebtProjectionCard`).
  - Emergency Fund Planner: Essential spending analytics over 90-day lookback, manual override baseline with source disclosure (`computed` vs `override`), coverage targets (3/6/12 months), designated source linking (account or goal), earmark conflict detection when backing accounts are earmarked to other goals, REST API at `/api/v1/emergency-fund/`, and interactive UI (`EmergencyFundCard`, `EmergencyConfigDialog`, `EmergencyProjectionCard`).
  - Performance & Verification: Query budgets verified ($O(1)$ queries for savings, debts, and emergency fund), zero ledger drift verified via `check_ledger --fail-on-drift` across all workspaces, OpenAPI 3.1 validation clean, test suite expanded to 237 backend pytest tests (100% pass) and 30 frontend vitest tests (100% pass), and production frontend build verified.
- 2026-11-18 — Phase 2 Core Financial Management:
  - Internal account transfers with same-currency and cross-currency FX clearing legs (`Transfer` model, `create_transfer`, `archive_transfer`, `/api/v1/transfers/`, and `TransferDialog`).
  - 2-level category hierarchy with kind matching and active transaction reassignment guard (`Category.parent`, `CategorySerializer`, `/api/v1/categories/`).
  - Tag & spending necessity analytics breakdown (`GET /api/v1/tags/analytics/`, `SpendingByTagCard`).
  - Budget management & positive-only rollover engine (`Budget`, `BudgetPeriod`, `BudgetRollover`, `calculate_budget_period_spending`, `close_budget_period`, `/api/v1/budgets/`, `BudgetCard`, `BudgetList`).
  - Multi-step CSV import engine with column mapping and duplicate scoring review (`ImportJob`, `ImportRecord`, `DuplicateCandidate`, `stage_csv_import`, `detect_duplicates`, `commit_import_job`, `/api/v1/imports/`, `ImportWizardDialog`).
  - Query count budgets: transfers list in 1 query; categories tree in 4 queries; tags analytics in 4 queries.
  - Test coverage expanded to 204 backend pytest tests (100%) and 20 frontend Vitest tests (100%) with 0 ledger drift.

- 2026-11-17 — Planning package established:
  - `README.md`, `GLOSSARY.md`, `.AGENT.md`
  - `docs/SRS.md`, `docs/FEATURE_MATRIX.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md`,
    `docs/ACCOUNTING_RULES.md`, `docs/API_SPECIFICATION.md`, `docs/SECURITY.md`, `docs/TESTING.md`,
    `docs/ROADMAP.md`, `docs/RISKS.md`, `docs/ACCEPTANCE_CRITERIA.md`, `docs/DESIGN_SYSTEM.md`,
    `docs/REPOSITORY_STRUCTURE.md`
  - `docs/adr/0001`–`0006`
  - `.agent/` operating context, standards, workflows, and checklists
  - Phase 1 implementation plan in `docs/superpowers/plans/`
- 2026-11-17 — Backend scaffold (Phase 1, Task 1):
  - Django 5.2 project with split settings (`base`, `local`, `test`, `production`)
  - `GET /health/live` and `GET /health/ready`, request-id middleware, stable error envelope
  - `pyproject.toml` with pytest, ruff, and mypy configuration
  - `docker-compose.yml` (PostgreSQL 16 on host port 55432, Redis on 56379), `Makefile`,
    CI workflow, `.env.example`, `.gitignore`, `.dockerignore`
  - Generated and validated `docs/openapi.yaml`
- 2026-11-17 — Identity, currency reference data, and registration (Phase 1, Task 4):
  - `User` (email login, Argon2id), `UserProfile`, `DashboardLayout`, `Workspace` models
  - `ref_currency` with USD and KHR seeded by data migration
  - Atomic `register_user` service and `POST /api/v1/auth/register/`
  - One workspace per user enforced by a unique `owner`; profile and workspace created in the same
    transaction
- 2026-11-17 — Rotating refresh sessions and revocation (Phase 1, Task 5):
  - `UserSession` ledger of refresh lineages with hashed IPs and device metadata
  - `POST /auth/login/`, `/auth/refresh/`, `/auth/logout/`, `/auth/logout-all/`,
    `GET /auth/sessions/`, and `DELETE /auth/sessions/{id}/`
  - Refresh tokens rotate on every use; replaying an old token revokes the family
  - Refresh cookie is `HttpOnly`, `Secure`, `SameSite=Lax`, scoped to `/api/v1/auth/`
  - Progressive login lockout: 5 failures in 15 minutes, escalating to 1/5/15/60 minutes
- 2026-11-17 — Email verification, password reset, and Google sign-in (Phase 1, Task 6):
  - `IdentityToken` stores SHA-256 hashes only; 24-hour verification and 1-hour reset tokens, both
    single use, with new tokens superseding unused predecessors
  - `POST /auth/verify-email/`, `/auth/verify-email/resend/`, `/auth/password/forgot/`,
    `/auth/password/reset/`, and `/auth/google/`
  - Registration now emails a verification link; password reset revokes every session and never
    reveals whether an account exists
  - `SocialIdentity` links Google subjects; existing password accounts require explicit linking and
    unverified Google emails are refused
  - Per-email and per-IP throttles on password reset, plus throttles on login, registration, and
    verification resends
  - Plain-text email templates in `backend/apps/identity/templates/identity/emails/`; console backend
    locally, Mailpit service in Compose for SMTP testing
- 2026-11-17 — Optional TOTP 2FA and recovery codes (Phase 1, Task 7):
  - `TwoFactorConfig` stores a 160-bit TOTP secret only as versioned Fernet ciphertext;
    `MFAChallenge` is a hashed, 5-minute, single-use token between password success and a code
  - `POST /auth/2fa/setup/`, `/auth/2fa/confirm/`, `/auth/2fa/verify/`, `/auth/2fa/disable/`, and
    `/auth/2fa/recovery-codes/`, plus `POST /auth/reauth/`
  - Login and Google sign-in return `202 {mfa_required, mfa_token, methods}` when 2FA is enabled
  - Replay protection records the last accepted time-step; five failures in ten minutes lock
    verification for fifteen minutes
  - Ten single-use recovery codes, Argon2id-hashed, returned once and invalidated as a batch on
    regeneration; disabling 2FA emails a security notification
  - Enrollment and recovery-code regeneration require a password reauthentication (`reauth_at`)
    inside a ten-minute window

- 2026-11-18 — Workspace Scoping & Multi-Tenancy (Phase 1, Task 8):
  - `WorkspaceScopedModel` and `WorkspaceScopedManager` auto-filtering queries by workspace.
  - `IsWorkspaceMember` DRF permission class strictly verifying access boundaries.
  - Cross-workspace isolation integration tests ensuring zero data leakage across workspaces.
- 2026-11-18 — Double-Entry Engine & PostgreSQL Triggers (Phase 1, Tasks 9–10):
  - System ledger accounts (Equity, Opening Balances, Retained Earnings, Category Ledger Accounts).
  - PostgreSQL trigger `trg_assert_journal_entry_balanced` asserting sum(amount) == 0 per currency.
  - PostgreSQL trigger `trg_prevent_posting_update_delete` locking journal entries and postings into immutable records.
  - `post_entry`, `reverse_entry`, and `reconcile_workspace` services.
  - Management command `check_ledger --fail-on-drift` validating zero accounting drift.
- 2026-11-18 — Transactions, Splits & Audit History (Phase 1, Task 11):
  - `Transaction`, `TransactionSplit`, `TransactionTag`, and `TaggedItem` models.
  - Dynamic multi-category splitting with validation that split totals equal transaction amount.
  - Status lifecycle (`pending`, `completed`, `cancelled`) ensuring only completed transactions hit ledger postings.
  - `TransactionAudit` recording revisions, actor, timestamp, reason, and previous JSON snapshot.
- 2026-11-18 — Account Lifecycle Services (Phase 1, Task 12):
  - `create_account`, `archive_account`, `restore_account`, and `change_currency` services.
  - Non-zero balance acknowledgement guard on archiving.
  - Currency immutability once ledger postings exist.
  - Dynamic `account_balance` selector deriving balances directly from ledger postings.
- 2026-11-18 — REST API & Idempotency (Phase 1, Task 13):
  - REST ViewSets for Accounts, Transactions, Categories, and Tags.
  - Cursor-based pagination (`(created_at, id)`).
  - RFC 7807 structured error envelope across all endpoints.
  - Redis-backed `Idempotency-Key` deduplication on write operations.
  - Auto-generated OpenAPI 3.1 specification validated via `spectacular`.
- 2026-11-18 — Frontend Architecture & UI Features (Phase 1, Tasks 14–15):
  - React 19 + TypeScript 5.8 + Vite + Tailwind CSS v4 setup adhering to `docs/DESIGN_SYSTEM.md`.
  - Obsidian (`#0F1216`) and Binance Gold (`#F0B90B`) tokens.
  - Typed Money library (`src/lib/money.ts`) with integer minor units arithmetic.
  - API client with automatic 401 token refresh queue.
  - UI pages and dialogs: Login, Register, Accounts listing, Statement drawer, Account creation, Archive dialog, Transactions table, Transaction creation drawer, Dynamic split editor with live balancing, and Audit drawer.
- 2026-11-18 — Phase 1 Hardening & Exit Verification (Phase 1, Task 16):
  - `seed_workspace` management command.
  - Query count regression budget: transaction listing optimized to 3 queries (select_related + in-memory tag prefetch).
  - Comprehensive exit review artifact created at `docs/PHASE_1_REPORT.md`.

### Decisions
- Double-entry ledger with system accounts is the accounting foundation.
- Money is stored as integer minor units; no floats anywhere.
- One transaction aggregate with type-specific detail tables; edits reverse and repost.
- Single workspace per user; no collaboration in V1.
- Golden `#F0B90B` brand accent, dark-first, with a text-safe gold for light mode.
- Transactions are account-currency only; FX exists only on transfers.
- Receipt attachments/OCR, multi-workspace, bank sync, and AI chat are out of V1.

### Known limitations
- Phase 1 Foundation is fully shipped, tested, and verified.
- Internal account transfers and foreign exchange clearing are scheduled for Phase 2.1.
- Budget management and positive rollover calculations are scheduled for Phase 2.2.
- Safe-to-Spend and Daily Spending Allowance calculations are scheduled for Phase 2.3.
- Analytics, financial reports, and CSV/JSON data import/export are scheduled for Phase 2.4 and 2.5.

---

## Template for future entries

```
## [Phase X.Y] — YYYY-MM-DD
### Added
- 2026-11-18 — Phase 2 Core Financial Management:
  - Internal account transfers with same-currency and cross-currency FX clearing legs (`Transfer` model, `create_transfer`, `archive_transfer`, `/api/v1/transfers/`, and `TransferDialog`).
  - 2-level category hierarchy with kind matching and active transaction reassignment guard (`Category.parent`, `CategorySerializer`, `/api/v1/categories/`).
  - Tag & spending necessity analytics breakdown (`GET /api/v1/tags/analytics/`, `SpendingByTagCard`).
  - Budget management & positive-only rollover engine (`Budget`, `BudgetPeriod`, `BudgetRollover`, `calculate_budget_period_spending`, `close_budget_period`, `/api/v1/budgets/`, `BudgetCard`, `BudgetList`).
  - Multi-step CSV import engine with column mapping and duplicate scoring review (`ImportJob`, `ImportRecord`, `DuplicateCandidate`, `stage_csv_import`, `detect_duplicates`, `commit_import_job`, `/api/v1/imports/`, `ImportWizardDialog`).
  - Query count budgets: transfers list in 1 query; categories tree in 4 queries; tags analytics in 4 queries.
  - Test coverage expanded to 204 backend pytest tests (100%) and 20 frontend Vitest tests (100%) with 0 ledger drift.

- <user-visible capability> (<requirement IDs>)
### Changed
- <behavior change and why>
### Fixed
- <defect> (<test that now covers it>)
### Security
- <control added or finding resolved>
### Database
- <migration name and effect>
### Known limitations
- <what remains, with owner/phase>
```
