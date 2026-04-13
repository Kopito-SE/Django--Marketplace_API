from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, filters
from .models import Product
from .serializers import ProductSerializer
from vendors.models import Vendor
from rest_framework.exceptions import ValidationError, PermissionDenied
from core.pagination import ProductPagination


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
    pagination_class = ProductPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["category"]  # DjangoFilterBackend auto-filters this
    search_fields = ["name", "description"]

    # No need to override get_queryset at all!

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
