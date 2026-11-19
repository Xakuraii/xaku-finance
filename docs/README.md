# XakuFinance Documentation

Welcome to the XakuFinance documentation repository. The documentation is organized into domain-focused directories:

## Documentation Structure

### 1. [API](api/)
API specifications and machine-readable schema contracts:
- [`API_SPECIFICATION.md`](api/API_SPECIFICATION.md) — Endpoints, payloads, errors, pagination, authentication, and idempotency contracts.
- [`openapi.yaml`](api/openapi.yaml) — OpenAPI 3.1 schema specification.

### 2. [Architecture](architecture/)
System architecture, domain models, and core invariants:
- [`ARCHITECTURE.md`](architecture/ARCHITECTURE.md) — System, ledger, reporting, auth, background, backup, and deployment architecture.
- [`ACCOUNTING_RULES.md`](architecture/ACCOUNTING_RULES.md) — Immutable double-entry ledger rules, posting recipes, money rules, reconciliation.
- [`DATABASE.md`](architecture/DATABASE.md) — Entity specification, check constraints, indexes, and ERD diagrams.
- [`DESIGN_SYSTEM.md`](architecture/DESIGN_SYSTEM.md) — Obsidian and gold design tokens, typography, chart palettes, accessible components.
- [`REPOSITORY_STRUCTURE.md`](architecture/REPOSITORY_STRUCTURE.md) — Codebase organization and layout conventions.
- [`SECURITY.md`](architecture/SECURITY.md) — Threat model, security controls, privacy, deletion, and backups.
- [`adr/`](adr/) — Architecture Decision Records (ADRs).

### 3. [Specifications](specifications/)
Product requirements, testing standards, and risk management:
- [`SRS.md`](specifications/SRS.md) — Software Requirements Specification (functional & non-functional requirements).
- [`ACCEPTANCE_CRITERIA.md`](specifications/ACCEPTANCE_CRITERIA.md) — V1.0 release acceptance checklist.
- [`FEATURE_MATRIX.md`](specifications/FEATURE_MATRIX.md) — Feature matrix (V1 required, optional, deferred).
- [`PLANNING_REVIEW.md`](specifications/PLANNING_REVIEW.md) — Consistency, arithmetic, double-counting, and feasibility review.
- [`RISKS.md`](specifications/RISKS.md) — Risk assessment, dependencies, and mitigation strategies.
- [`TESTING.md`](specifications/TESTING.md) — Test pyramid, financial-integrity test suite, and quality gates.

### 4. [Reports](reports/)
Milestone and phase completion reports with verification evidence:
- [`PHASE_1_REPORT.md`](reports/PHASE_1_REPORT.md) — Foundation & Identity verification report.
- [`PHASE_2_REPORT.md`](reports/PHASE_2_REPORT.md) — Core Financial Management verification report.
- [`PHASE_3_REPORT.md`](reports/PHASE_3_REPORT.md) — Financial Planning verification report.
- [`PHASE_4_REPORT.md`](reports/PHASE_4_REPORT.md) — Financial Intelligence verification report.
- [`PHASE_5_REPORT.md`](reports/PHASE_5_REPORT.md) — User Experience verification report.

### 5. Project Roadmap & History
- [`ROADMAP.md`](ROADMAP.md) — Multi-phase delivery roadmap, milestones, dependencies, and exit criteria.
- [`CHANGELOG.md`](CHANGELOG.md) — Chronological history of user-facing changes, features, and fixes.
- [`superpowers/plans/`](superpowers/plans/) — Historical implementation execution plans.
