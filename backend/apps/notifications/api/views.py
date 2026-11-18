"""API views for Notifications and Notification Preferences."""

from __future__ import annotations

from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.api.serializers import (
    BulkNotificationPreferenceSerializer,
    EvaluateResponseSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
    ReadActionResponseSerializer,
    ReadAllResponseSerializer,
    UnreadCountResponseSerializer,
)
from apps.notifications.models import Notification
from apps.notifications.services.evaluators import (
    evaluate_bill_notifications,
    evaluate_budget_notifications,
    evaluate_savings_notifications,
)
from apps.notifications.services.notifications import (
    SecurityNotificationLocked,
    ensure_user_preferences,
    get_unread_count,
    mark_all_notifications_read,
    mark_notification_read,
    update_user_preferences,
)


class NotificationListView(APIView):
    """Retrieve notifications for the authenticated user, optionally filtered."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: NotificationSerializer(many=True)},
        summary="List user notifications",
    )
    def get(self, request: Request) -> Response:
        qs = Notification.objects.filter(user=request.user)

        unread_param = request.query_params.get("unread")
        if unread_param is not None and unread_param.lower() in ("true", "1"):
            qs = qs.filter(read_at__isnull=True)

        category_param = request.query_params.get("category")
        if category_param:
            qs = qs.filter(category=category_param)

        qs = qs.order_by("-created_at")
        limit_param = request.query_params.get("limit")
        if limit_param:
            try:
                limit = min(int(limit_param), 200)
                qs = qs[:limit]
            except ValueError:
                pass

        serializer = NotificationSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationReadView(APIView):
    """Mark an individual notification as read."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReadActionResponseSerializer

    @extend_schema(
        responses={200: ReadActionResponseSerializer},
        summary="Mark notification as read",
    )
    def post(self, request: Request, pk: UUID) -> Response:
        if not Notification.objects.filter(id=pk, user=request.user).exists():
            raise NotFound(detail="Notification not found.")

        mark_notification_read(request.user, pk)
        return Response({"success": True}, status=status.HTTP_200_OK)


class NotificationReadAllView(APIView):
    """Mark all unread notifications for the user as read."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReadAllResponseSerializer

    @extend_schema(
        responses={200: ReadAllResponseSerializer},
        summary="Mark all notifications as read",
    )
    def post(self, request: Request) -> Response:
        updated_count = mark_all_notifications_read(request.user)
        return Response({"updated_count": updated_count}, status=status.HTTP_200_OK)


class NotificationUnreadCountView(APIView):
    """Get the current count of unread notifications for the authenticated user."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UnreadCountResponseSerializer

    @extend_schema(
        responses={200: UnreadCountResponseSerializer},
        summary="Get unread notification count",
    )
    def get(self, request: Request) -> Response:
        count = get_unread_count(request.user)
        return Response({"unread_count": count}, status=status.HTTP_200_OK)


class NotificationPreferenceView(APIView):
    """Retrieve and update notification preferences for the user."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: NotificationPreferenceSerializer(many=True)},
        summary="Get user notification preferences",
    )
    def get(self, request: Request) -> Response:
        prefs = ensure_user_preferences(request.user)
        serializer = NotificationPreferenceSerializer(prefs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=BulkNotificationPreferenceSerializer,
        responses={
            200: NotificationPreferenceSerializer(many=True),
            409: {"description": "Security notification preference locked"},
        },
        summary="Update user notification preferences",
    )
    def put(self, request: Request) -> Response:
        if isinstance(request.data, list):
            pref_data = request.data
        elif isinstance(request.data, dict) and "preferences" in request.data:
            pref_data = request.data["preferences"]
        elif isinstance(request.data, dict):
            pref_data = [request.data]
        else:
            return Response(
                {"detail": "Invalid request payload. Expected array or preferences object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated = update_user_preferences(request.user, pref_data)
        except SecurityNotificationLocked as err:
            return Response(
                {"detail": str(err), "code": "security_notification_locked"},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = NotificationPreferenceSerializer(updated, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EvaluateNotificationsTriggerView(APIView):
    """Trigger background evaluation of budget, bill, and savings notifications."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EvaluateResponseSerializer

    @extend_schema(
        responses={200: EvaluateResponseSerializer},
        summary="Trigger notification evaluators",
    )
    def post(self, request: Request) -> Response:
        workspace = getattr(request.user, "workspace", None)
        if not workspace:
            return Response(
                {"detail": "No workspace associated with authenticated user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        b_notifs = evaluate_budget_notifications(workspace)
        bill_notifs = evaluate_bill_notifications(workspace)
        s_notifs = evaluate_savings_notifications(workspace)
        total_created = len(b_notifs) + len(bill_notifs) + len(s_notifs)

        return Response(
            {"evaluated": True, "created_count": total_created},
            status=status.HTTP_200_OK,
        )
