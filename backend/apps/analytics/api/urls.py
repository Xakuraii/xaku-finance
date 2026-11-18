"""URL routes for Emergency Fund API."""

from __future__ import annotations

from django.urls import path

from apps.analytics.api.views import EmergencyFundProjectionView, EmergencyFundView

app_name = "emergency_fund"

urlpatterns = [
    path("", EmergencyFundView.as_view(), name="status"),
    path("projection/", EmergencyFundProjectionView.as_view(), name="projection"),
]
