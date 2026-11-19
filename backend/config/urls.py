"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import health_live, health_ready

urlpatterns = [
    path("", RedirectView.as_view(url="/api/docs/", permanent=False), name="root-redirect"),
    path("health/live", health_live, name="health-live"),
    path("health/ready", health_ready, name="health-ready"),
    path("api/v1/auth/", include("apps.identity.api.urls")),
    path("api/v1/accounts/", include("apps.accounts.api.urls")),
    path("api/v1/categories/", include("apps.categories.api.urls")),
    path("api/v1/tags/", include("apps.tags.api.urls")),
    path("api/v1/budgets/", include("apps.budgets.api.urls")),
    path("api/v1/imports/", include("apps.imports.api.urls")),
    path("api/v1/transactions/", include("apps.transactions.api.urls")),
    path("api/v1/transfers/", include("apps.transactions.api.transfer_urls")),
    path("api/v1/", include("apps.savings.api.urls")),
    path("api/v1/", include("apps.debts.api.urls")),
    path("api/v1/emergency-fund/", include("apps.analytics.api.urls")),
    path("api/v1/net-worth/", include("apps.analytics.api.net_worth_urls")),
    path("api/v1/reports/", include("apps.analytics.api.report_urls")),
    path("api/v1/", include("apps.analytics.api.intelligence_urls")),
    path("api/v1/", include("apps.workspaces.api.urls")),
    path("api/v1/", include("apps.notifications.api.urls")),
    path("api/v1/", include("apps.privacy.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("admin/", admin.site.urls),
]
