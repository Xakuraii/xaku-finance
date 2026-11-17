# ADR 0004 — JWT authentication with server-tracked sessions

**Status:** accepted
**Date:** 2026-11-17

## Context

The SPA needs stateless API auth with revocable sessions, optional TOTP 2FA, Google sign-in, session
listing, and "log out everywhere". The brief requires JWT and secure session management. Pure stateless
JWTs cannot revoke access or list sessions; pure cookie sessions complicate a future mobile client and
the requested JWT approach.

## Decision

- **SimpleJWT** issues a 15-minute access token and a 7-day rotating refresh token.
- Every refresh lineage is a `UserSession` row; `jti` is stored and rotated. Refresh reuse revokes the
  entire family.
- Web storage: access token in memory; refresh token in an `HttpOnly; Secure; SameSite=Lax` cookie scoped
  to `/api/v1/auth/`. Mutations use the `Authorization` header; refresh/logout also require a double-submit
  CSRF token.
- 2FA is a second step after password verification, returning a short-lived single-use `mfa_token`.
- TOTP secrets are Fernet-encrypted with a versioned key; recovery codes are Argon2id hashes.
- Google ID tokens are verified server-side (`iss`, `aud`, `exp`, `email_verified`); no client secret in
  the SPA; linking requires a verified email or an explicit post-login action.
- Sensitive actions require `reauth_at` within 10 minutes and re-check the session row.

## Consequences

- Sessions can be listed and revoked; refresh is immediate, access lags by ≤15 minutes.
- No token in `localStorage`, reducing XSS impact.
- Cookie + CSRF handling is limited to two endpoints, which is simple to test.
- Adds custom identity tables (`UserSession`, `TwoFactorConfig`, `RecoveryCode`) instead of relying wholly
  on library defaults.
- Logout must be server-side; clearing the cookie is insufficient.

## Alternatives considered

1. **Session cookies only (Django sessions).** Simple and revocable, but conflicts with the JWT requirement
   and mobile-readiness.
2. **Stateless JWT only.** Cannot revoke, list, or satisfy "log out all sessions" securely.
3. **django-allauth + dj-rest-auth social flows.** More moving parts and a social model we do not need for
   one provider; chosen a narrow Google verifier instead.
