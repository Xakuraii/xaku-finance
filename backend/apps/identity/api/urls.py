from django.urls import path

from apps.identity.api.views import (
    LoginView,
    LogoutAllView,
    LogoutView,
    RefreshView,
    RegisterView,
    SessionDetailView,
    SessionListView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout-all/", LogoutAllView.as_view(), name="logout-all"),
    path("sessions/", SessionListView.as_view(), name="session-list"),
    path("sessions/<uuid:session_id>/", SessionDetailView.as_view(), name="session-detail"),
]
