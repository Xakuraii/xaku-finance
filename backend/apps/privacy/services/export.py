"""Service to generate and manage user data exports.

See docs/architecture/SECURITY.md Section 9.1 and docs/api/API_SPECIFICATION.md Section 16.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.models import Account
from apps.budgets.models import Budget
from apps.debts.models import Liability
from apps.identity.models import User
from apps.privacy.models import DataExportJob, ExportFormat, ExportScope, ExportStatus
from apps.savings.models import SavingsGoal
from apps.transactions.models import Transaction
from apps.workspaces.models import Workspace


def get_export_dir() -> Path:
    """Return the filesystem directory for temporary export archives."""
    base_dir = getattr(settings, "MEDIA_ROOT", Path(settings.BASE_DIR) / "media")
    export_dir = Path(base_dir) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def create_export_job(
    *,
    user: User,
    workspace: Workspace,
    scope: str = "all",
    export_format: str = "json",
) -> DataExportJob:
    """Create and immediately execute a data export job."""
    if scope not in ExportScope.values:
        raise ValidationError(f"Invalid export scope '{scope}'.")
    if export_format not in ExportFormat.values:
        raise ValidationError(f"Invalid export format '{export_format}'.")

    now = timezone.now()
    job = DataExportJob.objects.create(
        user=user,
        workspace=workspace,
        scope=scope,
        format=export_format,
        status=ExportStatus.PROCESSING,
    )

    try:
        data = _compile_export_data(user=user, workspace=workspace, scope=scope)
        file_bytes, filename, content_type = _serialize_export(data, export_format, job.id)

        target_path = get_export_dir() / filename
        target_path.write_bytes(file_bytes)

        job.file_path = str(target_path)
        job.file_size_bytes = len(file_bytes)
        job.status = ExportStatus.COMPLETED
        job.completed_at = now
        job.download_expires_at = now + timedelta(hours=24)
        job.save(
            update_fields=[
                "file_path",
                "file_size_bytes",
                "status",
                "completed_at",
                "download_expires_at",
                "updated_at",
            ]
        )
        return job
    except Exception as exc:
        job.status = ExportStatus.FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message", "updated_at"])
        raise


def cancel_export_job(job_id: str, *, user: User) -> DataExportJob:
    """Cancel an active or pending export job."""
    job = DataExportJob.objects.filter(id=job_id, user=user).first()
    if job is None:
        raise NotFound("Export job not found.")

    if job.status in [ExportStatus.COMPLETED, ExportStatus.FAILED]:
        return job

    job.status = ExportStatus.CANCELLED
    job.save(update_fields=["status", "updated_at"])
    return job


def get_export_download_data(job_id: str, *, user: User) -> tuple[bytes, str, str]:
    """Retrieve exported file content, filename, and MIME type."""
    job = DataExportJob.objects.filter(id=job_id, user=user).first()
    if job is None:
        raise NotFound("Export job not found.")

    if job.status != ExportStatus.COMPLETED or not job.file_path:
        raise ValidationError("Export is not ready for download.")

    if job.download_expires_at and timezone.now() > job.download_expires_at:
        raise ValidationError("Export download link has expired. Please request a new export.")

    path = Path(job.file_path)
    if not path.exists():
        raise NotFound("Export file no longer exists on disk.")

    content = path.read_bytes()
    filename = path.name
    content_type = "application/json" if job.format == ExportFormat.JSON else "text/csv"
    return content, filename, content_type


def _compile_export_data(
    *,
    user: User,
    workspace: Workspace,
    scope: str,
) -> dict[str, Any]:
    """Compile structured dictionary of user and workspace financial records."""
    data: dict[str, Any] = {
        "export_metadata": {
            "version": "1.0.0",
            "generated_at": timezone.now().isoformat(),
            "scope": scope,
        },
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": getattr(getattr(user, "profile", None), "display_name", ""),
            "created_at": user.created_at.isoformat() if hasattr(user, "created_at") else "",
        },
        "workspace": {
            "id": str(workspace.id),
            "name": workspace.name,
            "reporting_currency": str(workspace.reporting_currency_id),
            "timezone": workspace.timezone,
        },
    }

    if scope in (ExportScope.ALL, ExportScope.ACCOUNTS):
        accounts = Account.objects.filter(workspace=workspace)
        data["accounts"] = [
            {
                "id": str(acc.id),
                "name": acc.name,
                "account_type": acc.account_type,
                "currency": str(acc.currency_id),
                "is_spendable": acc.is_spendable,
                "archived_at": acc.archived_at.isoformat() if acc.archived_at else None,
            }
            for acc in accounts
        ]

    if scope in (ExportScope.ALL, ExportScope.TRANSACTIONS):
        transactions = (
            Transaction.objects.filter(workspace=workspace)
            .prefetch_related("splits", "tagged_items")
            .order_by("-occurred_on")
        )
        data["transactions"] = [
            {
                "id": str(tx.id),
                "date": tx.occurred_on.isoformat(),
                "amount": str(tx.amount_minor),
                "currency": str(tx.currency_id),
                "status": tx.status,
                "title": tx.title,
                "description": tx.description or "",
                "merchant": tx.merchant or "",
                "splits": [
                    {
                        "amount": str(sp.amount_minor),
                        "category_id": str(sp.category_id) if sp.category_id else None,
                        "description": sp.memo or "",
                    }
                    for sp in tx.splits.all()
                ],
                "tags": [item.tag.name for item in tx.tagged_items.all()],
            }
            for tx in transactions
        ]

    if scope in (ExportScope.ALL, ExportScope.BUDGETS):
        budgets = Budget.objects.filter(workspace=workspace).select_related("category")
        data["budgets"] = [
            {
                "id": str(b.id),
                "category_id": str(b.category_id) if b.category_id else None,
                "category_name": b.category.name if b.category else None,
                "period_type": b.period_type,
                "amount": str(b.amount),
                "currency": str(b.currency_id),
                "rollover": b.rollover,
            }
            for b in budgets
        ]

    if scope == ExportScope.ALL:
        goals = SavingsGoal.objects.filter(workspace=workspace)
        data["savings_goals"] = [
            {
                "id": str(g.id),
                "name": g.name,
                "target_amount": str(g.target_amount),
                "currency": str(g.currency_id),
                "target_date": g.target_date.isoformat() if g.target_date else None,
                "status": g.status,
            }
            for g in goals
        ]

        debts = Liability.objects.filter(workspace=workspace)
        data["debts"] = [
            {
                "id": str(d.id),
                "name": d.name,
                "original_principal": str(d.original_principal),
                "currency": str(d.currency_id),
                "interest_rate_pct": str(d.interest_rate_pct),
                "status": d.status,
            }
            for d in debts
        ]

    return data


def _serialize_export(
    data: dict[str, Any],
    export_format: str,
    job_id: Any,
) -> tuple[bytes, str, str]:
    """Serialize dictionary into raw bytes (JSON or CSV)."""
    if export_format == ExportFormat.CSV:
        # Create CSV formatted transactions or accounts
        out = io.StringIO()
        writer = csv.writer(out)

        if "transactions" in data:
            writer.writerow(
                [
                    "Transaction ID",
                    "Date",
                    "Amount",
                    "Currency",
                    "Status",
                    "Title",
                    "Description",
                    "Merchant",
                    "Tags",
                ]
            )
            for tx in data.get("transactions", []):
                writer.writerow(
                    [
                        tx["id"],
                        tx["date"],
                        tx["amount"],
                        tx["currency"],
                        tx["status"],
                        tx["title"],
                        tx["description"],
                        tx["merchant"],
                        ", ".join(tx.get("tags", [])),
                    ]
                )
        elif "accounts" in data:
            writer.writerow(["Account ID", "Name", "Type", "Currency", "Spendable", "Archived"])
            for acc in data.get("accounts", []):
                writer.writerow(
                    [
                        acc["id"],
                        acc["name"],
                        acc["account_type"],
                        acc["currency"],
                        acc["is_spendable"],
                        acc["archived_at"],
                    ]
                )
        else:
            writer.writerow(["Key", "Value"])
            for k, v in data.items():
                writer.writerow([k, str(v)])

        filename = f"xakufinance-export-{job_id}.csv"
        return out.getvalue().encode("utf-8"), filename, "text/csv"

    # Default: JSON
    json_bytes = json.dumps(data, indent=2).encode("utf-8")
    filename = f"xakufinance-export-{job_id}.json"
    return json_bytes, filename, "application/json"
