# Workflow: release

## Pre-release (one week before)

- [ ] All mandatory acceptance criteria in `docs/ACCEPTANCE_CRITERIA.md` checked with evidence.
- [ ] `check_ledger --fail-on-drift` green on the 50k fixture and on staging.
- [ ] Restore drill executed from the latest backup and reconciled.
- [ ] Security checklist complete; pen-test findings closed or accepted in writing.
- [ ] Dependency audit and SAST clean; no high/critical unpatched.
- [ ] Performance targets met; no query-count regressions.
- [ ] Migrations forward and backward tested on a production-like dump.
- [ ] Rollback plan written and rehearsed for app and migrations.
- [ ] Support runbook: locked-out 2FA, deletion cancellation, restore request.
- [ ] Retention/deletion copy reviewed for truthfulness.

## Release day

1. Announce the maintenance window if any.
2. Take and verify a fresh backup; record its id and checksum.
3. Build immutable images; tag with the commit SHA; scan them.
4. Run migrations as a separate step; stop on failure.
5. Deploy API, worker, beat, then frontend.
6. Run smoke checks: health, login, create a transaction in a staging workspace, dashboard, report,
   ledger check.
7. Watch error rate, latency, queue depth, and backup status for 60 minutes.
8. Record the release in `docs/CHANGELOG.md` with the date and included requirement IDs.

## Rollback

- Application: redeploy the previous image tag.
- Migrations: reverse only if the migration was written reversible; otherwise use the documented
  forward-fix plan. Never hand-edit production data to "undo" a migration.
- If ledger drift is detected: stop financial writes (feature flag), restore from the verified backup,
  reconcile, then reopen. Preserve the affected database for investigation.

## Post-release

- 24-hour review: errors, backups, reconciliation, user reports.
- Write down what broke and what would have caught it; add a test or check.
- Update risks and limitations.

## Never

- Deploy on a Friday afternoon without someone available.
- Skip the restore drill because the last one passed.
- Declare a release green while a mandatory checkbox is unchecked.
- Claim data was deleted while backups still contain it.
