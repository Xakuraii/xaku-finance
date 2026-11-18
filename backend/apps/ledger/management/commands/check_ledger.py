"""Management command to verify double-entry ledger reconciliation."""

from __future__ import annotations

import sys
from typing import Any

from django.core.management.base import BaseCommand

from apps.ledger.services.reconciliation import reconcile_workspace
from apps.workspaces.models import Workspace


class Command(BaseCommand):
    help = "Verify double-entry ledger integrity across all workspaces."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--workspace",
            type=str,
            help="Specific workspace UUID to check.",
        )
        parser.add_argument(
            "--fail-on-drift",
            action="store_true",
            help="Exit with non-zero code if any reconciliation error is detected.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        workspace_id = options.get("workspace")
        fail_on_drift = options.get("fail_on_drift", False)

        if workspace_id:
            workspaces = Workspace.objects.filter(id=workspace_id)
        else:
            workspaces = Workspace.objects.all()

        total_workspaces = 0
        total_errors = 0

        for ws in workspaces:
            total_workspaces += 1
            report = reconcile_workspace(ws)
            if not report.is_valid:
                total_errors += len(report.errors)
                err_count = len(report.errors)
                self.stderr.write(
                    self.style.ERROR(f"Workspace {ws.id} ({ws.name}) has {err_count} errors:")
                )
                for err in report.errors:
                    self.stderr.write(f"  - {err}")
            else:
                self.stdout.write(self.style.SUCCESS(f"Workspace {ws.id} ({ws.name}): OK"))

        if total_errors > 0:
            msg = f"Reconciliation failed: {total_errors} errors across {total_workspaces}."
            self.stderr.write(self.style.ERROR(msg))
            if fail_on_drift:
                sys.exit(1)
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Reconciliation clean: {total_workspaces} workspaces checked.")
            )
