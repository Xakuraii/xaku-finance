"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import health_live, health_ready

urlpatterns = [
    path("health/live", health_live, name="health-live"),
    path("health/ready", health_ready, name="health-ready"),
    path("api/v1/auth/", include("apps.identity.api.urls")),
    path("api/v1/accounts/", include("apps.accounts.api.urls")),
    path("api/v1/transactions/", include("apps.transactions.api.urls")),
    path("api/v1/transfers/", include("apps.transactions.api.transfer_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("admin/", admin.site.urls),
]
