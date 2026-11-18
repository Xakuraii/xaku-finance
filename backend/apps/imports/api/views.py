"""Views and ViewSet for multi-step Import jobs and duplicate review."""

from __future__ import annotations

import json
from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import Account
from apps.common.pagination import XakuCursorPagination
from apps.common.permissions import IsWorkspaceMember
from apps.imports.api.serializers import (
    DuplicateCandidateSerializer,
    DuplicateResolveSerializer,
    ImportJobSerializer,
    ImportRecordSerializer,
)
from apps.imports.models import ImportJob, ImportRecord
from apps.imports.services.commit import (
    UnresolvedDuplicatesError,
    commit_import_job,
    resolve_duplicate_candidate,
)
from apps.imports.services.duplicate import detect_duplicates
from apps.imports.services.parser import stage_csv_import


class ImportRecordPagination(XakuCursorPagination):
    ordering = "row_number"


class ImportJobViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for managing CSV import workflows, duplicate reviews, and commits."""

    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    serializer_class = ImportJobSerializer

    def get_queryset(self) -> QuerySet[ImportJob]:
        ws = getattr(self.request.user, "workspace", None)
        if not ws:
            return ImportJob.objects.none()
        return ImportJob.objects.filter(workspace=ws).order_by("-created_at")

    @extend_schema(
        request={"multipart/form-data": {"type": "object"}},
        responses={201: ImportJobSerializer},
        description="Upload a CSV bank statement to stage records and run duplicate detection.",
    )
    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def upload(self, request: Request) -> Response:
        ws = request.user.workspace
        account_id = request.data.get("account_id")
        uploaded_file = request.FILES.get("file")

        if not account_id:
            return Response(
                {"detail": "account_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not uploaded_file:
            return Response(
                {"detail": "file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            account = Account.objects.get(id=account_id, workspace=ws)
        except Account.DoesNotExist:
            return Response(
                {"detail": "Target account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        mapping = None
        raw_mapping = request.data.get("mapping")
        if raw_mapping:
            if isinstance(raw_mapping, str):
                try:
                    mapping = json.loads(raw_mapping)
                except Exception:
                    mapping = None
            elif isinstance(raw_mapping, dict):
                mapping = raw_mapping

        file_bytes = uploaded_file.read()
        job = stage_csv_import(
            workspace=ws,
            account=account,
            actor=request.user,
            file_name=uploaded_file.name,
            file_bytes=file_bytes,
            mapping=mapping,
        )

        # Automatically execute duplicate scoring scan
        detect_duplicates(job)

        return Response(ImportJobSerializer(job).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: ImportRecordSerializer(many=True)})
    @action(detail=True, methods=["get"])
    def records(self, request: Request, pk: Any = None) -> Response:
        job = self.get_object()
        records_qs = (
            ImportRecord.objects.filter(import_job=job)
            .prefetch_related("duplicate_candidates")
            .order_by("row_number")
        )

        paginator = ImportRecordPagination()
        page = paginator.paginate_queryset(records_qs, request, view=self)
        if page is not None:
            serializer = ImportRecordSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ImportRecordSerializer(records_qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=DuplicateResolveSerializer,
        responses={200: DuplicateCandidateSerializer},
        description="Resolve a duplicate candidate by choosing 'import' or 'skip'.",
    )
    @action(detail=True, methods=["post"])
    def resolve(self, request: Request, pk: Any = None) -> Response:
        self.get_object()  # ensures job belongs to workspace
        serializer = DuplicateResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        candidate = resolve_duplicate_candidate(
            workspace=request.user.workspace,
            actor=request.user,
            candidate_id=vd["candidate_id"],
            decision=vd["decision"],
        )

        return Response(
            DuplicateCandidateSerializer(candidate).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={200: ImportJobSerializer},
        description="Atomically commit staged import records into real financial transactions.",
    )
    @action(detail=True, methods=["post"])
    def commit(self, request: Request, pk: Any = None) -> Response:
        job = self.get_object()
        try:
            completed_job = commit_import_job(
                workspace=request.user.workspace,
                actor=request.user,
                import_job_id=job.id,
            )
            return Response(
                ImportJobSerializer(completed_job).data,
                status=status.HTTP_200_OK,
            )
        except UnresolvedDuplicatesError as err:
            return Response(
                {"detail": str(err), "code": "unresolved_duplicates"},
                status=status.HTTP_409_CONFLICT,
            )
