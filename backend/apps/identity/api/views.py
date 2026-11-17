"""Authentication endpoints. Token issuing arrives in Task 5."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.api.serializers import RegisterResponseSerializer, RegisterSerializer
from apps.identity.services.registration import register_user


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @extend_schema(
        request=RegisterSerializer,
        responses={201: RegisterResponseSerializer},
        tags=["auth"],
        description="Create a user, profile, and workspace atomically.",
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = register_user(**serializer.validated_data)
        payload = {"user": user, "workspace": user.workspace}
        return Response(
            RegisterResponseSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )
