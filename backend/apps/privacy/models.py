"""Privacy, data export, and account deletion models.

See docs/architecture/SECURITY.md Section 9 and docs/api/API_SPECIFICATION.md Section 16.
"""

from __future__ import annotations

import uuid

from django.db import models
from django.db.models import CheckConstraint, Index, Q


class ExportScope(models.TextChoices):
    ALL = "all", "All Workspace Data"
    TRANSACTIONS = "transactions", "Transactions Only"
    ACCOUNTS = "accounts", "Accounts Only"
    BUDGETS = "budgets", "Budgets Only"


class ExportFormat(models.TextChoices):
    JSON = "json", "JSON"
    CSV = "csv", "CSV"
    ZIP = "zip", "ZIP Archive"


class ExportStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class DataExportJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="data_exports",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_exports",
    )
    scope = models.CharField(
        max_length=32,
        choices=ExportScope.choices,
        default=ExportScope.ALL,
    )
    format = models.CharField(
        max_length=16,
        choices=ExportFormat.choices,
        default=ExportFormat.JSON,
    )
    status = models.CharField(
        max_length=16,
        choices=ExportStatus.choices,
        default=ExportStatus.PENDING,
    )
    file_path = models.CharField(max_length=512, blank=True, default="")
    file_size_bytes = models.BigIntegerField(default=0)
    download_expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "data_export_job"
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["workspace", "created_at"], name="export_ws_created_idx"),
            Index(fields=["user", "status"], name="export_user_status_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(status__in=ExportStatus.values),
                name="export_status_valid_ck",
            ),
            CheckConstraint(
                condition=Q(scope__in=ExportScope.values),
                name="export_scope_valid_ck",
            ),
            CheckConstraint(
                condition=Q(format__in=ExportFormat.values),
                name="export_format_valid_ck",
            ),
        ]

    def __str__(self) -> str:
        return f"Export {self.id} ({self.scope}, {self.format}) [{self.status}]"


class DeletionRequestStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    CANCELLED = "cancelled", "Cancelled"
    EXECUTED = "executed", "Executed"


class AccountDeletionRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="deletion_requests",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deletion_requests",
    )
    status = models.CharField(
        max_length=16,
        choices=DeletionRequestStatus.choices,
        default=DeletionRequestStatus.REQUESTED,
    )
    execute_after = models.DateTimeField()
    backup_expiry_date = models.DateField()
    cancelled_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "account_deletion_request"
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["user", "status"], name="del_req_user_status_idx"),
            Index(fields=["execute_after", "status"], name="del_req_exec_status_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(status__in=DeletionRequestStatus.values),
                name="del_req_status_valid_ck",
            ),
        ]

    def __str__(self) -> str:
        return f"DeletionRequest {self.id} ({self.user.email}) [{self.status}]"
