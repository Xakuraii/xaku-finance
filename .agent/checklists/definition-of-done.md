# Definition of done

A change is done when all of the following are true. If one is not, say which and why.

## Functional

- [ ] Requirement ID(s) implemented; no partial behavior presented as complete.
- [ ] Happy path, validation failures, and permission denials behave as specified.
- [ ] Loading, empty, error, and partial-data states exist where the UI can encounter them.
- [ ] Copy matches the outcome; destructive actions state consequences.

## Financial

- [ ] Posting recipe documented and balanced per currency.
- [ ] Atomicity proven by a forced-failure test.
- [ ] Idempotency proven where retries are possible.
- [ ] Historical behavior verified if dates/rates are involved.
- [ ] Balances reconcile to postings after the operation.
- [ ] No float; no stored balance; no posted mutation.

## Security and privacy

- [ ] Authorization server-side and workspace-scoped.
- [ ] Cross-tenant test proves 404 and no side effects.
- [ ] Sensitive action reauth/throttle applied where required.
- [ ] No secrets or financial payloads in logs.
- [ ] Audit event written.

## Database

- [ ] Migration reviewed, forward and backward run cleanly.
- [ ] Constraints/indexes support the new queries.
- [ ] `docs/architecture/DATABASE.md` updated in the same commit.

## Tests

- [ ] Tests written before or with the code and observed failing first.
- [ ] Domain suite and financial integrity suite green.
- [ ] No skipped/flaky test introduced.
- [ ] Frontend typecheck, lint, test, build green.

## Contracts and docs

- [ ] OpenAPI regenerated and validated; client regenerated.
- [ ] `docs/api/API_SPECIFICATION.md` updated if the contract moved.
- [ ] `docs/CHANGELOG.md` updated with limitations.
- [ ] ADR added if a decision would surprise a future reader.

## Report

- [ ] Actual commands and results reported, not summarized as "all good".
- [ ] Known limitations listed with the next step.
