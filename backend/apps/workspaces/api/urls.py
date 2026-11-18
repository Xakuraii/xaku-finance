"""URL routing for workspace and dashboard endpoints."""

from django.urls import path

from apps.workspaces.api.dashboard_views import (
    DashboardLayoutResetView,
    DashboardLayoutView,
    DashboardView,
)

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard-data"),
    path("dashboard/layout/", DashboardLayoutView.as_view(), name="dashboard-layout"),
    path(
        "dashboard/layout/reset/",
        DashboardLayoutResetView.as_view(),
        name="dashboard-layout-reset",
    ),
]
