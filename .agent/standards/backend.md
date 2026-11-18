# Backend standards

Applies to `backend/`. Python 3.12+, Django 5.2 LTS, DRF, PostgreSQL.

## Layering

- **Views**: auth, permissions, throttles, parsing, response status. No business logic.
- **Serializers**: shape validation only. Never compute balances or totals.
- **Services** (`apps/<domain>/services/`): all business rules, atomicity, locking, audit, ledger calls.
  Public functions take `(workspace, actor, ...)` and plain typed arguments.
- **Selectors**: read-only queries and aggregates. No writes.
- **Models**: constraints, indexes, trivial properties. No cross-app orchestration.

## Financial writes

```python
@transaction.atomic
def create_expense(*, workspace, actor, data) -> Transaction:
    account = Account.objects.select_for_update().get(workspace=workspace, id=data.account_id)
    ...
    entry = ledger_services.post_entry(workspace=workspace, actor=actor, spec=spec)
    ...
```

Rules:

1. `transaction.atomic()` on every multi-write path.
2. Lock ledger accounts in ascending id order before posting; never hold locks across external calls.
3. Validate currency equality with the account; never coerce.
4. Never write a balance column; aggregate postings.
5. Append `TransactionAudit` inside the same transaction as the change.
6. Compute with `Decimal` through `apps.common.money`; no `float()` on money, ever.
7. Raise domain exceptions (`InsufficientFunds`, `SplitMismatch`), not `ValidationError`, from services;
   the API layer maps them to codes.
8. Idempotent endpoints store and replay the response in the same transaction.

## Models and migrations

- UUID PKs; `created_at`/`updated_at` on mutable models.
- `CheckConstraint` for local invariants; triggers for cross-row invariants (entry balance, split total).
- Names: `txn_transaction`, `txn_transaction_split`; app label + entity.
- Indexes lead with `workspace_id` on financial tables.
- One logical change per migration. Never edit an applied migration.
- Forward and reverse both tested; additive-first for production safety.

## API

- DRF ViewSets with explicit `serializer_class`, `permission_classes`, `throttle_classes`.
- All money as strings in and out; include `amount_minor` in responses.
- Cursor pagination for lists; bounded aggregates for reports.
- Error envelope per `docs/api/API_SPECIFICATION.md`; stable codes; no internals.
- drf-spectacular annotations on every endpoint; CI validates the schema.
- Cross-workspace ids return 404.

## Testing

- pytest + pytest-django + factory_boy; Postgres only.
- Test behavior names; exact money assertions (no `approx`).
- Every service has: happy path, validation failure, atomicity failure, isolation test.
- `django_assert_num_queries` on list endpoints.
- Mark slow/performance tests; keep the PR suite under 10 minutes.

## Style

- `ruff` for lint/format, `mypy` with `disallow_untyped_defs`.
- Type hints on all public service and selector functions.
- No `print`; use structured logging.
- No bare `except`; catch specific exceptions and re-raise with context.
- Docstrings explain *why* for non-obvious financial rules and cite the rule number.
