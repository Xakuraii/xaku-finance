"""API views for data export, privacy data map, and account deletion requests."""

from __future__ import annotations

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.api.views import _current_session_id, _require_recent_reauth
from apps.privacy.api.serializers import (
    AccountDeletionCreateSerializer,
    AccountDeletionResponseSerializer,
    DataExportCreateSerializer,
    DataExportJobSerializer,
    DataMapItemSerializer,
)
from apps.privacy.models import DataExportJob
from apps.privacy.services.data_map import get_privacy_data_map
from apps.privacy.services.deletion import (
    DELETION_CONSEQUENCES,
    cancel_account_deletion,
    get_current_deletion_request,
    request_account_deletion,
)
from apps.privacy.services.export import (
    cancel_export_job,
    create_export_job,
    get_export_download_data,
)


class ExportListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataExportJobSerializer

    @extend_schema(
        responses={200: DataExportJobSerializer(many=True)},
        summary="List user data export jobs",
    )
    def get(self, request: Request) -> Response:
        jobs = DataExportJob.objects.filter(user=request.user).order_by("-created_at")
        serializer = DataExportJobSerializer(jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=DataExportCreateSerializer,
        responses={201: DataExportJobSerializer},
        summary="Request a new data export job (requires recent re-authentication)",
    )
    def post(self, request: Request) -> Response:
        _require_recent_reauth(request)
        serializer = DataExportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = create_export_job(
            user=request.user,
            workspace=request.user.workspace,
            scope=serializer.validated_data.get("scope", "all"),
            export_format=serializer.validated_data.get("format", "json"),
        )
        return Response(DataExportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class ExportDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataExportJobSerializer

    @extend_schema(
        responses={200: DataExportJobSerializer},
        summary="Get export job status",
    )
    def get(self, request: Request, pk: str) -> Response:
        job = DataExportJob.objects.filter(id=pk, user=request.user).first()
        if not job:
            raise NotFound("Export job not found.")
        return Response(DataExportJobSerializer(job).data, status=status.HTTP_200_OK)


class ExportDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataExportJobSerializer

    @extend_schema(
        responses={(200, "application/octet-stream"): bytes},
        summary="Download exported archive file",
    )
    def get(self, request: Request, pk: str) -> HttpResponse:
        content, filename, content_type = get_export_download_data(pk, user=request.user)
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = str(len(content))
        return response


class ExportCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataExportJobSerializer

    @extend_schema(
        responses={200: DataExportJobSerializer},
        summary="Cancel an active export job",
    )
    def post(self, request: Request, pk: str) -> Response:
        job = cancel_export_job(pk, user=request.user)
        return Response(DataExportJobSerializer(job).data, status=status.HTTP_200_OK)


class DataMapView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataMapItemSerializer

    @extend_schema(
        responses={200: DataMapItemSerializer(many=True)},
        summary="Get transparency data map of stored user data and retention policies",
    )
    def get(self, request: Request) -> Response:
        data = get_privacy_data_map()
        return Response(DataMapItemSerializer(data, many=True).data, status=status.HTTP_200_OK)


class AccountDeletionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AccountDeletionResponseSerializer

    @extend_schema(
        request=AccountDeletionCreateSerializer,
        responses={200: AccountDeletionResponseSerializer},
        summary="Request account deletion with a 7-day grace period",
    )
    def post(self, request: Request) -> Response:
        serializer = AccountDeletionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req = request_account_deletion(
            user=request.user,
            password=serializer.validated_data["password"],
            confirm_text=serializer.validated_data["confirm"],
            code=serializer.validated_data.get("code") or None,
            current_session_id=_current_session_id(request),
        )

        resp_data = {
            "status": req.status,
            "execute_after": req.execute_after,
            "backup_expiry_date": req.backup_expiry_date,
            "consequences": DELETION_CONSEQUENCES,
        }
        return Response(AccountDeletionResponseSerializer(resp_data).data, status=status.HTTP_200_OK)


class CurrentAccountDeletionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AccountDeletionResponseSerializer

    @extend_schema(
        responses={200: AccountDeletionResponseSerializer, 404: dict},
        summary="Check current pending account deletion request",
    )
    def get(self, request: Request) -> Response:
        req = get_current_deletion_request(user=request.user)
        if not req:
            raise NotFound("No active deletion request.")

        resp_data = {
            "status": req.status,
            "execute_after": req.execute_after,
            "backup_expiry_date": req.backup_expiry_date,
            "consequences": DELETION_CONSEQUENCES,
        }
        return Response(AccountDeletionResponseSerializer(resp_data).data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={204: None, 404: dict},
        summary="Cancel pending account deletion request during grace period",
    )
    def delete(self, request: Request) -> Response:
        cancel_account_deletion(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
