# Design System — XakuFinance

**Direction:** *ledger, not lobby.* An obsidian-and-brass financial instrument: quiet surfaces, a single
golden accent that marks value and action, editorial serif for headlines, technical sans for controls, and
numbers that always line up in columns. It should feel like a private bank statement that happens to be
software — not a crypto exchange, and not a generic SaaS dashboard.

Golden is the brand (`#F0B90B`, the Binance-family gold the client asked for), used with restraint: as a
rule, a focus ring, a primary action, and the one number that matters on a screen. Never as a page wash,
never gradient-filled, never as body text on white.

**Status:** specification only. No UI is implemented.

---

## 1. Brand tokens

### 1.1 Color — dark (primary experience)

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#0B0E11` | App background, the "obsidian" |
| `--surface` | `#12161C` | Panels, statement body |
| `--surface-raised` | `#1A2027` | Menus, popovers, sticky headers |
| `--border` | `#262D36` | Hairlines, table rules |
| `--border-strong` | `#3A4450` | Focus-adjacent boundaries, selected rows |
| `--text` | `#F2F0EA` | Primary text (warm white, not #FFF) |
| `--text-muted` | `#9AA3AE` | Secondary labels, metadata |
| `--text-faint` | `#6B7480` | Disabled, timestamps |
| `--accent` | `#F0B90B` | Brand gold: primary action, active nav, key figure |
| `--accent-hover` | `#FFD34E` | Hover on gold |
| `--accent-press` | `#D9A600` | Pressed |
| `--on-accent` | `#14171C` | Text/icons on gold |
| `--positive` | `#2EBD85` | Income, progress, on-track |
| `--negative` | `#F0616D` | Expense, over-budget, destructive text |
| `--warning` | `#E8A33D` | Threshold warnings |
| `--info` | `#6EA8FE` | Neutral informational |
| `--focus` | `#F0B90B` | Focus ring, 2 px + 2 px offset |

### 1.2 Color — light

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#F7F5F0` | Warm paper background, not pure white |
| `--surface` | `#FFFFFF` | Statement panels |
| `--surface-raised` | `#FFFFFF` | Popovers with shadow |
| `--border` | `#E3DED2` | Hairlines (warm gray) |
| `--border-strong` | `#C9C2B2` | Stronger dividers |
| `--text` | `#171A1F` | Primary |
| `--text-muted` | `#5C6470` | Secondary |
| `--text-faint` | `#8A8F98` | Disabled |
| `--accent` | `#8A6508` | **Text-safe** gold for links/labels on paper |
| `--accent-fill` | `#F0B90B` | Filled buttons/active indicators |
| `--on-accent` | `#171A1F` | Text on gold fill |
| `--positive` | `#0F7A5A` | Text-safe positive |
| `--negative` | `#B4232F` | Text-safe negative |
| `--warning` | `#8A5A00` | Text-safe warning |
| `--info` | `#1F5FBF` | Text-safe info |

**Contrast rules**

- Gold `#F0B90B` on white is ~1.7:1 and must never be used for text on light surfaces. Use `#8A6508`
  (~5.0:1) instead.
- Gold fill uses `--on-accent` (#171A1F) text, never white.
- Red/green are never the only signal: pair with `+`/`−`, an icon, or a label.
- Muted text must remain ≥ 4.5:1 on its surface; `--text-faint` is for non-essential text only.
- Charts use the categorical palette below, tested for deuteranopia.

### 1.3 Categorical chart palette

| Slot | Dark | Light |
|---|---|---|
| 1 | `#F0B90B` gold | `#B8860B` |
| 2 | `#7FB6A4` sage | `#2F7F6B` |
| 3 | `#8AA4D6` slate blue | `#3F5E9E` |
| 4 | `#C99A7A` clay | `#9A5E36` |
| 5 | `#B7A6D9` lilac | `#6B4FA0` |
| 6 | `#9DA6B2` graphite | `#5A636F` |

Order is fixed by category id so a category keeps its color across screens. More than six categories
collapse into "Other" plus an accessible table.

---

## 2. Typography

| Role | Family | Size / weight | Notes |
|---|---|---|---|
| Display | **Fraunces** (variable, optical size 72, `wght 500–600`) | 40–56/1.05 | Page titles, net worth hero; used sparingly |
| Heading | Fraunces | 24–32/1.15 | Section titles, empty-state headlines |
| Body/UI | **IBM Plex Sans** | 14–16/1.5 | Controls, prose, tables |
| Data | IBM Plex Sans with `font-variant-numeric: tabular-nums` | 13–15 | All amounts, dates, counts |
| Micro | IBM Plex Sans | 11–12/1.35, letter-spacing 0.01em | Axis labels, helper text (sentence case, not all caps) |

Rules:

- Two families only. No monospace "for tech flavor"; tabular figures do the alignment work.
- Financial figures use tabular numbers and right-aligned columns in tables.
- Currency code is always visible (`1,250.50 USD`), never implied by a symbol alone.
- Max line length 72ch for prose, 90ch for tables.
- No all-caps labels. No italicized single-word emphasis in headings. No eyebrow labels above every
  section; a section earns a heading only when it needs one.
- Type scale: 11, 12, 13, 14, 16, 20, 25, 31, 39, 49. Line heights: 1.1 for display, 1.25 for headings,
  1.5 body, 1.3 data rows.

---

## 3. Layout

### 3.1 App shell

```
┌───────────────────────────────────────────────────────────────────────────┐
│  brand      workspace · reporting currency · period        user  theme    │ 56px
├───────────────┬───────────────────────────────────────────────────────────┤
│ Dashboard     │  Page title                              primary action   │
│ Transactions  │  ┌─────────────────────────────────────────────────────┐  │
│ Accounts      │  │ statement surface: no drop shadow, 1px hairline     │  │
│ Budgets       │  │                                                     │  │
│ Savings       │  │   Net worth            Assets          Liabilities  │  │
│ Debts         │  │   3,490.00 USD        4,390.00        900.00        │  │
│ Net Worth     │  │   ───────────────────────────────────────────────   │  │
│ Reports       │  │   chart / table / detail rows                       │  │
│ Emergency     │  └─────────────────────────────────────────────────────┘  │
│ Settings      │                                                           │
└───────────────┴───────────────────────────────────────────────────────────┘
```

- Left rail 232 px on ≥1280 px, icon rail 64 px at 1024–1279 px, bottom tab bar + drawer below 768 px.
- Content max width 1440 px, 32 px gutters at desktop, 20 px tablet, 16 px mobile.
- 12-column grid; financial detail uses columns 1–8 with a 4-column context panel (not a card grid).
- Primary surfaces are **statement sheets**: one border, hairline row dividers, generous vertical rhythm.
  Avoid the SaaS-card kit (identical rounded cards with the same shadow everywhere).
- Radius scale: 4 px inputs, 6 px surfaces, 999 px pills only for status chips. Not everything is a pill.
- Elevation: dark mode uses surface lightening + 1 px border, not shadows. Light mode uses one soft shadow
  only for popovers/dialogs.

### 3.2 Key screens

| Screen | Composition |
|---|---|
| Dashboard | Net worth hero with period delta; a single "position line" of four figures (income, expenses, safe-to-spend, allowance); spending chart; recent transactions; budgets; goals. Widget order user-controlled. |
| Transactions | Sticky filter bar, dense table (date, title, category/tags, account, amount), side detail drawer with splits and audit. Amount column right-aligned. Pending rows use a dotted left rule, archived are hidden by default. |
| Account detail | Balance header, currency badge, register table with running balance, transfer markers, reconciliation status. |
| Budgets | A vertical list of budget rows with a thin progress rule (not donut rings), base/rollover/spent/remaining in aligned columns, rollover explained in place. |
| Savings | Goal rows with progress rule, "funded from" account, per-account allocation capacity, contribute action. |
| Debts | Outstanding hero, principal vs interest split, repayment timeline, "why net worth moved" note. |
| Net worth | Large historical line chart with period markers, assets/liabilities stacked bar, breakdown table, FX effect line. |
| Reports | Report switcher as tabs, filter bar, chart + table toggle, reconciliation footnote. |
| Settings | Sectioned form pages, not one long scroll. Destructive actions isolated with explanation. |

### 3.3 Responsive rules

- 360 px: single column, tables become definition lists or horizontally scrollable with a sticky first
  column; charts simplify to sparkline + table link.
- 768 px: two-column metric rows; drawer becomes a full-height sheet.
- 1024 px: icon rail; content 2-column.
- 1440 px+: max width, optional context panel.
- No horizontal page scroll at any supported width. Touch targets ≥ 44 px.

---

## 4. Components

Built on Radix primitives (dialog, popover, select, tabs, tooltip, switch, checkbox) with project styling.

| Component | Notes |
|---|---|
| `Money` | Renders amount + currency, tabular, optional sign/color, never truncates without a title/aria label |
| `Metric` | Label, value, delta, period; one hero variant |
| `StatementSheet` | Bordered surface with header, rows, footer; the main content container |
| `DataTable` | Sticky header, right-aligned money columns, row hover, keyboard row actions, empty state |
| `ProgressRule` | 2 px horizontal rule with a filled portion, threshold ticks; not a ring |
| `StatusChip` | Text + dot; never color alone; includes state word |
| `PeriodPicker` | Month/week/year/custom; always shows resolved start–end and timezone |
| `CategoryPicker` | Searchable, grouped, "create" affordance, recent first |
| `SplitEditor` | Rows with category + amount, live total vs parent, blocks mismatch |
| `ChartFrame` | Title, legend, chart, "View as table" disclosure, footnote for rate policy |
| `EmptyState` | One sentence + one action; explains what will appear |
| `ErrorState` | What happened, what to do, request id; no apology copy |
| `ConfirmDialog` | Destructive actions require typing or explicit checkbox; states consequences |
| `Drawer` | Transaction detail and forms on desktop; full-screen sheet on mobile |
| `Toast` | Background job completion/failure only, not every save |
| `Skeleton` | Shape-matched, no shimmer cascade; reduced motion disables animation |

Copy rules: sentence case, verbs match outcomes ("Save transaction" → "Transaction saved"), no exclamation
marks, no jargon ("unallocated balance", not "earmark headroom"), error messages state cause and remedy.

Examples:

- Empty transactions: "No transactions yet. Add your first expense or import a CSV."
- Budget over: "Over by 24.00 USD. The next period starts at its base amount; overspending does not roll
  over."
- Safe-to-Spend zero: "0.00 USD available after 300.00 USD of reserved bills and 100.00 USD planned
  savings. See the breakdown."
- Missing rate: "No USD/KHR rate for this date. Add a rate in Settings to see a converted total."

---

## 5. Charts

1. Bar charts start at zero. Line charts may not, but the axis minimum is labeled and a zero reference line
   is drawn when the range includes zero.
2. No dual y-axes. Two measures → two stacked charts sharing an x-axis.
3. Currency is in the axis label or the tooltip, never omitted.
4. Tooltips show exact values with currency and date; hover is not required to read the chart (table
   fallback exists).
5. Series colors come from the fixed categorical palette, assigned by category id.
6. Converted series disclose `rate_policy` in the frame footnote.
7. Motion: one 240 ms draw-in on first load, disabled under `prefers-reduced-motion`. No looping animation.
8. Empty state: axis frame + "No data for this period" + link to change period. Never fake a flat line at
   zero.

---

## 6. Motion

| Token | Value | Use |
|---|---|---|
| `--dur-fast` | 120 ms | Hover, focus |
| `--dur-base` | 180 ms | Menus, drawers, chips |
| `--dur-slow` | 240 ms | Dialog enter, chart draw |
| `--ease` | `cubic-bezier(0.2, 0, 0, 1)` | Default |

- One orchestrated page-load moment on the dashboard: the net-worth figure settles and its delta fades in.
- No hover-lift on cards, no parallax, no gradient sweeps.
- Destructive actions do not animate playfully.
- `prefers-reduced-motion: reduce` removes transforms and chart draw-ins, keeps opacity under 100 ms.

---

## 7. Iconography and illustration

- Lucide icons, 1.5 px stroke, 18/20 px. Icons never replace a text label in primary navigation on desktop.
- No mascots, no 3D coins, no stock photography.
- Empty states use a simple geometric mark (a single brass rule or an outlined ledger glyph), not an
  illustrated scene.
- Brand mark: the word "Xaku" set in Fraunces with a small brass square replacing the tittle-less "a"? No —
  avoid clever typographic surgery. Use a brass square glyph + "XakuFinance" wordmark, and keep it simple
  until a real logo brief exists.

---

## 8. Accessibility requirements

- WCAG 2.2 AA: 4.5:1 text, 3:1 large text and UI boundaries, visible focus at 2 px with offset.
- All interactive elements keyboard reachable in a logical order; drawers/dialogs trap focus and restore it.
- Tables use real `<table>` semantics with `<th scope>`; money columns have accessible headers.
- Charts expose a table alternative and a text summary; color is never the only encoding.
- Form errors are linked with `aria-describedby`; the first invalid field receives focus.
- Live regions announce async job completion and balance-changing actions.
- Respects browser zoom to 200% without loss; no text in images.
- Both themes independently pass contrast; gold-on-paper uses `#8A6508`.

---

## 9. Content and tone

- Calm, factual, specific. "Saved." not "Awesome! 🎉".
- Never imply certainty about the future: "At your current pace, you'd reach this goal around May 2027."
- Never present an estimate as a guarantee; label computed figures with their source and period.
- Destructive copy names exactly what is lost, what is kept, and whether it can be undone.
- The product does not congratulate users for spending or saving; it informs them.

---

## 10. Implementation notes

- Tokens live in `frontend/src/styles/tokens.css` as CSS custom properties, with `[data-theme="dark"]` and
  `[data-theme="light"]` overrides; Tailwind v4 `@theme` maps them to utilities. No hard-coded hex values in
  components.
- Theme is applied before first paint from the user preference (server-provided on the bootstrap payload),
  avoiding a flash.
- Fonts are self-hosted WOFF2, subset to Latin + Khmer later; `font-display: swap`; preload only the two
  primary faces.
- One `ChartFrame` and one `DataTable` implementation; reports do not each reinvent axes or empty states.
- Visual regression: Playwright screenshots of key screens in both themes at 360/768/1440, reviewed on
  changes to tokens or layout.
- If a screen needs a new color, it needs a token and a contrast check first.
