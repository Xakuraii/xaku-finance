"""URL routing for transactions API."""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from apps.transactions.api.views import TransactionViewSet

router = DefaultRouter()
router.register(r"", TransactionViewSet, basename="transaction")

urlpatterns = router.urls
