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

        if otp.is_blocked():
            raise ValidationError("Too many Failed attempts.Request new otp")

        if otp.is_expired():
            raise ValidationError("OTP expired")

        if otp.code != code:
            raise ValidationError("Invalid OTP")

        user.is_active = True
        user.is_verified = True
        user.save()

        otp.delete()

        return Response({"message": "Account verified successfully"})
class ResendOTPView(generics.GenericAPIView):
    def post(self, request):
        email = request.data.get("email")
        try:
            user = User.objects.get(email=email)
            otp = user.otp

        except:
            raise ValidationError("User not Found")

        if not otp.can_resend():
            raise ValidationError("Wait before requesting another OTP")

        otp.generate_code()
        otp.save()

        send_otp_mail.delay(user.email, otp.code)

        return Response({"message":"OTP send successfully,check your email"})

class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
