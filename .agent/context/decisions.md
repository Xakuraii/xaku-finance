# Decisions index

Canonical decisions live in `docs/adr/` and `docs/ACCOUNTING_RULES.md`. This file is a quick index with
the practical consequence of each decision. If this index and an ADR disagree, the ADR wins.

| # | Decision | Practical consequence |
|---|---|---|
| 0001 | Double-entry ledger; derived balances | All writes go through `ledger.services.posting`; never store a balance |
| 0002 | Integer minor units + currency | `amount_minor BIGINT`; no floats; parse at the edge |
| 0003 | One transaction aggregate; reversal edits | Transfer/opening/debt detail are 1:1 tables; edits reverse + repost |
| 0004 | JWT access + rotating refresh + sessions | Access 15 min; refresh in HttpOnly cookie; reuse revokes family |
| 0005 | Django monolith; Celery for async only | Postgres is truth; Redis is disposable |
| 0006 | React SPA + generated client | Never hand-edit `lib/api/generated/`; regenerate with API changes |

## Settled product defaults

- One workspace per user, created at registration, unique by owner.
- Workspace reporting currency defaults to USD; change re-values, never rewrites amounts.
- Transactions are in their account's currency; FX only on transfers.
- Custom financial periods are stored; calendar periods are computed.
- Budget rollover is opt-in, positive-only, optionally capped; proration deferred.
- Savings goals use earmarks; total earmarks per account cannot exceed available balance.
- Debt outstanding is derived from the liability ledger account.
- Deleting a user's account is a 14-day grace, then hard delete; backups expire within 30 days.
- AI insights are off by default and never compute amounts.
- Receipts/OCR, bank sync, shared workspaces, and investment tracking are out of V1.

## Open decisions (defaults in force until changed)

| Topic | Default | Revisit when |
|---|---|---|
| Partitioning postings/audit | No partition; add at ~10M rows | Phase 6 load test |
| Credit cards | Model as liabilities | If users ask for a card account UX (S) |
| Per-account balance projection | None; aggregate on demand | If balance p95 > 150 ms at 50k postings |
| Provider exchange rates | Optional; manual rates always work | When a provider is integrated |
| Khmer localization | Not in V1 | After English copy stabilizes |
| Rollover proration | Deferred | If custom uneven periods are used heavily |

## How to change a decision

1. Write or amend an ADR with context, alternatives, and consequences.
2. Update `docs/ACCOUNTING_RULES.md` if money behavior changes, plus its tests.
3. Update the SRS requirement and feature matrix.
4. Update this index and `docs/CHANGELOG.md`.
5. Only then change code.
