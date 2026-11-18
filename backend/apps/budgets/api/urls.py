"""Budget API URL routing."""

from rest_framework.routers import SimpleRouter

from apps.budgets.api.views import BudgetViewSet

router = SimpleRouter()
router.register("", BudgetViewSet, basename="budget")

urlpatterns = router.urls
