# V1.0 Acceptance Criteria — XakuFinance

**Status:** not met. Nothing is implemented. This is the release checklist, not a claim.

A box is checked only with linked evidence (test name, CI run, screenshot, or signed manual note with a
date). Checked boxes without evidence are treated as unchecked.

---

## 1. Functional acceptance

### Identity and access
- [ ] Register creates user + profile + workspace atomically; duplicate email rejected.
- [ ] Email verification, resend, expiry, and single-use behavior verified.
- [ ] Login works; failures are generic and throttled; lockout escalates.
- [ ] Refresh rotation works; reuse revokes the session family.
- [ ] Session list shows device/time; revoke one and revoke all work immediately for refresh.
- [ ] Password reset invalidates sessions and does not enumerate accounts.
- [ ] Google sign-in works when configured and fails safely when not.
- [ ] 2FA enroll, confirm, login challenge, recovery code, regenerate, disable all work.
- [ ] Recovery codes are single-use and stored hashed.
- [ ] Reauthentication is required for sensitive actions and expires after 10 minutes.

### Accounts and transactions
- [ ] Account CRUD, archive/restore, reorder, spendable flag, negative-balance flag.
- [ ] Opening balance posts to equity and never appears as income.
- [ ] Balance equals sum of postings for every account after every test scenario.
- [ ] Archive with balance requires acknowledgement; history remains reportable.
- [ ] Delete blocked with postings; allowed for an unused account.
- [ ] Income/expense create, edit, archive, restore, status transitions per the matrix.
- [ ] Splits sum exactly; mismatch rejected on create and edit.
- [ ] Tags (system + custom) filter and analyze; necessity is optional and filterable.
- [ ] Audit shows every revision with before/after/actor/time and cannot be edited.
- [ ] Pending transactions never change balances; completing posts once; cancelled excluded.
- [ ] Stale `version` edits return 409 and write nothing.

### Transfers
- [ ] Same-currency transfer moves exactly the amount; no income/expense postings.
- [ ] Cross-currency transfer uses an explicit rate, records spread/fee, and balances each currency.
- [ ] Fees are expenses; principal is untouched.
- [ ] Same-account, archived-account, and insufficient-funds transfers are rejected.
- [ ] Failed transfer leaves no postings, detail, audit, or sequence bump.
- [ ] Idempotent replay does not move money twice.
- [ ] Transfer archive reverses correctly and is auditable.

### Budgets and periods
- [ ] Monthly/weekly/custom budgets with correct boundaries in the workspace timezone (incl. DST).
- [ ] Split-aware spending.
- [ ] Positive-only rollover with optional cap; overspending never creates negative rollover.
- [ ] Closed periods immutable; backdated edits produce prior-period adjustments, not rewrites.
- [ ] Threshold warnings fire once per threshold per period.
- [ ] Flexible vs fixed budgets drive the daily allowance correctly.
- [ ] Custom periods cannot overlap; validation is clear.

### Savings
- [ ] Goals with target, date, linked account, notes; edit and archive.
- [ ] Contributions of all four kinds validate correctly.
- [ ] Transfer-backed contribution creates transfer + contribution atomically.
- [ ] Earmarks never change balances/net worth; cap enforced sequentially and concurrently.
- [ ] Withdrawals reduce allocations and cannot exceed contributions.
- [ ] Archiving releases earmarks without moving money.
- [ ] Over-funding is displayed explicitly, not clamped.

### Debts
- [ ] Liability create/edit/archive; optional initial disbursement.
- [ ] Outstanding derived from ledger; not editable.
- [ ] Repayment splits principal/interest/fee and sums to the transaction amount.
- [ ] Principal > outstanding rejected.
- [ ] Interest and fees are expenses; principal is not.
- [ ] Net-worth effect matches the documented worked example.
- [ ] Payoff and history shown.

### Net worth, Safe-to-Spend, allowance, emergency fund
- [ ] Current and historical net worth; as-of uses historical postings.
- [ ] Savings goals are never counted as assets.
- [ ] FX policy disclosed; missing rate returns unavailable, never 1:1.
- [ ] Safe-to-Spend itemizes every component and lists included/excluded accounts with reasons.
- [ ] Pending outflows are projected, not silently deducted from balances.
- [ ] Daily allowance is zero (with explanation) when flexible budget ≤ 0 or the period ended.
- [ ] Emergency fund reproduces 300 × 6 = 1,800 and discloses computed vs override.

### Reports
- [ ] All report families implemented with period, account, category, tag filters.
- [ ] Every report reconciles to ledger sums for the same filters.
- [ ] Chart table alternatives match the series.
- [ ] Report exports match on-screen totals exactly.
- [ ] Empty periods show an explicit empty state, not fake zeroes.

### Notifications
- [ ] In-app center, read/unread, badge.
- [ ] Budget threshold, bill reminder, savings milestone notifications.
- [ ] Security notifications cannot be disabled and are marked locked.
- [ ] Quiet hours and digest cadence respected in the workspace timezone.
- [ ] Email suppressed without a verified address; failures recorded, not swallowed.

### Import / export / backup / restore
- [ ] CSV and XLSX import with mapping, validation, and clear row errors.
- [ ] Exact and potential duplicates detected and shown with reasons.
- [ ] No duplicate is discarded without a user decision; unresolved groups block commit.
- [ ] Import commit atomic; a forced failure imports zero rows.
- [ ] Imported rows produce audit entries referencing the job.
- [ ] Exports require reauth, expire, and are scoped to the workspace.
- [ ] Full archive export and restore reproduce balances and reconcile.
- [ ] Restore into a non-empty workspace is refused.
- [ ] Corrupt or wrong-version archives are refused with a clear error.
- [ ] Nightly backup + retention + checksum verification + failure alerting.
- [ ] Restore drill passes in CI on a release candidate.

### Privacy
- [ ] Data map page explains stored data and retention.
- [ ] Deletion requires reauth + typed confirmation (+2FA if enabled).
- [ ] 14-day grace period with cancellation works.
- [ ] Live data is hard-deleted at execution; audit record contains no financial content.
- [ ] Copy states backup expiry truthfully; no false "permanently deleted everywhere" claim.
- [ ] Exports/backups blocked after a deletion request.

### Dashboard and UX
- [ ] All twelve widgets exist and can be hidden/reordered; layout persists per user.
- [ ] Widgets with no data show an explicit empty state.
- [ ] Light and dark themes complete; no illegible combinations.
- [ ] Responsive at 360/768/1024/1440; no horizontal page scroll.
- [ ] Every destructive action has a confirmation stating consequences.
- [ ] Loading, empty, and error states exist on every data screen.
- [ ] Keyboard-only navigation works for primary flows.
- [ ] axe scan clean on primary screens; manual contrast/zoom check recorded.

---

## 2. Financial integrity gate (all must be green in CI)

- [ ] Every posted journal entry sums to zero per currency.
- [ ] No posting currency mismatches its ledger account.
- [ ] Every balance equals its posting sum.
- [ ] Pending/cancelled excluded; completed included exactly once.
- [ ] Edits reverse + repost + append audit; no posted row is updated or deleted.
- [ ] Splits sum to parent on create and edit.
- [ ] Transfers produce no income/expense principal postings.
- [ ] Cross-currency transfers balance and record spread/fees.
- [ ] Opening balances post to equity.
- [ ] Debt principal is a liability movement; interest/fees are expenses.
- [ ] Earmarks do not change balances/net worth and never exceed available funds.
- [ ] Net worth as-of uses historical postings and historical rates.
- [ ] Missing rate never falls back to 1:1.
- [ ] Reports reconcile to ledger.
- [ ] `check_ledger --fail-on-drift` passes on the seeded volume fixture.
- [ ] Property tests pass with ≥1000 generated event sequences.
- [ ] No float money in code or schema.

---

## 3. Security gate

- [ ] Argon2id configured and benchmarked.
- [ ] JWT secrets ≥512 bits; rotation documented.
- [ ] Cross-tenant matrix green for every endpoint family.
- [ ] Throttles verified under load, not merely configured.
- [ ] CORS allowlist, CSP, HSTS, nosniff, frame-ancestors verified in staging.
- [ ] No secrets in repo history (`gitleaks` clean).
- [ ] Backups encrypted, restore drill passed, retention documented.
- [ ] Exports require reauth and expire.
- [ ] Audit events cover all sensitive actions.
- [ ] Dependency audit and SAST clean or accepted with owners.
- [ ] Independent penetration test complete; findings resolved or explicitly accepted.
- [ ] Django admin disabled or staff+2FA only; no financial models registered.
- [ ] No third-party analytics or trackers in the authenticated app.

---

## 4. Quality gate

- [ ] Backend coverage: ledger/transactions/budgets/savings ≥95%; others ≥85%.
- [ ] Frontend coverage ≥80% on `lib/` and feature components.
- [ ] `ruff`, `mypy`, `eslint`, `tsc --noEmit` clean.
- [ ] OpenAPI validates; generated client compiles; no drift.
- [ ] E2E suite green on Chromium, WebKit, and a 390 px mobile viewport.
- [ ] Performance targets met at 50k transactions per workspace.
- [ ] No unbounded list query; query-count budgets enforced.
- [ ] Migrations forward and backward tested on a production-like dump.
- [ ] Docs updated and consistent with implementation; limitations listed.
- [ ] `docs/CHANGELOG.md` records what actually shipped, with dates.

---

## 5. Operational gate

- [ ] Production deployment reproducible from a clean checkout.
- [ ] Environment variables documented; production ones set in a secret store.
- [ ] Health checks, metrics, error tracking, and alerts configured.
- [ ] Log scrubbing verified (no tokens, passwords, or financial payloads).
- [ ] Database connection limits, statement timeout, and worker concurrency sized.
- [ ] Backup schedule, retention, and restore runbook written and rehearsed.
- [ ] Rollback plan tested for an application release and a migration.
- [ ] On-call/incident contact and escalation documented.
- [ ] Legal/privacy review of copy and retention completed for the target jurisdiction.
- [ ] Support path for locked-out 2FA users exists and is documented.

---

## 6. Explicitly not required for V1.0

Passkeys, recurring transactions, scheduled transfers, interest accrual automation, web push, rollover
proration, multi-currency splits, attachments/OCR, investment performance, Khmer localization, shared
workspaces, bank aggregation, native apps, AI chat.

---

## 7. Sign-off

| Role | Name | Date | Scope |
|---|---|---|---|
| Product owner | | | Scope and copy |
| Engineering | | | Functional + technical gates |
| Security review | | | Security gate |
| Manual QA | | | UX, accessibility, destructive flows |

Release is blocked while any mandatory checkbox is unchecked or any P0/P1 defect is open.
