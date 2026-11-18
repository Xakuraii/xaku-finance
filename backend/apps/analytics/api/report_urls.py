"""URL routes for Financial Reports."""

from __future__ import annotations

from django.urls import path

from apps.analytics.api.report_views import (
    CashFlowReportView,
    CategoryReportView,
    ExpenseReportView,
    IncomeReportView,
    TrendsReportView,
)

app_name = "reports"

urlpatterns = [
    path("income/", IncomeReportView.as_view(), name="income"),
    path("expenses/", ExpenseReportView.as_view(), name="expenses"),
    path("categories/", CategoryReportView.as_view(), name="categories"),
    path("cashflow/", CashFlowReportView.as_view(), name="cashflow"),
    path("trends/", TrendsReportView.as_view(), name="trends"),
]
