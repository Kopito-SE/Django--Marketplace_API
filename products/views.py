from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Product
from .serializers import ProductSerializer
from vendors.models import Vendor
from rest_framework.exceptions import ValidationError, PermissionDenied


class CreateProductView(generics.CreateAPIView):

    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):

        try:
            vendor = self.request.user.vendor_profile
        except Vendor.DoesNotExist:
            raise ValidationError("You must create a store first")
        if not vendor.is_active:  # If you have such a field
            raise PermissionDenied("Your vendor account is not active")

        serializer.save(vendor=vendor)

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer