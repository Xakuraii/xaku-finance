from django.urls import path

from apps.identity.api.views import RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
]
