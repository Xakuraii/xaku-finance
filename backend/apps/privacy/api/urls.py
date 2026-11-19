"""URL routing for privacy, data export, and deletion endpoints."""

from django.urls import path

from apps.privacy.api.views import (
    AccountDeletionView,
    CurrentAccountDeletionView,
    DataMapView,
    ExportCancelView,
    ExportDetailView,
    ExportDownloadView,
    ExportListCreateView,
)

urlpatterns = [
    path("exports/", ExportListCreateView.as_view(), name="export-list-create"),
    path("exports/<uuid:pk>/", ExportDetailView.as_view(), name="export-detail"),
    path("exports/<uuid:pk>/download/", ExportDownloadView.as_view(), name="export-download"),
    path("exports/<uuid:pk>/cancel/", ExportCancelView.as_view(), name="export-cancel"),
    path("privacy/data-map/", DataMapView.as_view(), name="privacy-data-map"),
    path(
        "privacy/deletion-requests/",
        AccountDeletionView.as_view(),
        name="privacy-deletion-requests",
    ),
    path(
        "privacy/deletion-requests/current/",
        CurrentAccountDeletionView.as_view(),
        name="privacy-deletion-current",
    ),
]
