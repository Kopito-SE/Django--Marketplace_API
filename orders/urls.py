from django.urls import path
from .views import CartView, AddToCartView, CheckoutView, UserOrderListView, OrderDetailsView, VendorOrderListView, \
    VendorOrderUpdateView

urlpatterns = [
    path("", CartView.as_view()),
    path("add/", AddToCartView.as_view()),
    path("checkout/", CheckoutView.as_view()),
    path("orders/", UserOrderListView.as_view()),
    path("orders/<int:pk>/", OrderDetailsView.as_view()),
    path("vendor/orders/", VendorOrderListView.as_view()),
    path("vendor/orders/<int:pk>/", VendorOrderUpdateView.as_view()),

]