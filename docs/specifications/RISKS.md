# Risk and Dependency Assessment — XakuFinance

**Status:** planning baseline. Reviewed at each phase exit.
**Scoring:** likelihood (L) and impact (I) each 1–5; score = L×I. ≥15 requires an owner and an active
mitigation before the phase starts.

---

## 1. Product and scope risks

| ID | Risk | L | I | Score | Mitigation |
|---|---|---:|---:|---:|---|
| R-01 | V1 scope (≈150 mandatory requirements) overwhelms a small team, producing many half-features | 4 | 5 | 20 | Phase gates with working software; defer S/C items explicitly; no feature starts before its dependencies are green |
| R-02 | Users expect bank sync and treat CSV import as a defect | 3 | 3 | 9 | State import scope in onboarding; design a clean import wizard |
| R-03 | Dashboard becomes a wall of widgets nobody understands | 3 | 3 | 9 | Fixed widget registry, one hero figure, "how calculated" disclosures |
| R-04 | Multi-currency UX confuses users and erodes trust | 4 | 4 | 16 | Always show currency codes; disclose rates; never 1:1 fallback; per-currency totals first |
| R-05 | Users expect savings goals to "add" money | 4 | 3 | 12 | Explicit copy: earmarks are claims on existing money; net worth unchanged; tests enforce |
| R-06 | Debt principal repayment is misread as reducing net worth | 4 | 3 | 12 | Show net-worth effect; explainer on the repayment confirmation |
| R-07 | Custom periods and rollover create rule ambiguity | 3 | 4 | 12 | Documented defaults; proration deferred; closed periods immutable |
| R-08 | Categories drift into an unusable tree | 2 | 3 | 6 | Max depth 2; archive not delete; default set |
| R-09 | Imported duplicate transactions inflate reports | 3 | 5 | 15 | Two-tier detection + mandatory review; unresolved groups block commit |
| R-10 | Reports disagree with each other, destroying trust | 3 | 5 | 15 | One ledger fact layer; reconciliation block per report; CI invariant |

## 2. Financial and accounting risks

| ID | Risk | L | I | Score | Mitigation |
|---|---|---:|---:|---:|---|
| R-11 | A write path bypasses the ledger and stores a balance | 3 | 5 | 15 | No balance column; single posting API; review gate; `check_ledger` |
| R-12 | Posted history is mutated, invalidating past reports | 2 | 5 | 10 | Immutable entries, DB triggers, reversal-only edits, append-only audit |
| R-13 | Rounding creates or destroys minor units in FX transfers | 4 | 4 | 16 | Integer minor units, explicit fee/spread, per-currency balancing, property tests |
| R-14 | Split totals drift after an edit | 3 | 4 | 12 | Deferred DB trigger + service validation + edit test |
| R-15 | Earmark allocation exceeds real money under concurrency | 3 | 5 | 15 | Row locks + serializable transaction + concurrency test + nightly check |
| R-16 | Historical net worth computed from current balances | 3 | 5 | 15 | As-of posting queries; snapshots keyed by ledger seq; historical fixture tests |
| R-17 | Closed budget periods change after backdated edits | 3 | 4 | 12 | Immutable closed periods; prior-period adjustment reporting |
| R-18 | Debt interest is recorded as principal (or vice versa) | 3 | 4 | 12 | Explicit split fields, sum trigger, ledger recipes, tests |
| R-19 | Currency conversion silently uses a stale or missing rate | 3 | 4 | 12 | Rate source + date always returned; no rate → unavailable |
| R-20 | Reconstruction after disaster loses postings | 2 | 5 | 10 | Verified backups + restore drills + reconciliation before reopening writes |

## 3. Security and privacy risks

| ID | Risk | L | I | Score | Mitigation |
|---|---|---:|---:|---:|---|
| R-21 | Cross-workspace data leak via a missed filter | 3 | 5 | 15 | Scoped manager, 404 policy, endpoint matrix tests, review |
| R-22 | Token theft via XSS | 2 | 5 | 10 | No localStorage, CSP, React escaping, no rich text |
| R-23 | Credential stuffing succeeds | 4 | 4 | 16 | Argon2id, throttles, lockout, optional 2FA, breach-pattern rejection |
| R-24 | Backup or export bucket is misconfigured public | 2 | 5 | 10 | Private bucket, block public access, signed URLs, IaC check |
| R-25 | Deletion claim is false because backups remain | 3 | 4 | 12 | Truthful copy with expiry date; deletion test asserts messaging |
| R-26 | Operator/db access exposes financial data | 2 | 5 | 10 | Least privilege, encrypted volumes, audit, contract; residual risk accepted |
| R-27 | Dependency compromise | 2 | 5 | 10 | Minimal deps, lockfiles, audits, pinned versions, review |
| R-28 | 2FA recovery codes are stored reversibly | 1 | 5 | 5 | Argon2 hashes only; test asserts no plaintext column |
| R-29 | AI provider retains or trains on user data | 3 | 4 | 12 | Off by default; minimized summaries; zero-retention contract or no AI |

## 4. Technical risks

| ID | Risk | L | I | Score | Mitigation |
|---|---|---:|---:|---:|---|
| R-30 | Ledger queries slow as postings grow | 3 | 3 | 9 | Indexes, period-bounded aggregates, snapshots, partition plan |
| R-31 | Report N+1 queries and unbounded scans | 4 | 3 | 12 | Selectors with `.values()`, query-count tests, pagination caps |
| R-32 | Celery tasks double-run (imports, rollover, notifications) | 3 | 4 | 12 | Idempotency keys, unique constraints, single beat, task locks |
| R-33 | Migrations lock large tables in production | 3 | 4 | 12 | Additive migrations, `NOT VALID` constraints, concurrent indexes |
| R-34 | Frontend money math diverges from backend | 3 | 4 | 12 | Display-only client math; generated types; no float; server totals |
| R-35 | Generated client drifts from API | 3 | 3 | 9 | CI regeneration diff; generated folder never hand-edited |
| R-36 | Timezone/DST bugs shift period boundaries | 4 | 4 | 16 | Workspace-timezone period utility, DST tests, explicit labels |
| R-37 | Restore is never actually tested | 3 | 5 | 15 | Nightly restore drill; release-candidate gate |
| R-38 | Redis flush breaks something treated as truth | 2 | 4 | 8 | Redis is cache/broker only; documented; tests with flushed cache |
| R-39 | Accessibility regressions in charts and dialogs | 4 | 2 | 8 | Radix primitives, axe in CI, manual audit, table fallbacks |

## 5. Delivery and operational risks

| ID | Risk | L | I | Score | Mitigation |
|---|---|---:|---:|---:|---|
| R-40 | Solo developer burnout / bus factor | 4 | 5 | 20 | Documentation-first, small milestones, no heroics; scope is explicitly reducible via S/C |
| R-41 | No independent security review before launch | 3 | 5 | 15 | Pen test scheduled in Phase 6; release blocker |
| R-42 | Hosting costs exceed expectation | 3 | 2 | 6 | Single small deployment; managed Postgres; object storage lifecycle |
| R-43 | Email deliverability problems | 3 | 3 | 9 | Reputable provider, SPF/DKIM/DMARC, in-app fallback |
| R-44 | Google OAuth verification/config friction | 3 | 2 | 6 | Feature-flagged; password auth always works |
| R-45 | Legal/privacy obligations vary by jurisdiction | 3 | 4 | 12 | Conservative defaults, truthful retention copy, counsel review before public launch |
| R-46 | Estimates are optimistic (finance + security always overrun) | 5 | 3 | 15 | Ranges not promises; buffers; phase gates |

---

## 6. External dependencies

| Dependency | Needed for | Failure mode | Fallback |
|---|---|---|---|
| PostgreSQL 16+ | Everything | App down | HA/managed instance, PITR |
| Redis | Celery, caches | Background jobs stall | Retry; core reads/writes still work |
| Object storage | Exports, backups | Async features fail | Local disk in dev; alert; retry |
| Email provider | Verification, reset, notifications | Users cannot verify/reset | In-app support path; logs in dev (Mailpit) |
| Google Identity | Social login | Google button fails | Password login remains |
| LLM provider | Insights only | Insights unavailable | Deterministic summary; core unaffected |
| Exchange-rate provider (optional) | Convenience rates | Manual rates required | Manual rate entry; no default 1:1 |

No external dependency is allowed to become a single point of failure for recording or reading core
financial data.

---

## 7. Assumption log

Assumptions A-01…A-20 are in `docs/SRS.md` §2. The ones with the largest blast radius if wrong:

| Assumption | If wrong | Cost to change |
|---|---|---|
| One workspace per user | A household/shared model is needed | High: permissions, membership, ownership rules, tests |
| Transactions are account-currency only | Users want per-transaction FX | High: ledger recipes, split rules, reports |
| Earmarks are the savings model | Users expect separate savings sub-accounts | Medium: UI + goal model, ledger unaffected |
| Reporting uses transaction-date/period-end rates | Users want one pinned rate everywhere | Low: policy is centralized |
| 14-day deletion grace | Legal requires immediate or longer | Low: constant + copy |
| KHR 2 decimals | Users expect integer riel | Low: currency metadata; display formatting |

---

## 8. Risk review cadence

- Before each phase: confirm scores, owners, and mitigations; no phase starts with an unmitigated ≥15.
- At each milestone: update this file with what actually happened; remove risks that no longer exist.
- Before release: full review; residual risks listed in `docs/SECURITY.md` §12.1 and the launch decision.
