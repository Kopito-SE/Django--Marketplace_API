from django.shortcuts import render
from rest_framework import generics
from .models import User
from .serializer import RegisterSerializer, LoginSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class =RegisterSerializer

class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
