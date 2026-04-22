from django.shortcuts import render
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import User
from .serializer import RegisterSerializer, LoginSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import EmailOTP
from .tasks import send_otp_mail

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class =RegisterSerializer

    def perform_create(self, serializer):
        user = serializer.save(is_active=False)

        otp, created = EmailOTP.objects.get_or_create(user=user)
        otp.generate_code()
        otp.save()

        # Send OTP via Celery
        send_otp_mail.delay(
            user.email,
            f"Your verification code is {otp.code}"
        )



class VerifyOTPView(generics.GenericAPIView):

    def post(self, request):

        email = request.data.get("email")
        code = request.data.get("code")

        try:
            user = User.objects.get(email=email)
            otp = user.otp
        except:
            raise ValidationError("Invalid email")

        if otp.is_expired():
            raise ValidationError("OTP expired")

        if otp.code != code:
            raise ValidationError("Invalid OTP")

        user.is_active = True
        user.is_verified = True
        user.save()

        otp.delete()

        return Response({"message": "Account verified successfully"})

class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
