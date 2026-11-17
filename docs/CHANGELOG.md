# Changelog — XakuFinance

All notable changes to this project are recorded here. Format loosely follows Keep a Changelog.
**Nothing in this file may claim a feature is implemented when it is not.**

## [Unreleased]

### Added
- 2026-11-17 — Planning package established:
  - `README.md`, `GLOSSARY.md`, `.AGENT.md`
  - `docs/SRS.md`, `docs/FEATURE_MATRIX.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md`,
    `docs/ACCOUNTING_RULES.md`, `docs/API_SPECIFICATION.md`, `docs/SECURITY.md`, `docs/TESTING.md`,
    `docs/ROADMAP.md`, `docs/RISKS.md`, `docs/ACCEPTANCE_CRITERIA.md`, `docs/DESIGN_SYSTEM.md`,
    `docs/REPOSITORY_STRUCTURE.md`
  - `docs/adr/0001`–`0006`
  - `.agent/` operating context, standards, workflows, and checklists
  - Phase 1 implementation plan in `docs/superpowers/plans/`
- 2026-11-17 — Backend scaffold (Phase 1, Task 1):
  - Django 5.2 project with split settings (`base`, `local`, `test`, `production`)
  - `GET /health/live` and `GET /health/ready`, request-id middleware, stable error envelope
  - `pyproject.toml` with pytest, ruff, and mypy configuration
  - `docker-compose.yml` (PostgreSQL 16 on host port 55432, Redis on 56379), `Makefile`,
    CI workflow, `.env.example`, `.gitignore`, `.dockerignore`
  - Generated and validated `docs/openapi.yaml`
- 2026-11-17 — Identity, currency reference data, and registration (Phase 1, Task 4):
  - `User` (email login, Argon2id), `UserProfile`, `DashboardLayout`, `Workspace` models
  - `ref_currency` with USD and KHR seeded by data migration
  - Atomic `register_user` service and `POST /api/v1/auth/register/`
  - One workspace per user enforced by a unique `owner`; profile and workspace created in the same
    transaction
- 2026-11-17 — Rotating refresh sessions and revocation (Phase 1, Task 5):
  - `UserSession` ledger of refresh lineages with hashed IPs and device metadata
  - `POST /auth/login/`, `/auth/refresh/`, `/auth/logout/`, `/auth/logout-all/`,
    `GET /auth/sessions/`, and `DELETE /auth/sessions/{id}/`
  - Refresh tokens rotate on every use; replaying an old token revokes the family
  - Refresh cookie is `HttpOnly`, `Secure`, `SameSite=Lax`, scoped to `/api/v1/auth/`
  - Progressive login lockout: 5 failures in 15 minutes, escalating to 1/5/15/60 minutes
- 2026-11-17 — Email verification, password reset, and Google sign-in (Phase 1, Task 6):
  - `IdentityToken` stores SHA-256 hashes only; 24-hour verification and 1-hour reset tokens, both
    single use, with new tokens superseding unused predecessors
  - `POST /auth/verify-email/`, `/auth/verify-email/resend/`, `/auth/password/forgot/`,
    `/auth/password/reset/`, and `/auth/google/`
  - Registration now emails a verification link; password reset revokes every session and never
    reveals whether an account exists
  - `SocialIdentity` links Google subjects; existing password accounts require explicit linking and
    unverified Google emails are refused
  - Per-email and per-IP throttles on password reset, plus throttles on login, registration, and
    verification resends
  - Plain-text email templates in `backend/apps/identity/templates/identity/emails/`; console backend
    locally, Mailpit service in Compose for SMTP testing

### Decisions
- Double-entry ledger with system accounts is the accounting foundation.
- Money is stored as integer minor units; no floats anywhere.
- One transaction aggregate with type-specific detail tables; edits reverse and repost.
- Single workspace per user; no collaboration in V1.
- Golden `#F0B90B` brand accent, dark-first, with a text-safe gold for light mode.
- Transactions are account-currency only; FX exists only on transfers.
- Receipt attachments/OCR, multi-workspace, bank sync, and AI chat are out of V1.

### Known limitations
- Registration, login, rotation, session revocation, email verification, password reset, and Google
  sign-in are implemented. TOTP 2FA, accounts, transactions, and reports are not; every other
  functional claim in the planning docs remains a requirement, not a shipped fact.
- The refresh cookie is `HttpOnly`/`Secure`/`SameSite=Lax`, but double-submit CSRF enforcement on
  refresh is not implemented yet. It must land with the frontend auth client before release.
- Password change from a signed-in session (`/auth/password/change/`) and explicit Google linking
  are not implemented yet. Google sign-in refuses to link an existing password account.
- Health endpoints, registration, session flows, email verification, password reset, and Google
  sign-in are the tested routes.
- Estimates in `docs/ROADMAP.md` are ranges, not commitments.

---

## Template for future entries

```
## [Phase X.Y] — YYYY-MM-DD
### Added
- <user-visible capability> (<requirement IDs>)
### Changed
- <behavior change and why>
### Fixed
- <defect> (<test that now covers it>)
### Security
- <control added or finding resolved>
### Database
- <migration name and effect>
### Known limitations
- <what remains, with owner/phase>
```
