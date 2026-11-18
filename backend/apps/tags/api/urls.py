"""Tag API URL routing."""

from rest_framework.routers import SimpleRouter

from apps.tags.api.views import TagViewSet

router = SimpleRouter()
router.register("", TagViewSet, basename="tag")

urlpatterns = router.urls
