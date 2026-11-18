"""URL routes for Safe-to-Spend, Daily Allowance, and Recurring Obligations."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.analytics.api.views import (
    DailyAllowanceView,
    RecurringObligationViewSet,
    SafeToSpendView,
)

app_name = "intelligence"

router = DefaultRouter()
router.register("recurring-obligations", RecurringObligationViewSet, basename="recurring-obligation")

urlpatterns = [
    path("safe-to-spend/", SafeToSpendView.as_view(), name="safe-to-spend"),
    path("daily-allowance/", DailyAllowanceView.as_view(), name="daily-allowance"),
    path("", include(router.urls)),
]
