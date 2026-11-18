"""URL routing for Debts API."""

from rest_framework.routers import DefaultRouter

from apps.debts.api.views import LiabilityViewSet

router = DefaultRouter()
router.register(r"debts", LiabilityViewSet, basename="debt")

urlpatterns = router.urls
