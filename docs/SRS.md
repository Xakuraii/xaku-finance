# Software Requirements Specification — XakuFinance V1.0

**Version:** 1.0 (planning baseline)
**Date:** 2026-11-17
**Status:** Approved for implementation planning. No requirement here is implemented yet.
**Owner:** Product / Engineering

---

## 1. Purpose and scope

XakuFinance is a web-based personal finance management system for one individual per workspace. It
must let a person record financial reality accurately, plan spending and saving, understand their
position over time, and trust every number the product shows.

This SRS defines **V1.0**. It records requirement priority using MoSCoW:

- **M** — mandatory for V1.0 release. Release blocking.
- **S** — should have. Included if Phase 6 capacity allows; may slip to V1.1 with sign-off.
- **C** — could have. Explicitly deferred, listed so nobody assumes it exists.
- **W** — won't have in V1.0. Out of scope, documented to prevent scope creep.

Requirement IDs are stable and are referenced by tests, plans, and the changelog.
`docs/FEATURE_MATRIX.md` is the compact view; this document is normative.

### 1.1 Goals

1. Accurate, reconcilable records for multi-account, multi-currency personal finances.
2. Clear answers to: what do I have, what did I spend, what can I safely spend, am I on budget,
   am I making progress on savings and debt.
3. A financial history that is never silently rewritten.
4. A product that looks and behaves like trustworthy financial software, not an admin template.
5. An architecture that can grow to V2 without replacing the ledger.

### 1.2 Non-goals for V1.0

- Multi-user or shared workspaces, household collaboration, adviser access.
- Bank account aggregation / open banking sync.
- Receipt images or OCR.
- Investment portfolio performance tracking, tax filing, invoicing, payroll.
- Automated financial advice presented as authoritative.
- Native mobile apps (responsive web only).
- Cryptocurrency or commodity holdings as first-class assets.
- Payment initiation of any kind.

### 1.3 Actors

| Actor | Description | Capabilities |
|---|---|---|
| Visitor | Unauthenticated person | Register, log in, reset password, verify email |
| User | Authenticated owner of exactly one workspace | All financial features within their workspace |
| Background worker | Celery process | Imports, exports, backups, notifications, snapshots, rollovers |
| Operator | Trusted deployment staff | Run backups, restore, rotate secrets; **no** access to plaintext financial data through the app UI |

There is no administrator role that can browse user financial data. Django admin is restricted to
non-financial operational models and requires staff + 2FA in production.

---

## 2. Assumptions

Professional defaults adopted because the brief leaves them open. Each is reversible, but changing
one is a product decision, not an implementation detail.

| ID | Assumption |
|---|---|
| A-01 | One workspace per user, created automatically at registration. No invites, no membership table. |
| A-02 | Supported currencies at launch: USD and KHR. The schema supports any ISO-4217 code with a configured minor unit; enabling another currency is data, not code. |
| A-03 | KHR is stored with 2 decimal places for uniformity, though everyday riel amounts use none. |
| A-04 | Transactions are denominated in their account's currency. Cross-currency value movement happens only through transfers with an explicit rate. |
| A-05 | A workspace has one reporting currency (default USD). Changing it re-values reports; it never rewrites stored amounts. |
| A-06 | Workspace timezone defaults to the browser timezone at signup and is user-editable; all period boundaries use it. Storage is UTC. |
| A-07 | Calendar periods are the default. Custom periods are explicit, named, and non-overlapping within the same scope. |
| A-08 | Budgets are per category and per currency; one budget per category per period series. |
| A-09 | Rollover is opt-in per budget, positive-only, and optionally capped. |
| A-10 | Pending transactions require no approval workflow; they are a user-declared state and become completed manually or on a user-set date via a background job. |
| A-11 | Email is the identity anchor. Google sign-in links to an existing verified email; an unverified email match requires explicit linking after login. |
| A-12 | Notifications are in-app by default. Email requires a verified address and provider configuration. |
| A-13 | AI insights are optional, manually triggered, and disabled by default. The product is fully functional with AI off. |
| A-14 | Exports and backups are generated asynchronously and expire (exports 7 days, user backups 30 days, system backups per retention policy). |
| A-15 | Currency conversion for reporting uses transaction-date rates for flows and period-end rates for balances, unless the user pins a rate. The rate policy is shown wherever a converted total appears. |
| A-16 | "Household" or shared finances are modeled by using one workspace; the product does not attempt to split ownership. |
| A-17 | A savings account may back many goals; total earmarks may not exceed the account's available balance. |
| A-18 | Debt interest is recorded when charged or paid, not accrued daily, unless the user records an interest charge explicitly. |
| A-19 | Account deletion is a scheduled, reauthenticated, 14-day-delayed hard delete of eligible data, with backups aging out per policy. |
| A-20 | English UI at launch. Copy is written to be translatable; Khmer localization is a V1.1 candidate. |

---

## 3. Functional requirements

### 3.1 Identity, authentication, session security

| ID | Requirement | Pri |
|---|---|---|
| FR-AUTH-01 | Register with email + password; create the user, profile, and workspace atomically. | M |
| FR-AUTH-02 | Log in with email + password; generic failure message that does not reveal whether the email exists. | M |
| FR-AUTH-03 | Hash passwords with Argon2id. Minimum 12 characters; reject common/breached-pattern passwords. | M |
| FR-AUTH-04 | Verify email via a single-use, expiring, hashed token. Unverified users have limited access (no exports, no deletion). | M |
| FR-AUTH-05 | Reset password via single-use, expiring, hashed token; revoke all sessions after reset. | M |
| FR-AUTH-06 | Sign in with Google via ID-token verification; link by verified email; never auto-link an unverified email. | M |
| FR-AUTH-07 | Issue short-lived access JWT (15 min) and rotating refresh token (7 days) whose `jti` is tracked as a UserSession. | M |
| FR-AUTH-08 | Refresh rotation with reuse detection: reusing a rotated token revokes the whole session lineage. | M |
| FR-AUTH-09 | List active sessions with device, approximate location (from IP, coarse), created/last-used times; revoke one or all. | M |
| FR-AUTH-10 | Log out revokes the current session; "log out everywhere" revokes all. | M |
| FR-AUTH-11 | Optional TOTP 2FA with QR provisioning, 6-digit verification, replay protection, and encrypted secret at rest. | M |
| FR-AUTH-12 | Generate 10 single-use recovery codes at 2FA enrollment; store only Argon2 hashes; regenerate invalidates old codes. | M |
| FR-AUTH-13 | Require 2FA challenge on password login and on sensitive actions (disable 2FA, delete account, export all data). | M |
| FR-AUTH-14 | Progressive lockout and rate limiting on login, reset, and 2FA verification. | M |
| FR-AUTH-15 | Profile: display name, avatar URL, timezone, locale, reporting currency, week start. | M |
| FR-AUTH-16 | Passkeys / WebAuthn. | C |

### 3.2 Workspace

| ID | Requirement | Pri |
|---|---|---|
| FR-WS-01 | Exactly one workspace per user, created at registration, unique by owner. | M |
| FR-WS-02 | Workspace stores name, reporting currency, timezone, week start, fiscal settings, created timestamp. | M |
| FR-WS-03 | All financial entities carry a workspace FK; every read and write is scoped to the authenticated user's workspace. | M |
| FR-WS-04 | Multiple or collaborative workspaces. | W |

### 3.3 Dashboard

| ID | Requirement | Pri |
|---|---|---|
| FR-DASH-01 | Show total balance per currency and a converted consolidated total with the rate policy disclosed. | M |
| FR-DASH-02 | Show period income, period expenses, and net cash flow for the active financial period. | M |
| FR-DASH-03 | Show net worth with change versus previous period and a link to history. | M |
| FR-DASH-04 | Show budget overview, savings progress, Safe-to-Spend, and daily allowance with a "how this is calculated" disclosure. | M |
| FR-DASH-05 | Show recent transactions, income-vs-expense chart, spending-by-category chart, and period summary. | M |
| FR-DASH-06 | Let users show/hide and reorder widgets; persist per user; provide a reset-to-default action. | M |
| FR-DASH-07 | Drag-and-drop free-form grid layout. | C |
| FR-DASH-08 | Never display fabricated, sample, or estimated financial values in a real workspace. | M |

### 3.4 Accounts

| ID | Requirement | Pri |
|---|---|---|
| FR-ACC-01 | Create accounts of type checking, savings, cash, e-wallet, credit card, investment, or other. | M |
| FR-ACC-02 | Each account has name, type, currency, optional opening balance and date, description, spendable flag, status. | M |
| FR-ACC-03 | Record an opening balance as an opening-balance transaction backed by an equity posting, never income. | M |
| FR-ACC-04 | Default a new account to zero when no opening balance is provided. | M |
| FR-ACC-05 | Edit account metadata without altering posted history. Currency changes are blocked once postings exist. | M |
| FR-ACC-06 | Archive and restore accounts. Archiving requires zero balance or explicit acknowledgement; history is retained and reportable. | M |
| FR-ACC-07 | Block deleting an account that has postings; allow deletion only for a never-used account. | M |
| FR-ACC-08 | View account detail: balance, currency, transaction history, transfer history, and reconciliation status. | M |
| FR-ACC-09 | Designate accounts as spendable; savings/investment/credit accounts default to non-spendable. | M |
| FR-ACC-10 | Reorder accounts for display; archived accounts are hidden by default but reachable. | M |
| FR-ACC-11 | Show a per-account balance in its own currency and an optional converted figure with disclosure. | M |

### 3.5 Transactions

| ID | Requirement | Pri |
|---|---|---|
| FR-TXN-01 | Create income and expense transactions with title, amount, currency, account, category or splits, date, description, notes, tags, optional necessity, status. | M |
| FR-TXN-02 | Validate amount > 0, currency matches account currency, account is active, category belongs to the workspace. | M |
| FR-TXN-03 | Support status pending, completed, cancelled with the documented balance semantics. | M |
| FR-TXN-04 | Only completed transactions affect balances and reports. Pending may appear in projections with a clear label. | M |
| FR-TXN-05 | Multi-category splits; allocations must sum exactly to the transaction amount. | M |
| FR-TXN-06 | Edit a transaction atomically: append an audit revision, reverse the prior journal entry if posted, and post the new one. | M |
| FR-TXN-07 | Keep full immutable audit history: before, after, changed fields, actor, reason, timestamp, revision number. | M |
| FR-TXN-08 | Archive transactions instead of hard deleting; archived records remain visible via an explicit include-archived filter for audit, but never contribute to balances or financial totals. | M |
| FR-TXN-09 | Restore an archived transaction, re-posting it on its original date. | M |
| FR-TXN-10 | Tags: built-in University, Work, Family, Travel, Weekend, Shopping; custom tags; many per transaction; filter and analyze by tag. | M |
| FR-TXN-11 | Necessity classification is optional and independently filterable. | M |
| FR-TXN-12 | Full-text-ish search across title, description, notes, and merchant. | S |
| FR-TXN-13 | Bulk categorize or tag selected transactions. | S |
| FR-TXN-14 | Recurring transaction templates. | C |
| FR-TXN-15 | Receipt attachments, OCR, or image storage. | W |
| FR-TXN-16 | Delete a transaction permanently from the UI. | W |

### 3.6 Internal transfers

| ID | Requirement | Pri |
|---|---|---|
| FR-TRF-01 | Transfer between two accounts in the same workspace with source, destination, amount, date, optional fee, notes. | M |
| FR-TRF-02 | Same-currency transfer moves exactly the amount; source decreases and destination increases by equal value; no income or expense. | M |
| FR-TRF-03 | Cross-currency transfer requires an explicit rate and records source amount, destination amount, rate, and residual. | M |
| FR-TRF-04 | Fees post to an expense category and reduce the source account; the fee is not part of the transfer principal. | M |
| FR-TRF-05 | Reject transfers where source = destination, source is archived, destination is archived, or the source lacks sufficient completed balance unless the account permits negative balance. | M |
| FR-TRF-06 | Transfers are atomic: a failed transfer leaves no postings and no audit artifacts. | M |
| FR-TRF-07 | Transfer history filterable by account and date, visible from both accounts. | M |
| FR-TRF-08 | Idempotent creation via `Idempotency-Key`, so a double-submit cannot move money twice. | M |
| FR-TRF-09 | Link a transfer to a savings goal contribution in one action. | M |
| FR-TRF-10 | Scheduled or recurring transfers. | C |

### 3.7 Budgets and financial periods

| ID | Requirement | Pri |
|---|---|---|
| FR-BUD-01 | Create category budgets for monthly, weekly, or custom repeating periods, with base amount and currency. | M |
| FR-BUD-02 | Track progress: base, rollover in, spent, remaining, percent used, projected overspend. | M |
| FR-BUD-03 | Positive-only rollover, opt-in per budget, with an optional cap and a visible rollover source. | M |
| FR-BUD-04 | Overspending never produces negative rollover; it is shown as a distinct over-budget state. | M |
| FR-BUD-05 | Configurable warning thresholds per budget (default 80% and 100%) feeding notifications. | M |
| FR-BUD-06 | Budget history by period with comparison to prior periods. | M |
| FR-BUD-07 | Mark a budget as flexible or fixed/reserved; only flexible budgets fund the daily allowance. | M |
| FR-BUD-08 | Budgets use split allocations, not whole-transaction categories, for spending totals. | M |
| FR-BUD-09 | Edit a budget prospectively; closed periods are never retroactively recalculated. | M |
| FR-BUD-10 | Custom financial periods with name, start, end, and reuse; calendar periods by default. | M |
| FR-BUD-11 | Enforce non-overlapping custom periods per budget series. | M |
| FR-BUD-12 | Rollover between custom periods of different lengths is prorated. | C |
| FR-PER-01 | All reporting endpoints accept a period selector: calendar month, week, year, or custom range. | M |
| FR-PER-02 | Boundaries are computed in the workspace timezone and returned with the response. | M |
| FR-PER-03 | Reports state the exact date range and timezone used. | M |

### 3.8 Savings goals

| ID | Requirement | Pri |
|---|---|---|
| FR-SAV-01 | Create goals with name, target amount, currency, target date, optional linked account, notes. | M |
| FR-SAV-02 | Record contributions as real money movements: transfer into a savings account, earmark of existing savings, adjustment, or withdrawal. | M |
| FR-SAV-03 | Progress reflects contributions, capped reporting never exceeds target unless over-funded (shown explicitly). | M |
| FR-SAV-04 | Multiple goals may share one savings account within available balance. | M |
| FR-SAV-05 | Reject earmarks that exceed the account's unallocated available balance. | M |
| FR-SAV-06 | Earmarks never increase account balance, total assets, or net worth. | M |
| FR-SAV-07 | Show contribution history, remaining amount, monthly required contribution, and estimated completion date at the current pace. | M |
| FR-SAV-08 | Edit and archive goals; archiving releases earmarks without moving money. | M |
| FR-SAV-09 | Auto-suggest a contribution schedule from target date and remaining amount. | S |
| FR-SAV-10 | One-click "move to savings" that creates the transfer and contribution atomically. | M |

### 3.9 Debts and liabilities

| ID | Requirement | Pri |
|---|---|---|
| FR-DEBT-01 | Create a liability with name, type, currency, original principal, optional interest rate, due day, lender, notes. | M |
| FR-DEBT-02 | Allow recording an initial disbursement that credits an account and creates the liability. | M |
| FR-DEBT-03 | Outstanding principal derives from ledger postings, not a hand-edited number. | M |
| FR-DEBT-04 | Record repayments split into principal, interest, and fees, linked to the paying account transaction. | M |
| FR-DEBT-05 | Principal reduces the liability; interest and fees post as expenses. | M |
| FR-DEBT-06 | Repayment history and progress; payoff estimate at the current pace. | M |
| FR-DEBT-07 | Reject principal repayment above outstanding principal. | M |
| FR-DEBT-08 | Archive and restore liabilities; paid-off liabilities remain visible with zero outstanding. | M |
| FR-DEBT-09 | Amortization schedules and interest accrual automation. | C |
| FR-DEBT-10 | Model a credit card as a liability instead of only an account. | S |

### 3.10 Net worth

| ID | Requirement | Pri |
|---|---|---|
| FR-NW-01 | Compute net worth = assets − liabilities in the reporting currency at a stated date. | M |
| FR-NW-02 | Provide account-level asset breakdown and liability breakdown. | M |
| FR-NW-03 | Historical net worth derived from ledger postings as of each date; never from today's balances. | M |
| FR-NW-04 | Compare periods: month over month, year over year, custom range. | M |
| FR-NW-05 | Store immutable snapshots for chart performance, each tagged with rate set and ledger checksum. | M |
| FR-NW-06 | Never count savings earmarks or goal progress as additional assets. | M |
| FR-NW-07 | Net worth excluding a chosen account or liability. | C |

### 3.11 Safe-to-Spend and daily allowance

| ID | Requirement | Pri |
|---|---|---|
| FR-STS-01 | Compute Safe-to-Spend from spendable accounts only. | M |
| FR-STS-02 | Subtract pending outflows in spendable accounts, reserved upcoming obligations within the horizon, and planned savings contributions. | M |
| FR-STS-03 | Return an itemized breakdown: starting available balance, each deduction, resulting figure, and horizon. | M |
| FR-STS-04 | Exclude non-spendable accounts by default; allow explicit opt-in per account. | M |
| FR-STS-05 | Floor the result at zero for display while exposing the raw signed value. | M |
| FR-DSA-01 | Daily allowance = remaining flexible budget ÷ remaining days in the active period. | M |
| FR-DSA-02 | Exclude fixed/reserved budgets and reserved obligations from the numerator. | M |
| FR-DSA-03 | When remaining is ≤ 0, return 0 with an over-budget explanation; never invent a positive allowance. | M |
| FR-DSA-04 | Use calendar days remaining inclusive of today, in the workspace timezone. | M |
| FR-DSA-05 | Allow the user to choose which budgets are flexible. | M |

### 3.12 Emergency fund

| ID | Requirement | Pri |
|---|---|---|
| FR-EMG-01 | Estimate essential monthly expenses from essential-classified spending over a chosen lookback (default 3 months), excluding transfers and one-offs the user excludes. | M |
| FR-EMG-02 | Let the user override the essential monthly expense figure and see the source. | M |
| FR-EMG-03 | Support 3/6/12-month coverage targets plus custom months. | M |
| FR-EMG-04 | Track current emergency savings from a designated account or goal; show remaining target and progress. | M |
| FR-EMG-05 | Plan a regular contribution and show months/days to completion. | M |
| FR-EMG-06 | Warn when the emergency fund account is also earmarked to other goals beyond available balance. | M |

### 3.13 Reports and analytics

| ID | Requirement | Pri |
|---|---|---|
| FR-RPT-01 | Income report by period, account, category, and tag. | M |
| FR-RPT-02 | Expense report by period, account, category (split-aware), tag, necessity, and merchant. | M |
| FR-RPT-03 | Category breakdown with share of total and period comparison. | M |
| FR-RPT-04 | Spending trend over time with selectable granularity. | M |
| FR-RPT-05 | Budget performance report per period. | M |
| FR-RPT-06 | Savings report: contributions, goal progress, pace. | M |
| FR-RPT-07 | Debt report: outstanding, principal paid, interest paid. | M |
| FR-RPT-08 | Net worth report with historical series. | M |
| FR-RPT-09 | Tag analytics: totals, trends, co-occurrence. | M |
| FR-RPT-10 | Export any report to CSV and XLSX with the same filters and totals as the screen. | M |
| FR-RPT-11 | Every chart has an accessible table equivalent and a textual summary. | M |
| FR-RPT-12 | Report figures must reconcile with ledger sums for the same period (tested invariant). | M |

### 3.14 Insights

| ID | Requirement | Pri |
|---|---|---|
| FR-INS-01 | On-demand analysis of spending patterns, budget performance, income vs expense, savings progress, unusual spending, and recommendations. | S |
| FR-INS-02 | Insights receive a server-computed, versioned summary; the model may not generate new numbers. | M |
| FR-INS-03 | Every insight shows the period, the data inputs, and a "not financial advice" notice. | S |
| FR-INS-04 | Insights are optional, disabled by default, and never block core features. | M |
| FR-INS-05 | Persist the exact input summary and model metadata used for each generated insight. | S |
| FR-INS-06 | Continuous AI chat or autonomous financial agents. | W |

### 3.15 Notifications and reminders

| ID | Requirement | Pri |
|---|---|---|
| FR-NOT-01 | In-app notification center with read/unread state. | M |
| FR-NOT-02 | Email delivery for opted-in categories with a verified address. | M |
| FR-NOT-03 | Budget threshold warnings at configurable percentages, deduplicated per period. | M |
| FR-NOT-04 | Bill and recurring obligation reminders before due dates. | M |
| FR-NOT-05 | Savings goal milestones and pace warnings. | M |
| FR-NOT-06 | Security notifications (new device, password change, 2FA change, deletion request) that cannot be disabled. | M |
| FR-NOT-07 | Quiet hours and a daily/weekly digest schedule in the workspace timezone. | M |
| FR-NOT-08 | Per-category channel preferences; security category locked on. | M |
| FR-NOT-09 | Push notifications / web push. | C |

### 3.16 Import and export

| ID | Requirement | Pri |
|---|---|---|
| FR-DATA-01 | Import transactions from CSV and XLSX with a guided column mapping step. | M |
| FR-DATA-02 | Validate every row before commit: required fields, parseable dates, valid amounts, known currency, existing account, category resolution. | M |
| FR-DATA-03 | Detect exact and potential duplicates using date proximity, amount, currency, account, normalized description, and merchant. | M |
| FR-DATA-04 | Present duplicates with reasons and confidence; the user decides import/skip per group. Never auto-discard silently. | M |
| FR-DATA-05 | Commit only approved rows, atomically per job, with an imported-row audit trail. | M |
| FR-DATA-06 | Allow cancelling a pending import job without side effects. | M |
| FR-DATA-07 | Export transactions, accounts, budgets, goals, debts, reports, and a complete data archive as CSV/XLSX where tabular, plus JSON for the archive. | M |
| FR-DATA-08 | Exports are generated asynchronously, delivered via a short-lived signed URL, and expire. | M |
| FR-DATA-09 | Validate a full archive before restoration and refuse partial or corrupt restores. | M |
| FR-DATA-10 | Restore only into an empty workspace, or into a new workspace created for the restore. | M |
| FR-DATA-11 | Excel formulas, images, or macro-enabled formats. | W |

### 3.17 Privacy, deletion, backups

| ID | Requirement | Pri |
|---|---|---|
| FR-PRV-01 | Self-service export of all personal data (machine-readable). | M |
| FR-PRV-02 | Self-service account deletion with explicit confirmation, reauthentication, and a plain-language consequence list. | M |
| FR-PRV-03 | 14-day grace period with cancellation; after that, eligible data is hard-deleted and backup expiry is stated truthfully. | M |
| FR-PRV-04 | Show active sessions and privacy/data-retention information in settings. | M |
| FR-PRV-05 | Every deletion request and completion is audit-logged without retaining the deleted financial content. | M |
| FR-PRV-06 | Automatic encrypted server backups with integrity verification, retention, and failure alerting. | M |
| FR-PRV-07 | Manual user backup download; restore tested, not merely enabled. | M |
| FR-PRV-08 | Never claim permanent deletion while backups containing the data remain; disclose the retention window. | M |

---

## 4. Non-functional requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-REL-01 | Financial operations are atomic; a forced mid-operation failure leaves no partial state. | 100% of multi-write paths tested |
| NFR-REL-02 | Ledger reconciles to zero per entry and to account balances at all times. | Nightly check + CI invariant suite |
| NFR-ACC-01 | Money math is decimal-safe and reproducible. | Zero float usage; property tests |
| NFR-ACC-02 | Report totals equal ledger sums for the same period and filters. | Automated reconciliation test per report |
| NFR-SEC-01 | All financial endpoints authorize against workspace ownership. | Cross-tenant test per endpoint |
| NFR-SEC-02 | Secrets never in source, logs, error responses, or exports. | Secret scan in CI |
| NFR-SEC-03 | Sensitive actions require reauthentication and are audit-logged. | Tested |
| NFR-PERF-01 | p95 API latency < 400 ms for list/detail at 50k transactions per workspace. | Load test at Phase 6 |
| NFR-PERF-02 | Dashboard first meaningful render < 2.5 s on a mid-tier laptop, warm API. | Lighthouse + manual |
| NFR-PERF-03 | Lists paginate; no unbounded queries. | Code review + query-count tests |
| NFR-A11Y-01 | WCAG 2.2 AA practical compliance: contrast, focus, labels, keyboard paths, chart alternatives. | axe checks + manual audit |
| NFR-UX-01 | Common actions (add expense, transfer, contribute) reachable in ≤ 2 interactions from anywhere. | UX review |
| NFR-UX-02 | Light and dark mode both complete, with no illegible token combinations. | Visual review |
| NFR-RESP-01 | Usable at 360 px, 768 px, 1024 px, 1440 px, 1920 px. | Playwright viewport matrix |
| NFR-MAINT-01 | Domain logic lives in services, not views/serializers; no duplicated money rules in the frontend. | Review gate |
| NFR-SCALE-01 | Schema and APIs can add features without destructive rewrites; partitions/indexes planned for high-volume tables. | Design review |
| NFR-PORT-01 | Config via environment; no environment logic baked into code. | 12-factor review |
| NFR-OBS-01 | Structured logs, request ids, error tracking, backup/import/export job status visible. | Phase 6 |

---

## 5. Technical constraints

1. Backend: Python 3.12+, Django 5.2 LTS, DRF, drf-spectacular, PostgreSQL 16+, Redis 7+, Celery.
2. Frontend: React + TypeScript + Vite; server state via TanStack Query; forms via RHF + Zod.
3. Authentication: JWT access + rotating refresh; no server-side session cookies for API auth other
   than the refresh cookie, which is HttpOnly, Secure, SameSite=Lax, and path-scoped.
4. All money in integer minor units in the database and `Decimal` in Python. `FloatField` is banned
   for money and rates.
5. UTC timestamps (`TIMESTAMPTZ`); financial dates are `DATE` interpreted in the workspace timezone.
6. OpenAPI is generated from code and validated in CI; the frontend client is generated from it.
7. Migrations are the only schema change mechanism; no manual production DDL.
8. Background jobs must be idempotent and safe to retry.
9. No feature may require a third-party paid service to keep core finance working. Google sign-in,
   email, and AI degrade gracefully when unconfigured.

---

## 6. Financial accounting constraints

These are expanded in `docs/ACCOUNTING_RULES.md` and are release-blocking.

1. Double entry: every journal entry's postings sum to zero per currency.
2. Transfers, opening balances, and savings earmarks are never income or expense.
3. Only completed transactions post; pending and cancelled never affect balances.
4. Splits sum exactly to the parent transaction amount.
5. Currencies are never added without an explicit conversion and disclosed rate.
6. Posted entries are immutable; corrections are reversals; edits are audited.
7. Historical reports use the ledger state at that date, not today's balances.
8. Savings goal allocations never create assets and never exceed available funds.
9. Debt principal repayment reduces liabilities; interest and fees are expenses.
10. Balance = sum of postings, always; any cached aggregate must be provably rebuildable.
11. Every financial movement is traceable from UI → transaction → journal entry → postings.

---

## 7. Constraints, contradictions, and resolved gaps

The brief is largely coherent. These points were ambiguous or missing and are resolved here. Each
resolution is a documented assumption, not a silent interpretation.

| ID | Issue in brief | Resolution |
|---|---|---|
| G-01 | Entity list includes both `Transaction` and `Transfer`, and `OpeningBalance`, which could imply separate parallel records. | One `Transaction` aggregate with type-specific 1:1 detail (`Transfer`, `OpeningBalance`, `DebtRepayment`). Single feed, single audit chain, single ledger link. |
| G-02 | "Current balance" is listed as an account field, but balances must reconcile with the ledger. | Balance is derived, never stored. A read projection may cache it, guarded by a reconciliation command and checksum. |
| G-03 | Safe-to-Spend mentions "upcoming bills" and "reserved obligations" but the entity list has no bill/obligation model. | Added `RecurringObligation` (bills and reserved commitments) with amount, cadence, next due date, and reserved flag. |
| G-04 | Notifications require schedules and quiet hours but no schedule entity is listed. | Preferences carry quiet hours and digest cadence; `NotificationDelivery` records attempts. |
| G-05 | Budget warnings need thresholds; the entity list has no threshold field. | Thresholds live on `Budget` (`warn_at_percent`, `alert_at_percent`) and are overridable in preferences. |
| G-06 | "Net worth snapshots" could be mistaken for the source of truth. | Ledger is authoritative; snapshots are a cache with `computed_from`, `rate_set_hash`, and ledger checksum. |
| G-07 | Savings "allocations" could be read as new money. | Earmarks are claims on existing balance. A DB/service invariant caps total earmarks per account at available balance. |
| G-08 | Transfers between different currencies must not create or destroy money, but rates always leave a residual. | Each currency balances separately. Residual posts to an FX gain/loss ledger account and is reported, never hidden. |
| G-09 | Pending transactions are said not to affect balances, but Safe-to-Spend must consider them. | Balances exclude pending entirely; Safe-to-Spend subtracts pending outflows as a projection, labeled as such. |
| G-10 | Account archiving is required, account deletion is implied by privacy rules. | Archive for anything with history; hard delete only for an account with no postings. Deletion workflow handles user data. |
| G-11 | "Custom budget periods" and "custom financial periods" are separate features that could diverge. | Custom periods are one definition, used by both budgets and reports. Budget series may reference a custom period. |
| G-12 | Interest "must be recorded separately" but no accrual model is defined. | `DebtInterestRecord` supports explicit charges; accrual automation is deferred (C). Interest is expensed when charged/paid. |
| G-13 | Email verification "where applicable" is vague. | Required for email notifications, exports, and deletion; not required to start tracking finances. |
| G-14 | The brief asks for Google auth but not account linking rules. | Verified-email linking only; otherwise explicit link after login. No silent account merging. |
| G-15 | Deletion must be secure, but backups create unavoidable retention. | 14-day grace, hard delete of live data, backups expire within the disclosed window, and the UI states exactly that. |
| G-16 | AI insights are "optional" but no failure mode is defined. | Core functionality has zero AI dependency; insights are a separate module with the feature flag off by default. |

---

## 8. Acceptance

V1.0 is accepted only when every **M** requirement has a passing automated test or a documented manual
verification, and the checklist in `docs/ACCEPTANCE_CRITERIA.md` is complete. Requirements marked
**S** may be deferred to V1.1 with an explicit written decision recorded in `docs/CHANGELOG.md`.
