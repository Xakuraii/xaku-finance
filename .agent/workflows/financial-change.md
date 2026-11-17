# Workflow: financial change gate

Apply this to any change that can alter a balance, total, report, budget, goal, debt, or net worth. When in
doubt, apply it.

## Before writing code

1. Write the posting recipe (debit/credit lines) and confirm it sums to zero per currency.
2. State which accounting rule numbers (`docs/ACCOUNTING_RULES.md` §1.4) are touched.
3. State the user-visible effect: what goes up, what goes down, what stays the same.
4. Identify the transaction boundary and the rows to lock.
5. Identify what happens on partial failure.
6. Decide the idempotency key/strategy if the operation can be retried.
7. Write down the exact test values (no approximations).

## Implementation checklist

- [ ] All writes inside one `transaction.atomic()`.
- [ ] Ledger accounts locked in deterministic id order.
- [ ] Entry built through `ledger_services.post_entry`, never raw `Posting.objects.create`.
- [ ] Currency equality validated; no implicit conversion.
- [ ] Rounding at one boundary only; residual posted explicitly.
- [ ] Splits re-validated on edit; deferred DB trigger present.
- [ ] Audit revision appended with before/after and actor.
- [ ] Posted entries reversed, never updated or deleted.
- [ ] Archived records excluded by default and included on request.
- [ ] Pending/cancelled excluded from balances.
- [ ] No float anywhere in the diff.
- [ ] Idempotency replay returns the first result.
- [ ] Cross-workspace objects rejected.

## Tests that must exist

1. Happy path with exact expected balances.
2. Each validation failure.
3. Forced failure after the first write → nothing persisted.
4. Replay with the same idempotency key → one movement.
5. Cross-tenant attempt → 404 and no write.
6. Historical/as-of behavior if time-dependent.
7. Reconciliation assertion (`balance == sum(postings)` and `entry sums to 0`).

## After implementation

- Run `pytest` for the domain plus the financial integrity suite.
- Run `check_ledger --fail-on-drift` on a seeded workspace.
- Manually verify the UI shows the same numbers as the API and that "how calculated" copy is accurate.
- Update `docs/ACCOUNTING_RULES.md` if a rule or recipe changed.
- Add a changelog entry; if a limitation exists, write it down rather than hiding it.

## Reject the change if

- It stores a balance.
- It posts income/expense for a transfer, opening balance, savings earmark, or debt principal.
- It mutates a posted entry.
- It converts currencies without recording the rate and date.
- It silently drops a duplicate or a rounding remainder.
- It claims atomicity without a rollback test.
- It computes a financial total in the frontend.
