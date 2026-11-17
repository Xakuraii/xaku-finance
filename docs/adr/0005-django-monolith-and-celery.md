# ADR 0005 — Django monolith with Celery for background work only

**Status:** accepted
**Date:** 2026-11-17

## Context

XakuFinance is a single-user workspace product with financial writes that must be atomic, reports that
aggregate relational data, and a handful of long-running operations (imports, exports, backups,
notifications). The team is small. The brief proposes Django + DRF, PostgreSQL, Redis, and Celery, while
warning against unnecessary infrastructure.

## Decision

- One Django project, one deployable API, modular apps with explicit service boundaries.
- PostgreSQL is the only source of truth.
- Celery + Redis handle only work that must not block a request or must retry: import commit, export,
  backup, notification delivery, period close, snapshot refresh, insight generation.
- Celery beat runs as a single scheduler; tasks are idempotent and keyed.
- No microservices, no message bus beyond Celery, no read replica in V1, no CQRS framework.
- Redis is never authoritative; flushing it must not lose financial data.

## Consequences

- Simple deployment: proxy, API containers, worker, beat, Postgres, Redis, object storage.
- Financial writes stay in one database transaction, which is what correctness needs.
- Background processing can be scaled independently later.
- The monolith will grow; app boundaries and service modules must be enforced by review to avoid a ball
  of mud.
- Long-running report queries could contend with writes at scale; period bounds and indexes mitigate,
  with a read replica as a future step.

## Alternatives considered

1. **Serverless functions per domain.** Cold starts, distributed transactions, and split schema ownership
   are all wrong for atomic financial writes.
2. **Separate reporting service/database.** Premature; adds sync complexity and a second truth.
3. **No Celery (synchronous exports).** Request timeouts and unreliable retries for backups and imports.
4. **Django + HTMX instead of an SPA.** Viable, but the requested frontend is React + TypeScript and the
   interactive charts/editors benefit from it.
