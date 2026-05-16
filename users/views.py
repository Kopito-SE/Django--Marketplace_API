from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
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

from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework_simplejwt.tokens import RefreshToken

@method_decorator(csrf_exempt, name='dispatch')
class GoogleLoginView(APIView):

    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response(
                {"error":"Token is Required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                "15201590657-fl68ek84i4a10vhaobnf08tvn6qltnjd.apps.googleusercontent.com"
            )
            email = idinfo["email"]
            name = idinfo.get("name","")
            first_name = idinfo.get("given_name","")
            last_name = idinfo.get("family_name","")

            #Create or get User
            user, created = User.objects.get_or_create(
                email=email,
                defaults={

                    "username": email, #Use email as username
                    "first_name": first_name or name,
                    "last_name": last_name,
                    "is_active": True,
                    "is_verified": True,

                }
            )
            #If User already exists but is not active, activate them

            if not created and not user.is_active:
                user.is_active = True
                user.is_verified = True
                user.save()

            refresh = RefreshToken.for_user(user)

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,

                },

                "is_new_user": created
            })

        except ValueError as e:
            # Invalid Token
            return Response(
                {"error": f"Invalid token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )



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




