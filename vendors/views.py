from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Vendor
from .serializers import VendorSerializer
from rest_framework.exceptions import ValidationError



class CreateVendorView(generics.CreateAPIView):
    serializer_class = VendorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        if hasattr(self.request.user, "vendor_profile"):
            raise ValidationError("You Already Have a store")
        serializer.save(owner=self.request.user)