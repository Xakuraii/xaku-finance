# Frontend standards

Applies to `frontend/`. React + TypeScript + Vite, Tailwind v4, Radix, TanStack Query, React Router,
RHF + Zod, Recharts.

## Structure

- `features/<domain>/` owns its pages, components, hooks, and tests.
- `components/` holds only genuinely shared primitives (Money, DataTable, ChartFrame, ConfirmDialog).
- `lib/` holds API client, money/date/format helpers, query keys.
- No circular imports between features; shared behavior moves up, not sideways.

## Money and dates

- Never store or compute money as a JS `number`. Parse to minor units with `lib/money.ts` for display, and
  send canonical decimal strings to the API.
- Format with `Intl.NumberFormat` using the workspace locale; always show the currency code in tables.
- Dates: `YYYY-MM-DD` for financial dates; render in the workspace timezone; never use local machine time
  to compute period boundaries.
- All totals come from the server. The client does not sum line items to produce a headline figure.

## Data fetching

- One query key factory in `lib/query-keys.ts`; keys include workspace and filters.
- Mutations invalidate the narrowest affected keys plus derived reports (`dashboard`, `net-worth`).
- No optimistic updates for balance-changing mutations. Show pending state, then refetch.
- API errors are rendered by field when `error.field` is present, otherwise as a form-level message.
- Generated client only; never hand-write request/response types for endpoints that exist in OpenAPI.

## Forms

- RHF + Zod for shape/format. Zod never decides sufficiency, budget validity, or accounting rules.
- Split editor blocks submit on total mismatch, but the server remains authoritative.
- Money inputs: `inputMode="decimal"`, accept comma or dot, reject >2 dp with a clear message.
- Destructive submits require an explicit confirm step with consequence copy.

## UI

- Use tokens from `styles/tokens.css`. No ad-hoc hex values.
- Radix for dialog, popover, select, tabs, switch; focus trap and restore are mandatory.
- Every async region has loading, empty, error, and partial states.
- Charts render inside `ChartFrame` with a table fallback and rate footnote.
- Tables use real semantics; money columns right-aligned and tabular.
- Light and dark mode are both first-class; check contrast before adding color.
- Respect `prefers-reduced-motion`.

## Accessibility

- Labels are associated with inputs; errors use `aria-describedby`.
- Keyboard reachable in DOM order; visible focus ring.
- Icon-only buttons have `aria-label`.
- Announce job completion and balance changes via a polite live region.
- No color-only status; include text.

## Testing

- Vitest + Testing Library for behavior; MSW for network.
- Playwright for critical flows; axe scan on primary pages.
- No snapshot tests of financial values; assert exact rendered strings.
- Test both themes where contrast matters, and the 360 px viewport for new screens.

## Style

- TypeScript strict; no `any` without a comment explaining why.
- Components small and focused; extract when a file exceeds ~250 lines.
- Named exports; default export only for route modules if required by the router.
- No `dangerouslySetInnerHTML`; insight/markdown text is rendered as plain text.
- ESLint + Prettier; run `typecheck` before claiming done.
