# Security and Privacy — XakuFinance

**Status:** planning baseline. Controls are requirements until implemented and tested.
**Companions:** `docs/adr/0004-authentication-and-sessions.md`, `docs/SRS.md` §3.1/3.17, `docs/API_SPECIFICATION.md`.

---

## 1. What we are protecting

| Asset | Sensitivity | Primary threats |
|---|---|---|
| Financial records (accounts, transactions, debts) | High | Unauthorized access, cross-tenant leakage, tampering |
| Credentials and 2FA secrets | Critical | Credential stuffing, phishing, database compromise |
| Session tokens | Critical | XSS, token theft, replay |
| Exports and backups | Critical | Unauthorized download, unencrypted storage, over-retention |
| Audit history | High | Repudiation, silent modification |
| Availability of financial data | High | Ransomware, accidental deletion, failed restore |

**Threat model summary:** opportunistic attackers and credential stuffing (high likelihood); a curious
or malicious authenticated user attempting to read another workspace (high impact); database or backup
theft (medium likelihood, critical impact); insider operator access (low likelihood, critical impact);
XSS through user-supplied descriptions (medium); supply-chain compromise of a dependency (medium).

Out of scope for V1: state-level adversaries, physical device seizure, coercion, and side-channel attacks
on the server. These are documented residual risks, not silently ignored.

---

## 2. Authentication

| Control | Requirement |
|---|---|
| Password hashing | Argon2id, Django Argon2 hasher first; parameters tuned to ~250 ms on production hardware; rehash on login when parameters change |
| Password policy | Minimum 12 characters, maximum 128; reject the top-10k common passwords and email-local-part passwords; no composition rules that encourage `P@ssw0rd1!` |
| Registration | Email verification token: 32 random bytes, SHA-256 hashed at rest, 24-hour expiry, single use |
| Login | Generic error, constant-ish time, per-IP + per-account throttles, progressive lockout |
| Password reset | Same token properties, 1-hour expiry, invalidates all sessions, never reveals account existence |
| JWT access | 15 min, HS256 with a ≥512-bit secret from env (or RS256 with rotating keys), claims `sub`, `sid`, `jti`, `typ`, `ver`, `iat`, `exp` |
| Refresh | 7 days, rotating, `jti` stored on the session, old token blacklisted, reuse revokes the lineage |
| Token storage | Access in memory only; refresh in `HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth/` cookie |
| CSRF | Bearer header for API mutations; refresh/logout additionally require a double-submit CSRF token bound to the session |
| Logout | Revokes session server-side; clearing the cookie alone is not logout |
| Google | ID token verified for signature, `iss`, `aud`, `exp`, `email_verified`; no implicit linking of unverified emails; no client secret in the SPA |
| Email enumeration | Register and forgot-password return the same response regardless of account existence |
| Reauthentication | Required within 10 minutes for 2FA changes, export-all, backup download, deletion request, and email change |

### 2.1 Two-factor authentication

- TOTP (RFC 6238), SHA-1/6 digits/30 s for compatibility; secret is 160-bit random.
- Secret encrypted at rest with Fernet; key from env with a version id, supporting rotation and re-wrap.
- Replay protection: the last accepted time-step counter is stored; a code at or below it is rejected.
- Enrollment requires password reauthentication and a successful code before enabling.
- Recovery codes: 10 codes, each 10 random bytes encoded, Argon2id-hashed, single use, invalidated as a
  batch on regeneration.
- Disabling 2FA requires password **and** a current TOTP or recovery code, and sends a security
  notification.
- 5 failed 2FA attempts in 10 minutes lock 2FA verification for 15 minutes (password login still works to
  reach the support path, but no session is issued).

### 2.2 Sessions

- Each session records device, hashed IP (HMAC with a server key), coarse location, timestamps.
- Users can revoke one or all. Revocation is effective for refresh immediately and for access tokens
  within 15 minutes. Sensitive actions check the session row as well as the JWT.
- Session list never reveals raw IP addresses.

---

## 3. Authorization and tenant isolation

1. Every financial endpoint resolves the workspace from `request.user.workspace`. A workspace id in a
   payload or URL is never trusted for authorization.
2. A `WorkspaceScopedManager` requires an explicit workspace; direct `.objects.all()` on financial models
   is forbidden by lint/review.
3. Cross-workspace resource access returns `404`, not `403`, to avoid existence leaks.
4. Object-level permission classes run on every retrieve/update/delete; list querysets are filtered before
   pagination.
5. Permission tests exist per endpoint family with two workspaces and assert both directions.
6. Django admin: available only to staff, requires 2FA, and does not register financial models. It is
   disabled entirely in production unless explicitly enabled.
7. Background tasks receive ids and resolve ownership themselves; they never accept a caller-supplied
   workspace without verifying the associated user.

### 3.1 Sensitive operations

| Operation | Additional proof | Audit |
|---|---|---|
| Change password | Current password | Yes |
| Disable 2FA | Password + TOTP/recovery | Yes |
| Regenerate recovery codes | Password + TOTP | Yes |
| Export all data | Reauth within 10 min, verified email | Yes |
| Download backup | Reauth, verified email | Yes |
| Request deletion | Password + 2FA (if enabled), typed confirmation | Yes |
| Restore backup | Reauth; target must be empty | Yes |
| Change email | Password + verification of the new address | Yes |

---

## 4. Input handling and application security

| Risk | Control |
|---|---|
| SQL injection | ORM and parameterized queries only; raw SQL requires review and `params`; no string interpolation into SQL |
| XSS | React escaping by default; no `dangerouslySetInnerHTML`; markdown/insight text rendered as plain text; strict CSP |
| CSRF | Bearer auth for mutations; SameSite cookies; double-submit token on refresh/logout |
| SSRF | No user-supplied URLs are fetched server-side in V1; avatar is a URL string rendered client-side, never fetched by the server |
| File upload abuse | MIME + extension allowlist, max 10 MB, row limit 50k, parsed in a worker with a timeout, no macros, files stored outside the web root, deleted after retention |
| Mass assignment | Explicit serializer fields; no `__all__` on financial models; no writable `workspace`, `status`, or computed fields |
| IDOR | Workspace scoping + object permissions + tests |
| Replay / double submit | Idempotency keys, optimistic `version` on edits, single-use tokens |
| Race conditions | `select_for_update`, deterministic lock order, unique constraints, serializable earmark transactions |
| Denial of service | Throttles, pagination caps, upload limits, query timeouts, statement timeout, worker concurrency limits |
| Open redirect | No redirect parameters; fixed post-login destination |
| Prototype pollution | Zod + typed client; no dynamic object merging of untrusted payloads |
| Dependency risk | Lockfiles, `pip-audit`/`npm audit` in CI, Dependabot, pinned major versions, review before adding packages |

### 4.1 Validation rules

- Server-side validation is authoritative. Zod on the client is convenience only.
- Amounts: decimal string, ≤2 dp, >0, parseable to `Decimal`, bounded (≤ 1e15 minor units).
- Currency: FK-validated ISO code matching the account.
- Dates: valid ISO dates; future dates allowed only where the feature permits (budget start, planned
  contribution); transaction dates limited to ±50 years.
- IDs: UUID, must belong to the workspace.
- Text: length limits enforced; no HTML accepted in financial text fields; control characters stripped.
- Enumerations: whitelist-validated.
- JSON blobs (`input_summary`, `metadata`) are size-limited and schema-checked where consumed.

---

## 5. Transport, headers, and browser security

- HTTPS only in production; HSTS `max-age=31536000; includeSubDomains; preload` after verification.
- TLS 1.2+; modern cipher suites; automated certificate renewal.
- Content-Security-Policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'`;
  no third-party scripts except Google Identity when enabled (explicit allowlist); `frame-ancestors 'none'`.
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
  `Permissions-Policy` disabling camera/microphone/geolocation.
- CORS: explicit origin allowlist from env; credentials allowed only for the auth cookie path; no wildcard.
- Cookies: `Secure`, `HttpOnly`, `SameSite=Lax`, narrow path, `__Host-` prefix where compatible.
- Frontend never stores tokens in `localStorage` or `sessionStorage`.
- Cache headers: `no-store` on authenticated API responses.

---

## 6. Secrets and configuration

- All secrets via environment: `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`, `DATABASE_URL`, `REDIS_URL`,
  `FERNET_KEY`/`FERNET_KEYS`, `GOOGLE_CLIENT_ID`, `EMAIL_*`, `AWS_*`/`S3_*`, `AI_API_KEY`, `IP_HASH_KEY`.
- `.env.example` contains placeholders only. `.env` is git-ignored. Secret scanning runs in CI.
- Separate credentials per environment; production secrets in a managed secret store, not in CI variables
  visible to forks.
- Key rotation: JWT signing keys support a `kid` and a verification set; Fernet keys are versioned and
  data is re-wrapped by a management command; database credentials rotate with a maintenance window.
- No secrets in logs, error responses, analytics, or crash reports. Error tracking is configured with
  scrubbers for `Authorization`, cookies, passwords, and long numeric strings.

---

## 7. Data protection at rest

| Data | Protection |
|---|---|
| Database | Encrypted volume (provider-managed), restricted network, TLS required for connections, least-privilege roles (app role cannot `DROP`/superuser) |
| Backups | Encrypted client-side (age/GPG) before upload; checksummed; separate credentials; immutability/object-lock where available |
| 2FA secrets | Application-level Fernet encryption, key outside the database |
| Recovery codes, tokens | Argon2id/SHA-256 hashes only |
| Passwords | Argon2id only |
| IP addresses | HMAC-SHA256 with a server key; never stored raw in sessions/audit |
| Export files | Stored in a private bucket, SSE, signed URLs, short TTL, deleted on schedule |
| Logs | No financial payloads, no tokens, no raw PII; retention 30 days hot, 90 days cold |

Field-level encryption of all financial amounts is **not** in V1: it breaks aggregation and reporting,
and the threat model (stolen volume) is addressed by disk encryption and access control. This trade-off is
recorded, not hidden.

---

## 8. Audit logging

Security events (append-only, retained 12 months):

- login success/failure, lockout, 2FA success/failure, recovery-code use
- session revocation, password change/reset, email change, 2FA enable/disable
- Google account link/unlink
- export created/downloaded, backup created/downloaded, restore started/completed/failed
- deletion requested/cancelled/executed
- permission denial and repeated 404 probing (rate-limited logging)
- operator actions on backups

Financial mutation audit lives in `transaction_audit`. Audit rows never contain secrets or full payloads;
they reference ids and changed field names. Audit writes are inside the same transaction as the action
where correctness matters, and must never block the action's success on logging failure for security
events (use a durable outbox pattern; V1 may log synchronously and accept the coupling, documented).

---

## 9. Privacy and data lifecycle

### 9.1 User rights implemented in-product

- Access: full export (JSON + CSV) including accounts, transactions, splits, tags, budgets, goals, debts,
  notifications, sessions, and audit summaries.
- Correction: normal edit flows with audit.
- Deletion: scheduled hard delete with grace period.
- Portability: documented schema plus a stable export version.
- Transparency: `/privacy/data-map/` explains stored data, purpose, and retention.

### 9.2 Deletion workflow

1. User requests deletion; must reauthenticate, type `DELETE`, and pass 2FA if enabled.
2. Request is recorded with `execute_after = now + 14 days`; all sessions except the current one are
   revoked; a security notification and email are sent.
3. During the grace period the user can cancel. No new exports are allowed after the request.
4. At execution: disable the account, run the deletion service transactionally, delete export files and
   user backups immediately, and mark the request executed with a non-content audit record.
5. System backups containing the data expire within 30 days (or the configured retention). The UI states
   this exact window before confirmation and in the confirmation email.
6. Legal-hold exceptions (if ever introduced) must be documented in the UI; V1 assumes none.

**Forbidden claim:** "Your data has been permanently deleted from all systems" while backups remain.
The correct statement is: "Deleted from the live service. Encrypted backups containing your data expire by
<date>."

### 9.3 Analytics and tracking

V1 uses no third-party analytics or advertising trackers in the authenticated app. Product metrics are
aggregate and server-side, with no financial values. If analytics is added, it must be self-hosted or
privacy-preserving, consented where required, and documented here first.

---

## 10. Backup and restoration security

- Backups are encrypted before leaving the database host; keys are separate from storage credentials.
- Restore requires an operator or user with reauthentication; restores into a new, empty workspace only.
- Restore validates checksums, archive version, and referential integrity before committing.
- Restore runs ledger reconciliation and refuses to complete on drift.
- Backup downloads are audited, rate-limited, and expire.
- Restore drills run in CI/nightly against synthetic data. A backup that has never been restored is not
  considered a backup.

---

## 11. AI-specific controls (optional feature)

1. Off by default; a workspace-level flag and a server-level flag must both be on.
2. Inputs are server-computed, minimized summaries — not raw transaction lists with descriptions unless
   the user opts in.
3. The model receives no credentials, ids, emails, or account numbers; categories may be generalized.
4. Output is treated as untrusted text: rendered escaped, length-limited, never executed.
5. Every response is checked against the supplied summary: numbers in the output that do not appear in the
   input are flagged as unverified and shown with a warning, or the response is rejected.
6. No training on user data; provider contract must state zero retention or the feature stays off.
7. Every insight stores `input_summary`, `prompt_version`, and model metadata for reproducibility.
8. The UI labels output as generated explanation, not advice, and links to the underlying figures.

---

## 12. Security testing and review gates

| Gate | When | Evidence |
|---|---|---|
| Cross-tenant isolation suite | Every PR | Green tests |
| Auth/2FA/session tests | Every PR touching identity | Green tests |
| Dependency audit | CI, weekly | No high/critical unpatched |
| Secret scan | CI | Clean |
| SAST (Bandit/Semgrep) | CI | No high findings |
| DAST baseline (ZAP) | Staging, Phase 6 | Report |
| Manual auth review | Phase 6 | Checklist signed |
| Restore drill | Every release candidate | Log + reconciliation |
| Permission matrix review | Phase 6 | Endpoint × role table |
| Dependency pinning review | Phase 6 | Lockfiles |
| CSP/header check | Phase 6 + staging | Header dump |

### 12.1 Known residual risks (accepted for V1)

| Risk | Impact | Mitigation / rationale |
|---|---|---|
| 15-minute access token window after revocation | Medium | Short TTL; sensitive actions re-check session; refresh revoked immediately |
| No field-level encryption of amounts | Medium | Disk encryption, least privilege, no bulk export without reauth; field encryption would break reporting |
| Email provider sees verification/reset links | Medium | Short expiry, single use, no financial content in emails |
| Operator with DB access can read data | High | Least privilege, audit, contractual controls; no admin UI for financial data |
| Backups retain deleted data up to 30 days | Medium | Disclosed accurately; object-lock and expiry |
| Client-side XSS via a future rich-text feature | High | Plain-text-only in V1; CSP; no `dangerouslySetInnerHTML` |
| Dependency compromise | High | Pinning, audits, minimal dependency set, review process |
| No independent pen test yet | High | Schedule before public launch; treat as release blocker |

---

## 13. Incident response (minimum viable)

1. Detect (alerts: failed-login spikes, ledger drift, backup failure, error-rate spike).
2. Contain (revoke sessions, rotate keys, disable affected feature flag, isolate host).
3. Assess scope (audit events, access logs) without copying financial data into chat tools.
4. Notify affected users if personal data was exposed, within the legally required window.
5. Recover from a verified backup; reconcile the ledger before reopening writes.
6. Write a blameless postmortem; add a regression test or control.

Contacts, escalation policy, and legal notification deadlines are deployment-specific and must be filled in
before production launch. This document does not pretend they exist yet.

---

## 14. Security checklist before V1.0 release

- [ ] Argon2id configured and benchmarked; no weak hasher fallback
- [ ] JWT secrets ≥512 bits, rotation plan documented, `kid` supported
- [ ] Refresh rotation + reuse detection tested
- [ ] 2FA enrollment, recovery, disable, and replay protection tested
- [ ] Rate limits verified with a load test (not just configured)
- [ ] CORS allowlist production-only, no wildcard
- [ ] CSP and security headers verified in staging
- [ ] Cross-workspace tests green for every endpoint family
- [ ] No secrets in repo history (`gitleaks` clean)
- [ ] Backups encrypted, restore drill passed, retention documented
- [ ] Deletion workflow executed end-to-end in staging, including backup expiry messaging
- [ ] Exports require reauth and expire
- [ ] Audit events cover all sensitive actions
- [ ] Dependency audit and SAST clean or accepted with owners
- [ ] Independent penetration test completed and findings resolved or accepted
