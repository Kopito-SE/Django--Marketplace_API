from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from django.contrib.auth.hashers import make_password
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=[
            "id",
            "email",
            "username",
            "password",
            "role"
        ]
        extra_kwargs = {
            "password":{"write_only":True}
        }
    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)
class LoginSerializer(TokenObtainPairSerializer):

    username_field = "email"

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(
            request =self.context.get("request"),
            username=email,
            password=password
        )
        if not user:
            raise serializers.ValidationError("Invalid email or password")

        if not user.is_active:
            raise serializers.ValidationError(
                "Account not verified.Please verify your account to Login"
            )
        if not user.is_verified:
            raise serializers.ValidationError(
                "Email not Verified.Please Verify your email before logging in."
            )

        data = super().validate(attrs)

        data["email"] = user.email
        data["role"] = user.role
        data["is_verified"] = user.is_verified

        return data
