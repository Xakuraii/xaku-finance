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

### Decisions
- Double-entry ledger with system accounts is the accounting foundation.
- Money is stored as integer minor units; no floats anywhere.
- One transaction aggregate with type-specific detail tables; edits reverse and repost.
- Single workspace per user; no collaboration in V1.
- Golden `#F0B90B` brand accent, dark-first, with a text-safe gold for light mode.
- Transactions are account-currency only; FX exists only on transfers.
- Receipt attachments/OCR, multi-workspace, bank sync, and AI chat are out of V1.

### Known limitations
- Only the backend scaffold exists. Registration, accounts, transactions, and reports are not
  implemented yet; every functional claim in the planning docs remains a requirement, not a shipped
  fact.
- Health endpoints and the schema endpoint are the only tested routes.
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
