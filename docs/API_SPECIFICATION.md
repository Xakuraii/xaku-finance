# API Specification — XakuFinance v1

**Base path:** `/api/v1/`
**Status:** planned contract. Generated `docs/openapi.yaml` will be authoritative once code exists.
**Auth:** `Authorization: Bearer <access_jwt>` except the public auth endpoints.

---

## 1. Conventions

### 1.1 Money

Requests send decimal **strings**, never JSON numbers:

```json
{ "amount": "1250.50", "currency": "USD" }
```

Responses include both a canonical decimal string and minor units:

```json
{
  "amount": "1250.50",
  "amount_minor": 125050,
  "currency": "USD",
  "amount_display": "1,250.50"
}
```

Rules:

- Maximum 2 decimals for USD/KHR. Excess precision is rejected with `invalid_precision`, not rounded
  silently.
- `amount` is always a positive magnitude on transactions; direction is the transaction type.
- Converted values add `converted: {amount, currency, rate, rate_date, rate_source, rate_policy}`.
- A currency with no available rate yields `conversion_unavailable: true`; the field is never faked.

### 1.2 Identifiers, dates, pagination

- IDs are UUID strings.
- Dates are `YYYY-MM-DD`; timestamps are ISO 8601 UTC (`2026-11-17T10:15:30Z`).
- Period selectors: `period=calendar_month|calendar_week|calendar_year|custom` with
  `start=YYYY-MM-DD&end=YYYY-MM-DD` required for `custom`. Responses echo
  `period: {start, end, timezone, label, resolved_from}`.
- Cursor pagination: `?limit=50&cursor=<opaque>`; response
  `{"results": [...], "next_cursor": "...", "has_more": true}`. Default limit 25, max 200.
- Filtering uses explicit whitelisted params (`account_id`, `category_id`, `tag_id`, `status`, `from`,
  `to`, `necessity`, `q`). Unknown params are ignored but logged; invalid values return 400.
- Sorting: `ordering=occurred_on|-occurred_on,amount`. Whitelisted fields only.

### 1.3 Idempotency

All financial `POST`s accept `Idempotency-Key: <uuid or 8–80 chars>`. Same key + same body returns the
original response with `Idempotent-Replay: true`. Same key + different body returns
`409 idempotency_conflict`.

### 1.4 Errors

```json
{
  "error": {
    "code": "insufficient_funds",
    "message": "This transfer needs 120.00 USD but 80.00 USD is available.",
    "field": "amount",
    "details": { "available": "80.00", "requested": "120.00" }
  },
  "request_id": "req_01JABCDEF"
}
```

| HTTP | Codes |
|---|---|
| 400 | `validation_error`, `invalid_precision`, `invalid_period`, `unbalanced_entry`, `split_total_mismatch` |
| 401 | `not_authenticated`, `token_expired`, `invalid_token` |
| 403 | `permission_denied`, `reauth_required`, `mfa_required`, `email_unverified` |
| 404 | `not_found` (also used for cross-workspace resources) |
| 409 | `idempotency_conflict`, `duplicate_opening_balance`, `transfer_same_account`, `period_overlap`, `account_has_postings` |
| 422 | `insufficient_funds`, `earmark_exceeds_balance`, `principal_exceeds_outstanding`, `currency_mismatch`, `archived_account` |
| 423 | `account_locked` (temporary lockout) |
| 429 | `rate_limited` with `Retry-After` |
| 500 | `internal_error` (no internals leaked) |

### 1.5 Throttles

| Scope | Limit |
|---|---|
| Anonymous per IP | 60/min |
| Authenticated per user | 300/min |
| Login / 2FA verify | 10/min per IP+email, then exponential lockout |
| Registration | 5/hour per IP |
| Password reset | 5/hour per email, 20/hour per IP |
| Export / backup creation | 5/hour per user |
| AI insight generation | 20/day per user |
| Import upload | 10/hour per user |

### 1.6 Headers

Responses include `X-Request-ID`, `X-API-Version: 1`, `Cache-Control: no-store` on financial data.
Security headers are documented in `docs/SECURITY.md`.

---

## 2. Authentication

### 2.1 Register

`POST /auth/register/`

```json
{
  "email": "mara@example.com",
  "password": "correct horse battery staple",
  "display_name": "Mara",
  "timezone": "Asia/Phnom_Penh",
  "reporting_currency": "USD"
}
```

`201` creates user + profile + workspace + default categories/tags in one transaction, sends a
verification email, and returns tokens (so the user can start immediately with limited access).

```json
{
  "user": {"id": "…", "email": "mara@example.com", "is_email_verified": false},
  "workspace": {"id": "…", "name": "Mara's finances", "reporting_currency": "USD",
                "timezone": "Asia/Phnom_Penh"},
  "access": "<jwt>",
  "access_expires_in": 900,
  "refresh_expires_in": 604800
}
```

`Set-Cookie: refresh=…; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth/`

### 2.2 Log in

`POST /auth/login/` → `200` (tokens) or `202` when 2FA is required:

```json
{"mfa_required": true, "mfa_token": "<short-lived>", "methods": ["totp", "recovery_code"]}
```

Failures are always `401 invalid_credentials`, regardless of whether the email exists. Lockout after 5
failures in 15 minutes is progressive (1, 5, 15, 60 minutes).

### 2.3 2FA

| Endpoint | Purpose |
|---|---|
| `POST /auth/2fa/verify/` | `{mfa_token, method, code}` → tokens (single-use token) |
| `POST /auth/2fa/setup/` | Begin enrollment → `{secret, otpauth_uri, qr_svg}` (requires reauth) |
| `POST /auth/2fa/confirm/` | `{code}` → enables 2FA and returns 10 recovery codes **once** |
| `POST /auth/2fa/disable/` | `{password, code}` → disables and revokes recovery codes |
| `POST /auth/2fa/recovery-codes/` | `{password, code}` → regenerates and returns new codes |

### 2.4 Sessions

| Endpoint | Purpose |
|---|---|
| `GET /auth/sessions/` | List sessions `{id, device, approx_location, created_at, last_used_at, current}` |
| `DELETE /auth/sessions/{id}/` | Revoke one (reauth not required for own sessions) |
| `POST /auth/logout/` | Revoke current session, clear cookie |
| `POST /auth/logout-all/` | Revoke all sessions |
| `POST /auth/refresh/` | Rotate refresh cookie → new access; reuse revokes the family |
| `POST /auth/reauth/` | `{password?, code?}` → sets `reauth_at` for 10 minutes |

### 2.5 Email, password, Google

| Endpoint | Purpose |
|---|---|
| `POST /auth/verify-email/` | `{token}` |
| `POST /auth/verify-email/resend/` | Throttled |
| `POST /auth/password/forgot/` | Always `202` (no account enumeration) |
| `POST /auth/password/reset/` | `{token, new_password}`; revokes all sessions |
| `POST /auth/password/change/` | `{current_password, new_password}`; revokes other sessions |
| `POST /auth/google/` | `{id_token}` → tokens, links by verified email |

Google failure codes: `google_invalid_token`, `google_email_unverified`, `google_link_required`
(returns `409`; the user must log in with the password and link explicitly).

---

## 3. Profile and workspace

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/me/` | User + profile + workspace summary + capabilities |
| `PATCH` | `/me/` | display_name, avatar_url, timezone, locale, week_start, theme |
| `PATCH` | `/workspace/` | name, reporting_currency, timezone, week_start |
| `GET` | `/workspace/summary/` | counts, onboarding state, feature flags |
| `GET` | `/dashboard/` | Assembled dashboard payload for the active layout and period |
| `GET` | `/dashboard/layout/` | Widgets in order |
| `PUT` | `/dashboard/layout/` | Full replacement, validated against the widget registry |
| `POST` | `/dashboard/layout/reset/` | Default layout |

`GET /dashboard/?period=calendar_month&start=…&end=…&currency=USD`

```json
{
  "period": {"start": "2026-11-01", "end": "2026-11-30", "timezone": "Asia/Phnom_Penh"},
  "balances": [
    {"currency": "USD", "total": "4210.75"},
    {"currency": "KHR", "total": "1250000.00"}
  ],
  "converted_total": {"amount": "4521.50", "currency": "USD",
    "rate_policy": "period_end", "rates_used": [{"pair": "USD/KHR", "rate": "4100", "date": "2026-11-30"}]},
  "income": {"amount": "3000.00", "currency": "USD", "converted": {…}},
  "expenses": {"amount": "1010.00", "currency": "USD"},
  "net_worth": {"amount": "3490.00", "currency": "USD", "change": "110.00", "change_direction": "down"},
  "safe_to_spend": {…},
  "daily_allowance": {…},
  "budget_overview": […],
  "savings_progress": […],
  "recent_transactions": […],
  "charts": {"income_vs_expense": […], "spending_by_category": […]},
  "widget_order": ["net_worth", "safe_to_spend", "…"]
}
```

Widgets the user hid are absent. Widgets with insufficient data return an explicit
`{"state": "empty", "reason": "no_transactions"}` rather than zeroes pretending to be facts.

---

## 4. Accounts

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/accounts/` | List with derived balances; `?include_archived=` |
| `POST` | `/accounts/` | Create (optional opening balance) |
| `GET` | `/accounts/{id}/` | Detail with balance, reconciliation status, counts |
| `PATCH` | `/accounts/{id}/` | Metadata only; currency locked once postings exist |
| `POST` | `/accounts/{id}/archive/` | `{reason, acknowledge_balance}` |
| `POST` | `/accounts/{id}/restore/` | |
| `DELETE` | `/accounts/{id}/` | Only if no postings exist |
| `POST` | `/accounts/reorder/` | `{ids: [...]}` |
| `GET` | `/accounts/{id}/register/` | Paginated ledger register (transactions + running balance) |
| `GET` | `/accounts/{id}/balance-history/` | Daily balances for a period |

Create:

```json
{
  "name": "KBank checking",
  "account_type": "checking",
  "currency": "USD",
  "opening_balance": "2000.00",
  "opening_balance_date": "2026-11-01",
  "is_spendable": true,
  "description": "Main spending account",
  "allows_negative_balance": false
}
```

`201` returns the account and `opening_balance_transaction_id` when applicable. A second opening balance
for the same account returns `409 duplicate_opening_balance`.

Archive with a non-zero balance:

```json
{"reason": "Closed at bank", "acknowledge_balance": true}
```

Without acknowledgement → `422 account_balance_not_zero` with the balance in `details`. History is never
deleted.

---

## 5. Categories and tags

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/categories/` | `?kind=expense&include_archived=` |
| `POST` | `/categories/` | name, kind, parent_id, icon, color |
| `PATCH` | `/categories/{id}/` | rename/recolor/reparent |
| `POST` | `/categories/{id}/archive/` | blocked if active budgets reference it unless reassigned |
| `GET` | `/tags/` | list with usage counts |
| `POST` | `/tags/` | create custom |
| `PATCH` | `/tags/{id}/` | rename/recolor (system tags: color only) |
| `DELETE` | `/tags/{id}/` | blocked when in use; archive instead |

Default categories seeded per workspace: Housing, Groceries, Utilities, Transport, Dining, Health,
Education, Personal care, Entertainment, Savings, Debt payments, Fees, Other. Default tags from the SRS.

---

## 6. Transactions

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/transactions/` | Paginated list with filters |
| `POST` | `/transactions/` | Create income/expense (or transfer via `/transfers/`) |
| `GET` | `/transactions/{id}/` | Detail incl. splits, tags, audit summary, entry status |
| `PATCH` | `/transactions/{id}/` | Edit (audited, reverse/repost) |
| `POST` | `/transactions/{id}/archive/` | `{reason}` |
| `POST` | `/transactions/{id}/restore/` | |
| `POST` | `/transactions/{id}/status/` | `{status, reason}` with the state matrix enforced |
| `GET` | `/transactions/{id}/audit/` | Paginated immutable revisions |
| `GET` | `/transactions/summary/` | Totals for the active filters |
| `POST` | `/transactions/bulk-tag/` | `{ids, add_tags, remove_tags}` (S) |

Filters: `account_id`, `category_id`, `tag_id`, `status`, `type`, `necessity`, `from`, `to`, `q`,
`min_amount`, `max_amount`, `include_archived`, `is_split`.

Create income:

```json
{
  "type": "income",
  "account_id": "…",
  "amount": "3000.00",
  "currency": "USD",
  "occurred_on": "2026-11-15",
  "title": "Monthly salary",
  "category_id": "…",
  "description": "November payroll",
  "notes": "Includes overtime",
  "tags": ["work"],
  "necessity": null,
  "status": "completed"
}
```

Create a split expense:

```json
{
  "type": "expense",
  "account_id": "…",
  "amount": "100.00",
  "currency": "USD",
  "occurred_on": "2026-11-16",
  "title": "Supermarket run",
  "merchant": "Lucky Supermarket",
  "status": "completed",
  "necessity": "essential",
  "tags": ["family", "weekend"],
  "splits": [
    {"category_id": "…groceries", "amount": "60.00"},
    {"category_id": "…household", "amount": "25.00"},
    {"category_id": "…personal", "amount": "15.00"}
  ]
}
```

Errors: splits not summing to `100.00` → `400 split_total_mismatch` with `details.difference`; currency
≠ account currency → `422 currency_mismatch`; archived account → `422 archived_account`.

Response (abridged):

```json
{
  "id": "…",
  "type": "expense",
  "status": "completed",
  "amount": "100.00",
  "amount_minor": 10000,
  "currency": "USD",
  "account": {"id": "…", "name": "KBank checking"},
  "occurred_on": "2026-11-16",
  "title": "Supermarket run",
  "is_split": true,
  "splits": [
    {"id": "…", "category": {"id": "…", "name": "Groceries"}, "amount": "60.00"},
    {"id": "…", "category": {"id": "…", "name": "Household"}, "amount": "25.00"},
    {"id": "…", "category": {"id": "…", "name": "Personal care"}, "amount": "15.00"}
  ],
  "tags": [{"id": "…", "name": "family"}],
  "necessity": "essential",
  "audit": {"revision": 1, "last_action": "created", "last_actor": "…", "last_at": "…"},
  "links": {"self": "/api/v1/transactions/…", "account": "/api/v1/accounts/…"}
}
```

Pending transactions return `"affects_balance": false`. The client must not present pending amounts as
spent.

Edit requires `If-Match` with the current `version` (optimistic concurrency) OR `version` in the body:
`409 version_conflict` with the current resource when stale, preventing silent overwrites from two tabs.

Audit entry:

```json
{
  "revision": 2,
  "action": "updated",
  "actor": {"id": "…", "display_name": "Mara"},
  "changed_fields": ["amount", "splits"],
  "before": {"amount": "100.00", "splits": [...]},
  "after": {"amount": "110.00", "splits": [...]},
  "reason": "Forgot the delivery fee",
  "created_at": "2026-11-17T09:12:00Z"
}
```

---

## 7. Transfers

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/transfers/` | List with source/destination |
| `POST` | `/transfers/` | Create (atomic, idempotent) |
| `GET` | `/transfers/{id}/` | Detail with rate, spread, fees, entry status |
| `POST` | `/transfers/{id}/archive/` | Reverse with reason |

```json
{
  "source_account_id": "…checking-usd",
  "destination_account_id": "…savings-khr",
  "amount": "100.00",
  "currency": "USD",
  "destination_amount": "405000.00",
  "rate": "4050.00",
  "reference_rate": "4100.00",
  "transfer_fee": "0.00",
  "transfer_fee_category_id": null,
  "conversion_fee_category_id": "…fees",
  "occurred_on": "2026-11-17",
  "notes": "Top up riel savings",
  "savings_goal_id": null
}
```

Response includes `conversion_fee: "5000.00" KHR`, `savings_contribution_id` when linked, and
`conversion: {rate, reference_rate, spread_amount, spread_currency, policy_note}`.

Validation failures: same account → `409 transfer_same_account`; missing rate for cross-currency →
`400 validation_error`; insufficient funds → `422 insufficient_funds`; missing fee category when a spread
exists → `400 validation_error`. The API never silently rounds a spread to zero.

Same-currency example: omit `destination_amount`, `rate`, `reference_rate`; supplying them → `400`.

---

## 8. Budgets and periods

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/budgets/` | List with current-period progress |
| `POST` | `/budgets/` | Create |
| `GET` | `/budgets/{id}/` | Detail with current and previous periods |
| `PATCH` | `/budgets/{id}/` | Prospective edits only |
| `POST` | `/budgets/{id}/archive/` | |
| `GET` | `/budgets/{id}/periods/` | Period history incl. rollover |
| `GET` | `/budgets/overview/` | Dashboard widget payload with totals |
| `GET` | `/financial-periods/` | Custom periods |
| `POST` | `/financial-periods/` | Create custom period |
| `PATCH`/`DELETE` | `/financial-periods/{id}/` | If not referenced by a closed period |

`GET /budgets/{id}/?period=calendar_month`

```json
{
  "id": "…",
  "name": "Groceries",
  "category": {"id": "…", "name": "Groceries"},
  "currency": "USD",
  "period_type": "monthly",
  "is_flexible": true,
  "base_amount": "200.00",
  "rollover_enabled": true,
  "rollover_cap": null,
  "period": {"start": "2026-11-01", "end": "2026-11-30", "status": "open"},
  "spent": "160.00",
  "rollover_in": "0.00",
  "rollover_out_projected": "40.00",
  "remaining": "40.00",
  "percent_used": 80.0,
  "state": "warning",
  "thresholds": {"warn_at": 80, "alert_at": 100},
  "next_period_available": "240.00"
}
```

`spent` uses split allocations. Editing a closed period's underlying transaction does not change its
numbers; the response adds `prior_period_adjustments` when relevant.

---

## 9. Savings goals

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/savings-goals/` | List with progress and available account capacity |
| `POST` | `/savings-goals/` | Create |
| `GET` | `/savings-goals/{id}/` | Detail incl. contributions and allocation |
| `PATCH` | `/savings-goals/{id}/` | Metadata, target |
| `POST` | `/savings-goals/{id}/archive/` | Releases earmarks (money does not move) |
| `DELETE` | `/savings-goals/{id}/` | Only when no contributions |
| `POST` | `/savings-goals/{id}/contributions/` | Record transfer, earmark, adjustment, withdrawal |
| `GET` | `/savings-goals/{id}/contributions/` | History |
| `GET` | `/savings-goals/{id}/projection/` | Required monthly / ETA at current pace |

Earmark contribution:

```json
{"kind": "earmark", "account_id": "…savings", "amount": "300.00", "currency": "USD",
 "occurred_on": "2026-11-17", "note": "Emergency buffer"}
```

Transfer-backed contribution (creates the transfer and contribution atomically):

```json
{"kind": "transfer_in", "source_account_id": "…checking", "account_id": "…savings",
 "amount": "100.00", "currency": "USD", "occurred_on": "2026-11-17",
 "idempotency_hint": "nov-savings"}
```

`422 earmark_exceeds_balance` returns `{available: "…", already_allocated: "…", requested: "…"}`.
The response for `transfer_in` includes `transfer_id` and confirms `assets_unchanged: true` for clarity
in the UI.

Progress:

```json
{
  "target": "1800.00",
  "contributed": "900.00",
  "remaining": "900.00",
  "percent": 50.0,
  "target_date": "2027-05-01",
  "pace": {"average_monthly": "150.00", "required_monthly": "150.00",
           "estimated_completion": "2027-05-01", "on_track": true},
  "allocations": [{"account_id": "…", "allocated": "900.00", "account_available": "1200.00"}]
}
```

---

## 10. Debts

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/liabilities/` | List with outstanding and progress |
| `POST` | `/liabilities/` | Create (optionally with initial disbursement) |
| `GET` | `/liabilities/{id}/` | Detail + repayment history + interest records |
| `PATCH` | `/liabilities/{id}/` | Metadata; principal is never editable |
| `POST` | `/liabilities/{id}/archive/` | |
| `POST` | `/liabilities/{id}/repayments/` | Record principal/interest/fee against an account |
| `GET` | `/liabilities/{id}/repayments/` | History |
| `POST` | `/liabilities/{id}/interest-records/` | Charge interest (accrual/manual) |
| `GET` | `/liabilities/{id}/projection/` | Payoff estimate |

Create with disbursement:

```json
{
  "name": "Student loan",
  "liability_type": "student_loan",
  "currency": "USD",
  "original_principal": "1000.00",
  "interest_rate": "5.00",
  "interest_type": "simple",
  "lender": "University credit union",
  "due_day": 15,
  "initial_disbursement": {"account_id": "…checking", "occurred_on": "2026-11-01",
                           "category_id": null}
}
```

Repayment:

```json
{
  "account_id": "…checking",
  "principal": "100.00",
  "interest": "10.00",
  "fee": "0.00",
  "occurred_on": "2026-11-17",
  "note": "November payment",
  "interest_category_id": "…interest",
  "fee_category_id": "…fees"
}
```

Response:

```json
{
  "id": "…",
  "principal": "100.00", "interest": "10.00", "fee": "0.00", "total": "110.00",
  "outstanding_before": "1000.00", "outstanding_after": "900.00",
  "net_worth_effect": {"principal": "100.00", "expense": "10.00"},
  "transaction_id": "…", "entry_status": "posted"
}
```

`net_worth_effect` is explanatory metadata computed server-side; it is never used as an accounting input.

---

## 11. Net worth, Safe-to-Spend, allowance, emergency fund

### 11.1 Net worth

`GET /net-worth/?as_of=2026-11-17&currency=USD`

```json
{
  "as_of": "2026-11-17",
  "currency": "USD",
  "assets": "4390.00",
  "liabilities": "900.00",
  "net_worth": "3490.00",
  "change": {"amount": "-10.00", "since": "2026-10-31", "direction": "down"},
  "breakdown": {
    "assets": [{"account_id": "…", "name": "Checking", "amount": "3490.00", "currency": "USD"}],
    "liabilities": [{"liability_id": "…", "name": "Student loan", "outstanding": "900.00"}]
  },
  "fx_effect": "0.00",
  "rate_policy": "period_end",
  "rates_used": [{"pair": "USD/KHR", "rate": "4100", "date": "2026-11-17"}],
  "ledger_seq": 1842,
  "computed_from": "ledger"
}
```

`GET /net-worth/history/?from=…&to=…&granularity=month|week|day&currency=USD` returns an ordered
series plus a table-ready array and `stale: false|true` for snapshots.

### 11.2 Safe-to-Spend

`GET /safe-to-spend/?horizon=period_end` (or `horizon_days=14`)

```json
{
  "currency": "USD",
  "display": "820.00",
  "raw": "820.00",
  "is_negative": false,
  "horizon": {"start": "2026-11-17", "end": "2026-11-30", "label": "to end of month"},
  "components": {
    "spendable_balance": "1500.00",
    "pending_outflows": "-280.00",
    "reserved_bills": "-300.00",
    "planned_savings": "-100.00"
  },
  "accounts": [
    {"id": "…", "name": "Checking", "included": true, "balance": "1500.00", "reason": "spendable"}
  ],
  "excluded_accounts": [
    {"id": "…", "name": "Savings", "reason": "not_spendable"}
  ],
  "notes": ["Pending transactions are not yet deducted from balances."]
}
```

### 11.3 Daily allowance

`GET /daily-allowance/?period=calendar_month`

```json
{
  "currency": "USD",
  "period": {"start": "2026-11-01", "end": "2026-11-30", "timezone": "Asia/Phnom_Penh"},
  "remaining_days": 14,
  "flexible_remaining": "280.00",
  "allowance": "20.00",
  "state": "ok",
  "explanation": "280.00 USD flexible budget remaining across 14 days.",
  "budgets": [{"name": "Groceries", "remaining": "40.00", "flexible": true}],
  "excluded": [{"name": "Rent", "remaining": "0.00", "reason": "not_flexible"}]
}
```

Over-budget: `state: "over_budget"`, `allowance: "0.00"`, explanation names the over-budget budgets.

### 11.4 Emergency fund

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/emergency-fund/` | Settings, current progress, computed essentials |
| `PUT` | `/emergency-fund/` | Coverage months, linked account, overrides |
| `GET` | `/emergency-fund/projection/?monthly_contribution=100` | Target, ETA, shortfall |

```json
{
  "essential_monthly_expenses": {"amount": "300.00", "currency": "USD",
    "source": "computed", "lookback_months": 3, "included_categories": ["…"]},
  "coverage_months": 6,
  "target": "1800.00",
  "current": "900.00",
  "remaining": "900.00",
  "progress_percent": 50.0,
  "contribution_plan": {"monthly": "150.00", "estimated_completion": "2027-05-01"},
  "warnings": []
}
```

`source` is `computed` or `override`; the UI must show which. Overrides never silently replace computed
values without changing `source`.

---

## 12. Reports

All report endpoints accept `period`, `start`, `end`, `currency`, `account_id`, `category_id`, `tag_id`,
and return `{period, currency, totals, series, table, rate_policy, rates_used, generated_from: "ledger"}`.

| Method | Path | Report |
|---|---|---|
| `GET` | `/reports/income/` | Income by period/category/account/tag |
| `GET` | `/reports/expenses/` | Expenses by period/category/account/tag/necessity |
| `GET` | `/reports/categories/` | Category breakdown with shares and comparison |
| `GET` | `/reports/trends/` | Income/expense/net series by granularity |
| `GET` | `/reports/budgets/` | Budget performance |
| `GET` | `/reports/savings/` | Contributions and goal progress |
| `GET` | `/reports/debts/` | Outstanding, principal paid, interest paid |
| `GET` | `/reports/net-worth/` | Net worth series and breakdown |
| `GET` | `/reports/tags/` | Tag totals and trends |
| `GET` | `/reports/cashflow/` | Inflows/outflows excluding transfers, with reconciliation block |
| `POST` | `/reports/{report}/export/` | Queue CSV/XLSX export with identical filters |

Every report response includes a reconciliation block:

```json
{"reconciliation": {"ledger_income": "3000.00", "reported_income": "3000.00",
                    "difference": "0.00", "checked_at": "…"}}
```

A non-zero difference is a server error, not a silently rounded display.

---

## 13. Insights

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/insights/` | List generated insights |
| `POST` | `/insights/` | `{kind, period, options}` → queued/generated |
| `GET` | `/insights/{id}/` | Text, inputs, model metadata, disclaimer |
| `DELETE` | `/insights/{id}/` | Remove a stored insight |

```json
{
  "kind": "budget_review",
  "period": {"start": "2026-11-01", "end": "2026-11-30"},
  "options": {"tone": "concise"}
}
```

Response includes `input_summary` (the exact verified figures), `output_text`, and:

```json
{"ai_generated": true, "model": {"provider": "…", "name": "…"},
 "disclaimer": "This explains your recorded data. It is not financial advice.",
 "numbers_verified": true, "prompt_version": "insight-v1"}
```

When AI is disabled or unavailable, `503 ai_unavailable` with a fallback deterministic summary endpoint
`GET /insights/{kind}/summary/` that produces factual text without a model.

---

## 14. Notifications

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/notifications/` | List, `?unread=true&category=` |
| `POST` | `/notifications/{id}/read/` | |
| `POST` | `/notifications/read-all/` | |
| `GET` | `/notification-preferences/` | Per-category channels, quiet hours, digest |
| `PUT` | `/notification-preferences/` | Bulk update; security category immutable |
| `GET` | `/notifications/unread-count/` | Badge count |

Security preferences return `locked: true` and a `409 security_notification_locked` if a client tries to
disable them.

---

## 15. Imports

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/imports/` | Upload CSV/XLSX (`multipart`), returns job with detected columns |
| `GET` | `/imports/{id}/` | Job status and counts |
| `POST` | `/imports/{id}/mapping/` | Confirm column mapping and target account |
| `POST` | `/imports/{id}/validate/` | Start validation (async) |
| `GET` | `/imports/{id}/records/` | Paginated staged rows, `?status=` |
| `GET` | `/imports/{id}/duplicates/` | Grouped candidate matches with scores/reasons |
| `POST` | `/imports/{id}/duplicates/decide/` | `{decisions: [{group_key, decision}]}` |
| `POST` | `/imports/{id}/commit/` | Atomically import approved rows |
| `POST` | `/imports/{id}/cancel/` | No side effects |

Upload response:

```json
{
  "id": "…", "status": "uploaded", "file_name": "kbank-nov.csv",
  "columns": ["Date", "Description", "Amount", "Currency"],
  "suggested_mapping": {"date": "Date", "description": "Description",
                        "amount": "Amount", "currency": "Currency"},
  "row_count": 143
}
```

Duplicate group:

```json
{
  "group_key": "…",
  "score": 0.93,
  "records": [{"import_record_id": "…", "row_number": 12,
               "normalized": {"date": "2026-11-04", "amount": "12.50", "currency": "USD",
                              "description": "LUCKY SUPERMARKET"}}],
  "existing": [{"transaction_id": "…", "date": "2026-11-04", "amount": "12.50",
                "account": "KBank checking", "description": "Lucky Supermarket"}],
  "reasons": ["same_account", "same_amount", "same_currency", "date_within_1_day",
              "description_similar_0.91"],
  "decision": "pending"
}
```

Commit refuses unresolved groups: `409 unresolved_duplicates` with the group keys. Imported rows are
linked via `import_record.transaction_id`, and each created transaction carries an audit row with
`action=created` and `actor=null` plus the job id in `reason`.

---

## 16. Exports, backups, restore, privacy

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/exports/` | `{scope, format, filters}` → job |
| `GET` | `/exports/` | Job list |
| `GET` | `/exports/{id}/` | Status; `download_url` when ready (signed, 15 min) |
| `POST` | `/exports/{id}/cancel/` | |
| `POST` | `/backups/` | Manual user backup |
| `GET` | `/backups/` | List with status, size, retention |
| `GET` | `/backups/{id}/download/` | Signed URL, reauth required |
| `POST` | `/restores/` | `{backup_id or upload_token, target: "new_workspace"}` |
| `GET` | `/restores/{id}/` | Validation report, progress, reconciliation |
| `GET` | `/privacy/data-map/` | What is stored, why, retention |
| `POST` | `/privacy/deletion-requests/` | `{password, code?, confirm: "DELETE"}` |
| `GET` | `/privacy/deletion-requests/current/` | Status, execute_after, backup_expiry |
| `DELETE` | `/privacy/deletion-requests/current/` | Cancel during grace period |

Deletion response:

```json
{
  "status": "requested",
  "execute_after": "2026-12-01T00:00:00Z",
  "backup_expiry_date": "2027-01-01",
  "consequences": [
    "All accounts, transactions, budgets, goals, debts, and reports will be permanently deleted.",
    "Encrypted backups containing this data expire by the date shown above.",
    "This cannot be undone after the grace period."
  ]
}
```

No endpoint claims immediate or absolute deletion.

---

## 17. Health and metadata

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health/live` | Process liveness (no auth) |
| `GET` | `/health/ready` | DB, Redis, storage readiness (internal network) |
| `GET` | `/meta/currencies/` | Active currencies with minor units and symbols |
| `GET` | `/meta/exchange-rates/?base=USD&quote=KHR` | Latest known rate with source and date |
| `GET` | `/meta/feature-flags/` | Client-visible flags (AI, email, Google) |
| `GET` | `/docs/` | Swagger UI (non-production or staff-only) |
| `GET` | `/schema/` | OpenAPI 3.1 document |

---

## 18. Contract governance

1. drf-spectacular generates the schema; CI fails on schema validation errors or untyped endpoints.
2. The TypeScript client is generated into `frontend/src/lib/api/generated/`; hand edits are rejected.
3. Breaking changes require a new path version (`/v2/`) or a documented deprecation window.
4. Every mutating endpoint has: permission test, validation test, idempotency test (where applicable),
   and cross-workspace isolation test.
5. Response examples in this document are illustrative; the generated schema and tests are authoritative
   once implemented. Any divergence is a documentation bug fixed in the same commit.
