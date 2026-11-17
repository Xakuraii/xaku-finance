# ADR 0002 — Integer minor units for money

**Status:** accepted
**Date:** 2026-11-17

## Context

The product handles USD and KHR, splits, FX rates, budgets, and reports. Floats produce 0.1 + 0.2 errors
and make exact equality tests unreliable. Decimal columns are exact, but leave rounding policy implicit
and allow accidental mixing of currencies. The brief forbids floating-point arithmetic and requires
decimal-safe calculations that reconcile.

## Decision

- Persist money as `amount_minor BIGINT` plus `currency_code`.
- Currency metadata (`minor_unit`) lives in `ref_currency` (USD 2, KHR 2).
- Rates are `NUMERIC(20,10)`.
- Python uses `Decimal`; a `Money` value object owns parsing, quantization (ROUND_HALF_UP), and equality.
- Convert at one boundary only; record the rate, its date, its source, and the rounding mode.
- API requests use decimal strings; responses include the canonical string and minor units.
- TypeScript never performs money arithmetic; it parses for display and sends strings.
- Any difference in a cross-currency transfer becomes an explicit conversion fee/gain posting.

## Consequences

- Exact, reproducible arithmetic and simple tests.
- Conversion precision is explicit and auditable.
- Developers must convert at the edges and resist doing math in the client.
- Adding a currency with a different exponent (e.g. JPY 0, KWD 3) is metadata, not a migration.
- `BIGINT` supports up to ~92 quadrillion minor units, far beyond personal finance needs.

## Alternatives considered

1. **`NUMERIC(19,4)` columns.** Exact, but the exponent is arbitrary, currency can drift from the number,
   and rounding is less explicit. Rejected.
2. **Decimal strings in the database.** Correct but awkward to aggregate and index. Rejected.
3. **Floats.** Forbidden by the brief and by arithmetic reality.
