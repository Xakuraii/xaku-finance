# Product context

XakuFinance is a personal finance management web app for one individual per private workspace. It is
built by a very small team, so the architecture favors a boring, well-tested monolith over distributed
systems.

## Who it is for

Students, employees, freelancers, and everyday users in USD- and KHR-based lives. They want to know what
they have, where it went, what they can safely spend, and whether their savings and debts are moving in
the right direction. They are not accountants and should not need accounting vocabulary.

## What makes it different

- A real double-entry ledger under a consumer-friendly UI.
- Multi-currency that is honest: no silent 1:1 conversion, rates and spreads are visible.
- Savings goals tied to real money, not invented progress.
- Debt repayment that separates principal from interest and explains net worth.
- History that cannot be silently rewritten.

## Product principles

1. **Correct before clever.** A wrong number is worse than a missing feature.
2. **Show the working.** Every derived figure has a "how this was calculated" path.
3. **Never fake data.** No placeholder statistics in a real workspace.
4. **Calm interface.** One figure matters per screen; everything else supports it.
5. **Respect the user's money.** Destructive actions explain consequences and are hard to trigger by
   accident.
6. **Privacy is a feature.** No trackers, no data sales, no vague deletion promises.

## Non-goals (V1)

Shared/household workspaces, bank aggregation, receipts/OCR, investment performance, tax, invoicing,
native apps, AI chat, automated advice presented as authoritative.

## Success signals (post-launch, honest metrics)

- A user can record a week of real transactions without confusion or duplicate entries.
- Balances reconcile after every operation; no support tickets about "the total is wrong".
- Users return to check Safe-to-Spend and budgets, not just to log expenses.
- Export → restore round-trip works when someone actually needs it.
- Zero cross-workspace data incidents.

## Vocabulary

Root `GLOSSARY.md` is canonical. Use "transaction", "transfer", "earmark", "financial period",
"Safe-to-Spend", "reporting currency" exactly as defined there. Do not call a transfer an expense, and do
not call archiving deletion.
