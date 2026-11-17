# Glossary quick reference

The root `GLOSSARY.md` is canonical. This is a short reminder for everyday work; do not add new
definitions here without adding them there first.

| Term | Means | Does not mean |
|---|---|---|
| Amount | Non-negative magnitude in one currency | A signed balance |
| Posting | One immutable ledger line, debit-positive | A transaction |
| Journal entry | Balanced set of postings for one event | A user-facing record |
| Transaction | User-facing financial event | A ledger entry |
| Transfer | Movement between two owned accounts | Income or expense |
| Opening balance | Starting value, posted to equity | Income |
| Pending | Recorded, not posted, no balance effect | Completed with a delay |
| Archived | Hidden but retained and reportable | Deleted |
| Earmark | Virtual claim on existing savings | New money or an asset |
| Contribution | Movement toward a savings goal | Always a transfer |
| Principal | Debt amount that reduces what is owed | Interest or fees |
| Safe-to-Spend | Spendable capacity after commitments | Account balance |
| Daily allowance | Flexible budget ÷ remaining days | Income projection |
| Financial period | Bounded date range in workspace timezone | Calendar month only |
| Reporting currency | Currency for consolidated totals | Account currency |
| Conversion residual | Difference from rate/rounding, recorded explicitly | A hidden adjustment |
| Reconciliation | Proof that balances equal postings | A visual check |

Use sentence case in UI copy. Prefer "money set aside for this goal" over "earmark" in user-facing text;
keep the precise term in code, docs, and tests.
