# Security standards

Full model and residual risks: `docs/architecture/SECURITY.md`. These are the rules that matter in code review.

## Every endpoint

1. Explicit `permission_classes`; default is authenticated.
2. Resolve workspace from the user, never from the payload or URL.
3. Scope the queryset; cross-workspace ids return 404.
4. Validate all input server-side; whitelist filters and ordering fields.
5. Throttle expensive or sensitive operations.
6. Return the standard error envelope; never leak stack traces, SQL, or model names.

## Sensitive actions (reauth within 10 minutes)

Password change, 2FA disable/regenerate, full export, backup download, account deletion, restore, email
change. Re-check the `UserSession` row in addition to the JWT.

## Tokens and secrets

- Access JWT in memory only; refresh in `HttpOnly; Secure; SameSite=Lax` cookie scoped to `/api/v1/auth/`.
- No tokens, passwords, or financial payloads in logs, errors, analytics, or crash reports.
- All secrets via environment; `.env` git-ignored; `.env.example` has placeholders only.
- TOTP secrets Fernet-encrypted with a versioned key; recovery codes and reset tokens hashed.
- Never log raw IPs; store HMAC-SHA256.

## Input and output

- No `dangerouslySetInnerHTML`; insight text and user text render escaped.
- File uploads: allowlist MIME/extension, 10 MB limit, 50k rows, worker timeout, stored outside web root.
- Money: decimal string, ≤2 dp, bounded; reject rather than round silently.
- CSP, HSTS, nosniff, frame-ancestors, explicit CORS allowlist; no wildcard.
- `Cache-Control: no-store` on authenticated API responses.

## Financial integrity is security

- Idempotency on financial POSTs; optimistic `version` on edits.
- Row locks and deterministic ordering on balance-affecting writes.
- Audit every sensitive action; financial audits are append-only.
- Exports and backups are scoped, signed, expiring, and audited.
- Deletion must never claim more than it does: live data removed, backups expire on a stated date.

## Dependency and supply chain

- Add a dependency only with a written reason (ADR or PR note).
- Lockfiles committed; `pip-audit`/`npm audit` clean of high/critical.
- No postinstall scripts from untrusted packages; no unpinned git dependencies.
- Secret scanning and SAST run in CI.

## Review checklist

- [ ] Authorization is server-side and workspace-scoped
- [ ] No secret or token in code, logs, or responses
- [ ] Input validated; output escaped
- [ ] Throttle and reauth where required
- [ ] Financial write is atomic and idempotent
- [ ] Audit event written for sensitive actions
- [ ] Tests prove cross-tenant denial and failure rollback
