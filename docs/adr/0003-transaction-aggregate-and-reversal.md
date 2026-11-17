# ADR 0003 — One transaction aggregate, reversal-based edits

**Status:** accepted
**Date:** 2026-11-17

## Context

The brief lists `Transaction`, `Transfer`, `OpeningBalance`, `TransactionSplit`, and
`TransactionAuditLog` as separate entities. It also requires a single transaction feed, tags, splits,
statuses, audit history, restoration, and historical report preservation.

Implementing transfers and opening balances as unrelated records would duplicate tagging, audit, search,
and ledger plumbing, and would create two definitions of "a financial event".

## Decision

- `Transaction` is the single financial-event aggregate with a `type`:
  `income | expense | transfer | opening_balance | debt_disbursement | debt_repayment | adjustment`.
- Type-specific details are 1:1 tables sharing the transaction id: `Transfer`, `OpeningBalance`,
  `DebtRepayment`.
- Splits, tags, and audit attach to the transaction.
- Edits are append-only in audit and reversal-based in the ledger:
  1. lock affected ledger accounts,
  2. reverse the previous posted entry,
  3. post the new entry,
  4. update transaction values and `version`,
  5. append a `TransactionAudit` revision with before/after.
- Archiving reverses the entry; restoring reposts it on the original effective date.
- Pending entries exist as `pending` journal entries but are excluded from balances.

## Consequences

- One feed, one filter system, one audit chain, one ledger integration.
- Historical reports remain valid because old entries are never mutated.
- The transaction table carries some type-specific nullable fields (e.g. `category_id`), constrained by
  checks and services.
- Reversals double the number of postings for edited records; this is the cost of auditability.
- A user-facing "delete" is an archive; only unused accounts and goals without contributions can be hard
  deleted.

## Alternatives considered

1. **Separate Transfer/OpeningBalance tables with their own feeds.** Rejected: duplicated behavior and
   inconsistent auditability.
2. **In-place updates to journal entries.** Simpler, but destroys history and invalidates reports.
3. **Full event sourcing.** More than this product needs; the ledger plus audit already captures facts.
