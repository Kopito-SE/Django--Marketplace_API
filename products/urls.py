from django.urls import path
from .views import CreateProductView, ProductListView, ProductDetailView, CategoryListView

urlpatterns = [
    path("create/", CreateProductView.as_view()),
    path("", ProductListView.as_view()),
    path("<int:pk>/", ProductDetailView.as_view()),
    path("categories/", CategoryListView.as_view(), name="categories")
]