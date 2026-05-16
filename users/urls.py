from django.urls import path
from .views import RegisterView, LoginView, VerifyOTPView, ResendOTPView, ProfileView, ChangePasswordView, \
    GoogleLoginView

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view(), name="login"),
    path("verify/", VerifyOTPView.as_view()),
    path("resend/", ResendOTPView.as_view()),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("google/", GoogleLoginView.as_view())
]