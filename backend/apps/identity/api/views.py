"""Authentication and session endpoints."""

from __future__ import annotations

import uuid

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.common.throttles import PasswordResetEmailThrottle
from apps.identity.api.cookies import REFRESH_COOKIE, clear_refresh_cookie, set_refresh_cookie
from apps.identity.api.serializers import (
    DetailResponseSerializer,
    GoogleLoginSerializer,
    GoogleTokenResponseSerializer,
    LoginSerializer,
    MFARequiredSerializer,
    MFAVerifySerializer,
    PasswordForgotSerializer,
    PasswordResetResponseSerializer,
    PasswordResetSerializer,
    ReauthResponseSerializer,
    ReauthSerializer,
    RecoveryCodesResponseSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    SentResponseSerializer,
    SessionSerializer,
    TokenResponseSerializer,
    TwoFactorCodeSerializer,
    TwoFactorConfirmResponseSerializer,
    TwoFactorFactorSerializer,
    TwoFactorSetupResponseSerializer,
    UserSummarySerializer,
    VerifyEmailResponseSerializer,
    VerifyEmailSerializer,
)
from apps.identity.models import UserSession
from apps.identity.services import two_factor
from apps.identity.services.email_tokens import send_verification, verify_email
from apps.identity.services.google import login_with_google
from apps.identity.services.passwords import request_password_reset, reset_password
from apps.identity.services.registration import register_user
from apps.identity.services.sessions import (
    InvalidToken,
    ReauthRequired,
    RequestMeta,
    SessionNotFound,
    TokenPair,
    authenticate_user,
    has_recent_reauth,
    issue_tokens,
    mark_reauth,
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


def _require_recent_reauth(request: Request) -> None:
    if not has_recent_reauth(user=request.user, session_id=_current_session_id(request)):
        raise ReauthRequired("Confirm your password again before changing security settings.")


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

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
        meta = RequestMeta.from_request(request)
        send_verification(user, requested_ip_hash=meta.ip_hash)
        tokens = issue_tokens(user, request_meta=meta)
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
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: TokenResponseSerializer,
            202: MFARequiredSerializer,
            401: dict,
        },
        tags=["auth"],
        description=(
            "Exchange email and password for an access token and refresh cookie. When 2FA is "
            "enabled, returns 202 with a short-lived challenge instead of tokens."
        ),
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate_user(**serializer.validated_data)

        if two_factor.is_enabled(user):
            challenge = two_factor.create_challenge(user)
            payload = {
                "mfa_required": True,
                "mfa_token": challenge.token,
                "methods": ["totp", "recovery_code"],
                "expires_in": challenge.expires_in,
            }
            return Response(
                MFARequiredSerializer(payload).data,
                status=status.HTTP_202_ACCEPTED,
            )

        tokens = issue_tokens(user, request_meta=RequestMeta.from_request(request))
        ws = None
        if user:
            try:
                ws = user.workspace
            except Exception:
                ws = None
        payload = {
            **_token_payload(tokens),
            "user": user,
            "workspace": ws,
        }
        response = Response(
            TokenResponseSerializer(payload).data, status=status.HTTP_200_OK
        )
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
        tokens = rotate_refresh(raw_refresh, request_meta=RequestMeta.from_request(request))
        user = tokens.user
        ws = None
        if user:
            try:
                ws = user.workspace
            except Exception:
                ws = None
        payload = {
            **_token_payload(tokens),
            "user": user,
            "workspace": ws,
        }
        response = Response(
            TokenResponseSerializer(payload).data, status=status.HTTP_200_OK
        )
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


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_verification"

    @extend_schema(
        request=VerifyEmailSerializer,
        responses={200: VerifyEmailResponseSerializer, 400: dict, 409: dict},
        tags=["auth"],
        description="Mark the account verified using a single-use token.",
    )
    def post(self, request: Request) -> Response:
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verify_email(serializer.validated_data["token"])
        return Response({"verified": True}, status=status.HTTP_200_OK)


class ResendVerificationView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_verification"

    @extend_schema(
        request=None,
        responses={202: SentResponseSerializer, 400: dict},
        tags=["auth"],
        description="Send a fresh verification link to the signed-in user.",
    )
    def post(self, request: Request) -> Response:
        meta = RequestMeta.from_request(request)
        send_verification(request.user, requested_ip_hash=meta.ip_hash)
        return Response({"sent": True}, status=status.HTTP_202_ACCEPTED)


class PasswordForgotView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle, PasswordResetEmailThrottle]
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordForgotSerializer,
        responses={202: DetailResponseSerializer},
        tags=["auth"],
        description="Always 202: the response never reveals whether the account exists.",
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordForgotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        meta = RequestMeta.from_request(request)
        request_password_reset(serializer.validated_data["email"], requested_ip_hash=meta.ip_hash)
        return Response(
            {"detail": "If an account exists, a reset link has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordResetSerializer,
        responses={200: PasswordResetResponseSerializer, 400: dict, 409: dict},
        tags=["auth"],
        description="Set a new password with a single-use token and revoke every session.",
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_password(
            serializer.validated_data["token"],
            serializer.validated_data["new_password"],
        )
        return Response({"reset": True}, status=status.HTTP_200_OK)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        request=GoogleLoginSerializer,
        responses={
            200: GoogleTokenResponseSerializer,
            202: MFARequiredSerializer,
            400: dict,
            409: dict,
        },
        tags=["auth"],
        description="Exchange a Google ID token for tokens. Existing accounts must be linked.",
    )
    def post(self, request: Request) -> Response:
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = login_with_google(serializer.validated_data["id_token"])

        if two_factor.is_enabled(user):
            challenge = two_factor.create_challenge(user)
            payload = {
                "mfa_required": True,
                "mfa_token": challenge.token,
                "methods": ["totp", "recovery_code"],
                "expires_in": challenge.expires_in,
            }
            return Response(
                MFARequiredSerializer(payload).data,
                status=status.HTTP_202_ACCEPTED,
            )

        tokens = issue_tokens(user, request_meta=RequestMeta.from_request(request))
        payload = {
            "user": UserSummarySerializer(user).data,
            **_token_payload(tokens),
        }
        response = Response(payload, status=status.HTTP_200_OK)
        set_refresh_cookie(response, tokens.refresh, tokens.refresh_expires_in)
        return response


class ReauthView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ReauthSerializer,
        responses={200: ReauthResponseSerializer, 401: dict, 403: dict},
        tags=["auth"],
        description="Re-enter the password to unlock sensitive security actions for 10 minutes.",
    )
    def post(self, request: Request) -> Response:
        from apps.identity.services.two_factor import InvalidPassword

        serializer = ReauthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.has_usable_password() or not request.user.check_password(
            serializer.validated_data["password"]
        ):
            raise InvalidPassword("Password is incorrect.")

        session_id = _current_session_id(request)
        if session_id is None:
            raise InvalidToken("Session is no longer valid.")
        mark_reauth(user=request.user, session_id=session_id)
        return Response(
            {"reauth_expires_in": int(_reauth_seconds())},
            status=status.HTTP_200_OK,
        )


def _reauth_seconds() -> int:
    from django.conf import settings

    return int(settings.REAUTH_WINDOW.total_seconds())


class TwoFactorSetupView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: TwoFactorSetupResponseSerializer, 403: dict, 409: dict},
        tags=["auth"],
        description="Start TOTP enrollment. Requires a recent password confirmation.",
    )
    def post(self, request: Request) -> Response:
        _require_recent_reauth(request)
        enrollment = two_factor.begin_enrollment(request.user)
        payload = {
            "secret": enrollment.secret,
            "otpauth_uri": enrollment.otpauth_uri,
            "qr_svg": enrollment.qr_svg,
        }
        return Response(
            TwoFactorSetupResponseSerializer(payload).data,
            status=status.HTTP_200_OK,
        )


class TwoFactorConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TwoFactorCodeSerializer,
        responses={
            200: TwoFactorConfirmResponseSerializer,
            401: dict,
            403: dict,
            409: dict,
        },
        tags=["auth"],
        description="Enable 2FA with a code from the authenticator app and return recovery codes.",
    )
    def post(self, request: Request) -> Response:
        _require_recent_reauth(request)
        serializer = TwoFactorCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codes = two_factor.confirm_enrollment(request.user, serializer.validated_data["code"])
        payload = {"enabled": True, "recovery_codes": codes}
        return Response(
            TwoFactorConfirmResponseSerializer(payload).data,
            status=status.HTTP_200_OK,
        )


class TwoFactorVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "two_factor"

    @extend_schema(
        request=MFAVerifySerializer,
        responses={200: TokenResponseSerializer, 401: dict, 429: dict},
        tags=["auth"],
        description="Complete a 2FA login challenge with a TOTP or recovery code.",
    )
    def post(self, request: Request) -> Response:
        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = two_factor.verify_challenge(
            serializer.validated_data["mfa_token"],
            serializer.validated_data["code"],
            request_meta=RequestMeta.from_request(request),
        )
        response = Response(_token_payload(tokens), status=status.HTTP_200_OK)
        set_refresh_cookie(response, tokens.refresh, tokens.refresh_expires_in)
        return response


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TwoFactorFactorSerializer,
        responses={204: None, 401: dict, 409: dict, 429: dict},
        tags=["auth"],
        description="Disable 2FA. Requires the password and a current code.",
    )
    def post(self, request: Request) -> Response:
        serializer = TwoFactorFactorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        two_factor.disable(
            request.user,
            password=serializer.validated_data["password"],
            code=serializer.validated_data["code"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecoveryCodesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TwoFactorFactorSerializer,
        responses={
            200: RecoveryCodesResponseSerializer,
            401: dict,
            409: dict,
            429: dict,
        },
        tags=["auth"],
        description="Replace recovery codes. Requires the password and a current code.",
    )
    def post(self, request: Request) -> Response:
        serializer = TwoFactorFactorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codes = two_factor.regenerate_recovery_codes(
            request.user,
            password=serializer.validated_data["password"],
            code=serializer.validated_data["code"],
        )
        payload = {"recovery_codes": codes}
        return Response(
            RecoveryCodesResponseSerializer(payload).data,
            status=status.HTTP_200_OK,
        )
