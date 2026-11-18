"""URL routing for accounts API."""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from apps.accounts.api.views import AccountViewSet

router = DefaultRouter()
router.register(r"", AccountViewSet, basename="account")

urlpatterns = router.urls
