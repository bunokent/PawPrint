from django.urls import path

from .views import (
    GoogleCallbackView,
    GoogleUrlView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="auth-register"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("me", MeView.as_view(), name="auth-me"),
    path("google/url", GoogleUrlView.as_view(), name="auth-google-url"),
    path("google/callback", GoogleCallbackView.as_view(), name="auth-google-callback"),
]
