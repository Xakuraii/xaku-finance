"""Commit service: atomic creation of ledger transactions from staged import records."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.categories.models import Category, CategoryKind
from apps.imports.models import (
    DuplicateCandidate,
    DuplicateCandidateDecision,
    ImportJob,
    ImportJobStatus,
    ImportRecord,
    ImportRecordAction,
    ImportRecordStatus,
)
from apps.transactions.services.create import create_transaction

if TYPE_CHECKING:
    from apps.identity.models import User
    from apps.workspaces.models import Workspace


class ImportCommitError(ValueError):
    """Base error for import commit operations."""


class UnresolvedDuplicatesError(ImportCommitError):
    """Job cannot be committed while duplicate candidates remain in pending status."""


def resolve_duplicate_candidate(
    *,
    workspace: Workspace,
    actor: User,
    candidate_id: uuid.UUID,
    decision: str,
) -> DuplicateCandidate:
    """Mark a duplicate candidate decision as 'import' or 'skip'."""
    if decision not in (DuplicateCandidateDecision.IMPORT, DuplicateCandidateDecision.SKIP):
        raise ValueError(f"Invalid decision '{decision}': must be 'import' or 'skip'.")

    with transaction.atomic():
        cand = (
            DuplicateCandidate.objects.select_for_update()
            .select_related("import_record")
            .get(id=candidate_id, workspace=workspace)
        )
        cand.decision = decision
        cand.decided_by = actor
        cand.decided_at = timezone.now()
        cand.save(update_fields=["decision", "decided_by", "decided_at", "updated_at"])

        # Also update the record action
        rec = cand.import_record
        if decision == DuplicateCandidateDecision.SKIP:
            rec.action = ImportRecordAction.SKIP
            rec.status = ImportRecordStatus.SKIPPED
        else:
            rec.action = ImportRecordAction.IMPORT
            rec.status = ImportRecordStatus.VALID
        rec.save(update_fields=["action", "status", "updated_at"])

        return cand


def commit_import_job(
    *,
    workspace: Workspace,
    actor: User,
    import_job_id: uuid.UUID,
) -> ImportJob:
    """Commit all valid and resolved records of an import job into transactions atomically."""
    with transaction.atomic():
        job = (
            ImportJob.objects.select_for_update()
            .select_related("account")
            .get(id=import_job_id, workspace=workspace)
        )

        if job.status == ImportJobStatus.COMPLETED:
            return job

        # Guard: check for unresolved duplicates
        pending_candidates = DuplicateCandidate.objects.filter(
            import_record__import_job=job,
            decision=DuplicateCandidateDecision.PENDING,
        ).count()

        if pending_candidates > 0:
            raise UnresolvedDuplicatesError(
                f"Cannot commit import job: {pending_candidates} duplicate candidate(s) "
                "require explicit review ('import' or 'skip')."
            )

        job.status = ImportJobStatus.COMMITTING
        job.save(update_fields=["status", "updated_at"])

        records = ImportRecord.objects.filter(
            import_job=job,
        ).order_by("row_number")

        imported_count = 0

        # Ensure fallback uncategorized category if row has no category
        default_cat = Category.objects.filter(
            workspace=workspace,
            kind=CategoryKind.EXPENSE,
            is_archived=False,
        ).first()

        for rec in records:
            if rec.status in (ImportRecordStatus.INVALID, ImportRecordStatus.SKIPPED):
                continue
            if rec.action == ImportRecordAction.SKIP:
                rec.status = ImportRecordStatus.SKIPPED
                rec.save(update_fields=["status", "updated_at"])
                continue

            norm = rec.normalized
            if not norm:
                continue

            cat_id = norm.get("category_id")
            if not cat_id and default_cat:
                cat_id = default_cat.id

            txn = create_transaction(
                workspace=workspace,
                actor=actor,
                kind=norm.get("kind", "expense"),
                account_id=job.account_id,
                amount=norm["amount"],
                currency=norm["currency"],
                occurred_on=date.fromisoformat(norm["date"]),
                title=norm.get("title") or "Imported Transaction",
                category_id=cat_id,
                notes=norm.get("notes") or f"Imported via {job.file_name}",
            )

            rec.transaction = txn
            rec.status = ImportRecordStatus.IMPORTED
            rec.save(update_fields=["transaction", "status", "updated_at"])
            imported_count += 1

        job.imported_count = imported_count
        job.status = ImportJobStatus.COMPLETED
        job.finished_at = timezone.now()
        job.save(update_fields=["imported_count", "status", "finished_at", "updated_at"])

        return job
