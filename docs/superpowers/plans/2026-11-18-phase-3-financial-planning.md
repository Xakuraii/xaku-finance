# Phase 3 Financial Planning — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase 3 Financial Planning: Savings Goals & Earmarks with strict allocation capacity constraints, Debts & Liabilities with double-entry disbursement and split repayments, and the Emergency Fund Planner with essential expense analytics and conflict detection.

**Architecture:** Django 5.2 + DRF monolith extending the immutable double-entry ledger. Savings goals support virtual earmarks with row-locked capacity guarantees ($\sum \text{allocated} \le \text{account available balance}$) and transfer-backed contributions. Liabilities maintain a strict 1:1 ledger account mapping, where repayments atomically split into principal (liability debit), interest (expense debit), and fees (expense debit). Emergency fund analytics compute essential-classified spending over lookback windows with disclosure of computed versus manual overrides. React 19 frontend components adhere to the obsidian-and-gold design system (`docs/DESIGN_SYSTEM.md`).

**Tech Stack:** Python 3.12, Django 5.2 LTS, DRF, PostgreSQL 16, Redis, React 19, TypeScript 5.8, Tailwind CSS v4, TanStack Query v5, Radix UI, Vitest, pytest.

**Spec:** `docs/SRS.md` (§3.8 FR-SAV-01..10, §3.9 FR-DEBT-01..10, §3.12 FR-EMG-01..06), `docs/ACCOUNTING_RULES.md` (§5 Savings, §6 Debt, §7 Net Worth), `docs/DATABASE.md` (§2.7, §2.8, §2.9), `docs/API_SPECIFICATION.md` (§9, §10, §11.4).

---

## Global Constraints

- Python 3.12+; Django 5.2 LTS; PostgreSQL 16 (no SQLite, including in tests).
- Money: integer minor units (`amount_minor: int`) + currency code (`currency: str`). Zero floats anywhere.
- API amounts are decimal strings in requests, returned as decimal strings + minor units in responses.
- Balances are derived dynamically from ledger postings; no mutable `balance` column.
- Outstanding debt principal is derived dynamically from `−SUM(posting.amount_minor)` on the liability's ledger account.
- Every journal entry balances to zero per currency. Posted entries are immutable.
- Earmarks create NO journal entries or postings. Net worth, total assets, and ledger account balances are completely unaffected by earmarks.
- Earmark capacity rule: $\sum \text{allocated} \le \text{account available balance}$. Violations are blocked under row lock (`select_for_update`).
- Debt repayment: principal reduces liability, interest and fees are expenses. Principal repayment exceeding outstanding balance is strictly rejected.
- Initial debt disbursement: debits asset account, credits liability ledger account; never income.
- Every row is scoped by `workspace_id`; cross-workspace queries return 404.
- All multi-write paths run inside `transaction.atomic()` with deterministic `select_for_update` row ordering to avoid deadlocks.

---

## Review Focus

1. **Attempting to allocate an earmark exceeding account available balance.** Expected: Rejected with `AllocationCapacityError` under row lock; no allocation or contribution created.
2. **Archiving a savings goal with active earmarks.** Expected: Earmarks are released (`allocated_minor = 0`) immediately; money never moves; account unallocated balance is restored.
3. **Debt repayment where principal exceeds outstanding liability balance.** Expected: Blocked with domain validation error (`400 Bad Request`); no transaction or posting created.
4. **Recording debt repayment with interest and fee.** Expected: Balanced journal entry crediting paying account for total, debiting liability for principal, and debiting expense accounts for interest and fees. Net worth decreases only by interest + fees.
5. **Emergency fund essential expense calculation and override disclosure.** Expected: Accurately averages 3 months of `essential` necessity transactions/splits, excluding transfers; when user sets override, API returns both computed and override values with `is_override: true`.

---

## Task Breakdown

### Milestone 3.1: Savings Goals & Earmarks

#### Task 1: Savings Models & Migrations (`apps/savings`)
- **Files:**
  - Create: `backend/apps/savings/__init__.py`
  - Create: `backend/apps/savings/apps.py`
  - Create: `backend/apps/savings/models.py`
  - Modify: `backend/config/settings/base.py` (add `apps.savings` to `INSTALLED_APPS`)
  - Test: `backend/tests/integration/savings/test_savings_models.py`
- **Steps:**
  - [ ] Configure `apps.savings.apps.SavingsConfig`.
  - [ ] Define `SavingsGoal`:
    - `workspace` (FK `WorkspaceScopedModel`), `name` (varchar 120), `target_amount_minor` (bigint), `currency_code` (char 3), `target_date` (date null), `linked_account` (FK `Account` null, PROTECT), `strategy` (varchar 16 default 'linked_account': 'linked_account'|'earmark'), `status` (varchar 12 default 'active': 'active'|'achieved'|'paused'|'archived'), `notes` (text null), `is_archived` (bool default False), `achieved_at` (timestamptz null).
    - Check constraints: `target_amount_minor > 0`, `strategy <> 'linked_account' OR linked_account_id IS NOT NULL`.
  - [ ] Define `SavingsContribution`:
    - `workspace`, `goal` (FK `SavingsGoal`, PROTECT), `account` (FK `Account`, PROTECT), `transfer_transaction` (FK `Transaction` null, PROTECT), `kind` (varchar 16: 'transfer_in'|'earmark'|'adjustment'|'withdrawal'), `amount_minor` (bigint, signed), `currency_code` (char 3), `occurred_on` (date), `note` (varchar 240 null), `created_by` (FK `User`, PROTECT).
    - Check constraints: `amount_minor <> 0`, `kind <> 'transfer_in' OR (transfer_transaction_id IS NOT NULL AND amount_minor > 0)`, `kind <> 'withdrawal' OR amount_minor < 0`, `kind NOT IN ('earmark','adjustment') OR transfer_transaction_id IS NULL`.
  - [ ] Define `SavingsAllocation`:
    - `workspace`, `goal` (FK `SavingsGoal`, PROTECT), `account` (FK `Account`, PROTECT), `allocated_minor` (bigint default 0), `currency_code` (char 3).
    - Unique constraint: `(goal, account)`.
    - Check constraint: `allocated_minor >= 0`.
  - [ ] Run `python manage.py makemigrations savings` and execute migration.
  - [ ] Write model constraint and initialization unit tests in `test_savings_models.py`.

#### Task 2: Savings Domain Services & Capacity Engine
- **Files:**
  - Create: `backend/apps/savings/services.py`
  - Create: `backend/apps/savings/selectors.py`
  - Test: `backend/tests/integration/savings/test_savings_services.py`
- **Steps:**
  - [ ] Implement `create_savings_goal`: validates currency, strategy, and linked account; creates goal.
  - [ ] Implement `update_savings_goal`: updates metadata, status, target amount/date.
  - [ ] Implement `archive_savings_goal`: sets `is_archived=True`, `status='archived'`; atomically zeroes all `SavingsAllocation` rows for this goal without creating ledger movements.
  - [ ] Implement `record_savings_contribution`:
    - For `kind='earmark'`: acquires `select_for_update()` on `account` and all allocations for this account. Computes `current_allocated = sum(allocated_minor)` across active goals. Verifies `current_allocated + amount_minor <= account_available_balance`. Updates or inserts `SavingsAllocation` and inserts `SavingsContribution`.
    - For `kind='withdrawal'`: reduces `SavingsAllocation` (down to 0) and records negative `SavingsContribution`.
    - For `kind='adjustment'`: adjusts allocation and records contribution.
    - For `kind='transfer_in'`: links provided transfer transaction, adjusts allocation on the destination savings account.
    - Checks if total contributed $\ge$ target: sets `achieved_at=now()`, `status='achieved'` if target met.
  - [ ] Implement selectors in `selectors.py`:
    - `get_goal_progress(goal)`: returns `current_amount_minor`, `target_amount_minor`, `progress_percent`, `is_overfunded`, `overfunded_amount_minor`.
    - `get_account_unallocated_balance(account)`: returns `account_balance - total_allocated_to_goals`.
    - `get_goal_projection(goal)`: computes required monthly contribution to reach target by `target_date`, or estimated completion date at recent contribution pace.
  - [ ] Write comprehensive service tests covering: earmark within capacity, earmark exceeding capacity rejection, archiving releases earmarks, withdrawal, and progress calculations.

#### Task 3: Savings REST API & Idempotency
- **Files:**
  - Create: `backend/apps/savings/api/__init__.py`
  - Create: `backend/apps/savings/api/serializers.py`
  - Create: `backend/apps/savings/api/views.py`
  - Create: `backend/apps/savings/api/urls.py`
  - Modify: `backend/config/urls.py`
  - Test: `backend/tests/integration/api/test_savings_api.py`
- **Steps:**
  - [ ] Implement `SavingsGoalSerializer` (includes progress, allocated amount, strategy, unallocated account capacity) and `CreateSavingsGoalSerializer`.
  - [ ] Implement `SavingsContributionSerializer` and `RecordContributionSerializer`.
  - [ ] Implement `SavingsGoalViewSet` with actions:
    - `list`, `retrieve`, `create`, `partial_update`, `destroy` (blocked if contributions exist).
    - `POST /api/v1/savings-goals/{id}/archive/`
    - `GET` & `POST /api/v1/savings-goals/{id}/contributions/`
    - `GET /api/v1/savings-goals/{id}/projection/`
  - [ ] Apply `Idempotency-Key` deduplication on contribution creation and goal creation.
  - [ ] Register routes in `backend/config/urls.py` under `/api/v1/savings-goals/`.
  - [ ] Write integration API tests in `test_savings_api.py`.

#### Task 4: Savings Frontend Components & Routing
- **Files:**
  - Create: `frontend/src/features/savings/api/savings-api.ts`
  - Create: `frontend/src/features/savings/components/savings-goal-card.tsx`
  - Create: `frontend/src/features/savings/components/create-goal-dialog.tsx`
  - Create: `frontend/src/features/savings/components/contribute-dialog.tsx`
  - Create: `frontend/src/features/savings/components/goal-projection-card.tsx`
  - Create: `frontend/src/features/savings/pages/savings-page.tsx`
  - Modify: `frontend/src/app/router.tsx`
  - Modify: `frontend/src/components/layout/authenticated-layout.tsx`
  - Test: `frontend/src/features/savings/components/savings-goal-card.test.tsx`
- **Steps:**
  - [ ] Define TypeScript types for `SavingsGoal`, `SavingsContribution`, `GoalProjection` in `savings-api.ts`.
  - [ ] Build `savings-goal-card.tsx` with gold progress bar, over-funded indicator, unallocated capacity, and quick action buttons.
  - [ ] Build `create-goal-dialog.tsx` with target amount, currency, strategy selector, and linked account dropdown.
  - [ ] Build `contribute-dialog.tsx` supporting Earmark, Transfer In, and Withdrawal modes with live balance capacity validation.
  - [ ] Build `savings-page.tsx` displaying goals grid, total saved across goals, and create dialog trigger.
  - [ ] Register `/savings` in router and add sidebar navigation item.
  - [ ] Write Vitest tests in `savings-goal-card.test.tsx`.

---

### Milestone 3.2: Debts & Liabilities

#### Task 5: Debt Models & Migrations (`apps/debts`)
- **Files:**
  - Create: `backend/apps/debts/__init__.py`
  - Create: `backend/apps/debts/apps.py`
  - Create: `backend/apps/debts/models.py`
  - Modify: `backend/config/settings/base.py` (add `apps.debts` to `INSTALLED_APPS`)
  - Test: `backend/tests/integration/debts/test_debt_models.py`
- **Steps:**
  - [ ] Configure `apps.debts.apps.DebtsConfig`.
  - [ ] Define `Liability`:
    - `workspace`, `name` (varchar 120), `liability_type` (varchar 20: 'personal_loan'|'student_loan'|'credit_card'|'mortgage'|'family_loan'|'other'), `currency_code` (char 3), `original_principal_minor` (bigint), `interest_rate` (numeric 7,4 null), `interest_type` (varchar 8 default 'none': 'none'|'simple'|'compound'), `lender` (varchar 120 null), `due_day` (smallint null), `next_due_date` (date null), `linked_account` (FK `Account` null, PROTECT), `ledger_account` (1:1 FK `LedgerAccount` unique, PROTECT), `status` (varchar 12 default 'active': 'active'|'paid_off'|'archived'), `is_archived` (bool default False), `notes` (text null).
    - Check constraints: `original_principal_minor > 0`, `interest_rate IS NULL OR interest_rate >= 0`.
  - [ ] Define `DebtRepayment`:
    - `workspace`, `liability` (FK `Liability`, PROTECT), `transaction` (1:1 FK `Transaction`, PROTECT), `principal_minor` (bigint default 0), `interest_minor` (bigint default 0), `fee_minor` (bigint default 0), `currency_code` (char 3), `paid_on` (date), `note` (varchar 240 null).
    - Check constraints: `principal_minor >= 0 AND interest_minor >= 0 AND fee_minor >= 0`, `principal_minor + interest_minor + fee_minor > 0`.
  - [ ] Define `DebtInterestRecord`:
    - `workspace`, `liability` (FK `Liability`, PROTECT), `period_start` (date), `period_end` (date), `amount_minor` (bigint), `rate_used` (numeric 7,4 null), `interest_type` (varchar 8 default 'simple'), `posted_transaction` (FK `Transaction` null, PROTECT), `note` (varchar 240 null).
    - Check constraint: `amount_minor > 0 AND period_end >= period_start`.
  - [ ] Run `python manage.py makemigrations debts` and execute migration.
  - [ ] Write unit tests verifying constraints in `test_debt_models.py`.

#### Task 6: Debt Double-Entry Services & Outstanding Balance Selector
- **Files:**
  - Create: `backend/apps/debts/services.py`
  - Create: `backend/apps/debts/selectors.py`
  - Test: `backend/tests/integration/debts/test_debt_services.py`
- **Steps:**
  - [ ] Implement `create_liability`:
    - Creates a dedicated `LedgerAccount` (`kind='liability'`, `code=f"liability:{uuid}"`, `currency_code`).
    - Creates `Liability` model instance.
    - If `initial_disbursement_account_id` provided: creates JournalEntry with debit asset account (cash received) and credit liability ledger account (debt owed). Net worth is unchanged. Creates `Transaction` with `kind='debt_disbursement'`.
  - [ ] Implement `record_debt_repayment`:
    - Acquires `select_for_update()` on liability and paying account.
    - Queries current outstanding principal: `outstanding = get_liability_outstanding(liability)`.
    - Validates `principal_minor <= outstanding` (raises `OverpaymentError` if principal exceeds remaining balance).
    - Creates JournalEntry:
      - Credit paying account ledger account: `principal_minor + interest_minor + fee_minor`.
      - Debit liability ledger account: `principal_minor`.
      - Debit interest expense system account: `interest_minor` (if > 0).
      - Debit bank fee expense system account: `fee_minor` (if > 0).
    - Creates `Transaction` (`kind='debt_repayment'`) and `DebtRepayment` record.
    - If `outstanding - principal_minor == 0`: updates `liability.status = 'paid_off'`.
  - [ ] Implement `record_accrued_interest`:
    - Posts debit interest expense, credit liability ledger account; increases outstanding principal.
  - [ ] Implement selectors in `selectors.py`:
    - `get_liability_outstanding(liability)`: computes `−SUM(amount_minor)` from liability's ledger account postings.
    - `get_debt_payoff_projection(liability, monthly_payment)`: calculates estimated months to payoff and total interest payable.
  - [ ] Write service tests covering: loan creation with and without disbursement, repayment split (liability reduction vs expense), overpayment rejection, and payoff status transition.

#### Task 7: Debts REST API & Idempotency
- **Files:**
  - Create: `backend/apps/debts/api/__init__.py`
  - Create: `backend/apps/debts/api/serializers.py`
  - Create: `backend/apps/debts/api/views.py`
  - Create: `backend/apps/debts/api/urls.py`
  - Modify: `backend/config/urls.py`
  - Test: `backend/tests/integration/api/test_debts_api.py`
- **Steps:**
  - [ ] Implement `LiabilitySerializer` (includes `outstanding_principal_minor`, `progress_percent`, `paid_principal_minor`, `ledger_account_id`) and `CreateLiabilitySerializer`.
  - [ ] Implement `DebtRepaymentSerializer` and `CreateDebtRepaymentSerializer`.
  - [ ] Implement `DebtInterestRecordSerializer`.
  - [ ] Implement `LiabilityViewSet` with actions:
    - `list`, `retrieve`, `create`, `partial_update`, `archive`, `restore`.
    - `GET` & `POST /api/v1/debts/{id}/repayments/`
    - `GET` & `POST /api/v1/debts/{id}/interest/`
    - `GET /api/v1/debts/{id}/projection/`
  - [ ] Integrate Redis idempotency via `Idempotency-Key` on repayments and disbursements.
  - [ ] Register routes in `backend/config/urls.py` under `/api/v1/debts/`.
  - [ ] Write integration API tests in `test_debts_api.py`.

#### Task 8: Debts Frontend Components & Routing
- **Files:**
  - Create: `frontend/src/features/debts/api/debts-api.ts`
  - Create: `frontend/src/features/debts/components/debt-card.tsx`
  - Create: `frontend/src/features/debts/components/create-debt-dialog.tsx`
  - Create: `frontend/src/features/debts/components/repayment-dialog.tsx`
  - Create: `frontend/src/features/debts/components/debt-projection-card.tsx`
  - Create: `frontend/src/features/debts/pages/debts-page.tsx`
  - Modify: `frontend/src/app/router.tsx`
  - Modify: `frontend/src/components/layout/authenticated-layout.tsx`
  - Test: `frontend/src/features/debts/components/debt-card.test.tsx`
- **Steps:**
  - [ ] Define TypeScript types for `Liability`, `DebtRepayment`, `DebtProjection` in `debts-api.ts`.
  - [ ] Build `debt-card.tsx` with outstanding balance, original principal, interest rate pill, due date badge, and repayment button.
  - [ ] Build `create-debt-dialog.tsx` with liability type, principal amount, interest rate, lender, and optional initial disbursement account.
  - [ ] Build `repayment-dialog.tsx` with live split breakdown (principal vs interest vs fee) and real-time net worth impact explainer banner.
  - [ ] Build `debts-page.tsx` with summary cards (Total Debt, Monthly Interest, Next Due) and liabilities grid.
  - [ ] Register `/debts` in router and sidebar.
  - [ ] Write Vitest tests in `debt-card.test.tsx`.

---

### Milestone 3.3: Emergency Fund Planner

#### Task 9: Emergency Fund Backend Analytics Engine (`apps/analytics`)
- **Files:**
  - Create: `backend/apps/analytics/__init__.py`
  - Create: `backend/apps/analytics/apps.py`
  - Create: `backend/apps/analytics/models.py`
  - Create: `backend/apps/analytics/emergency_fund.py`
  - Modify: `backend/config/settings/base.py` (add `apps.analytics` to `INSTALLED_APPS`)
  - Test: `backend/tests/integration/analytics/test_emergency_fund.py`
- **Steps:**
  - [ ] Configure `apps.analytics.apps.AnalyticsConfig`.
  - [ ] Define `EmergencyFundConfig`:
    - `workspace` (1:1 FK `Workspace`, PROTECT), `target_months` (smallint default 6), `designated_account` (FK `Account` null, PROTECT), `designated_goal` (FK `SavingsGoal` null, PROTECT), `monthly_expense_override_minor` (bigint null), `currency_code` (char 3 default 'USD'), `updated_at`.
    - Check constraint: `target_months > 0`, `monthly_expense_override_minor IS NULL OR monthly_expense_override_minor > 0`.
  - [ ] Run `python manage.py makemigrations analytics` and execute migration.
  - [ ] Implement `get_or_create_emergency_fund_config(workspace)`.
  - [ ] Implement `calculate_essential_monthly_expenses(workspace, lookback_days=90)`:
    - Queries all completed transactions and splits in workspace with `necessity='essential'` within lookback window.
    - Excludes transfers, opening balances, and debt disbursements.
    - Averages total essential expenses into a 30-day monthly figure.
  - [ ] Implement `get_emergency_fund_status(workspace)`:
    - Computes `computed_monthly_minor`.
    - Determines `effective_monthly_minor`: override if set, else computed.
    - Computes `target_amount_minor = effective_monthly_minor * target_months`.
    - Computes `current_savings_minor`: balance from designated account or goal.
    - Computes `progress_percent = min(100.0, current_savings / target)`.
    - Checks `has_earmark_conflict`: if designated account is used, checks whether other goals earmark more than available balance.
  - [ ] Implement `get_emergency_fund_projection(workspace, monthly_contribution_minor)`:
    - Calculates remaining shortfall and estimated months/days to reach full emergency coverage.
  - [ ] Write integration tests in `test_emergency_fund.py`.

#### Task 10: Emergency Fund API & Endpoints
- **Files:**
  - Create: `backend/apps/analytics/api/__init__.py`
  - Create: `backend/apps/analytics/api/serializers.py`
  - Create: `backend/apps/analytics/api/views.py`
  - Create: `backend/apps/analytics/api/urls.py`
  - Modify: `backend/config/urls.py`
  - Test: `backend/tests/integration/api/test_emergency_fund_api.py`
- **Steps:**
  - [ ] Implement `EmergencyFundStatusSerializer` returning config, computed vs override breakdown, target, current savings, progress, and conflict warning.
  - [ ] Implement `UpdateEmergencyFundConfigSerializer`.
  - [ ] Implement `EmergencyFundProjectionSerializer`.
  - [ ] Implement `EmergencyFundView`:
    - `GET /api/v1/emergency-fund/`: returns full status and metrics.
    - `PUT /api/v1/emergency-fund/`: updates target months, designated account/goal, and override amount.
    - `GET /api/v1/emergency-fund/projection/?monthly_contribution=100.00`: returns projection calculation.
  - [ ] Register routes under `/api/v1/emergency-fund/`.
  - [ ] Write integration API tests in `test_emergency_fund_api.py`.

#### Task 11: Emergency Fund Frontend UI & Routing
- **Files:**
  - Create: `frontend/src/features/emergency-fund/api/emergency-fund-api.ts`
  - Create: `frontend/src/features/emergency-fund/components/emergency-fund-card.tsx`
  - Create: `frontend/src/features/emergency-fund/components/emergency-config-dialog.tsx`
  - Create: `frontend/src/features/emergency-fund/components/emergency-projection-card.tsx`
  - Create: `frontend/src/features/emergency-fund/pages/emergency-fund-page.tsx`
  - Modify: `frontend/src/app/router.tsx`
  - Modify: `frontend/src/components/layout/authenticated-layout.tsx`
  - Test: `frontend/src/features/emergency-fund/components/emergency-fund-card.test.tsx`
- **Steps:**
  - [ ] Define TypeScript types for `EmergencyFundStatus`, `EmergencyFundConfig`, `EmergencyProjection`.
  - [ ] Build `emergency-fund-card.tsx` with coverage meter, months badge (3/6/12), computed vs override badge, and earmark conflict alert banner.
  - [ ] Build `emergency-config-dialog.tsx` with target months selector (3, 6, 12, or custom), designated account/goal dropdown, and manual monthly expense override input.
  - [ ] Build `emergency-projection-card.tsx` with dynamic slider/input for regular contribution and projected completion date.
  - [ ] Build `emergency-fund-page.tsx` tying all components together.
  - [ ] Register `/emergency-fund` in router and sidebar.
  - [ ] Write Vitest tests in `emergency-fund-card.test.tsx`.

---

### Milestone 3.4: Phase 3 Verification, Hardening & Audit Gates

#### Task 12: Query Performance & Ledger Drift Verification
- **Files:**
  - Create: `backend/tests/performance/test_phase3_queries.py`
  - Test: `backend/tests/performance/test_phase3_queries.py`
- **Steps:**
  - [ ] Write query count test for `GET /api/v1/savings-goals/`: $\le 3$ queries (goals with preloaded allocations/accounts).
  - [ ] Write query count test for `GET /api/v1/debts/`: $\le 2$ queries (liabilities with ledger postings aggregate).
  - [ ] Write query count test for `GET /api/v1/emergency-fund/`: $\le 4$ queries.
  - [ ] Run `python manage.py check_ledger --fail-on-drift` across all workspaces to verify zero accounting drift.

#### Task 13: Schema Validation, Full Test Pass & Exit Documentation
- **Files:**
  - Modify: `docs/openapi.yaml`
  - Create: `docs/PHASE_3_REPORT.md`
  - Modify: `docs/CHANGELOG.md`
  - Modify: `docs/ROADMAP.md`
- **Steps:**
  - [ ] Regenerate and validate OpenAPI 3.1 specification: `python manage.py spectacular --file docs/openapi.yaml --validate`.
  - [ ] Run `ruff check backend` and `ruff format --check backend`.
  - [ ] Run `mypy backend/apps`.
  - [ ] Run backend `pytest backend/tests`.
  - [ ] Run frontend `npm run typecheck`, `npm run lint`, `npm run test`, and `npm run build`.
  - [ ] Author `docs/PHASE_3_REPORT.md` documenting verified acceptance criteria, test counts, and exit criteria.
  - [ ] Update `docs/CHANGELOG.md` and `docs/ROADMAP.md`.
