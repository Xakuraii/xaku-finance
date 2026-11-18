"""Import models: multi-step import jobs, staged records, and duplicate candidates."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

from apps.common.models import WorkspaceScopedModel


class ImportJobStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    VALIDATING = "validating", "Validating"
    VALIDATED = "validated", "Validated"
    AWAITING_REVIEW = "awaiting_review", "Awaiting Review"
    COMMITTING = "committing", "Committing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class ImportRecordStatus(models.TextChoices):
    VALID = "valid", "Valid"
    INVALID = "invalid", "Invalid"
    DUPLICATE_EXACT = "duplicate_exact", "Duplicate Exact"
    DUPLICATE_POTENTIAL = "duplicate_potential", "Duplicate Potential"
    SKIPPED = "skipped", "Skipped"
    IMPORTED = "imported", "Imported"


class ImportRecordAction(models.TextChoices):
    IMPORT = "import", "Import"
    SKIP = "skip", "Skip"


class DuplicateCandidateDecision(models.TextChoices):
    PENDING = "pending", "Pending"
    IMPORT = "import", "Import"
    SKIP = "skip", "Skip"


class ImportJob(WorkspaceScopedModel):
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="import_jobs",
    )
    created_by = models.ForeignKey(
        "identity.User",
        on_delete=models.PROTECT,
        related_name="import_jobs",
    )
    file_name = models.CharField(max_length=240)
    file_format = models.CharField(max_length=8, default="csv")
    source_hash = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16,
        choices=ImportJobStatus.choices,
        default=ImportJobStatus.UPLOADED,
    )
    mapping = models.JSONField(default=dict)
    row_count = models.IntegerField(default=0)
    valid_count = models.IntegerField(default=0)
    invalid_count = models.IntegerField(default=0)
    duplicate_count = models.IntegerField(default=0)
    imported_count = models.IntegerField(default=0)
    error_summary = models.JSONField(default=dict)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "import_job"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["workspace", "status", "-created_at"],
                name="imp_job_ws_stat_date_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"ImportJob {self.id}: {self.file_name} ({self.status})"


class ImportRecord(WorkspaceScopedModel):
    import_job = models.ForeignKey(
        ImportJob,
        on_delete=models.CASCADE,
        related_name="records",
    )
    row_number = models.IntegerField()
    raw = models.JSONField(default=dict)
    normalized = models.JSONField(null=True, blank=True)
    fingerprint = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ImportRecordStatus.choices,
        default=ImportRecordStatus.VALID,
    )
    action = models.CharField(
        max_length=8,
        choices=ImportRecordAction.choices,
        default=ImportRecordAction.IMPORT,
    )
    errors = models.JSONField(default=list)
    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_records",
    )

    class Meta:
        db_table = "import_record"
        ordering = ["row_number"]
        indexes = [
            models.Index(
                fields=["import_job", "status"],
                name="imp_rec_job_stat_idx",
            ),
            models.Index(
                fields=["workspace", "fingerprint"],
                name="imp_rec_ws_fp_idx",
            ),
        ]
        constraints = [
            UniqueConstraint(
                fields=["import_job", "row_number"],
                name="imp_rec_job_row_uq",
            ),
        ]

    def __str__(self) -> str:
        return f"Row {self.row_number} ({self.status}) for job {self.import_job_id}"


class DuplicateCandidate(WorkspaceScopedModel):
    import_record = models.ForeignKey(
        ImportRecord,
        on_delete=models.CASCADE,
        related_name="duplicate_candidates",
    )
    existing_transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.PROTECT,
        related_name="duplicate_candidates",
    )
    score = models.DecimalField(max_digits=4, decimal_places=3)
    reasons = models.JSONField(default=dict)
    decision = models.CharField(
        max_length=8,
        choices=DuplicateCandidateDecision.choices,
        default=DuplicateCandidateDecision.PENDING,
    )
    decided_by = models.ForeignKey(
        "identity.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "duplicate_candidate"
        constraints = [
            CheckConstraint(
                condition=Q(score__gte=0) & Q(score__lte=1),
                name="dup_cand_score_range_ck",
            ),
            UniqueConstraint(
                fields=["import_record", "existing_transaction"],
                name="dup_cand_rec_tx_uq",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Candidate for row {self.import_record.row_number} vs tx "
            f"{self.existing_transaction_id} (score={self.score}, decision={self.decision})"
        )
