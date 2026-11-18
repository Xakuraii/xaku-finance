# Phase 4 — Financial Intelligence Implementation Plan

## Goal
Implement Milestone 4.1 (Net Worth & Snapshots), Milestone 4.2 (Safe-to-Spend & Daily Allowance), and Milestone 4.3 (Financial Reports & Analytics), ensuring ledger-backed mathematical integrity, strict query count budgets, zero ledger drift, accessible UI, and OpenAPI 3.1 documentation.

---

## Architecture & Accounting Rules

1. **Net Worth:**
   - $\text{Net Worth} = \text{Assets} - \text{Liabilities} = \sum_{\text{ASSET}} \text{Postings} - \sum_{\text{LIABILITY}} (-\text{Postings})$.
   - As-of net worth queries ledger postings with `journal_entry__effective_date <= as_of`.
   - Multi-currency: uses `ExchangeRate` for the date (or nearest prior stored rate); 1:1 fallback is strictly forbidden.
   - Snapshot cache in `NetWorthSnapshot` pinned to `(workspace, as_of_date, reporting_currency_code)`. Verified against `workspace.ledger_seq`.

2. **Safe-to-Spend & Daily Allowance:**
   - $\text{Safe-to-Spend} = \text{Spendable Cash} - \text{Pending Outflows} - \text{Reserved Obligations} - \text{Planned Savings}$.
   - Daily Allowance: $\lfloor \text{Remaining Flexible Budgets} / \text{Remaining Days in Period} \rfloor$.
   - Full itemization of included accounts, excluded accounts with reasons, and component breakdown.

3. **Financial Reports:**
   - Income vs Expense Statement, Cash Flow Statement, Category & Necessity Breakdown, Spending Trends.
   - Every report contains a `reconciliation` block verifying reported figures against ledger sums.

---

## Detailed Task Breakdown

### Milestone 4.1: Net Worth & Historical Snapshots
- [ ] Task 1.1: Define `NetWorthSnapshot` model in `apps/analytics/models.py`, generate and run migrations.
- [ ] Task 1.2: Implement `apps/analytics/net_worth.py` service (as-of ledger calculation, FX conversion engine, snapshot caching).
- [ ] Task 1.3: Implement Net Worth serializers and API views (`/api/v1/net-worth/` and `/api/v1/net-worth/history/`).
- [ ] Task 1.4: Write comprehensive backend integration tests in `backend/tests/integration/analytics/test_net_worth.py`.
- [ ] Task 1.5: Build frontend Net Worth components (`net-worth-card.tsx`, `net-worth-chart.tsx`, `analytics-api.ts`) and Vitest tests.

### Milestone 4.2: Safe-to-Spend & Daily Allowance
- [ ] Task 2.1: Define `RecurringObligation` model in `apps/analytics/models.py`, generate and run migrations.
- [ ] Task 2.2: Implement `apps/analytics/safe_to_spend.py` and `apps/analytics/daily_allowance.py` services.
- [ ] Task 2.3: Implement API serializers, views, and routes for `/api/v1/safe-to-spend/`, `/api/v1/daily-allowance/`, and `/api/v1/recurring-obligations/`.
- [ ] Task 2.4: Write comprehensive backend integration tests in `backend/tests/integration/analytics/test_safe_to_spend.py`.
- [ ] Task 2.5: Build frontend components (`safe-to-spend-card.tsx`, `daily-allowance-card.tsx`, `recurring-obligations-card.tsx`) and Vitest tests.

### Milestone 4.3: Financial Reports & Analytics
- [ ] Task 3.1: Implement `apps/analytics/reports.py` services (Income vs Expense, Cash Flow, Category Breakdown, Spending Trends) with ledger reconciliation blocks.
- [ ] Task 3.2: Implement API serializers and views for `/api/v1/reports/{income,expenses,categories,trends,cashflow,tags}/`.
- [ ] Task 3.3: Write backend integration tests in `backend/tests/integration/analytics/test_reports.py`.
- [ ] Task 3.4: Build frontend reports shell and views in `frontend/src/features/analytics/pages/reports-page.tsx`.

### Milestone 4.4: Hardening, Performance & Verification
- [ ] Task 4.1: Write performance tests verifying query budgets in `backend/tests/performance/test_phase4_queries.py`.
- [ ] Task 4.2: Run `python manage.py check_ledger --fail-on-drift` across all workspaces.
- [ ] Task 4.3: Update and validate OpenAPI 3.1 schema: `python manage.py spectacular --file docs/openapi.yaml --validate`.
- [ ] Task 4.4: Run code formatting, linter, and static type checks (`ruff`, `mypy`).
- [ ] Task 4.5: Run full test suites (`pytest` backend and `vitest` frontend) and verify production frontend build (`npm run build`).
- [ ] Task 4.6: Author `docs/PHASE_4_REPORT.md` and update `docs/CHANGELOG.md` and `docs/ROADMAP.md`.
