# Planning Review — XakuFinance V1.0

**Date:** 2026-11-17
**Purpose:** the Step 8 review required before implementation: prove the package is internally consistent,
financially coherent, and implementable. This is a self-review with evidence, not a celebration.

---

## 1. Requirement coverage

| Check | Result |
|---|---|
| Every brief section mapped to requirement IDs | Yes — `docs/SRS.md` §3.1–3.17 covers auth, dashboard, accounts, transactions, transfers, budgets, periods, savings, debts, net worth, Safe-to-Spend, daily allowance, emergency fund, reports, insights, notifications, import/export, privacy, backups, workspace |
| Mandatory / optional / future separated | Yes — MoSCoW per row; totals verified by script: **149 M, 7 S, 8 C, 5 W** across 169 FR rows, plus 17 NFRs |
| Missing requirements identified | 6 gaps logged and resolved (G-01…G-16), notably recurring obligations, notification schedules, budget thresholds, savings earmark semantics, FX residual, interest accrual |
| Contradictions resolved | Yes — one transaction aggregate vs parallel records, derived vs stored balance, pending vs Safe-to-Spend, archive vs delete, custom periods shared by budgets and reports |
| Each M requirement has an owning phase | Yes — Phase 1–6 mapping in `docs/ROADMAP.md`; reports/analytics split across 2.5, 4.3 |
| Deferred items documented with reasons | Yes — `docs/FEATURE_MATRIX.md` |

## 2. Financial consistency (arithmetic verified by hand)

| Scenario | Expected | Verified |
|---|---|---|
| $100 expense split 60/40 | expense +100, asset −100, sum 0 | Yes |
| $100 same-currency transfer | asset −100, asset +100, income/expense 0 | Yes |
| $100 USD → 405,000 KHR at reference 4,100 | USD leg sums 0; KHR: +40,500,000 savings, +500,000 fee, −41,000,000 clearing = 0 | Yes |
| $500 opening balance | asset +500, equity +500, income 0 | Yes |
| $1,000 borrowing | asset +1,000, liability +1,000, net worth unchanged | Yes |
| $100 principal + $10 interest repayment | asset −110, liability −100, expense +10, net worth −10 | Yes |
| Worked end-to-end example (§11) | net worth 1,500 → 4,500 → 3,600 → 3,500 → 3,500 → 3,500 → 3,490 | Yes, recomputed line by line |
| Emergency fund 300 × 6 | 1,800 | Yes |
| Daily allowance 280 / 14 | 20, and 0 when remaining ≤ 0 | Yes |

Rounding: one quantization point per conversion, half-up; residual explicitly posted. No scenario adds
USD to KHR without a rate.

## 3. Double-counting analysis

| Pair | Risk | Resolution |
|---|---|---|
| Account balance vs savings goal progress | Counting goal progress as an asset | Net worth reads only asset postings; goals are earmarks; test `test_net_worth_ignores_goal_progress` |
| Transfer vs income/expense | Double counting a movement | Transfer posts asset↔asset only; no income/expense postings; test |
| Opening balance vs income | Inflating income | Equity posting; test |
| Debt disbursement vs income | Counting borrowed money as earnings | Liability credit; test |
| Debt repayment principal vs expense | Counting the same outflow twice | Principal debits liability; only interest/fees are expenses; test |
| Split allocations vs whole transaction | Counting $100 in three categories | Reports aggregate splits, never the parent amount when split; test |
| Budget spend vs expense report | Different totals | Both read splits + completed only; reconciliation test |
| Snapshot vs ledger | Stale cache | Snapshot keyed by `ledger_seq`; invalidated when it moves |
| Archived transaction vs current balances | Counting a reversed entry | Archive reverses; archived rows excluded from postings |
| Pending vs completed | Counting twice on completion | Pending entry is `pending`; completion flips to `posted`, no duplicate postings; test |

## 4. Isolation and authorization

- Every financial table has `workspace_id`; the manager requires a workspace.
- Cross-workspace access returns 404, with a matrix test per endpoint family.
- No client-supplied workspace id is trusted.
- One workspace per user is a DB constraint, not a convention.
- Background jobs resolve ownership; no task accepts an unverified workspace id.

Residual: an operator with database credentials can read data. Accepted and documented; mitigated by least
privilege, encryption at rest, and audit.

## 5. Security review

Addressed: Argon2id, rotating refresh with reuse detection, HttpOnly refresh cookie, no tokens in
localStorage, optional TOTP with encrypted secrets and hashed recovery codes, reauth for sensitive actions,
throttles, CORS allowlist, CSP/headers, upload limits, workspace isolation, encrypted backups, signed
expiring exports, truthful deletion messaging, audit events.

Open before release: independent penetration test, production secrets configuration, legal review of
retention copy. These are release blockers, not "nice to have".

## 6. Testing review

- The 35-item financial integrity suite covers every accounting rule plus rollback, idempotency, history,
  isolation, imports, and restore.
- Property tests pin decimal arithmetic and generated ledger sequences.
- Each Phase 1 task has a failing test, a verification command, and an exit check.
- E2E covers the flows where numbers must agree across screens.
- Coverage gates are floors; the integrity suite is the real gate.
- Manual verification is recorded, not assumed.

Gap: no test yet exists (nothing is implemented). `docs/TESTING.md` is a plan, not evidence.

## 7. Roadmap feasibility

- Phase 1 is decomposed into 16 tasks with exact files, interfaces, tests, and commands.
- The ledger is built before any feature depends on it.
- Reporting depends on budgets and savings being settled; the order reflects that.
- Hard dependencies are graphed; no phase requires a later phase.
- Effort ranges sum to 27–40 developer-weeks for one experienced developer. This is plausible but tight;
  the S/C items are the release valve.
- Deferred features do not block any mandatory requirement.

## 8. Remaining decisions that genuinely need the product owner

None block Phase 1. Before Phase 3/4, confirm:

1. Whether a credit card is modeled as a liability only (current default) or also as an account.
2. Whether custom-period rollover proration is needed in V1.1.
3. The jurisdiction whose privacy retention rules govern launch copy.

## 9. Verdict

The package is internally consistent, arithmetically checked, and ready for Phase 1 implementation. It is
**not** evidence that any feature exists. The next action is to approve the plan and execute Task 1.
