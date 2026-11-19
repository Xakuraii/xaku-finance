"""Data map definition for user transparency.

Provides clear visibility into what user data is stored, its purpose,
storage location, and retention schedule.
"""

from __future__ import annotations

from typing import Any


def get_privacy_data_map() -> list[dict[str, Any]]:
    """Return the structured data inventory map."""
    return [
        {
            "category": "Identity & Authentication",
            "description": "User email address, argon2id password hash, profile preferences, and encrypted TOTP 2FA secret.",
            "purpose": "Account creation, authentication, security enforcement, and multi-factor verification.",
            "lawful_basis": "Contractual necessity & security compliance",
            "retention": "Retained while the account is active; permanently removed upon account deletion.",
            "shared_with_third_parties": False,
        },
        {
            "category": "Financial Accounts & Balances",
            "description": "Account names, types (asset, liability, equity), currencies, and immutable double-entry ledger postings.",
            "purpose": "Core financial tracking, balance computation, and reconciliation verification.",
            "lawful_basis": "Contractual necessity",
            "retention": "Retained while the account is active; permanently removed upon account deletion.",
            "shared_with_third_parties": False,
        },
        {
            "category": "Transactions, Splits & Transfers",
            "description": "Financial movements, payment amounts, dates, descriptions, split allocations, transfer exchange rates, and tags.",
            "purpose": "Expense tracking, cashflow computation, and budget vs actual analysis.",
            "lawful_basis": "Contractual necessity",
            "retention": "Retained while the account is active; permanently removed upon account deletion.",
            "shared_with_third_parties": False,
        },
        {
            "category": "Budgets, Savings Goals & Liabilities",
            "description": "Category budget limits, rollover balances, savings goal targets, earmarked capacities, and debt repayment schedules.",
            "purpose": "Financial planning, forward projections, and debt reduction progress.",
            "lawful_basis": "Contractual necessity",
            "retention": "Retained while the account is active; permanently removed upon account deletion.",
            "shared_with_third_parties": False,
        },
        {
            "category": "Security, Audit & Notifications",
            "description": "HMAC-SHA256 hashed IP addresses, session identifiers, security notifications, delivery logs, and audit revisions.",
            "purpose": "Fraud prevention, replay attack mitigation, session management, and system integrity.",
            "lawful_basis": "Legitimate interest & security integrity",
            "retention": "Security audit records are retained for 12 months; live notifications removed on account deletion.",
            "shared_with_third_parties": False,
        },
        {
            "category": "Encrypted Database Backups",
            "description": "Encrypted point-in-time database snapshots stored securely in disaster recovery volumes.",
            "purpose": "Disaster recovery, data corruption protection, and business continuity.",
            "lawful_basis": "Legitimate interest & operational resilience",
            "retention": "Encrypted backup archives expire automatically within 30 days of creation.",
            "shared_with_third_parties": False,
        },
    ]
