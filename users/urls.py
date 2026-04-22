from django.urls import path
from .views import RegisterView, LoginView, VerifyOTPView

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view(), name="login"),
    path("verify/", VerifyOTPView.as_view())
]