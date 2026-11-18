"""URL routing for Savings API."""

from rest_framework.routers import DefaultRouter

from apps.savings.api.views import SavingsGoalViewSet

router = DefaultRouter()
router.register(r"savings-goals", SavingsGoalViewSet, basename="savings-goal")

urlpatterns = router.urls
