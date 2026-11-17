# XakuFinance Glossary

Canonical vocabulary. If code, docs, or conversation uses a term differently, the definition here
wins until this file is changed deliberately. No implementation details belong in this file.

## Money and value

**Minor unit** — the smallest indivisible unit of a currency. USD has 2 (cents); KHR has 2 in
XakuFinance for consistency, even though riel cash is rarely subdivided. All amounts are counted in
minor units.

**Amount** — a non-negative magnitude of money in one currency. Direction is never encoded in the
sign of an amount; direction comes from the posting side or the transaction type.

**Money** — an amount together with exactly one currency. Adding two Moneys of different currencies
is undefined until an explicit conversion produces a rate and a valued result.

**Exchange rate** — the number of quote-currency minor units per one base-currency major unit, at a
stated date and source (manual, provider, or transfer-specific).

**Conversion residual** — the difference between the converted value and the amount the user
expected, caused by rate and rounding. It is recorded as an FX gain/loss, never hidden.

**Reporting currency** — the single currency a workspace uses for consolidated totals and charts.
It does not change the currency in which accounts or transactions are denominated.

## Ledger

**Ledger account** — the accounting record that receives postings. Kinds: asset, liability, equity,
income, expense. Every financial Account and Liability owns exactly one ledger account.

**Posting** — one immutable line on a ledger account, signed debit-positive, in one currency.

**Journal entry** — an atomic, immutable set of postings that sums to zero per currency. It is the
only thing that can change a balance.

**Financial event** — the user-facing thing that happened, represented by one Transaction plus the
journal entry (or entries) it produced.

**Reversal** — a new journal entry that exactly negates a prior posted entry. Used instead of editing
posted history.

**Balance** — the signed sum of postings on a ledger account. For an asset account, a positive
balance means money is held. For a liability account, a positive balance means money is owed.

**Reconciliation** — proving that a balance equals the sum of its postings, and that a journal entry
sums to zero per currency.

**Opening balance** — the value an account held before tracking began. It is an equity movement, not
income, and it is recorded as a transaction with type `opening_balance`.

**System ledger account** — a ledger account that exists to make double entry work (income, expense,
equity, FX clearing) and is not shown as a user account.

## Transactions

**Transaction** — the user-facing financial event record: income, expense, transfer, opening balance,
debt disbursement, debt repayment, or adjustment.

**Split** — a category allocation inside an expense or income transaction. Splits of one transaction
sum exactly to its amount.

**Transfer** — a movement of value between two accounts owned by the same workspace. Never income,
never expense. Cross-currency transfers carry an explicit rate, optionally a fee, and always a
conversion residual channel.

**Pending** — recorded but not posted. Does not affect balances. May affect spending capacity
projections.

**Completed** — posted to the ledger. Affects balances and reports.

**Cancelled** — recorded as withdrawn. Never affects balances or reports, retained for audit.

**Archived** — hidden from everyday views but fully retained and reportable. Archiving is not deletion.

**Necessity** — optional spending classification: `essential`, `important`, `lifestyle`, `unplanned`.

**Tag** — a free-form, workspace-scoped label for cross-cutting analysis. Tags carry no accounting
meaning.

## Planning

**Financial period** — a bounded date range used for reporting and budgeting. Calendar month/week/year,
or a user-defined custom period. Boundaries are interpreted in the workspace timezone.

**Budget** — a plan for spending in one category over repeating periods. It has a base allocation and
optional positive-only rollover.

**Base allocation** — the money a budget grants in a period before rollover.

**Rollover in / out** — value carried from the previous period into the current one / value carried
from the current period into the next. Only positive unused value carries; overspending never creates
negative rollover.

**Flexible budget** — a budget whose remaining value may fund discretionary daily spending. Fixed and
reserved budgets are excluded from the daily allowance.

**Savings goal** — a target amount of money the user intends to set aside, with a target date.

**Earmark (allocation)** — a virtual claim by a savings goal on money that already sits in an account.
Earmarks never create assets and can never exceed the account's available balance.

**Contribution** — a recorded movement of money toward a goal: either a transfer into a linked savings
account, an earmark of existing savings, an adjustment, or a withdrawal.

**Liability** — a debt the user owes. Its outstanding principal is a ledger balance, not a manually
maintained number.

**Principal** — the part of a debt repayment that reduces the amount owed.

**Interest** — the cost of borrowing. Always an expense, never principal.

**Safe-to-Spend** — spendable account money minus committed outflows (pending spending, upcoming
reserved obligations, planned savings contributions). A capacity figure, not a balance.

**Daily spending allowance** — remaining flexible budget divided by remaining days in the active
financial period, floored at zero.

**Emergency fund target** — essential monthly expenses multiplied by a chosen coverage in months.

**Net worth** — total assets minus total liabilities, valued at a stated date in the reporting
currency. Historical net worth is derived from ledger history at that date, using the rates in effect
then, never today's balances.

## Identity and platform

**User** — an authenticated person. Owns exactly one workspace.

**Workspace** — the privacy and accounting boundary. All financial data belongs to exactly one
workspace. There are no shared workspaces in V1.

**Session** — a refresh-token lineage that a user can inspect and revoke individually.

**Security notification** — a notification about account security that cannot be disabled or muted.

**Import job** — a staged CSV/XLSX import that must be validated and reviewed before any row becomes a
transaction.

**Duplicate candidate** — an imported row suspected of matching an existing transaction, presented to
the user for a decision. Never discarded silently.

**Backup** — an encrypted, checksummed copy of data with a declared retention window.

**Restoration** — a validated, non-destructive load of backup or export data into an empty workspace.

## Forbidden vocabulary

- "Balance" used to mean an account's transaction list.
- "Expense" used for a transfer, savings earmark, debt principal, or opening balance.
- "Deleted" for an archived financial record.
- "Real-time rate" for a rate that was manually entered.
- "AI forecast" for any number the server did not deterministically compute.
- "Synced" for data that was imported once.
