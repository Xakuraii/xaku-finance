"""URL routing for workspace, settings, and dashboard endpoints."""

from django.urls import path

from apps.workspaces.api.dashboard_views import (
    DashboardLayoutResetView,
    DashboardLayoutView,
    DashboardView,
)
from apps.workspaces.api.settings_views import (
    MeView,
    WorkspaceSettingsView,
    WorkspaceSummaryView,
)

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("workspace/", WorkspaceSettingsView.as_view(), name="workspace-settings"),
    path("workspace/summary/", WorkspaceSummaryView.as_view(), name="workspace-summary"),
    path("dashboard/", DashboardView.as_view(), name="dashboard-data"),
    path("dashboard/layout/", DashboardLayoutView.as_view(), name="dashboard-layout"),
    path(
        "dashboard/layout/reset/",
        DashboardLayoutResetView.as_view(),
        name="dashboard-layout-reset",
    ),
]
