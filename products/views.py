from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, filters
from rest_framework.response import Response

from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from vendors.models import Vendor
from rest_framework.exceptions import ValidationError, PermissionDenied
from core.pagination import ProductPagination
from django.core.cache import cache
from rest_framework.parsers import MultiPartParser, FormParser




class CreateProductView(generics.CreateAPIView):

    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):

        try:
            vendor = self.request.user.vendor_profile
        except Vendor.DoesNotExist:
            raise ValidationError("You must create a store first")
        if not vendor.is_active:  # If you have such a field
            raise PermissionDenied("Your vendor account is not active")

        serializer.save(vendor=vendor)
        # CLEAR CACHE
        cache.delete("product_list")

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)

    serializer_class = ProductSerializer
    pagination_class = ProductPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["category"]  # DjangoFilterBackend auto-filters this
    search_fields = ["name", "description"]

    # Cache Product List
    def list(self, request, *args, **kwargs):
        print("🔵 View is being called!")

        page = request.query_params.get("page", 1)
        search = request.query_params.get("search", "")
        category = request.query_params.get("category", "")

        cache_key = f"product_list_page_{page}_search_{search}_category_{category}"

        data = cache.get(cache_key)
        print(f"🔵 Cache key: {cache_key}")
        print(f"🔵 Cache data: {data}")

        if not data:
            print("🟡 CACHE MISS - Fetching from database")
            response = super().list(request, *args, **kwargs)
            cache.set(cache_key, response.data, timeout=60)
            print("🟢 Data cached successfully")
            return response

        print("✅ CACHE HIT")
        return Response(data)
class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer

    #Cache Product Details
    def retrieve(self, request, *args, **kwargs):

        product_id = kwargs.get("pk")
        cache_key = f"product_{product_id}"

        data = cache.get(cache_key)

        if not data:
            response = super().retrieve(request, *args, **kwargs)
            cache.set(cache_key, response.data, timeout=60)
            return response
        return Response(data)
class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer