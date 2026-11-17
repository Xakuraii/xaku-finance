# ADR 0001 — Double-entry ledger with system accounts

**Status:** accepted
**Date:** 2026-11-17
**Supersedes:** none

## Context

XakuFinance must report balances, net worth, budgets, savings, and debts that reconcile with a verifiable
record. The brief requires: balances reconcile with an underlying ledger; historical reports use historical
information; transfers, opening balances, savings earmarks, and debt principal must not be income or
expense; savings must not double-count assets; every movement must be traceable.

A single `transactions` table with a stored account balance cannot satisfy these simultaneously. Once a
balance is a mutable column, every write path must remember to update it, every report must trust it, and
history is lost on each update.

## Decision

Use a double-entry ledger:

- `LedgerAccount` of kind asset, liability, equity, income, expense.
- Every financial Account and Liability owns exactly one ledger account.
- `JournalEntry` is immutable and balances to zero **per currency**.
- `Posting` is a signed, debit-positive amount in one currency.
- Balances are derived from postings; no mutable balance column is authoritative.
- Posted records are corrected by reversal, never by update.
- Cross-currency entries use per-currency FX clearing accounts so no entry ever adds USD to KHR.

Reports read postings joined to transaction dimensions. Snapshots are caches keyed by a workspace ledger
sequence, not truth.

## Consequences

Positive:

- Reconciliation is a property of the schema, not a discipline.
- Historical net worth and as-of reports become straightforward aggregations.
- Savings earmarks cannot inflate assets because they never post.
- Every balance is explainable line by line.

Negative:

- More tables and a service layer that all writes must use.
- Aggregations require careful indexing and period bounds.
- The team must understand accounting basics.
- Reporting-currency translation needs an explicit, documented rate policy.

## Alternatives considered

1. **Single-entry transactions with a stored balance.** Simpler, but fails reconciliation, historical
   accuracy, and audit requirements. Rejected.
2. **Event sourcing with projections.** Powerful, but a large operational and cognitive cost for a
   single-developer product. The ledger already provides a durable fact log.
3. **Third-party accounting engine.** Adds a dependency and hides the rules we must prove. Rejected.
