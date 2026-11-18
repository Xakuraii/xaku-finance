"""Duplicate detection scoring engine for staged import records."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.imports.models import (
    DuplicateCandidate,
    DuplicateCandidateDecision,
    ImportJob,
    ImportJobStatus,
    ImportRecord,
    ImportRecordStatus,
)
from apps.transactions.models import Transaction


def score_candidate(
    record_date: date,
    record_amount_minor: int,
    record_title: str,
    tx: Transaction,
) -> tuple[Decimal, dict[str, Any]]:
    """Score potential duplicate match (0.000 to 1.000) and return match reasons."""
    reasons: dict[str, Any] = {}
    score = Decimal("0.000")

    # 1. Exact amount match (minor units): +0.500
    if tx.amount_minor == record_amount_minor:
        score += Decimal("0.500")
        reasons["exact_amount"] = True

    # 2. Date proximity (+/- 2 days window)
    date_diff = abs((tx.occurred_on - record_date).days)
    if date_diff == 0:
        score += Decimal("0.400")
        reasons["same_date"] = True
    elif date_diff == 1:
        score += Decimal("0.250")
        reasons["date_diff_days"] = 1
    elif date_diff <= 2:
        score += Decimal("0.100")
        reasons["date_diff_days"] = 2

    # 3. Title / Merchant text overlap
    t1 = record_title.strip().lower()
    t2 = tx.title.strip().lower()
    m2 = (tx.merchant or "").strip().lower()

    if t1 == t2 or (m2 and t1 == m2):
        score += Decimal("0.100")
        reasons["exact_title_or_merchant"] = True
    elif t1 in t2 or t2 in t1 or (m2 and t1 in m2):
        score += Decimal("0.050")
        reasons["partial_text_match"] = True

    score = min(score, Decimal("1.000"))
    return score, reasons


def detect_duplicates(job: ImportJob) -> int:
    """Scan all valid records in the job against existing transactions and score duplicates."""
    with transaction.atomic():
        valid_records = ImportRecord.objects.filter(
            import_job=job,
            status=ImportRecordStatus.VALID,
        ).order_by("row_number")

        duplicate_count = 0

        for record in valid_records:
            norm = record.normalized
            if not norm or not norm.get("date") or not norm.get("amount_minor"):
                continue

            rec_date = date.fromisoformat(norm["date"])
            rec_amount_minor = norm["amount_minor"]
            rec_title = norm.get("title", "")
            rec_kind = norm.get("kind", "expense")

            start_window = rec_date - timedelta(days=2)
            end_window = rec_date + timedelta(days=2)

            existing_candidates = Transaction.objects.filter(
                workspace_id=job.workspace_id,
                account_id=job.account_id,
                transaction_type=rec_kind,
                is_archived=False,
                amount_minor=rec_amount_minor,
                occurred_on__gte=start_window,
                occurred_on__lte=end_window,
            )

            record_has_dup = False
            for tx in existing_candidates:
                score, reasons = score_candidate(
                    record_date=rec_date,
                    record_amount_minor=rec_amount_minor,
                    record_title=rec_title,
                    tx=tx,
                )

                if score >= Decimal("0.600"):
                    DuplicateCandidate.objects.create(
                        workspace_id=job.workspace_id,
                        import_record=record,
                        existing_transaction=tx,
                        score=score,
                        reasons=reasons,
                        decision=DuplicateCandidateDecision.PENDING,
                    )
                    record_has_dup = True

            if record_has_dup:
                duplicate_count += 1
                record.status = (
                    ImportRecordStatus.DUPLICATE_EXACT
                    if score >= Decimal("0.900")
                    else ImportRecordStatus.DUPLICATE_POTENTIAL
                )
                record.save(update_fields=["status", "updated_at"])

        job.duplicate_count = duplicate_count
        if duplicate_count > 0:
            job.status = ImportJobStatus.AWAITING_REVIEW
        else:
            job.status = ImportJobStatus.VALIDATED
        job.save(update_fields=["duplicate_count", "status", "updated_at"])

        return duplicate_count
