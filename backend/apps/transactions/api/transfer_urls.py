"""URL routing for transfers API."""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from apps.transactions.api.transfer_views import TransferViewSet

router = DefaultRouter()
router.register(r"", TransferViewSet, basename="transfer")

urlpatterns = router.urls
