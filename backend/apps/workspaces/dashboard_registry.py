"""Canonical Dashboard Widget Registry for XakuFinance.

Defines the supported widgets, default ordering, and validation logic.
See docs/SRS.md FR-DSH-01..08 and docs/API_SPECIFICATION.md Section 3.
"""

from __future__ import annotations

from typing import Any

CANONICAL_WIDGETS: dict[str, dict[str, Any]] = {
    "total_balance": {
        "key": "total_balance",
        "title": "Account Balances",
        "description": "Total balance per currency and converted consolidated total.",
        "default_enabled": True,
    },
    "net_worth": {
        "key": "net_worth",
        "title": "Net Worth",
        "description": "Current net worth and change versus prior period.",
        "default_enabled": True,
    },
    "safe_to_spend": {
        "key": "safe_to_spend",
        "title": "Safe-to-Spend",
        "description": (
            "Spendable cash available after obligations, pending outflows, and earmarks."
        ),
        "default_enabled": True,
    },
    "daily_allowance": {
        "key": "daily_allowance",
        "title": "Daily Allowance",
        "description": "Daily pacing allowance across remaining flexible budgets.",
        "default_enabled": True,
    },
    "cash_flow": {
        "key": "cash_flow",
        "title": "Cash Flow",
        "description": "Period income, period expenses, and net cash flow.",
        "default_enabled": True,
    },
    "budget_overview": {
        "key": "budget_overview",
        "title": "Budget Health",
        "description": "Active budgets, spent vs target, and progress.",
        "default_enabled": True,
    },
    "savings_progress": {
        "key": "savings_progress",
        "title": "Savings Goals",
        "description": "Progress toward targets, contributions, and pace.",
        "default_enabled": True,
    },
    "recent_transactions": {
        "key": "recent_transactions",
        "title": "Recent Transactions",
        "description": "Latest completed transactions across accounts.",
        "default_enabled": True,
    },
    "spending_by_category": {
        "key": "spending_by_category",
        "title": "Category Spending",
        "description": "Spending breakdown by expense category.",
        "default_enabled": True,
    },
}

DEFAULT_WIDGET_ORDER: list[str] = [
    "total_balance",
    "net_worth",
    "safe_to_spend",
    "daily_allowance",
    "cash_flow",
    "budget_overview",
    "savings_progress",
    "recent_transactions",
    "spending_by_category",
]


def get_default_layout() -> list[dict[str, Any]]:
    """Return the default widget list in canonical order."""
    return [
        {
            "key": key,
            "title": CANONICAL_WIDGETS[key]["title"],
            "enabled": CANONICAL_WIDGETS[key]["default_enabled"],
        }
        for key in DEFAULT_WIDGET_ORDER
    ]


def validate_widget_list(widgets: list[Any]) -> list[dict[str, Any]]:
    """Validate and sanitize a widget list for layout persistence.

    Ensures every entry has a valid canonical 'key' and a boolean 'enabled'.
    Unknown widgets are preserved to avoid wiping client customizations.
    Duplicate keys are rejected.
    """
    if not isinstance(widgets, list):
        raise ValueError("Widgets must be a list.")

    seen_keys: set[str] = set()
    sanitized: list[dict[str, Any]] = []

    for item in widgets:
        if not isinstance(item, dict):
            raise ValueError("Each widget entry must be an object.")
        key = item.get("key")
        if not key or not isinstance(key, str):
            raise ValueError("Each widget entry must have a non-empty string 'key'.")
        if key in seen_keys:
            raise ValueError(f"Duplicate widget key '{key}'.")
        seen_keys.add(key)

        enabled = bool(item.get("enabled", True))
        title = item.get("title") or (
            CANONICAL_WIDGETS[key]["title"] if key in CANONICAL_WIDGETS else key
        )

        sanitized.append({
            "key": key,
            "title": title,
            "enabled": enabled,
        })

    return sanitized
