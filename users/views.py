
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth.hashers import check_password
from .models import User
from .serializer import RegisterSerializer, LoginSerializer,UserProfileSerializer
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


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and update the logged-in user's profile
    URL: GET/PATCH /api/profile/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        # Return the currently logged-in user
        return self.request.user

    def update(self, request, *args, **kwargs):
        # Allow partial updates (PATCH)
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """
    Change user's password
    URL: POST /api/change-password/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        # Check if current password is correct
        if not check_password(current_password, user.password):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if new passwords match
        if new_password != confirm_password:
            return Response(
                {'error': 'New passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check password length
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )




class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET /auth/profile/ - Get user profile
    PUT /auth/profile/ - Update user profile
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    POST /auth/change-password/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        # Check if old password is correct
        if not check_password(old_password, user.password):
            return Response(
                {'detail': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check password length
        if len(new_password) < 8:
            return Response(
                {'detail': 'Password must be at least 8 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        return Response(
            {'detail': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )