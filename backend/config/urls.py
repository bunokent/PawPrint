"""Root URL configuration — NO django.contrib.admin (admin is fully removed)."""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import HealthView

urlpatterns = [
    path("api/health", HealthView.as_view(), name="health"),
    path("api/auth", include("apps.users.urls")),
    path("api/pets", include("apps.pets.urls")),
    path("api/flyers", include("apps.flyers.urls")),
    path("api/rewards", include("apps.rewards.urls")),
    path("api/webhooks", include("apps.webhooks.urls")),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
