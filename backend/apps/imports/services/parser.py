"""CSV import parser: file hashing, configurable column mapping, and record staging."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db import transaction

from apps.categories.models import Category
from apps.common.models import Currency
from apps.common.money import Money
from apps.imports.models import ImportJob, ImportJobStatus, ImportRecord, ImportRecordStatus

if TYPE_CHECKING:
    from apps.accounts.models import Account
    from apps.identity.models import User
    from apps.workspaces.models import Workspace


# Common date formats
DATE_PATTERNS = [
    r"^\d{4}-\d{2}-\d{2}$",  # 2026-11-15
    r"^\d{2}/\d{2}/\d{4}$",  # 11/15/2026 or 15/11/2026
    r"^\d{2}-\d{2}-\d{4}$",  # 15-11-2026
]


def parse_date_str(value: str) -> date | None:
    """Parse common date formats safely."""
    val = value.strip()
    # Try ISO YYYY-MM-DD
    try:
        return date.fromisoformat(val)
    except ValueError:
        pass

    # Try MM/DD/YYYY or DD/MM/YYYY
    parts = re.split(r"[/.-]", val)
    if len(parts) == 3:
        try:
            p1, p2, p3 = int(parts[0]), int(parts[1]), int(parts[2])
            if p3 > 1000:  # Year is last
                # Try MM/DD/YYYY first
                if 1 <= p1 <= 12 and 1 <= p2 <= 31:
                    return date(p3, p1, p2)
                # Try DD/MM/YYYY
                if 1 <= p2 <= 12 and 1 <= p1 <= 31:
                    return date(p3, p2, p1)
            elif p1 > 1000:  # Year is first
                return date(p1, p2, p3)
        except ValueError:
            pass

    return None


def calculate_fingerprint(
    *,
    occurred_on: str,
    amount_minor: int,
    currency: str,
    account_id: uuid.UUID,
    title: str,
) -> str:
    """Deterministic hash of normalized transaction properties."""
    raw = f"{account_id}|{currency}|{occurred_on}|{amount_minor}|{title.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def stage_csv_import(
    *,
    workspace: Workspace,
    account: Account,
    actor: User,
    file_name: str,
    file_bytes: bytes,
    mapping: dict[str, str] | None = None,
) -> ImportJob:
    """Parse CSV rows according to column mapping and stage them into ImportRecord rows."""
    source_hash = hashlib.sha256(file_bytes).hexdigest()
    text_content = file_bytes.decode("utf-8-sig", errors="replace")

    col_map = mapping or {
        "date": "date",
        "amount": "amount",
        "title": "title",
        "category": "category",
        "notes": "notes",
    }

    currency_obj = Currency.objects.get(code=account.currency_id)
    minor_unit = currency_obj.minor_unit

    with transaction.atomic():
        job = ImportJob.objects.create(
            workspace=workspace,
            account=account,
            created_by=actor,
            file_name=file_name,
            file_format="csv",
            source_hash=source_hash,
            status=ImportJobStatus.VALIDATING,
            mapping=col_map,
        )

        reader = csv.DictReader(io.StringIO(text_content))
        if not reader.fieldnames:
            job.status = ImportJobStatus.FAILED
            job.error_summary = {"detail": "CSV file contains no headers or is empty."}
            job.save(update_fields=["status", "error_summary", "updated_at"])
            return job

        # Case-insensitive column resolution
        header_lookup = {h.strip().lower(): h for h in reader.fieldnames if h}

        def get_col(field_key: str, row_dict: dict[str, Any]) -> str:
            mapped_name = col_map.get(field_key, field_key).strip().lower()
            actual_header = header_lookup.get(mapped_name)
            if actual_header and actual_header in row_dict:
                return (row_dict[actual_header] or "").strip()
            return ""

        row_number = 1
        valid_count = 0
        invalid_count = 0

        # Preload workspace categories for matching
        ws_categories = {
            c.name.strip().lower(): c
            for c in Category.objects.filter(workspace=workspace, is_archived=False)
        }

        records_to_create = []

        for row in reader:
            raw_date = get_col("date", row)
            raw_amount = get_col("amount", row)
            raw_title = get_col("title", row) or get_col("description", row)
            raw_category = get_col("category", row)
            raw_notes = get_col("notes", row)

            errors = []
            parsed_date = parse_date_str(raw_date)
            if not parsed_date:
                errors.append(f"Invalid date format: '{raw_date}'")

            parsed_amount_minor = 0
            kind = "expense"
            if not raw_amount:
                errors.append("Amount cannot be empty.")
            else:
                clean_amt = raw_amount.replace("$", "").replace(",", "").strip()
                try:
                    dec = Decimal(clean_amt)
                    if dec < 0:
                        kind = "expense"
                        dec = abs(dec)
                    else:
                        kind = "income"
                    parsed_amount_minor = Money.parse(
                        f"{dec:.{minor_unit}f}", currency_obj.code, minor_unit
                    ).amount_minor
                    if parsed_amount_minor <= 0:
                        errors.append("Amount must be non-zero.")
                except Exception:
                    errors.append(f"Invalid decimal amount: '{raw_amount}'")

            if not raw_title:
                raw_title = "Imported Transaction"

            cat_id = None
            if raw_category:
                matched_cat = ws_categories.get(raw_category.lower())
                if matched_cat:
                    cat_id = str(matched_cat.id)

            rec_status = ImportRecordStatus.VALID if not errors else ImportRecordStatus.INVALID
            if rec_status == ImportRecordStatus.VALID:
                valid_count += 1
            else:
                invalid_count += 1

            normalized = {
                "date": parsed_date.isoformat() if parsed_date else None,
                "amount": f"{(parsed_amount_minor / (10**minor_unit)):.{minor_unit}f}",
                "amount_minor": parsed_amount_minor,
                "currency": account.currency_id,
                "kind": kind,
                "title": raw_title,
                "category_id": cat_id,
                "notes": raw_notes,
            }

            fingerprint = None
            if parsed_date and parsed_amount_minor > 0:
                fingerprint = calculate_fingerprint(
                    occurred_on=parsed_date.isoformat(),
                    amount_minor=parsed_amount_minor,
                    currency=account.currency_id,
                    account_id=account.id,
                    title=raw_title,
                )

            records_to_create.append(
                ImportRecord(
                    workspace=workspace,
                    import_job=job,
                    row_number=row_number,
                    raw=dict(row),
                    normalized=normalized,
                    fingerprint=fingerprint,
                    status=rec_status,
                    errors=errors,
                )
            )
            row_number += 1

        ImportRecord.objects.bulk_create(records_to_create)

        job.row_count = len(records_to_create)
        job.valid_count = valid_count
        job.invalid_count = invalid_count
        job.status = ImportJobStatus.VALIDATED
        job.save(
            update_fields=[
                "row_count",
                "valid_count",
                "invalid_count",
                "status",
                "updated_at",
            ]
        )

        return job
