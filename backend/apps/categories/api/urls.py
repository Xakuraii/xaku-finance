"""Category API URL routing."""

from rest_framework.routers import SimpleRouter

from apps.categories.api.views import CategoryViewSet

router = SimpleRouter()
router.register("", CategoryViewSet, basename="category")

urlpatterns = router.urls
