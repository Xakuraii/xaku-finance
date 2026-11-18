# Phase 2 Core Financial Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase 2 Core Financial Management: same-currency and cross-currency internal transfers with FX clearing, two-level category hierarchies with tag & necessity analytics, budget management with positive-only rollover, and a multi-step CSV import engine with duplicate review.

**Architecture:** Django 5.2 + DRF monolith extending the Phase 1 immutable double-entry ledger. All transfers post balanced debits and credits across accounts or FX clearing ledger accounts. Budgets calculate split-aware spending dynamically with an immutable closed-period rollover engine. React 19 frontend features obsidian/gold components matching `docs/DESIGN_SYSTEM.md`.

**Tech Stack:** Python 3.12, Django 5.2 LTS, DRF, PostgreSQL 16, Redis, Celery, React 19, TypeScript 5.8, Tailwind CSS v4, TanStack Query v5, Radix UI, Vitest, pytest.

**Spec:** `docs/SRS.md` (FR-TRF, FR-CAT, FR-BDG, FR-IMP), `docs/ACCOUNTING_RULES.md`, `docs/DATABASE.md`, `docs/API_SPECIFICATION.md`.

---

## Global Constraints

- Python 3.12+; Django 5.2 LTS; PostgreSQL 16 (no SQLite, including in tests).
- Money: integer minor units (`amount_minor: int`) + currency code (`currency: str`). Zero floats anywhere.
- API amounts are decimal strings in requests, returned as decimal strings + minor units in responses.
- Balances are derived dynamically from ledger postings; no mutable `balance` column.
- Every journal entry must sum to zero per currency. Posted entries are immutable.
- Same-currency transfers never create income or expense (asset to asset movement only, with optional transfer fee expense).
- Cross-currency transfers balance per currency using dedicated `fx_clearing:<CURRENCY>` system accounts and an explicit conversion fee / spread expense.
- Budgets implement positive-only rollover: unused budget rolls over; overspending NEVER produces negative rollover.
- Every row is scoped by `workspace_id`; cross-workspace queries return 404.
- All multi-write paths run inside `transaction.atomic()` with deterministic `select_for_update` row ordering to avoid deadlocks.

---

## Review Focus

1. **Cross-currency transfer with spread and exchange rate differences.** Expected: Each currency's postings independently sum to zero; conversion difference is posted to the conversion fee expense account; 0 drift.
2. **Transfer between the same account, or involving archived accounts.** Expected: Rejected with domain validation errors; no journal entry created.
3. **Budget rollover when actual spending exceeds the allocated amount.** Expected: Zero negative rollover; next period available equals only the new base allocation.
4. **Modifying or deleting a category that has active transactions.** Expected: Blocked with a protected foreign key error or requires reallocating child transactions.
5. **Importing a CSV with duplicate records.** Expected: Duplicate detection flags candidates; commit is blocked until duplicates are explicitly resolved or skipped.

---

## Task Breakdown

### Task 1: Transfer Model & Ledger Posting Services (Milestone 2.1 Backend)
- **Files to create/modify:**
  - Create: `backend/apps/transactions/models/transfer.py` (or add to `backend/apps/transactions/models.py`)
  - Create: `backend/apps/transactions/services/transfer.py`
  - Modify: `backend/apps/transactions/models.py`
  - Test: `backend/tests/integration/transactions/test_transfers.py`
- **Steps:**
  - [ ] Define `Transfer` model with `transaction` (1-to-1 PK fk to `Transaction`), `source_account`, `destination_account`, `source_amount_minor`, `destination_amount_minor`, `rate`, `reference_rate`, `conversion_fee_minor`, `conversion_fee_category`, `transfer_fee_minor`, `transfer_fee_category`, `notes`.
  - [ ] Add check constraints: `source_account_id <> destination_account_id`, `source_amount_minor > 0`, `destination_amount_minor > 0`, `rate > 0`.
  - [ ] Create database migration for `Transfer`.
  - [ ] Implement `create_transfer(*, workspace, actor, source_account_id, destination_account_id, amount, destination_amount=None, rate=None, reference_rate=None, transfer_fee="0.00", transfer_fee_category_id=None, conversion_fee_category_id=None, occurred_on, notes="")`.
  - [ ] In `create_transfer`:
    - Acquire `select_for_update` on both accounts ordered by `id`.
    - Same currency: create JournalEntry with debit destination asset, credit source asset, and debit transfer fee expense if fee > 0.
    - Cross currency: create JournalEntry with 2 currency legs (source: debit FX clearing, credit source asset, debit transfer fee; dest: debit destination asset, debit conversion fee, credit FX clearing).
    - Insert `Transaction` (kind="transfer") and `Transfer` record.
    - Append `TransactionAudit` revision 1.
  - [ ] Implement `archive_transfer`: reverses ledger entries atomically and records audit entry.
  - [ ] Write tests in `test_transfers.py` covering: same-currency transfer, cross-currency transfer with spread, zero income/expense creation on transfer principal, same account rejection, and archived account rejection.
  - [ ] Run pytest to verify all tests pass.

### Task 2: Transfers REST API & Idempotency (Milestone 2.1 API)
- **Files to create/modify:**
  - Create: `backend/apps/transactions/api/transfer_serializers.py`
  - Create: `backend/apps/transactions/api/transfer_views.py`
  - Modify: `backend/apps/transactions/api/urls.py`
  - Test: `backend/tests/integration/api/test_transfers_api.py`
- **Steps:**
  - [ ] Create `TransferSerializer` (read representation with conversion details) and `CreateTransferSerializer` (validating source/dest accounts, rates, fees).
  - [ ] Implement `TransferViewSet` supporting `list`, `retrieve`, `create`, and `archive` action.
  - [ ] Integrate Redis idempotency via `Idempotency-Key` header.
  - [ ] Register routes under `/api/v1/transfers/`.
  - [ ] Update and validate OpenAPI schema.
  - [ ] Write integration API tests in `test_transfers_api.py`.
  - [ ] Run pytest to verify all tests pass.

### Task 3: Transfer UI & Live Rate Conversion (Milestone 2.1 Frontend)
- **Files to create/modify:**
  - Create: `frontend/src/features/transfers/components/transfer-dialog.tsx`
  - Create: `frontend/src/features/transfers/api/transfers-api.ts`
  - Modify: `frontend/src/features/accounts/components/statement-sheet.tsx`
  - Modify: `frontend/src/components/layout/authenticated-layout.tsx`
  - Test: `frontend/src/features/transfers/components/transfer-dialog.test.tsx`
- **Steps:**
  - [ ] Build `transfer-dialog.tsx` with Radix Dialog, source and destination account selects, live exchange rate calculator, fee inputs, and notes.
  - [ ] Support live calculation: when currency differs, rate input appears with preview of received amount.
  - [ ] Integrate Transfer button into accounts view and main action bar.
  - [ ] Write Vitest tests verifying calculation, form validation, and submit mutation.
  - [ ] Verify `npm run typecheck`, `npm run test`, and `npm run build`.

### Task 4: Category Hierarchy & Subcategories (Milestone 2.2 Backend & API)
- **Files to create/modify:**
  - Modify: `backend/apps/categories/models.py`
  - Modify: `backend/apps/categories/services.py`
  - Modify: `backend/apps/categories/api/serializers.py`
  - Modify: `backend/apps/categories/api/views.py`
  - Test: `backend/tests/integration/categories/test_categories.py`
- **Steps:**
  - [ ] Add `parent` self-referential ForeignKey to `Category`.
  - [ ] Enforce depth cap of 2: subcategories cannot have subcategories (`parent.parent is None`).
  - [ ] Add protection: category cannot be deleted or archived if it has active transactions unless reallocated.
  - [ ] Update `CategorySerializer` to include `subcategories` tree and transaction count.
  - [ ] Write tests verifying tree structure, depth cap enforcement, and archive protection.
  - [ ] Run pytest to verify all tests pass.

### Task 5: Tag & Necessity Analytics (Milestone 2.2 Backend & Frontend)
- **Files to create/modify:**
  - Create: `backend/apps/tags/services/analytics.py`
  - Create: `backend/apps/tags/api/analytics_views.py`
  - Modify: `backend/apps/tags/api/urls.py`
  - Create: `frontend/src/features/analytics/components/spending-by-tag-card.tsx`
  - Test: `backend/tests/integration/tags/test_tag_analytics.py`
- **Steps:**
  - [ ] Implement `get_tag_spending_breakdown(*, workspace, period)` and `get_necessity_spending_breakdown(*, workspace, period)`.
  - [ ] Register `GET /api/v1/tags/analytics/` endpoint returning aggregated minor units and percentages.
  - [ ] Add frontend analytics card displaying breakdown by tag and necessity (Essential vs Lifestyle).
  - [ ] Run tests and verify query count budget.

### Task 6: Budget Models & Financial Periods (Milestone 2.3 Backend)
- **Files to create/modify:**
  - Create: `backend/apps/budgets/models.py`
  - Create: `backend/apps/budgets/services/create.py`
  - Create: `backend/apps/budgets/services/spending.py`
  - Modify: `backend/config/settings/base.py` (add `apps.budgets`)
  - Test: `backend/tests/integration/budgets/test_budgets.py`
- **Steps:**
  - [ ] Define `Budget` model (workspace, category, name, period_type: monthly/weekly/custom, base_amount_minor, currency, cap_minor, is_active).
  - [ ] Define `BudgetPeriod` model (budget, start_date, end_date, base_amount_minor, rollover_minor, spent_minor, is_closed, closed_at).
  - [ ] Implement split-aware budget spending calculation aggregating completed expense splits within the date range.
  - [ ] Write unit and integration tests verifying spending calculations match transaction splits.
  - [ ] Run pytest to verify all tests pass.

### Task 7: Positive-Only Rollover Engine (Milestone 2.3 Backend)
- **Files to create/modify:**
  - Create: `backend/apps/budgets/services/rollover.py`
  - Create: `backend/apps/budgets/management/commands/close_budget_periods.py`
  - Test: `backend/tests/integration/budgets/test_rollover.py`
- **Steps:**
  - [ ] Implement `close_budget_period(*, period_id)`:
    - Lock budget period.
    - Calculate final spent.
    - If `spent < total_available`: `rollover = min(total_available - spent, budget.cap_minor or INF)`.
    - If `spent >= total_available`: `rollover = 0` (STRICT: NO negative rollover!).
    - Mark period `is_closed=True`, `closed_at=now()`.
    - Create next period allocation with calculated `rollover_minor`.
  - [ ] Implement management command `close_budget_periods`.
  - [ ] Write tests verifying: positive rollover transfers, overspending produces 0 rollover (never negative), closed periods are immutable.
  - [ ] Run pytest to verify all tests pass.

### Task 8: Budgets REST API (Milestone 2.3 API)
- **Files to create/modify:**
  - Create: `backend/apps/budgets/api/serializers.py`
  - Create: `backend/apps/budgets/api/views.py`
  - Create: `backend/apps/budgets/api/urls.py`
  - Modify: `backend/config/urls.py`
  - Test: `backend/tests/integration/api/test_budgets_api.py`
- **Steps:**
  - [ ] Implement `BudgetSerializer` and `BudgetPeriodSerializer`.
  - [ ] Create `BudgetViewSet` supporting CRUD, active periods summary, and close-period action.
  - [ ] Validate OpenAPI schema.
  - [ ] Write API integration tests in `test_budgets_api.py`.
  - [ ] Run pytest to verify all tests pass.

### Task 9: Budget Management UI (Milestone 2.3 Frontend)
- **Files to create/modify:**
  - Create: `frontend/src/features/budgets/components/budget-list.tsx`
  - Create: `frontend/src/features/budgets/components/budget-card.tsx`
  - Create: `frontend/src/features/budgets/components/create-budget-dialog.tsx`
  - Create: `frontend/src/features/budgets/api/budgets-api.ts`
  - Modify: `frontend/src/router.tsx`
  - Test: `frontend/src/features/budgets/components/budget-card.test.tsx`
- **Steps:**
  - [ ] Build budget card with visual progress bar, rollover indicator pill, spent vs available money formatters, and warning colors at 80% and 100%.
  - [ ] Build create/edit budget modal.
  - [ ] Add `/budgets` route to router.
  - [ ] Write Vitest tests verifying progress bar math and threshold warning states.
  - [ ] Verify `npm run typecheck`, `npm run test`, and `npm run build`.

### Task 10: Import Engine & Duplicate Detection (Milestone 2.4 Backend)
- **Files to create/modify:**
  - Create: `backend/apps/imports/models.py`
  - Create: `backend/apps/imports/services/parser.py`
  - Create: `backend/apps/imports/services/duplicate.py`
  - Create: `backend/apps/imports/services/commit.py`
  - Modify: `backend/config/settings/base.py` (add `apps.imports`)
  - Test: `backend/tests/integration/imports/test_imports.py`
- **Steps:**
  - [ ] Define `ImportJob` (workspace, account, file, format: CSV/XLSX, status: pending/reviewed/committed/failed) and `ImportRecord` (job, raw_data, parsed_date, parsed_amount_minor, parsed_title, duplicate_status: none/suspected/confirmed, resolved_action: import/skip).
  - [ ] Implement CSV parser supporting configurable headers (date, amount, description, payee).
  - [ ] Implement duplicate scoring algorithm checking matching account, date window (+/- 2 days), exact minor units, and text similarity.
  - [ ] Implement `commit_import_job`: atomic batch creation of `Transaction` records; blocks commit if any unresolved duplicate exists; complete rollback on error.
  - [ ] Write tests verifying parsing, duplicate detection, and atomic commit/rollback.
  - [ ] Run pytest to verify all tests pass.

### Task 11: Import REST API & Review Flow (Milestone 2.4 API)
- **Files to create/modify:**
  - Create: `backend/apps/imports/api/serializers.py`
  - Create: `backend/apps/imports/api/views.py`
  - Create: `backend/apps/imports/api/urls.py`
  - Modify: `backend/config/urls.py`
  - Test: `backend/tests/integration/api/test_imports_api.py`
- **Steps:**
  - [ ] Implement `POST /api/v1/imports/upload/` (multipart file upload).
  - [ ] Implement `GET /api/v1/imports/{id}/records/` (paginated preview of parsed rows with duplicate flags).
  - [ ] Implement `POST /api/v1/imports/{id}/resolve/` (marking duplicate candidate as import or skip).
  - [ ] Implement `POST /api/v1/imports/{id}/commit/` (final commit into ledger transactions).
  - [ ] Write API integration tests in `test_imports_api.py`.
  - [ ] Run pytest to verify all tests pass.

### Task 12: Import Wizard UI (Milestone 2.4 Frontend)
- **Files to create/modify:**
  - Create: `frontend/src/features/imports/components/import-wizard-dialog.tsx`
  - Create: `frontend/src/features/imports/components/column-mapping-step.tsx`
  - Create: `frontend/src/features/imports/components/duplicate-review-step.tsx`
  - Create: `frontend/src/features/imports/api/imports-api.ts`
  - Test: `frontend/src/features/imports/components/column-mapping-step.test.tsx`
- **Steps:**
  - [ ] Build 4-step wizard: 1. File upload & account select; 2. Column mapping; 3. Duplicate review table; 4. Commit confirmation.
  - [ ] Write Vitest tests verifying mapping and duplicate resolution actions.
  - [ ] Verify `npm run typecheck`, `npm run test`, and `npm run build`.

### Task 13: Phase 2 Hardening, Query Optimization & Exit Review (Milestone 2.5)
- **Files to create/modify:**
  - Create: `backend/tests/performance/test_phase2_queries.py`
  - Create: `docs/PHASE_2_REPORT.md`
  - Modify: `docs/CHANGELOG.md`
- **Steps:**
  - [ ] Verify N+1 query budgets for transfers, budgets, and import endpoints.
  - [ ] Re-run `check_ledger --fail-on-drift` across all workspaces.
  - [ ] Re-run full test suites: `pytest backend/tests` and `npm run test`.
  - [ ] Run Ruff lint & format checks, mypy, and TypeScript compiler checks.
  - [ ] Author `docs/PHASE_2_REPORT.md` and update `docs/CHANGELOG.md`.
  - [ ] Final Phase 2 git commit.
