"""
Authentication URL configuration.
"""

from django.urls import path
from .views import (
    RegisterView,
    VerifyCodeView,
    LoginView,
    RefreshTokenView,
    LogoutView,
    MeView,
)

app_name = "authentication"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-code/", VerifyCodeView.as_view(), name="verify-code"),
    path("verify-otp/", VerifyCodeView.as_view(), name="verify-otp"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]
