# Financial integrity checklist

Run before merging anything that touches money, balances, budgets, savings, debts, or reports.

## Ledger

- [ ] Entry sums to zero per currency.
- [ ] Posting currency matches its ledger account currency.
- [ ] Cross-currency entry routes through FX clearing; residual posted explicitly.
- [ ] Posted entry is immutable; correction is a reversal.
- [ ] Pending entry excluded from balances; completing posts once.
- [ ] Cancelled entry has no posted balance effect.
- [ ] Ledger sequence bumps exactly once per posted entry.

## Transactions

- [ ] Amount > 0, currency = account currency, account active.
- [ ] Splits sum exactly to the amount; duplicates and zero splits rejected.
- [ ] Split totals re-validated on edit.
- [ ] Audit revision appended with before/after, actor, timestamp, reason.
- [ ] Archive reverses; restore reposts on the original date.
- [ ] Concurrent edit with stale `version` writes nothing.

## Transfers

- [ ] Source ≠ destination; both in the workspace and active.
- [ ] Same currency moves exactly the amount.
- [ ] Cross currency requires rate and destination amount; spread becomes a fee/gain.
- [ ] Fees are expenses, principal untouched.
- [ ] Sufficient funds unless negative balances are explicitly allowed.
- [ ] Failed transfer leaves nothing behind.
- [ ] Replay does not move money twice.

## Budgets

- [ ] Spend uses split allocations, completed only, correct period boundaries.
- [ ] Rollover positive-only and capped; overspend is a state, not negative carry.
- [ ] Closed periods immutable; backdated edits produce prior-period adjustments.
- [ ] Flexible/fixed classification drives the allowance correctly.
- [ ] Currency conversion disclosed.

## Savings

- [ ] Earmarks do not post and do not change balances/net worth.
- [ ] Total earmarks ≤ account available balance, including under concurrency.
- [ ] Transfer-backed contribution is atomic.
- [ ] Withdrawal cannot exceed the contribution.
- [ ] Archive releases earmarks without moving money.
- [ ] Over-funding displayed, not clamped.

## Debt

- [ ] Disbursement is a liability, not income.
- [ ] Repayment components sum to the transaction amount.
- [ ] Principal ≤ outstanding.
- [ ] Interest/fees are expenses.
- [ ] Net worth explanation matches the ledger.
- [ ] Outstanding derives from postings.

## Reports and analytics

- [ ] Totals reconcile to ledger for the same filters.
- [ ] Missing rate returns unavailable, never 1:1.
- [ ] Historical figures use as-of postings and rates.
- [ ] Goals/snapshots don't double-count assets.
- [ ] CSV/XLSX export totals equal the screen.

## Final

- [ ] `check_ledger --fail-on-drift` green.
- [ ] Property tests and integrity suite green.
- [ ] No float money in the diff.
- [ ] Limitations documented honestly.
