"""Import API URL routing."""

from rest_framework.routers import SimpleRouter

from apps.imports.api.views import ImportJobViewSet

router = SimpleRouter()
router.register("", ImportJobViewSet, basename="import")

urlpatterns = router.urls
