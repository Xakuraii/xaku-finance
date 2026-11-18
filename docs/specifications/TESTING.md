# Testing Strategy — XakuFinance

**Status:** planning baseline.
**Principle:** a feature is done when its behavior is verified by an automated test (or a recorded manual
verification where automation is impractical). "The page renders" is not evidence.

---

## 1. Tooling

| Layer | Tools |
|---|---|
| Backend unit/integration | pytest, pytest-django, factory_boy, freezegun, pytest-cov, Hypothesis |
| API contract | DRF APIClient + drf-spectacular schema validation |
| Database | PostgreSQL 16 in CI (same major as production); no SQLite |
| Concurrency | `pytest.mark.django_db(transaction=True)`, threads/processes, `select_for_update` tests |
| Frontend unit | Vitest, React Testing Library, MSW |
| Frontend E2E | Playwright (Chromium + WebKit + one mobile viewport) |
| Accessibility | axe-core via Playwright, keyboard-path tests |
| Performance | Locust/k6 API load, Playwright trace + Lighthouse for the dashboard |
| Security | pip-audit, npm audit, Bandit/Semgrep, gitleaks, OWASP ZAP baseline |
| CI | GitHub Actions: lint → typecheck → unit → integration → E2E → schema validation → security scans |

---

## 2. Test layout

```
backend/tests/
  conftest.py                 # workspace/user/account factories, api clients, frozen clock
  factories/                  # factory_boy factories per app
  unit/                       # pure functions: money, periods, rollover math, fingerprints
  integration/
    identity/                 # auth, 2FA, sessions, throttles
    accounts/                 # lifecycle, opening balances, archiving
    ledger/                   # engine, reversal, reconciliation, balancing
    transactions/             # CRUD, splits, audit, status matrix
    transfers/                # same/FX, fees, atomicity, idempotency
    budgets/                  # periods, rollover, closed-period behavior
    savings/                  # contributions, earmarks, caps, concurrency
    debts/                    # disbursement, repayment split, principal limits
    analytics/                # net worth, safe-to-spend, allowance, emergency fund
    reports/                  # totals vs ledger reconciliation
    datamanagement/           # import, duplicates, export, restore
    privacy/                  # deletion, retention, export access
  property/                   # Hypothesis: money, ledger, allocation invariants
  security/                   # cross-tenant matrix, permission checks, header tests
  performance/                # query-count tests, volume fixtures (marked slow)

frontend/src/**/*.test.tsx    # component/unit tests colocated
frontend/e2e/                 # Playwright specs
```

Test names describe behavior, not implementation: `test_cross_currency_transfer_posts_fee_and_balancing`.

---

## 3. The financial integrity suite (release-blocking)

These tests must exist before Phase 2 is considered complete and must stay green forever.

| # | Invariant | Test |
|---|---|---|
| 1 | Every posted journal entry balances per currency | `test_every_entry_balances_per_currency` (Hypothesis) |
| 2 | Postings never reference a currency different from their ledger account | `test_posting_currency_matches_ledger_account` |
| 3 | Account balance equals sum of its postings | `test_account_balance_equals_posting_sum` |
| 4 | Pending and cancelled entries never affect balances | `test_pending_and_cancelled_excluded` |
| 5 | Completing a pending entry posts it exactly once | `test_pending_completion_is_idempotent` |
| 6 | Editing a posted transaction reverses and reposts, preserving the old entry | `test_edit_creates_reversal_and_new_entry` |
| 7 | Repeated edits append audit revisions, never overwrite | `test_audit_revisions_are_append_only` |
| 8 | Splits always sum to the transaction amount | `test_split_total_equals_transaction_amount` |
| 9 | Split total mismatch is rejected (including on edit) | `test_split_mismatch_rejected` |
| 10 | Transfers create no income or expense postings | `test_transfer_has_no_income_expense_postings` |
| 11 | Same-currency transfer moves exactly the amount | `test_same_currency_transfer_preserves_value` |
| 12 | Cross-currency transfer balances each currency and records spread | `test_cross_currency_transfer_balances_and_records_fee` |
| 13 | Opening balances post to equity, never income | `test_opening_balance_is_equity` |
| 14 | Debt disbursement creates a liability, not income | `test_debt_disbursement_not_income` |
| 15 | Debt principal repayment reduces liability and does not change net worth by the principal | `test_principal_repayment_net_worth_neutral` |
| 16 | Interest and fees are expenses | `test_interest_and_fees_are_expenses` |
| 17 | Principal cannot exceed outstanding | `test_principal_exceeds_outstanding_rejected` |
| 18 | Earmarks do not change balances or net worth | `test_earmark_does_not_change_balances` |
| 19 | Earmarks cannot exceed available account balance, including under concurrency | `test_concurrent_earmarks_respect_cap` |
| 20 | Goal progress never double-counts with account assets | `test_net_worth_ignores_goal_progress` |
| 21 | Net worth as of a past date uses that date's ledger, not today's | `test_net_worth_as_of_uses_historical_postings` |
| 22 | Safe-to-Spend excludes non-spendable accounts and itemizes deductions | `test_safe_to_spend_itemization` |
| 23 | Daily allowance is zero when remaining flexible budget ≤ 0 | `test_daily_allowance_never_negative_or_invented` |
| 24 | Budget rollover is positive-only and capped | `test_rollover_positive_only` |
| 25 | Closed budget periods never change | `test_closed_period_immutable_after_backdated_edit` |
| 26 | Multi-currency totals require conversion and disclose rates | `test_totals_never_sum_currencies_without_conversion` |
| 27 | No rate means no converted total, never 1:1 | `test_missing_rate_reports_unavailable` |
| 28 | Failed transfer leaves no postings, detail row, or audit row | `test_failed_transfer_rolls_back_completely` |
| 29 | Idempotent replay does not duplicate money movement | `test_idempotency_prevents_double_transfer` |
| 30 | Reports reconcile to ledger sums for the same period | `test_report_reconciles_to_ledger` |
| 31 | Archived transactions disappear from defaults but remain reportable | `test_archived_visible_only_with_flag` |
| 32 | Cross-workspace access returns 404 for every financial resource | `test_cross_workspace_matrix` |
| 33 | Import commit is atomic and refuses unresolved duplicates | `test_import_commit_requires_duplicate_decisions` |
| 34 | Export → restore round-trip reproduces balances and ledger checksums | `test_export_restore_reconciles` |
| 35 | No float field or float arithmetic exists for money | `test_no_float_money_usage` (static grep + review) |

### 3.1 Property-based tests

Using Hypothesis with generated event sequences:

- Generate N random valid financial events; apply them; assert after every step that the ledger balances,
  balances equal posting sums, and net worth = assets − liabilities.
- Generate split amounts that sum to a total; assert exactness at 2 dp for USD and KHR.
- Generate cross-currency transfers with random rates and rounding edge cases; assert each currency sums
  to zero and the fee equals reference value minus received value.
- Generate contributions/withdrawals against an account; assert earmarks never exceed available balance.
- Generate edits and reversals; assert final balances equal a fresh replay of the effective event set.

Hypothesis examples are persisted as regression fixtures.

### 3.2 Money arithmetic tests

- Rounding half-up at the single conversion boundary; no double rounding.
- `0.1 + 0.2`-style traps never appear because arithmetic is integer minor units.
- Precision rejection: `"1.005"` USD is rejected, not silently rounded.
- Large values (1e15 minor units) do not overflow `BIGINT`; overflow is rejected.
- Negative zero never appears in serialized output.
- Formatting uses the workspace locale but serialization is canonical.

---

## 4. Feature test matrix

### 4.1 Identity

| Area | Required tests |
|---|---|
| Registration | creates user+profile+workspace atomically; duplicate email; weak password; throttle |
| Email verification | valid, expired, reused, wrong user; limited-access enforcement |
| Login | success, wrong password, unknown email (same response), lockout, verified vs unverified |
| JWT | expiry, invalid signature, revoked session, refresh rotation, reuse revokes family |
| 2FA | setup requires reauth; confirm enables; wrong code; replay rejected; recovery code single use; disable requires both factors |
| Google | valid token, wrong audience, unverified email, link required, already linked |
| Password reset | single use, expiry, revokes sessions, no enumeration |
| Sessions | list, revoke one, revoke all, current flag, IP never exposed raw |
| Reauth | required window, expiry, wrong password |

### 4.2 Accounts and transactions

- Opening balance posts to equity; duplicate opening balance rejected; zero balance allowed.
- Archive with non-zero balance requires acknowledgement; history retained; restore works.
- Delete blocked with postings; allowed when unused.
- Currency change blocked after postings exist.
- Expense/income validation: currency mismatch, archived account, foreign category, zero/negative amount.
- Splits: 2+ allocations, mismatch, duplicate category rejected, edit updates splits and audit.
- Tags: system and custom, duplicate name case-insensitive, filter and analytics.
- Necessity: optional, filterable, null handled.
- Status matrix: every allowed/denied transition from `docs/ACCOUNTING_RULES.md` §2.5.
- Audit: revision increments, before/after correct, changed_fields accurate, append-only trigger.
- Archive/restore report behavior, including include_archived filters.
- Optimistic concurrency: stale `version` returns 409 and no write.

### 4.3 Transfers

- Same currency, exact movement, no income/expense.
- Cross currency with reference rate and spread; fee category required; each currency zero-sum.
- Fees: bank fee as expense, principal unchanged.
- Insufficient funds, same account, archived account, cross-workspace account.
- Atomicity with a forced failure after the first posting.
- Idempotency replay and conflict.
- Savings-linked transfer creates contribution atomically or not at all.
- Transfer archive reverses and restores correctly.

### 4.4 Budgets and periods

- Monthly/weekly boundaries in a non-UTC timezone (Asia/Phnom_Penh, DST timezone like America/New_York).
- Custom periods: overlap rejection, inclusive end date, validation.
- Split-aware spending.
- Rollover: positive only, cap, disabled, first period, closed period.
- Warning thresholds and notification dedupe.
- Closed period stays immutable after backdated transaction; prior-period adjustment appears.
- Flexible vs fixed exclusion from daily allowance.
- Budget currency conversion with disclosed rate.

### 4.5 Savings

- Contribution kinds and validation.
- Transfer-backed contribution creates transfer + contribution atomically.
- Earmark cap: sequential and concurrent (two threads, one must fail cleanly).
- Withdrawal reduces allocation; cannot withdraw more than contributed.
- Archive releases earmarks without moving money.
- Delete blocked when contributions exist.
- Progress, remaining, ETA math.
- Over-funding is displayed explicitly, not clamped.

### 4.6 Debts

- Create with/without disbursement.
- Outstanding derived from ledger.
- Repayment split validation (sum equals transaction amount, cross-row trigger).
- Principal > outstanding rejected.
- Interest-only payment.
- Payoff status; archive/restore.
- Net worth effect matches the worked example.
- Interest record posting increases outstanding and expense.

### 4.7 Analytics and reports

- Net worth current and historical; as-of boundary at 23:59:59 workspace time.
- FX translation and `fx_effect` line.
- Safe-to-Spend components, horizon variants, negative raw vs zero display, excluded accounts.
- Daily allowance: zero remaining, mid-period, last day, period ended.
- Emergency fund computed vs override, lookback window, coverage variants.
- Every report reconciles with ledger for the same filter.
- Report exports produce identical totals to the screen.
- Charts' accessible table arrays match series data.

### 4.8 Import/export/restore

- Valid CSV, valid XLSX, malformed rows, missing columns, bad dates, bad amounts, unknown currency.
- Exact duplicate, potential duplicate, no duplicate; decision per group; unresolved commit rejected.
- Import commit atomic: a failure on row N leaves zero imported rows.
- Imported transactions have audit actor null and job reference.
- Export contains all entities, excludes other workspaces, expires.
- Restore into non-empty workspace refused; corrupted archive refused; version mismatch refused.
- Round-trip reconciles balances and ledger sequence semantics.

### 4.9 Privacy

- Deletion requires reauth + confirmation; grace period; cancel works.
- At execution, live data gone; audit record contains no financial content.
- Export/backup blocked after request.
- Retention messaging includes backup expiry date.
- Sessions revoked on request.

### 4.10 Security

- Endpoint × role matrix: anonymous 401, other user 404, owner 200.
- Rate limits enforced per scope (not just configured).
- Security headers present on all responses.
- Upload MIME/size limits.
- No secrets in error responses; debug off.
- Admin inaccessible without staff + 2FA.
- XSS attempt in description/title renders as text (E2E).

---

## 5. Frontend testing

### 5.1 Unit/component

- Money input parsing/formatting: valid, invalid precision, locale grouping, negative display rules.
- Period selector and timezone labels.
- Form validation messages (shape only; server errors rendered inline by field).
- Empty, loading, error, and partial-conversion states for each widget.
- Chart frame: table fallback, axis labels, no-data state.
- Dashboard layout reducer: show/hide, reorder, reset, persists via API.
- Transaction split editor: totals update, mismatch blocks submit, server error displayed.
- Confirmation dialogs for archive/delete/transfer/deletion.

### 5.2 E2E (Playwright)

1. Register → verify email (mailpit) → create account with opening balance → see balance.
2. Add expense with splits and tags → appears in list, dashboard, report, budget.
3. Edit expense → audit visible, report totals change, history preserved.
4. Transfer same currency → both account balances change, income/expense unchanged.
5. Cross-currency transfer → rate, spread, fee shown; net worth consistent.
6. Budget with rollover → next period shows base + unused.
7. Savings goal transfer + earmark → progress updates; net worth unchanged; over-earmark blocked.
8. Debt repayment → outstanding drops, interest shown as expense.
9. Safe-to-Spend breakdown opens and matches components; daily allowance over-budget shows zero.
10. Import CSV with duplicates → review → decide → commit → counts match.
11. Export → download → restore into new workspace (API-assisted) → balances match.
12. Enable 2FA → log out → log in with TOTP → recovery code path.
13. Delete account request → grace state → cancel.
14. Theme toggle, keyboard-only navigation, mobile viewport smoke, axe scan on primary pages.

### 5.3 Contract tests

- Generated client compiles against the OpenAPI schema.
- MSW handlers are generated from the schema (or kept in a fixtures file with a schema test) so frontend
  tests fail when the contract changes.
- Snapshot tests are forbidden for financial values; assertions are explicit.

---

## 6. Performance and scalability tests

| Test | Target |
|---|---|
| Transaction list, 50k rows, filtered | p95 < 400 ms |
| Account balance for 50k postings | p95 < 150 ms |
| Monthly report over 50k transactions | p95 < 800 ms |
| Net worth history, 24 months | p95 < 1 s |
| Dashboard aggregate | p95 < 1 s |
| Query count per list endpoint | ≤ 8 queries, guarded by `django_assert_num_queries` |
| Import 10k rows | < 60 s in a worker, memory bounded |
| Ledger reconciliation on 50k postings | < 30 s |

Volume fixtures are generated deterministically and committed as a factory, not as a database dump.

---

## 7. CI pipeline

```
1. Lint + format      ruff, eslint, prettier
2. Types              mypy (backend), tsc --noEmit (frontend)
3. Unit               pytest unit/property, vitest
4. Integration        pytest with Postgres service
5. Schema             spectacular --validate; client generation diff
6. Security           pip-audit, npm audit --audit-level=high, bandit, gitleaks
7. Build              docker build, frontend build
8. E2E                Playwright against docker compose stack (PR + main)
9. Perf smoke         marked slow; nightly, not on every PR
10. Restore drill     nightly and release candidates
```

Coverage gates:

- `apps/ledger`, `apps/transactions`, `apps/budgets`, `apps/savings`: **≥ 95%** line/branch.
- Other backend apps: **≥ 85%**.
- Frontend: **≥ 80%** statements on `lib/` and `features/*/components` (not a goal in itself).
- Coverage is a floor, not proof. The integrity suite is the real gate.

Flaky tests are quarantined with an owner and a deadline; they are never silently skipped.

---

## 8. Test data policy

- Factories create only synthetic data. No real user data in any environment.
- Production data never enters CI; a sanitized, tiny fixture may be used only with explicit approval and
  after removing names, descriptions, and identifiers.
- Demo seed data is a dev-only management command, never a production migration.
- E2E uses a fresh workspace per test with deterministic clocks (`freezegun` / Playwright clock API).
- Time-dependent tests pin the clock and assert timezone behavior explicitly (Asia/Phnom_Penh, UTC,
  America/New_York across DST).

---

## 9. Manual verification (recorded, not assumed)

Some things need a human: visual contrast, chart legibility, destructive-action copy, screen-reader
behavior. Each gets a checklist entry in `docs/ACCEPTANCE_CRITERIA.md` with the date and the person who
verified it. Manual checks supplement, never replace, the automated suite.

---

## 10. Definition of test-done for a feature

1. Tests were written before or with the implementation.
2. Failure modes were tested, not only the happy path.
3. Atomicity, isolation, and permission paths have a test.
4. Money paths have exact-value assertions (no tolerances).
5. The test was observed failing for the right reason before the fix.
6. CI is green, including the financial integrity suite.
7. Any deferred test is listed as a limitation with an owner and a phase.
