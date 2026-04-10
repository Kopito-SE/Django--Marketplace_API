from django.urls import path
from .views import CreateVendorView

urlpatterns = [
    path("create-store/", CreateVendorView.as_view())
]