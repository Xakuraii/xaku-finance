# Phase 1 Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a runnable Phase 1 where a user can register, create accounts with opening balances, record income and split expenses, and see balances that provably derive from an immutable double-entry ledger with audited edits.

**Architecture:** Django + DRF monolith with a ledger service as the only balance writer. React SPA consumes a generated client. Money is integer minor units with a `Decimal` value object. Every financial write is atomic, workspace-scoped, and audited.

**Tech Stack:** Python 3.12, Django 5.2 LTS, DRF, SimpleJWT, drf-spectacular, PostgreSQL 16, Redis, Celery (scaffold only), pytest, ruff, mypy, React 19, TypeScript, Vite, Tailwind v4, TanStack Query, React Router, RHF + Zod, Vitest, Playwright.

**Spec:** `docs/SRS.md` (FR-AUTH, FR-WS, FR-ACC, FR-TXN), `docs/ACCOUNTING_RULES.md`, `docs/DATABASE.md`, `docs/API_SPECIFICATION.md`, `docs/adr/0001`–`0004`.

---

## Global Constraints

- Python 3.12+; Django 5.2 LTS; PostgreSQL 16 (no SQLite, including tests).
- Money: `amount_minor BIGINT` + `currency_code CHAR(3)`. No `FloatField`, no `float()` on money, no JS `number` arithmetic on money.
- Amounts in API requests are decimal strings; responses include `amount` string and `amount_minor`.
- Balances are derived from postings. No writable `balance` column.
- Every journal entry must sum to zero **per currency**. Posted entries are immutable; corrections are reversals.
- Only `completed` transactions post. `pending` and `cancelled` never affect balances.
- Every financial row carries `workspace_id`; every query is workspace-scoped; cross-workspace ids return 404.
- All multi-write paths run in `transaction.atomic()` with deterministic `select_for_update` ordering.
- UUID primary keys; `TIMESTAMPTZ` UTC; financial dates are `DATE`.
- No secrets in source; `.env.example` placeholders only.
- Tests: exact money assertions, no `approx`; each task's tests must be observed failing first.
- Conventional Commits; one task per commit (or a small commit series).
- Docs and `docs/CHANGELOG.md` update in the same change when behavior or schema moves.

## Review Focus

The spec implies these inputs but no task's happy path exercises them; each is pinned to a test below.

1. **Editing a completed split expense after its budget period closed.** Expected: the closed period's numbers never change; the edit succeeds, reverses/reposts, and surfaces a prior-period adjustment. Pinned in Task 11.
2. **Two tabs editing the same transaction, and double-submitted transfers.** Expected: stale `version` writes nothing; a replayed idempotency key returns the first result and moves money once. Pinned in Tasks 11 and 13.
3. **Archiving or changing the currency of an account referenced by pending transactions.** Expected: currency change is refused once any posting or detail exists; archiving is explicit about pending items and never orphans them. Pinned in Task 12.
4. **A transaction at 00:30 local on the first day of a month, and across a DST boundary.** Expected: it lands in the local month, not the previous UTC month, and period reports agree. Pinned in Tasks 3 and 13.
5. **Edge amounts: `0.005`, `1e15` minor units, and a split remainder of one minor unit.** Expected: extra precision is rejected, overflow is rejected, and splits must still sum exactly. Pinned in Tasks 2 and 11.

---

## File Structure

Created by this plan (paths relative to repo root):

```
backend/pyproject.toml
backend/manage.py
backend/config/{settings/{base,local,test,production}.py,urls.py,wsgi.py,asgi.py,celery.py}
backend/apps/common/{money.py,periods.py,models.py,managers.py,permissions.py,pagination.py,errors.py,middleware.py,apps.py}
backend/apps/identity/{models.py,services/{registration,sessions,two_factor,passwords,google}.py,api/{serializers,views,urls}.py}
backend/apps/workspaces/{models.py,services.py}
backend/apps/accounts/{models.py,services.py,selectors.py,api/{serializers,views,urls}.py}
backend/apps/ledger/{models.py,services/{posting,reversal,accounts,reconciliation}.py,selectors.py,management/commands/check_ledger.py}
backend/apps/transactions/{models.py,services/{create,update,archive,status,splits,opening}.py,selectors.py,api/{serializers,views,urls}.py}
backend/apps/categories/{models.py,services.py}
backend/apps/tags/{models.py,services.py}
backend/tests/{conftest.py,factories/**,unit/**,integration/**,security/**}
docker-compose.yml
.env.example
.github/workflows/ci.yml
frontend/… (Task 14–15)
```

Key interface decisions:

- `apps.common.money.Money` is the only money type in services.
- `apps.ledger.services.posting.post_entry(*, actor, spec) -> JournalEntry` is the only writer of postings.
- `apps.transactions.services.create.create_transaction(...)` is the only writer of transactions.
- Selectors return plain dataclasses/dicts, never querysets to views.

---

### Task 1: Backend scaffold, health, OpenAPI, CI

**Files:**
- Create: `backend/pyproject.toml`, `backend/manage.py`, `backend/config/__init__.py`, `backend/config/settings/{__init__,base,local,test,production}.py`, `backend/config/urls.py`, `backend/config/wsgi.py`, `backend/config/asgi.py`, `backend/apps/common/apps.py`, `backend/apps/common/views.py`, `backend/tests/conftest.py`, `backend/tests/test_health.py`, `.env.example`, `docker-compose.yml`, `.github/workflows/ci.yml`, `.gitignore`, `.dockerignore`, `Makefile`

**Interfaces:**
- Produces: `GET /health/live -> {"status": "ok"}`, `GET /api/schema/`, settings via env (`DJANGO_SETTINGS_MODULE`, `DATABASE_URL`, `REDIS_URL`, `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`).
- Produces: `pytest` configured with `DJANGO_SETTINGS_MODULE=config.settings.test`.

- [ ] **Step 1: Write the failing health test**

```python
# backend/tests/test_health.py
def test_liveness(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run it and confirm failure**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError` or 404, because the project does not exist.

- [ ] **Step 3: Create the project, settings, health view, and tooling**

Split settings; parse env with `os.environ` and `dj-database-url`. Add `ATOMIC_REQUESTS=True`, `DEFAULT_AUTO_FIELD=BigAutoField` for logs only, `LANGUAGE_CODE=en-us`, `TIME_ZONE=UTC`, `USE_TZ=True`. Add drf-spectacular, SimpleJWT, CORS, django-filter, Argon2 hasher (Argon2 first), and pytest-django config. Health view is a plain `@api_view` with `permission_classes=[AllowAny]`. Add `pyproject.toml` with ruff/mypy/pytest settings, and a CI workflow running ruff, mypy, and pytest against a Postgres 16 service.

- [ ] **Step 4: Verify**

Run: `cd backend && pytest tests/test_health.py -v && ruff check . && mypy apps`
Expected: PASS; ruff/mypy clean.
Run: `cd backend && python manage.py spectacular --file ../docs/openapi.yaml --validate`
Expected: schema written, no validation errors.

- [ ] **Step 5: Commit**

```bash
git add backend .env.example docker-compose.yml .github .gitignore .dockerignore Makefile docs/openapi.yaml
git commit -m "chore(backend): scaffold Django project, health endpoint, and CI"
```

---

### Task 2: Money value object

**Files:**
- Create: `backend/apps/common/money.py`, `backend/tests/unit/test_money.py`, `backend/tests/property/test_money_properties.py`
- Test: same files

**Interfaces:**
- Produces:

```python
class CurrencyMismatch(ValueError): ...
class InvalidPrecision(ValueError): ...

@dataclass(frozen=True)
class Money:
    amount_minor: int
    currency: str          # ISO-4217 code
    minor_unit: int        # injected from ref_currency

    @classmethod
    def parse(cls, value: str, currency: str, minor_unit: int = 2) -> "Money": ...
    def serialize(self) -> str: ...
    def format(self, locale: str = "en-US") -> str: ...
    def __add__(self, other: "Money") -> "Money": ...
    def __sub__(self, other: "Money") -> "Money": ...
    def __neg__(self) -> "Money": ...

def parse_rate(value: str) -> Decimal: ...
def convert(amount: Money, rate: Decimal, target_currency: str, target_minor_unit: int = 2) -> Money: ...
```

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_money.py
import pytest
from decimal import Decimal
from apps.common.money import Money, InvalidPrecision, CurrencyMismatch, convert

def test_parse_keeps_minor_units_exact():
    assert Money.parse("1250.50", "USD").amount_minor == 125050

def test_parse_rejects_extra_precision():
    with pytest.raises(InvalidPrecision):
        Money.parse("0.005", "USD")

def test_add_different_currencies_raises():
    with pytest.raises(CurrencyMismatch):
        Money.parse("1.00", "USD") + Money.parse("1.00", "KHR")

def test_convert_rounds_half_up_once():
    result = convert(Money.parse("100.00", "USD"), Decimal("4100"), "KHR")
    assert result.amount_minor == 41_000_000

def test_format_is_canonical():
    assert Money.parse("1250.50", "USD").format("en-US") == "1,250.50 USD"
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && pytest tests/unit/test_money.py -v`
Expected: FAIL — `ModuleNotFoundError: apps.common.money`.

- [ ] **Step 3: Implement `Money`, `parse_rate`, `convert`**

Use `Decimal(value)` and `quantize(Decimal(1).scaleb(-minor_unit), rounding=ROUND_HALF_UP)`. Reject `NaN`, `Infinity`, negatives where not allowed, and strings with more decimals than `minor_unit`. `convert` multiplies the major-unit `Decimal` by the rate, quantizes once to the target minor unit, and returns a `Money`. `format` uses `Decimal(amount_minor).scaleb(-minor_unit)` and `Intl`-equivalent grouping; append the currency code.

- [ ] **Step 4: Add the property test and verify**

```python
# backend/tests/property/test_money_properties.py
from hypothesis import given, strategies as st
from apps.common.money import Money

@given(st.integers(min_value=-10**15, max_value=10**15))
def test_roundtrip_minor_units(value):
    m = Money(value, "USD", 2)
    assert Money.parse(m.serialize(), "USD").amount_minor == value
```

Run: `cd backend && pytest tests/unit/test_money.py tests/property/test_money_properties.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/common/money.py backend/tests/unit/test_money.py backend/tests/property/test_money_properties.py
git commit -m "feat(common): add exact Money value object and conversion"
```

---

### Task 3: Financial period resolution

**Files:**
- Create: `backend/apps/common/periods.py`, `backend/tests/unit/test_periods.py`

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class DateRange:
    start: date
    end: date
    timezone: str
    resolved_from: str      # calendar_month | calendar_week | calendar_year | custom

def resolve_period(*, period: str, timezone: str, anchor: date | None = None,
                   start: date | None = None, end: date | None = None,
                   week_start: int = 1) -> DateRange: ...
def days_remaining(period: DateRange, today: date) -> int: ...
def utc_bounds(period: DateRange) -> tuple[datetime, datetime]: ...
```

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_periods.py
from datetime import date
from apps.common.periods import resolve_period, days_remaining

def test_month_bounds_are_local_and_inclusive():
    r = resolve_period(period="calendar_month", timezone="Asia/Phnom_Penh", anchor=date(2026, 11, 17))
    assert (r.start, r.end) == (date(2026, 11, 1), date(2026, 11, 30))

def test_unknown_period_rejected():
    import pytest
    with pytest.raises(ValueError):
        resolve_period(period="fortnight", timezone="UTC")

def test_days_remaining_is_inclusive():
    r = resolve_period(period="calendar_month", timezone="UTC", anchor=date(2026, 11, 17))
    assert days_remaining(r, date(2026, 11, 17)) == 14

def test_custom_requires_both_dates():
    import pytest
    with pytest.raises(ValueError):
        resolve_period(period="custom", timezone="UTC", start=date(2026, 11, 1))
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && pytest tests/unit/test_periods.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement with `zoneinfo`**

Compute boundaries in the workspace timezone using `ZoneInfo(timezone)`; validate the zone and the period enum. Custom ranges must be inclusive and ordered. `utc_bounds` converts local 00:00 start and 23:59:59.999999 end to UTC.

- [ ] **Step 4: Add DST and local-midnight tests, then verify**

```python
def test_first_local_day_not_previous_utc_day():
    r = resolve_period(period="calendar_month", timezone="Asia/Phnom_Penh", anchor=date(2026, 11, 1))
    start_utc, _ = utc_bounds(r)
    assert start_utc.date() == date(2026, 10, 31)  # 00:00 +07 is 17:00 UTC previous day
```

Add an `America/New_York` month containing the DST transition and assert the inclusive end. Run: `pytest tests/unit/test_periods.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/common/periods.py backend/tests/unit/test_periods.py
git commit -m "feat(common): resolve financial periods in workspace timezone"
```

---

### Task 4: Identity models, workspace creation, registration

**Files:**
- Create: `backend/apps/identity/__init__.py`, `backend/apps/identity/models.py`, `backend/apps/identity/services/registration.py`, `backend/apps/identity/api/{serializers,views,urls}.py`, `backend/apps/workspaces/models.py`, `backend/apps/workspaces/services.py`, migrations, `backend/tests/factories/users.py`, `backend/tests/integration/identity/test_registration.py`, `backend/apps/workspaces/migrations/*` (initial)

**Interfaces:**
- Produces:

```python
class User(AbstractBaseUser, PermissionsMixin):
    id: UUID; email: str; is_email_verified: bool; ...

def register_user(*, email: str, password: str, display_name: str,
                  timezone: str = "UTC", reporting_currency: str = "USD") -> User: ...
def ensure_workspace(user: User) -> Workspace: ...
```

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integration/identity/test_registration.py
import pytest
from apps.identity.models import User
from apps.identity.services.registration import register_user

@pytest.mark.django_db
def test_registration_creates_user_profile_and_workspace():
    user = register_user(email="mara@example.com", password="correct horse battery staple",
                         display_name="Mara", timezone="Asia/Phnom_Penh")
    assert user.workspace.owner_id == user.id
    assert user.profile.reporting_currency.code == "USD"

@pytest.mark.django_db
def test_duplicate_email_rejected():
    register_user(email="mara@example.com", password="correct horse battery staple", display_name="Mara")
    with pytest.raises(Exception):
        register_user(email="MARA@example.com", password="correct horse battery staple", display_name="Mara 2")
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && pytest tests/integration/identity/test_registration.py -v`
Expected: FAIL — models/services missing.

- [ ] **Step 3: Implement models and transactional registration**

User with `email` unique (citext or lower unique), Argon2 hasher, `UserProfile`, `Workspace` (unique owner), `DashboardLayout` placeholder. `register_user` runs in `transaction.atomic()`, validates password with Django validators plus a 12-character minimum, creates user + profile + workspace, and seeds default categories/tags (a no-op stub in this task, real seed in Task 11/13).

- [ ] **Step 4: Add API endpoint and tests**

`POST /api/v1/auth/register/` returns 201 with user/workspace/access token (token issuing lands in Task 5; return a placeholder 201 with user/workspace now and add tokens in Task 5 without changing the route). Tests: duplicate email → 400 `email_taken`; weak password → 400; timezone validated.

Run: `pytest tests/integration/identity/test_registration.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/identity backend/apps/workspaces backend/tests
git commit -m "feat(identity): add user, profile, workspace, and registration"
```

---

### Task 5: JWT sessions, refresh rotation, revocation

**Files:**
- Modify: `backend/apps/identity/models.py`, `backend/apps/identity/api/{views,urls}.py`
- Create: `backend/apps/identity/services/sessions.py`, `backend/tests/integration/identity/test_sessions.py`
- Modify: `backend/config/settings/base.py`

**Interfaces:**
- Produces:

```python
def issue_tokens(user: User, *, request_meta: RequestMeta) -> TokenPair: ...
def rotate_refresh(raw_refresh: str) -> TokenPair: ...      # revokes family on reuse
def revoke_session(*, user: User, session_id: UUID) -> None: ...
def revoke_all_sessions(*, user: User) -> int: ...
```

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.django_db
def test_refresh_rotation_issues_new_jti(api, user):
    pair = login(api, user)
    old = pair.refresh
    new = api.post("/api/v1/auth/refresh/", cookies={"refresh": old})
    assert new.status_code == 200
    assert new.cookies["refresh"].value != old

@pytest.mark.django_db
def test_refresh_reuse_revokes_family(api, user):
    pair = login(api, user)
    first = api.post("/api/v1/auth/refresh/", cookies={"refresh": pair.refresh})
    second = api.post("/api/v1/auth/refresh/", cookies={"refresh": pair.refresh})
    assert second.status_code == 401
    assert not UserSession.objects.filter(user=user, revoked_at__isnull=True).exists()
```

- [ ] **Step 2: Run and confirm failure** — endpoints missing.

- [ ] **Step 3: Implement sessions and tokens**

Custom SimpleJWT serializer: access 15 min; refresh 7 days; `sid`/`jti` claims; `UserSession` row with `family_id`. Set the refresh cookie `HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth/`. Rotate inside `transaction.atomic()` with `select_for_update` on the session; reuse marks all sessions in the family revoked. Add `/auth/login/`, `/auth/refresh/`, `/auth/logout/`, `/auth/logout-all/`, `/auth/sessions/`, `DELETE /auth/sessions/{id}/`.

- [ ] **Step 4: Verify**

Run: `pytest tests/integration/identity -v` → PASS. Manual: confirm cookie flags in the test response.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/identity backend/config/settings/base.py backend/tests/integration/identity
git commit -m "feat(identity): add rotating refresh sessions and revocation"
```

---

### Task 6: Email verification, password reset, Google sign-in

**Files:**
- Create: `backend/apps/identity/services/{passwords,google}.py`, `backend/apps/identity/models.py` additions, templates, `backend/tests/integration/identity/test_email_flows.py`, `test_google.py`

**Interfaces:**
- Produces: `send_verification(user)`, `verify_email(token)`, `request_password_reset(email)`, `reset_password(token, new_password)`, `login_with_google(id_token) -> User`.

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.django_db
def test_verification_token_is_single_use(mailoutbox, user):
    send_verification(user)
    token = extract_token(mailoutbox[0].body)
    assert verify_email(token) is True
    with pytest.raises(TokenAlreadyUsed):
        verify_email(token)

@pytest.mark.django_db
def test_password_reset_revokes_sessions(user, user_session):
    request_password_reset(user.email)
    reset_password(token=extract_token(...), new_password="a new long passphrase")
    assert not UserSession.objects.filter(user=user, revoked_at__isnull=True).exists()
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement tokens and flows**

Store SHA-256 hashes only; 24 h verification / 1 h reset expiry; single use; throttles; no enumeration. Email is sent through `django.core.mail` (Mailpit in Compose). Google: verify with `google.oauth2.id_token.verify_oauth2_token`, check `aud` against `GOOGLE_CLIENT_ID`, require `email_verified`, link only to a verified email, else return `google_link_required`.

- [ ] **Step 4: Verify** — `pytest tests/integration/identity -v` → PASS; no token appears in logs (grep the test caplog).

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(identity): add email verification, password reset, and Google sign-in"
```

---

### Task 7: Optional TOTP 2FA and recovery codes

**Files:**
- Create: `backend/apps/identity/services/two_factor.py`, `backend/apps/identity/models.py` additions, `backend/tests/integration/identity/test_two_factor.py`
- Modify: auth views/urls

**Interfaces:**
- Produces: `begin_enrollment(user) -> Enrollment`, `confirm_enrollment(user, code) -> list[str]`, `verify_challenge(mfa_token, code) -> TokenPair`, `disable(user, password, code)`, `regenerate_recovery_codes(user, password, code)`.

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.django_db
def test_recovery_code_is_single_use(user_with_2fa):
    codes = regenerate_recovery_codes(user_with_2fa, password=PASSWORD, code=current_totp(user_with_2fa))
    assert verify_challenge(mfa_token_for(user_with_2fa), codes[0]).access
    with pytest.raises(InvalidCode):
        verify_challenge(mfa_token_for(user_with_2fa), codes[0])

@pytest.mark.django_db
def test_totp_replay_rejected(user_with_2fa):
    code = current_totp(user_with_2fa)
    verify_challenge(mfa_token_for(user_with_2fa), code)
    with pytest.raises(InvalidCode):
        verify_challenge(mfa_token_for(user_with_2fa), code)
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement**

`pyotp` for TOTP; Fernet-encrypt the secret with `FERNET_KEYS` and `key_version`; store `last_used_counter`; recovery codes 10 × 10 bytes, Argon2id-hashed, batch invalidation; enrollment/disable require reauth; failed attempts lock verification; security notification stub.

- [ ] **Step 4: Verify** — all 2FA tests pass; assert the DB column is ciphertext, not the plaintext secret.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(identity): add optional TOTP 2FA with hashed recovery codes"
```

---

### Task 8: Workspace scoping and isolation harness

**Files:**
- Create: `backend/apps/common/managers.py`, `backend/apps/common/permissions.py`, `backend/tests/security/test_isolation.py`, `backend/tests/factories/workspaces.py`

**Interfaces:**
- Produces:

```python
class WorkspaceScopedManager(models.Manager):
    def for_workspace(self, workspace: Workspace) -> QuerySet: ...

class IsWorkspaceMember(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool: ...
```

- [ ] **Step 1: Write the failing isolation test**

```python
@pytest.mark.django_db
def test_account_from_other_workspace_is_404(api, user, other_user, account_factory):
    other = account_factory(workspace=other_user.workspace)
    api.force_authenticate(user)
    assert api.get(f"/api/v1/accounts/{other.id}/").status_code == 404
```

- [ ] **Step 2: Run and confirm failure** (endpoint absent → 404 already; assert the body code is `not_found` and that no data leaks by checking a same-workspace request returns 200 first).

- [ ] **Step 3: Implement manager, permission, and a shared test helper**

`for_workspace` requires an explicit workspace. The permission resolves ownership through the view's queryset, which is always workspace-filtered. Add a factory + helper `assert_isolated(api, user, other_user, url)` used by every later domain task.

- [ ] **Step 4: Verify** — `pytest tests/security -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(common): enforce workspace scoping and isolation tests"
```

---

### Task 9: Accounts and ledger models with DB constraints

**Files:**
- Create: `backend/apps/accounts/models.py`, `backend/apps/ledger/models.py`, `backend/apps/categories/models.py`, `backend/apps/tags/models.py`, migrations, `backend/tests/integration/ledger/test_ledger_constraints.py`, `backend/tests/factories/accounts.py`

**Interfaces:**
- Produces: `Account`, `LedgerAccount`, `JournalEntry`, `Posting`, `Category`, `Tag`, `Currency`, `ExchangeRate` per `docs/DATABASE.md` §2.

- [ ] **Step 1: Write failing constraint tests**

```python
@pytest.mark.django_db(transaction=True)
def test_unbalanced_entry_is_rejected_at_commit(ledger_accounts):
    with pytest.raises(IntegrityError), transaction.atomic():
        entry = JournalEntry.objects.create(..., status="posted", posted_at=timezone.now())
        Posting.objects.create(journal_entry=entry, ledger_account=ledger_accounts["cash"], amount_minor=100)
        # no offsetting posting; deferred trigger fires at commit

@pytest.mark.django_db
def test_one_ledger_account_per_account(account, ledger_accounts):
    with pytest.raises(IntegrityError):
        LedgerAccount.objects.create(workspace=account.workspace, owner_type="account",
                                     owner_id=account.id, kind="asset", code="duplicate",
                                     currency_code="USD")
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement models and SQL**

Migration includes:
- `ref_currency` seeded with USD/KHR.
- `UNIQUE (id, currency_code)` on `account`; composite FK on transactions later.
- `UNIQUE (owner_type, owner_id) WHERE owner_id IS NOT NULL` on `ledger_account`.
- Deferred constraint trigger `assert_journal_entry_balances` (per-currency zero sum).
- Deferred trigger `assert_posting_currency` (posting currency = ledger account currency).
- Trigger rejecting `UPDATE`/`DELETE` on posted `journal_entry` and on `txn_transaction_audit` (the audit table's database name; `TransactionAudit` in Django).
- Check constraints for amounts, rates, enum values.

- [ ] **Step 4: Verify**

Run: `pytest tests/integration/ledger/test_ledger_constraints.py -v` → PASS. Run `python manage.py sqlmigrate ledger 0001` and confirm the triggers appear.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(ledger): add accounts, ledger, categories, tags, and balance triggers"
```

---

### Task 10: Ledger service, reversal, reconciliation

**Files:**
- Create: `backend/apps/ledger/services/{posting,reversal,accounts,reconciliation}.py`, `backend/apps/ledger/selectors.py`, `backend/apps/ledger/management/commands/check_ledger.py`, `backend/tests/integration/ledger/test_posting.py`, `backend/tests/property/test_ledger_properties.py`

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class PostingSpec: ledger_account_id: UUID; amount_minor: int; currency: str
@dataclass(frozen=True)
class EntrySpec:
    entry_type: str; status: str; effective_date: date
    source_type: str; source_id: UUID | None; postings: list[PostingSpec]
    description: str = ""; fx_snapshot: dict = field(default_factory=dict)
    reverses_entry_id: UUID | None = None

def post_entry(*, workspace: Workspace, actor: User | None, spec: EntrySpec) -> JournalEntry: ...
def reverse_entry(*, workspace: Workspace, actor: User | None, entry: JournalEntry,
                  reason: str) -> JournalEntry: ...
def postings_balance(*, ledger_account_id: UUID, as_of: date | None = None) -> int: ...
def provision_system_accounts(*, workspace: Workspace) -> None: ...
```

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.django_db
def test_post_entry_increments_ledger_seq_and_balances(workspace, ledger_accounts):
    entry = post_entry(workspace=workspace, actor=None, spec=EntrySpec(
        entry_type="expense", status="posted", effective_date=date(2026, 11, 17),
        source_type="manual", source_id=None,
        postings=[PostingSpec(ledger_accounts["groceries"].id, 6000, "USD"),
                  PostingSpec(ledger_accounts["cash"].id, -6000, "USD")]))
    assert entry.ledger_seq == 1
    assert postings_balance(ledger_account_id=ledger_accounts["cash"].id) == -6000

@pytest.mark.django_db
def test_reverse_entry_negates_and_marks_original(entry_fixture):
    reversal = reverse_entry(workspace=entry_fixture.workspace, actor=None,
                             entry=entry_fixture, reason="test")
    entry_fixture.refresh_from_db()
    assert entry_fixture.status == "reversed"
    assert sum(p.amount_minor for p in reversal.postings.all()) == 0

@pytest.mark.django_db
def test_unbalanced_spec_raises_before_write(workspace, ledger_accounts):
    with pytest.raises(UnbalancedEntry):
        post_entry(workspace=workspace, actor=None, spec=EntrySpec(... one posting ...))
    assert not JournalEntry.objects.filter(workspace=workspace).exists()
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement the single posting entry point**

Lock the workspace row (`select_for_update`) for the sequence, lock involved ledger accounts in ascending UUID order, validate that every ledger account belongs to the workspace and that per-currency sums are zero, then insert entry + postings and bump `ledger_seq`. `reverse_entry` builds negated postings, posts them, and flips the original status in the same transaction. `check_ledger` verifies entry balance, posting currency, account ownership, split totals (when transaction models exist), and reports drift without printing amounts.

- [ ] **Step 4: Run property tests + command**

```python
@given(st.lists(st.integers(min_value=-10**9, max_value=10**9), min_size=2))
def test_generated_postings_never_unbalance(amounts):
    # build amounts that sum to zero by construction, post, assert balance
```
Run: `pytest tests/integration/ledger tests/property/test_ledger_properties.py -v && python manage.py check_ledger --fail-on-drift` → PASS.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(ledger): add atomic posting, reversal, and reconciliation"
```

---

### Task 11: Transactions, splits, audit, opening balances

**Files:**
- Create: `backend/apps/transactions/models.py`, `backend/apps/transactions/services/{create,update,archive,status,splits,opening}.py`, `backend/apps/transactions/selectors.py`, migrations, `backend/tests/integration/transactions/{test_create,test_splits,test_edit,test_opening,test_status}.py`, `backend/tests/factories/transactions.py`

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class SplitInput: category_id: UUID; amount: str

def create_transaction(*, workspace, actor, kind: str, account_id: UUID, amount: str,
                       currency: str, occurred_on: date, title: str,
                       category_id: UUID | None = None, splits: list[SplitInput] | None = None,
                       tags: list[str] | None = None, necessity: str | None = None,
                       status: str = "completed", description: str = "",
                       notes: str = "") -> Transaction: ...
def update_transaction(*, workspace, actor, transaction_id: UUID, expected_version: int,
                       reason: str, **changes) -> Transaction: ...
def archive_transaction(*, workspace, actor, transaction_id: UUID, reason: str) -> Transaction: ...
def restore_transaction(*, workspace, actor, transaction_id: UUID) -> Transaction: ...
def create_opening_balance(*, workspace, actor, account: Account, amount: str,
                           as_of: date) -> Transaction: ...
```

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.django_db
def test_split_mismatch_rejected(...):
    with pytest.raises(SplitTotalMismatch) as exc:
        create_transaction(..., amount="100.00", splits=[SplitInput(cat1, "60.00"), SplitInput(cat2, "39.99")])
    assert exc.value.difference_minor == 1

@pytest.mark.django_db
def test_edit_reverses_and_appends_audit(...):
    tx = create_transaction(..., amount="100.00", status="completed")
    first_entry = tx.current_journal_entry
    updated = update_transaction(..., expected_version=1, reason="fee", amount="110.00")
    first_entry.refresh_from_db()
    assert first_entry.status == "reversed"
    assert updated.current_journal_entry_id != first_entry.id
    assert TransactionAudit.objects.filter(transaction=tx).count() == 2
    assert TransactionAudit.objects.get(transaction=tx, revision=2).changed_fields == ["amount"]

@pytest.mark.django_db
def test_stale_version_writes_nothing(...):
    with pytest.raises(VersionConflict):
        update_transaction(..., expected_version=1, ...)  # already at 2

@pytest.mark.django_db
def test_opening_balance_posts_to_equity(...):
    tx = create_opening_balance(..., amount="500.00")
    assert tx.transaction_type == "opening_balance"
    assert expense_total(tx.workspace) == 0
    assert income_total(tx.workspace) == 0
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement models, triggers, and services**

Models per `docs/DATABASE.md` §2.5. Add deferred trigger `assert_split_total`. `create_transaction` locks the account, validates currency and category ownership, creates the transaction, posts the entry when `completed`, and writes audit revision 1 — all atomic. `update_transaction` requires `expected_version`, locks the transaction row, reverses the old posted entry, posts the new one, bumps `version`, and appends audit. `archive_transaction` reverses and flags. `create_opening_balance` creates the transaction + detail + equity posting; a second opening balance for the account raises `DuplicateOpeningBalance`.

- [ ] **Step 4: Verify, including the closed-period review case**

Add a test that edits a completed expense whose date falls in a `closed` budget period; until budgets exist in Phase 2, assert the audit records `closed_period_affected: true` in the result metadata and the old entry remains reversed. Run the whole transactions suite → PASS.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(transactions): add create, splits, audited edit, and opening balances"
```

---

### Task 12: Account service and lifecycle

**Files:**
- Create: `backend/apps/accounts/services.py`, `backend/apps/accounts/selectors.py`, `backend/tests/integration/accounts/{test_create,test_archive,test_currency}.py`

**Interfaces:**
- Produces:

```python
def create_account(*, workspace, actor, name: str, account_type: str, currency: str,
                   opening_balance: str | None = None, opening_balance_date: date | None = None,
                   is_spendable: bool = False, description: str = "",
                   allows_negative_balance: bool = False) -> Account: ...
def archive_account(*, workspace, actor, account_id: UUID, reason: str,
                    acknowledge_balance: bool = False) -> Account: ...
def restore_account(*, workspace, actor, account_id: UUID) -> Account: ...
def change_currency(*, workspace, actor, account_id: UUID, currency: str) -> Account: ...
def account_balance(*, account: Account, as_of: date | None = None) -> Money: ...
```

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.django_db
def test_opening_balance_is_not_income(workspace, actor):
    account = create_account(..., opening_balance="2000.00", opening_balance_date=date(2026, 11, 1))
    assert account_balance(account=account).amount_minor == 200000
    assert workspace_income_minor(workspace) == 0

@pytest.mark.django_db
def test_archive_requires_acknowledgement_when_balance_nonzero(...):
    with pytest.raises(AccountHasBalance):
        archive_account(..., reason="closed")
    archive_account(..., reason="closed", acknowledge_balance=True)

@pytest.mark.django_db
def test_currency_change_blocked_after_posting(...):
    with pytest.raises(CurrencyImmutable):
        change_currency(account, "KHR")
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement**

Create the account + ledger account + opening balance atomically. Default `is_spendable`: true for checking/cash/ewallet, false for savings/investment/credit_card. Archive sets flags and refuses a nonzero balance without acknowledgement; archived accounts cannot receive new transactions or transfers. Currency change raises when any posting exists. Delete raises when postings exist.

- [ ] **Step 4: Verify** — `pytest tests/integration/accounts -v` → PASS; assert the archived account's register is still queryable with `include_archived`.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(accounts): add account lifecycle and opening balances"
```

---

### Task 13: Accounts and transactions API

**Files:**
- Create: `backend/apps/accounts/api/{serializers,views,urls}.py`, `backend/apps/transactions/api/{serializers,views,urls}.py`, `backend/apps/common/{pagination,errors,idempotency}.py`, `backend/tests/integration/api/{test_accounts_api,test_transactions_api,test_idempotency}.py`
- Modify: `backend/config/urls.py`

**Interfaces:**
- Produces: endpoints from `docs/API_SPECIFICATION.md` §4–§6; cursor pagination `{results, next_cursor, has_more}`; error envelope `{error: {code, message, field, details}, request_id}`.

- [ ] **Step 1: Write failing API tests**

```python
@pytest.mark.django_db
def test_create_expense_with_splits(api, user, account, categories):
    api.force_authenticate(user)
    response = api.post("/api/v1/transactions/", {
        "type": "expense", "account_id": str(account.id), "amount": "100.00",
        "currency": "USD", "occurred_on": "2026-11-16", "title": "Supermarket",
        "splits": [{"category_id": str(categories["groceries"].id), "amount": "60.00"},
                   {"category_id": str(categories["household"].id), "amount": "40.00"}],
    }, format="json")
    assert response.status_code == 201
    assert response.json()["amount_minor"] == 10000
    assert response.json()["is_split"] is True

@pytest.mark.django_db
def test_split_mismatch_returns_code(api, user, account, categories):
    ... assert response.status_code == 400
    assert response.json()["error"]["code"] == "split_total_mismatch"
    assert response.json()["error"]["details"]["difference"] == "0.01"

@pytest.mark.django_db
def test_idempotent_replay_creates_one_transaction(api, user, account):
    key = "9f1c..."
    first = api.post("/api/v1/transactions/", payload, format="json", HTTP_IDEMPOTENCY_KEY=key)
    second = api.post("/api/v1/transactions/", payload, format="json", HTTP_IDEMPOTENCY_KEY=key)
    assert first.json()["id"] == second.json()["id"]
    assert Transaction.objects.count() == 1
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement serializers, views, errors, idempotency**

Serializers validate shape only and delegate to services. Map domain exceptions to codes (`insufficient_funds`, `currency_mismatch`, `archived_account`, `split_total_mismatch`, `version_conflict`, `duplicate_opening_balance`). Add `Idempotency-Key` handling storing the response in the same transaction. Add filters (`account_id`, `status`, `from`, `to`, `tag_id`, `necessity`, `q`) and cursor pagination with `(occurred_on, id)` ordering.

- [ ] **Step 4: Verify + isolation**

Run `pytest tests/integration/api -v` and the isolation helper for every new endpoint. Confirm API output matches the examples in `docs/API_SPECIFICATION.md`; regenerate `docs/openapi.yaml`.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(api): add accounts and transactions endpoints with idempotency"
```

---

### Task 14: Frontend foundation, auth, accounts

**Files:**
- Create: `frontend/package.json`, `vite.config.ts`, `tsconfig.json`, `src/app/{router,providers,authenticated-layout,error-boundary}.tsx`, `src/lib/{api/client.ts,money.ts,query-keys.ts,format.ts}`, `src/styles/{tokens.css,base.css,tailwind.css}`, `src/features/auth/**`, `src/features/accounts/**`, `src/components/{money,statement-sheet,data-table,empty-state,error-state,confirm-dialog}.tsx`, `src/test/setup.ts`, `frontend/e2e/auth-accounts.spec.ts`

**Interfaces:**
- Consumes: API endpoints from Task 13, OpenAPI client generation.
- Produces: authenticated shell, route guard, login/register pages, accounts list/create/detail/archive.

- [ ] **Step 1: Write failing tests**

```tsx
// src/lib/money.test.ts
import { parseMoneyInput, formatMoney } from "./money";
it("rejects more than two decimals", () => {
  expect(parseMoneyInput("1.005", 2)).toEqual({ ok: false, reason: "precision" });
});
it("formats with currency code", () => {
  expect(formatMoney(125050, "USD", "en-US")).toBe("1,250.50 USD");
});
```

- [ ] **Step 2: Run and confirm failure** — `cd frontend && npm run test` → module missing.

- [ ] **Step 3: Implement tokens, shell, auth, accounts**

Dark-first tokens from `docs/DESIGN_SYSTEM.md` (gold `#F0B90B`, ink `#0B0E11`); access token in memory; refresh via cookie; query client with retry off for 4xx; auth guard that refreshes once. Accounts list uses a statement sheet, not a card grid. Forms use RHF + Zod; server errors map to fields. Archive dialog states consequences and requires acknowledgement when the balance is non-zero.

- [ ] **Step 4: Verify + E2E**

Run: `npm run typecheck && npm run lint && npm run test && npm run build`.
Run: `npx playwright test e2e/auth-accounts.spec.ts` (register → create account with opening balance → see balance → reload → still signed in).
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(web): add app shell, authentication, and account management"
```

---

### Task 15: Frontend transactions, splits, audit

**Files:**
- Create: `src/features/transactions/**`, `src/components/{split-editor,status-chip,drawer,chart-frame}.tsx`, `frontend/e2e/transactions.spec.ts`

**Interfaces:**
- Consumes: `/api/v1/transactions/` endpoints.
- Produces: list with filters, create/edit form, split editor, detail drawer with audit, archive/restore.

- [ ] **Step 1: Write failing tests**

```tsx
it("blocks submit when splits do not sum to the total", async () => {
  render(<SplitEditor total={10000} currency="USD" value={[{amount: 6000}, {amount: 3900}]} onChange={vi.fn()} />);
  expect(screen.getByText(/0.01 USD unallocated/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /save transaction/i })).toBeDisabled();
});
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement**

Transactions table with pending (dotted rule + "Pending" chip) and archived states; amount right-aligned with tabular numerals; filters in the URL; create/edit in a drawer; split editor shows exact difference; 409 version conflict offers reload; audit list shows before/after fields; archive confirmation explains reversal. No client-side balance math.

- [ ] **Step 4: Verify + E2E**

Run unit tests, typecheck, and Playwright: login → add split expense → row appears → edit amount → audit shows revision 2 → dashboard/report totals reflect the edit (report placeholder until Phase 4). Run axe on the transactions page. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(web): add transaction list, split editor, and audit history"
```

---

### Task 16: Phase 1 hardening and exit review

**Files:**
- Create: `backend/apps/common/management/commands/seed_workspace.py`, `backend/tests/security/test_endpoint_matrix.py`, `backend/tests/performance/test_query_counts.py`, `docs/PHASE_1_REPORT.md`
- Modify: `docs/CHANGELOG.md`, `docs/DATABASE.md` (if drift), `docs/openapi.yaml`

- [ ] **Step 1: Write failing isolation and query-count tests**

```python
@pytest.mark.django_db
@pytest.mark.parametrize("method,url", [
    ("get", "/api/v1/accounts/"), ("get", "/api/v1/transactions/"),
    ("get", f"/api/v1/accounts/{OTHER_ID}/"), ("get", f"/api/v1/transactions/{OTHER_ID}/"),
])
def test_other_workspace_never_leaks(api, user, method, url):
    api.force_authenticate(user)
    response = getattr(api, method)(url)
    assert response.status_code == 404
    assert "other-workspace-name" not in response.content.decode()
```

- [ ] **Step 2: Run and confirm failure** where scoping is incomplete; fix the query, not the test.

- [ ] **Step 3: Seed, measure, and document**

Seed a workspace with 10k transactions through the service layer (never raw inserts). Add query-count budgets (≤8 per list request). Write `docs/PHASE_1_REPORT.md` with: what shipped, actual test results, known limitations (budgets/reports absent; no transfers yet; no 2FA UI yet), and the next milestone (Phase 2.1 transfers).

- [ ] **Step 4: Full verification**

```bash
cd backend && ruff check . && ruff format --check . && mypy apps && pytest
cd backend && python manage.py check --deploy
cd backend && python manage.py spectacular --file ../docs/openapi.yaml --validate
cd backend && python manage.py check_ledger --fail-on-drift
cd frontend && npm run typecheck && npm run lint && npm run test && npm run build && npx playwright test
```

Expected: all green; if anything fails, record the exact failure in the report instead of claiming success.

- [ ] **Step 5: Commit**

```bash
git commit -am "test: harden phase 1 isolation and queries; document exit review"
```

---

## Phase 1 exit criteria

- [ ] A new user gets exactly one workspace and can authenticate, refresh, and revoke sessions.
- [ ] Accounts support opening balances that post to equity, archiving with acknowledgement, and immutable currency after postings.
- [ ] Income, expenses, and split allocations are created through services and post balanced entries.
- [ ] Edits reverse and repost, append audit revisions, and reject stale versions.
- [ ] Pending and cancelled transactions never affect balances.
- [ ] Every account balance equals the sum of its postings; `check_ledger` is green.
- [ ] Cross-workspace access is 404 for every endpoint, proven by a matrix test.
- [ ] Idempotent replay creates one transaction.
- [ ] Frontend covers auth, accounts, transactions, splits, and audit with unit + E2E tests.
- [ ] OpenAPI validates; the generated client compiles; docs and changelog reflect reality.

## Deliberately out of scope for Phase 1

Transfers (Phase 2.1), budgets/periods (2.3), imports (2.4), savings, debts, net worth, Safe-to-Spend,
reports, notifications, 2FA UI, exports, backups, deletion. Do not stub these as if they work.
