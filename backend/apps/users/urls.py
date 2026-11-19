from django.urls import path

from .views import (
    AvatarUploadView,
    GoogleCallbackView,
    GoogleUrlView,
    LoginView,
    LogoutView,
    MeView,
    ProfileView,
    RegisterView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="auth-register"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("me", MeView.as_view(), name="auth-me"),
    path("profile", ProfileView.as_view(), name="auth-profile"),
    path("avatar", AvatarUploadView.as_view(), name="auth-avatar"),
    path("google/url", GoogleUrlView.as_view(), name="auth-google-url"),
    path("google/callback", GoogleCallbackView.as_view(), name="auth-google-callback"),
]
