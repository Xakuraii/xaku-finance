# ADR 0006 — React SPA with a generated API client

**Status:** accepted
**Date:** 2026-11-17

## Context

The frontend is React + TypeScript. Financial screens need consistent formatting, accessible charts, and
strict agreement with backend calculations. Hand-written API types drift silently, especially during a
long build with many endpoints.

## Decision

- React 19 + Vite + TypeScript, Tailwind v4 with CSS-variable design tokens, Radix primitives.
- TanStack Query owns server state; URL parameters own filters and pagination.
- React Hook Form + Zod validate shape and format only; the server validates business rules.
- drf-spectacular generates OpenAPI 3.1; a generated TypeScript client lands in
  `frontend/src/lib/api/generated/` and is never hand-edited.
- CI regenerates the schema and client and fails on drift.
- Money is parsed and formatted in `lib/money.ts`, never used for arithmetic.
- Charts use Recharts behind a single `ChartFrame` that provides a table fallback and rate-policy footnote.
- No global store for financial data; no optimistic updates for balance-changing mutations.

## Consequences

- Type errors surface at build time when the API contract changes.
- The UI cannot silently disagree with the server about field names or shapes.
- Contract-first discipline is required: API changes and client regeneration ship together.
- Optimistic UI is limited, trading a little snappiness for correctness.
- Tailwind + tokens keep both themes consistent; the design system constrains ad-hoc styling.

## Alternatives considered

1. **Hand-written types and fetch wrappers.** Fast to start, but drift is inevitable.
2. **Next.js with server components.** Adds a Node runtime and a second place where financial
   authorization could be enforced; DRF is the requested backend.
3. **GraphQL.** More flexible queries, but heavier schema governance and no request from the product.
