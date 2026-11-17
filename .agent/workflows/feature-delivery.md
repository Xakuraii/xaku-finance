# Workflow: feature delivery

Use this for every feature, fix, or refactor. It is deliberately small enough to follow.

## 0. Frame

- Identify the requirement ID(s) in `docs/SRS.md` and any ADR/accounting rule involved.
- If the requirement is ambiguous, choose a documented default and add it to the SRS assumptions; do not
  stop for a question unless the decision is irreversible or financial behavior would be wrong either way.
- If this is a new feature with UX, write three sentences of intent and the empty state before coding.

## 1. Design (short)

- List the files to create/modify and the service function signatures.
- Identify the transaction boundary, locks, and idempotency key.
- Identify the DB constraints/indexes needed.
- Identify the tests that will prove it, including failure and isolation cases.
- For money changes, read `docs/ACCOUNTING_RULES.md` and write the posting recipe first.

## 2. Test first

- Write the failing test(s) for the smallest behavior.
- Run them; confirm they fail for the expected reason (not an import error).
- Commit tests and implementation together, or as two commits in the same PR.

## 3. Implement

- Service first, then serializer/view, then frontend.
- Keep the app runnable and migrations applied.
- No unrelated refactors in the same change; note them for later.
- Update `docs/API_SPECIFICATION.md` and regenerate OpenAPI/client when contracts move.

## 4. Verify

Run, in this order, and keep the outputs:

```bash
ruff check . && ruff format --check .
mypy apps
pytest path/to/test.py -v
pytest
python manage.py check --deploy
python manage.py spectacular --file docs/openapi.yaml --validate
python manage.py check_ledger --fail-on-drift
cd frontend && npm run typecheck && npm run lint && npm run test && npm run build
```

Report actual results. If something fails and is unrelated, say so and do not claim green.

## 5. Document

- Update the requirement's status/traceability.
- Add a `docs/CHANGELOG.md` entry under Unreleased, with limitation notes.
- Update `docs/DATABASE.md` in the same commit as a schema change.
- Add or amend an ADR if a decision was made that a future reader would question.

## 6. Report

Use this shape:

```
Implemented: <what, with requirement ids>
Files: <created/modified>
Decisions: <why, with ADR link if any>
Database: <migration + effect>
Tests run: <commands>
Results: <actual output summary>
Limitations: <what is not done / not tested>
Next: <single recommended next step>
```

## 7. Commit

Conventional Commits, scoped by domain: `feat(ledger): post balanced entries`,
`fix(budgets): prevent negative rollover`, `test(savings): earmark concurrency cap`.

Never commit secrets, `.env`, generated data dumps, or commented-out code.
