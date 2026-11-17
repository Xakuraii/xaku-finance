"""Authentication and session endpoints."""

from __future__ import annotations

import uuid

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.api.cookies import REFRESH_COOKIE, clear_refresh_cookie, set_refresh_cookie
from apps.identity.api.serializers import (
    LoginSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    SessionSerializer,
    TokenResponseSerializer,
)
from apps.identity.models import UserSession
from apps.identity.services.registration import register_user
from apps.identity.services.sessions import (
    InvalidToken,
    RequestMeta,
    SessionNotFound,
    TokenPair,
    authenticate_user,
    issue_tokens,
    revoke_all_sessions,
    revoke_session,
    rotate_refresh,
)


def _token_payload(tokens: TokenPair) -> dict[str, object]:
    return {
        "access": tokens.access,
        "access_expires_in": tokens.access_expires_in,
        "refresh_expires_in": tokens.refresh_expires_in,
    }


def _current_session_id(request: Request) -> uuid.UUID | None:
    auth = request.auth
    if auth is None or not hasattr(auth, "get"):
        return None
    raw = auth.get("sid")
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @extend_schema(
        request=RegisterSerializer,
        responses={201: RegisterResponseSerializer},
        tags=["auth"],
        description="Create a user, profile, and workspace atomically, then open a session.",
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = register_user(**serializer.validated_data)
        tokens = issue_tokens(user, request_meta=RequestMeta.from_request(request))
        payload = {
            "user": user,
            "workspace": user.workspace,
            **_token_payload(tokens),
        }
        response = Response(
            RegisterResponseSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )
        set_refresh_cookie(response, tokens.refresh, tokens.refresh_expires_in)
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @extend_schema(
        request=LoginSerializer,
        responses={200: TokenResponseSerializer, 401: dict},
        tags=["auth"],
        description="Exchange email and password for an access token and refresh cookie.",
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate_user(**serializer.validated_data)
        tokens = issue_tokens(user, request_meta=RequestMeta.from_request(request))
        response = Response(_token_payload(tokens), status=status.HTTP_200_OK)
        set_refresh_cookie(response, tokens.refresh, tokens.refresh_expires_in)
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @extend_schema(
        request=None,
        responses={200: TokenResponseSerializer, 401: dict},
        tags=["auth"],
        description="Rotate the refresh cookie. Replaying an old token revokes the session family.",
    )
    def post(self, request: Request) -> Response:
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE)
        if not raw_refresh:
            raise InvalidToken("Session is no longer valid.")
        tokens = rotate_refresh(
            raw_refresh, request_meta=RequestMeta.from_request(request)
        )
        response = Response(_token_payload(tokens), status=status.HTTP_200_OK)
        set_refresh_cookie(response, tokens.refresh, tokens.refresh_expires_in)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={204: None},
        tags=["auth"],
        description="Revoke the current session and clear the refresh cookie.",
    )
    def post(self, request: Request) -> Response:
        session_id = _current_session_id(request)
        if session_id is not None:
            try:
                revoke_session(user=request.user, session_id=session_id)
            except SessionNotFound:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response


class LogoutAllView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: dict},
        tags=["auth"],
        description="Revoke every session for the current user.",
    )
    def post(self, request: Request) -> Response:
        revoked = revoke_all_sessions(user=request.user)
        response = Response({"revoked": revoked}, status=status.HTTP_200_OK)
        clear_refresh_cookie(response)
        return response


class SessionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: SessionSerializer(many=True)}, tags=["auth"])
    def get(self, request: Request) -> Response:
        sessions = UserSession.objects.filter(
            user=request.user,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).order_by("-last_used_at")
        serializer = SessionSerializer(
            sessions,
            many=True,
            context={"current_session_id": _current_session_id(request)},
        )
        return Response(serializer.data)


class SessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None, 404: dict}, tags=["auth"])
    def delete(self, request: Request, session_id: uuid.UUID) -> Response:
        revoke_session(user=request.user, session_id=session_id, reason="user_revoked")
        return Response(status=status.HTTP_204_NO_CONTENT)
