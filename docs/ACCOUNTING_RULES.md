# Accounting Rules — XakuFinance

**Status:** normative. These rules are release-blocking. Every backend service must be traceable to a
rule here, and every rule needs a test in `docs/TESTING.md`.

---

## 1. The model in one page

XakuFinance keeps a **double-entry ledger**. Users never see journal entries; they see transactions,
transfers, goals, and debts. The server translates each event into balanced postings.

```
LedgerAccount (kind: asset | liability | equity | income | expense)
        ▲
        │ many postings
JournalEntry (immutable, one financial event, status: pending | posted | reversed | cancelled)
        │
        └─ Posting (signed amount in one currency, debit-positive)
```

- Every **Account** and every **Liability** owns exactly one ledger account.
- System ledger accounts (income, expense, equity, FX clearing) exist so entries balance and reports can
  read meaningful totals. They are never shown as accounts.
- **Balance** is always `SUM(posting.amount_minor)` over posted, non-reversed entries.
- Nothing else may store an authoritative balance.

### 1.1 Sign convention

Postings are **debit-positive**: debit `+`, credit `−`.

| Kind | Normal side | Reading a positive sum |
|---|---|---|
| Asset | debit | Money held |
| Liability | credit | Money owed (outstanding = `−SUM`) |
| Equity | credit | Owner/opening equity (`−SUM`) |
| Income | credit | Income earned (`−SUM`) |
| Expense | debit | Expense incurred (`SUM`) |

Each journal entry must satisfy `SUM(amount_minor) = 0` **for each currency present**. Multi-currency
entries achieve this by using per-currency FX clearing accounts; the entry never balances USD against
KHR directly.

### 1.2 Amounts, currencies, precision

- Amounts are integer **minor units**: `amount_minor BIGINT`, `currency_code CHAR(3)`.
- Currency metadata (`minor_unit`, symbol) lives in `Currency`.
- Rates are `NUMERIC(20,10)` — never float.
- Python uses `Decimal` with explicit quantization. TypeScript never does money arithmetic.
- Rounding is **ROUND_HALF_UP** at the single point where a value changes currency or is quantized to a
  display precision. Intermediate arithmetic stays exact.
- A converted value always carries the rate, its date, its source, and the rounding mode used.

### 1.3 Posting recipes

All examples use USD (2 minor digits) and KHR (2 minor digits, so 1 KHR = 100 minor units).

#### Expense, split across two categories

$100.00 from Checking: Groceries $60.00, Household $40.00.

| Account | Debit | Credit |
|---|---:|---:|
| Groceries (expense) | 6000 | |
| Household (expense) | 4000 | |
| Checking (asset) | | 10000 |
| **Sum** | **10000** | **10000** |

#### Income

$1,000.00 salary into Checking.

| Account | Debit | Credit |
|---|---:|---:|
| Checking (asset) | 100000 | |
| Salary (income) | | 100000 |

#### Opening balance

$500.00 starting balance in Cash. **Never income.**

| Account | Debit | Credit |
|---|---:|---:|
| Cash (asset) | 50000 | |
| Opening balance equity | | 50000 |

#### Same-currency transfer

$100.00 Checking → Savings. **Never income or expense.**

| Account | Debit | Credit |
|---|---:|---:|
| Savings (asset) | 10000 | |
| Checking (asset) | | 10000 |

With a $2.00 transfer fee charged by the bank, expensed from Checking:

| Account | Debit | Credit |
|---|---:|---:|
| Savings (asset) | 10000 | |
| Bank fees (expense) | 200 | |
| Checking (asset) | | 10200 |

The fee is its own expense; the transfer principal stays exactly $100.00.

#### Cross-currency transfer with spread

Send $100.00 USD from Checking; receive 405,000 KHR into Savings. Market/reference rate: 4,100 KHR per
USD → expected 410,000 KHR. The 5,000 KHR difference is recorded as an explicit conversion fee, not
silently absorbed.

USD side:

| Account | Debit | Credit |
|---|---:|---:|
| FX clearing · USD | 10000 | |
| Checking · USD (asset) | | 10000 |

KHR side (adapted to minor units: 410,000 KHR = 41,000,000 minor; 5,000 KHR = 500,000 minor):

| Account | Debit | Credit |
|---|---:|---:|
| Savings · KHR (asset) | 40500000 | |
| Currency conversion fees (expense) · KHR | 500000 | |
| FX clearing · KHR | | 41000000 |

Each currency sums to zero. The clearing accounts hold the FX position; the fee is visible and
categorized. If the received amount exceeds the reference value, the difference is a negative fee
(a conversion gain) posted to the same account with a credit, and reports show it separately — never as
ordinary income.

#### Debt disbursement

Borrow $1,000.00 into Checking.

| Account | Debit | Credit |
|---|---:|---:|
| Checking (asset) | 100000 | |
| Loan payable (liability) | | 100000 |

This is not income. Net worth is unchanged: assets +1,000, liabilities +1,000.

#### Debt repayment with interest

Pay $100.00 principal + $10.00 interest from Checking.

| Account | Debit | Credit |
|---|---:|---:|
| Loan payable (liability) | 10000 | |
| Interest expense | 1000 | |
| Checking (asset) | | 11000 |

Principal reduces the liability (net worth rises by $100), interest is consumption (net worth −$10).

#### Savings contribution via transfer

$100.00 Checking → Savings, allocated to a goal.

Ledger: the transfer recipe only. The goal allocation is a virtual earmark with **no posting**. Net
worth is unchanged; total assets are unchanged; only the composition of assets moves.

#### Adjustment / reconciliation entry

When a user corrects a balance, the difference posts to an **equity adjustment** account, never income
or expense:

| Account | Debit | Credit |
|---|---:|---:|
| Cash (asset) | 1500 | |
| Balance adjustments (equity) | | 1500 |

Adjustments appear in a separate report line so they cannot inflate income or hide spending.

### 1.4 The twenty rules, made operational

| # | Rule | Implementation | Test |
|---|---|---|---|
| 1 | Transfers are not income or expense | `entry_type=transfer`; only asset↔asset + fee expense | `test_transfer_no_income_expense` |
| 2 | Opening balances are not income | Equity posting, `entry_type=opening_balance` | `test_opening_balance_equity` |
| 3 | Pending never affects balances | Postings exist but entry status `pending`; balance selectors filter `posted` | `test_pending_excluded_from_balance` |
| 4 | Cancelled never affects calculations | Status `cancelled`; all selectors exclude | `test_cancelled_excluded` |
| 5 | Completed affects balances | Status `posted`; entry included | `test_completed_posts` |
| 6 | Debt principal reduces liabilities | Debit liability posting | `test_debt_principal_reduces_liability` |
| 7 | Interest and fees are expenses | Expense postings, separate from principal | `test_debt_interest_is_expense` |
| 8 | Savings allocations create no assets | Earmarks are not postings | `test_earmark_does_not_change_balance` |
| 9 | Splits equal transaction total | Service check + deferred DB trigger | `test_split_sum_equals_total` |
| 10 | No adding currencies without conversion | API returns per-currency + converted with rates | `test_totals_require_conversion` |
| 11 | Archived records stay auditable | `archived_at`, never hard-delete if posted | `test_archived_still_reported` |
| 12 | Historical reports use historical state | As-of queries on `effective_date`, rate by date | `test_networth_as_of_date` |
| 13 | Duplicate imports reviewed first | Two-phase import with decisions | `test_duplicate_requires_decision` |
| 14 | Decimal-safe arithmetic | Minor units, `Decimal`, no float fields | `test_no_float_money`, hypothesis |
| 15 | Every movement traceable | `source_type/source_id` + audit + request id | `test_traceability_chain` |
| 16 | FX transfers account for rate and difference | FX clearing per currency + explicit spread fee | `test_cross_currency_balances` |
| 17 | Atomic operations | `transaction.atomic` + row locks | `test_failed_transfer_rolls_back` |
| 18 | User data isolated | Workspace-scoped managers + endpoint tests | `test_cross_workspace_denied` |
| 19 | No silent modification invalidating history | Reverse + repost + audit revision | `test_edit_preserves_history` |
| 20 | Balances reconcile with ledger | `check_ledger` command + invariant tests | `test_ledger_reconciles` |

---

## 2. Entry lifecycle

### 2.1 Creating

1. Service validates input and workspace ownership.
2. Service locks affected ledger accounts (`SELECT … FOR UPDATE`) in a deterministic order (by account
   id) to avoid deadlocks.
3. Service builds postings.
4. Ledger engine asserts per-currency zero sum; raises `UnbalancedEntry` otherwise.
5. Entry is inserted with `status=posted` (or `pending` when the transaction is pending) and a
   `workspace_ledger_seq`.
6. Audit revision 1 is appended for the transaction.
7. Transaction commits. Any failure rolls back everything, including the sequence bump.

### 2.2 Editing

Editing a **pending** transaction: update the transaction and rewrite its pending postings; append audit
revision.

Editing a **completed** transaction (atomic):

1. Lock accounts.
2. Insert a reversal entry (`entry_type=reversal`, `status=posted`) with negated postings, linked to the
   original.
3. Mark the original `status=reversed`.
4. Insert the new entry with the new values.
5. Update the transaction's current values, increment `version`, and append audit revision with
   `before` and `after`.
6. If the effective date moved across a closed budget period, the period recomputation job is queued;
   closed periods keep their historical numbers and the change is reported as a prior-period adjustment.

Archived transactions: an edit requires restore first. This prevents invisible changes to history.

### 2.3 Archiving and restoring

- Archiving sets `is_archived=true`, `archived_at`, and reverses the posted entry (so balances reflect
  reality: the user says this never happened).
- Archived transactions are excluded from default lists and reports, but remain queryable with
  `include_archived=true`, and their full audit chain remains.
- Restoring reposts the entry on the original effective date and appends audit revision.

### 2.4 Cancelling

- Pending → cancelled: no postings are posted; entry marked cancelled.
- Completed → cancelled requires an explicit reversal (it is an edit-class action and is audited).
- Cancelled records never appear in income/expense/balance totals.

### 2.5 Status matrix

| From | To | Allowed | Ledger effect |
|---|---|---|---|
| pending | completed | yes | entry posted |
| pending | cancelled | yes | entry cancelled, no postings posted |
| pending | pending (edit) | yes | postings rewritten |
| completed | pending | no (revert is an edit: reverse, then create pending) | reversal |
| completed | completed (edit) | yes | reverse + repost |
| completed | cancelled | yes, via edit | reversal |
| cancelled | pending | yes (restore intent) | new pending entry |
| archived | active | yes | repost on original date |

---

## 3. Transfers

A transfer is one `Transaction` of type `transfer` with a 1:1 `Transfer` detail.

Validation:

1. Source ≠ destination, both active, both in the workspace.
2. Source currency = transaction currency.
3. Same currency: `destination_amount = source_amount`.
4. Different currencies: `rate > 0` and `destination_amount` provided; `reference_value =
   source_amount × rate` (quantized to destination minor units). Difference = `destination_amount −
   reference_value`; if non-zero it must be recorded as a conversion fee/gain, with a category.
5. Sufficient funds: `available_balance(source) ≥ source_amount + transfer_fee`, unless the account
   allows negative balances (an explicit account setting, default off).
6. Fee posts as an expense to a chosen category, from the source account (or a separate fee account if
   configured).
7. All postings and the detail row commit together or not at all.
8. `Idempotency-Key` required by the client; a replay returns the original result.

Never allowed: a transfer that produces only one posting, a transfer that posts to income/expense for
principal, a transfer between workspaces, a transfer that silently rounds away money.

---

## 4. Budgets and rollover

### 4.1 Definitions

- **Base allocation** — the budget's amount for one period.
- **Rollover in** — positive unused amount carried from the prior period.
- **Spent** — sum of split allocations in the budget's category, in the budget's currency, for completed
  transactions with effective dates inside the period.
- **Remaining** — `base + rollover_in − spent`.
- **Rollover out** — `max(0, remaining)`, optionally capped by `rollover_cap_minor`.

### 4.2 Rules

1. Rollover is per budget, opt-in, and positive only. Overspending produces `rollover_out = 0` and an
   over-budget state; it never becomes negative debt in the next period.
2. Only completed transactions count. Pending and cancelled do not.
3. Splits are the unit of measurement. A $100 split as $60/$25/$15 contributes $60 to Groceries, not
   $100.
4. A period closes once (`status=closed`), computing `rollover_out` and creating one `BudgetRollover`
   row. Closed periods are immutable; later backdated transactions trigger a **prior-period adjustment**
   report entry, not a rewrite.
5. Budget currency must match the categories' transactions. A transaction in another currency is
   converted using the transaction-date rate, and the report discloses that.
6. Editing a budget changes future periods only.
7. Rollover across custom periods of different lengths is prorated only when enabled and is deferred
   (FR-BUD-12, C). V1 carries the full positive remainder.
8. `spent` may be cached per period; the cache stores `ledger_seq` and is invalidated when the sequence
   moves.

### 4.3 Period boundaries

- Calendar month: first day 00:00:00 to last day 23:59:59.999999 in the **workspace timezone**.
- Calendar week: respects `week_start` (default Monday).
- Calendar year: Jan 1 – Dec 31 in workspace timezone.
- Custom: user-supplied inclusive start/end dates, validated and non-overlapping within a series.
- API always returns `period_start`, `period_end`, `timezone`, and `resolved_from` ("calendar_month"
  or "custom").

---

## 5. Savings

1. A contribution is one of: `transfer_in` (backed by a transfer), `earmark` (claim on existing savings
   balance), `adjustment`, or `withdrawal` (negative amount, may be backed by a transfer out).
2. Contributions are stored with `amount_minor` signed for direction; the detail must remain consistent
   with any linked transfer.
3. Goal progress = `SUM(contribution.amount_minor)` for the goal, floored at 0 for display; over-funding
   is shown explicitly, never clamped silently.
4. `SavingsAllocation` tracks the claim per (goal, account). Invariant:
   `Σ allocations(account) ≤ available_balance(account)` where available = posted balance − pending
   outflows for that account. Enforced in a serializable service transaction with row locks plus a
   verification command.
5. Earmarks create **no** postings. Total assets, account balances, and net worth are unchanged.
6. Withdrawing reduces the earmark first. If the earmark is backed by an actual transfer, the user is
   shown both operations and confirms the money movement.
7. Archiving a goal releases its earmarks but does not move money. The user is told this explicitly.
8. A single account can back many goals; the total claims cannot exceed real money.
9. Deleting a goal is only allowed if it has no contributions; otherwise archive.

---

## 6. Debt

1. `Liability.original_principal_minor` is the amount borrowed at origination.
2. Outstanding principal = `−SUM(postings on the liability ledger account)`. It is never edited directly.
3. Disbursement: debit asset, credit liability. Not income.
4. Repayment split:
   - principal → debit liability (reduces outstanding),
   - interest → debit interest expense,
   - fee → debit fee expense,
   - total → credit the paying asset account.
5. Principal repayment may not exceed outstanding. Interest may be zero.
6. Interest records are created when charged (or when paid, if the user does not track accrual). Accrual
   automation is deferred.
7. Net worth effect: principal repayment increases net worth by the principal amount (asset down,
   liability down equally); interest and fees reduce net worth.
8. Crediting the liability for interest charged (rather than paying it) is allowed only as an explicit
   interest record that debits interest expense and credits the liability; this increases outstanding and
   is disclosed on the debt page.

---

## 7. Net worth

```
net_worth(t) = Σ asset_balances(t) − Σ liability_outstanding(t)
```

- `t` is a date boundary in workspace timezone, converted to UTC for the query.
- Only postings of **posted** entries with `effective_date ≤ t` count.
- Conversion to the reporting currency:
  - asset/liability balances at the period-end rate for `t` (or the pinned rate),
  - flows in the period at transaction-date rates,
  - the difference is disclosed as an **FX effect** line in the net worth bridge, never as income.
- Snapshots store `ledger_seq`, `rate_set_hash`, and the components; a changed sequence invalidates them.
- Savings goals, earmarks, and goal progress never appear as assets. A goal is a claim on an asset that
  is already counted.
- Credit cards modeled as accounts with liability nature (or as Liabilities) are counted once; the schema
  forbids an account and a liability sharing the same underlying ledger account.

---

## 8. Safe-to-Spend and daily allowance

### 8.1 Safe-to-Spend

```
available_spendable = Σ posted balances of spendable accounts
pending_out         = Σ pending expenses and transfer outflows from spendable accounts
reserved_bills      = Σ reserved recurring obligations with next_due_date within horizon
planned_savings     = Σ planned savings contributions within horizon
raw                 = available_spendable − pending_out − reserved_bills − planned_savings
display             = max(0, raw)
```

- Multi-currency: compute per currency; convert for a single headline figure with the rate policy shown.
- The horizon defaults to the end of the active financial period and is user-adjustable (7/14/30 days or
  period end).
- Response includes every component, the horizon, the accounts included, and excluded accounts with a
  reason. A user must be able to see why the number is what it is.
- Pending outflows are labeled "not yet deducted from balances".

### 8.2 Daily allowance

```
remaining_flexible = Σ (flexible budget remaining, floored at 0 per budget)
remaining_days     = days from today through period end, inclusive
allowance          = floor(remaining_flexible / remaining_days) in minor units
```

- Fixed/reserved budgets and reserved obligations are excluded.
- If `remaining_flexible = 0`, the allowance is 0 with an "over budget" or "fully allocated" reason.
- If the period has ended, the allowance is 0 and the UI offers the next period.
- The allowance never invents money and never uses a projection of future income.

---

## 9. Multi-currency reporting policy

| Figure | Rate used | Disclosed as |
|---|---|---|
| Transaction amount | None (native currency) | Native amount |
| Period income/expense totals | Transaction-date rate | `rate_policy: "transaction_date"` + rates used |
| Account balance | Native | Never converted by default; converted optional on demand |
| Net worth at date | Period-end rate for that date | `rate_policy: "period_end"` |
| Budget progress | Transaction-date rate | Converted badge + note |
| Cross-currency transfer | User-entered rate + reference rate | Rate, reference rate, spread, fee |
| Historical chart | Rate effective at each point | Chart footnote + accessible table |

Rate source priority: user-pinned rate → stored manual rate for the date → provider rate for the date →
nearest prior stored rate (with the actual date shown) → error (never silently assume 1:1).

**1:1 is never a fallback.** If no rate exists, the API returns a partial result with
`conversion_unavailable: true` for that currency and the UI says so.

---

## 10. Reconciliation and integrity checks

`python manage.py check_ledger [--fail-on-drift]` verifies:

1. Each journal entry sums to zero per currency.
2. Each posting's currency matches its ledger account's currency.
3. Each financial account/liability has exactly one ledger account, and vice versa.
4. Account balances equal their posting sums (when a projection is used).
5. Split totals equal their transaction amount.
6. Transfer details match their postings (source/destination amounts and fees).
7. Opening balance entries have no income/expense postings.
8. Debt repayment principal ≤ outstanding at the time of posting, and outstanding ≥ 0.
9. Earmarks ≤ available balance per account.
10. No posted entry is orphaned from its source, and no source lacks a posted entry when completed.
11. Budget period `spent` caches equal recomputed values.
12. Snapshots match their `ledger_seq` or are marked stale.

Failures log entry ids and account ids (internal), never amounts in external alerts.

---

## 11. Worked end-to-end example

Start: USD workspace, checking $2,000, savings $500, loan $1,000 outstanding.

1. **Opening balances:** checking 2,000, savings 500, equity +2,500. Liabilities 1,000.
   Net worth = 2,500 − 1,000 = **1,500**.
2. **Salary income** $3,000 to checking. Assets 5,500, liabilities 1,000 → net worth **4,500**.
3. **Rent expense** $900 from checking, category Housing. Assets 4,600 → net worth **3,600**.
4. **Groceries** $100 split 60/25/15. Assets 4,500 → net worth **3,500**.
   Budget spend: Groceries 60, Household 25, Personal care 15.
5. **Transfer** $400 checking → savings. Assets stay 4,500 (checking 3,600, savings 900) → net worth
   **3,500**. No income, no expense.
6. **Savings earmark** $300 of savings to "Emergency fund". Assets still 4,500; goal progress 300; the UI
   shows 600 unallocated in the savings account. Net worth unchanged.
7. **Debt repayment** $100 principal + $10 interest from checking. Checking 3,600 → 3,490, savings 900,
   assets 4,390; liability 1,000 → 900. Net worth **3,490**, down exactly the $10 interest. The principal
   moved value from an asset to a liability reduction and did not change net worth — the UI must explain
   this because users expect a payment to "cost" the whole amount.
8. **Report check:** income 3,000; expenses 900 + 100 + 10 = 1,010; transfers and earmarks excluded;
   net worth 3,490. Ledger reconciliation: every entry zero-sum; assets = 4,390; liabilities = 900;
   4,390 − 900 = 3,490.

---

## 12. Explicit non-rules

- No daily accrual of interest in V1.
- No automatic categorization that changes a transaction without an audit row.
- No rewriting of closed budget periods.
- No "current balance" stored independently of postings.
- No 1:1 currency fallback.
- No income recognition from debt disbursement, transfers, opening balances, or FX gains.
- No expense recognition from debt principal, savings transfers, or earmarks.
