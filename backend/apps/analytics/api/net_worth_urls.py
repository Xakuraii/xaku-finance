"""URL routes for Net Worth API."""

from __future__ import annotations

from django.urls import path

from apps.analytics.api.views import NetWorthHistoryView, NetWorthView

app_name = "net_worth"

urlpatterns = [
    path("", NetWorthView.as_view(), name="current"),
    path("history/", NetWorthHistoryView.as_view(), name="history"),
]
