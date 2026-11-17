# Database standards

PostgreSQL 16+. Full schema in `docs/DATABASE.md`; accounting meaning in `docs/ACCOUNTING_RULES.md`.

## Mandatory patterns

| Concern | Pattern |
|---|---|
| PK | `uuid` default `uuid4`; append-only logs may use `bigserial` |
| Tenant key | `workspace_id` on every financial row, indexed first |
| Money | `amount_minor BIGINT` + `currency_code CHAR(3)` FK; no `FLOAT`, no `MONEY` |
| Rate | `NUMERIC(20,10)` with `CHECK (rate > 0)` |
| Timestamps | `TIMESTAMPTZ` in UTC; financial dates as `DATE` |
| Enums | `VARCHAR` + named `CheckConstraint` (no PG enum types) |
| Archive | `is_archived`, `archived_at`; never `DELETE` financial history |
| Case-insensitive names | `citext` for email; `UNIQUE (workspace_id, lower(name))` elsewhere |
| Cross-table key agreement | composite FK, e.g. `(account_id, currency_code)` → `account(id, currency_code)` |

## Invariants

- Posted journal entry: immutable, per-currency zero sum, enforced by deferred constraint trigger.
- Posting currency must equal its ledger account currency.
- Split totals must equal the parent transaction amount (deferred trigger).
- `TransactionAudit` and posted `JournalEntry` rows reject `UPDATE`/`DELETE` via triggers.
- One ledger account per Account/Liability (`UNIQUE (owner_type, owner_id)` partial).
- One workspace per user (`UNIQUE (owner_id)`).
- Earmarks per account ≤ available balance: service + serializable transaction + nightly check (not a
  CHECK constraint; it spans tables and changes over time).
- Net worth snapshot: `net_worth = assets − liabilities`, `ledger_seq` recorded.

## Query rules

1. No unbounded list query. Cursor pagination for rows; bounded date range for aggregates.
2. Every query filters by workspace before any other predicate.
3. Balance aggregation joins posts to posted, non-reversed entries only.
4. Use `.values()`/`.only()` for list endpoints; no `SELECT *`.
5. Guard with `django_assert_num_queries`; investigate anything above the budget.
6. Reports never loop queries per account/category; aggregate in SQL.
7. `EXPLAIN ANALYZE` any query over 100 ms on the 50k fixture.

## Migrations

- Generate with `makemigrations`, review the SQL with `sqlmigrate`, commit model + migration together.
- Additive-first: nullable column → backfill → constraint → later removal.
- Large tables: `NOT VALID` + `VALIDATE CONSTRAINT`; `CREATE INDEX CONCURRENTLY` in a documented manual
  migration.
- Data migrations must be idempotent and reversible where possible.
- Seed reference data (currencies, system categories/tags) via data migration or idempotent command, never
  fixtures in production.
- Test forward and backward on a production-like dump before release.

## Anti-patterns (reject in review)

- Storing a mutable `balance` on `account` and using it in reports.
- Computing money in SQL with `::float` or in Python with `float`.
- Adding a nullable `workspace_id` "temporarily".
- Cascading deletes from user/workspace into financial tables outside the deletion service.
- Raw SQL with string interpolation.
- Using the ORM's `.update()` on a posted journal entry or audit row.
- Adding an index without checking the query it serves.
