from django.urls import path
from .views import (
    CartView,
    AddToCartView,
    UpdateCartItemView,
    RemoveFromCartView,
    ClearCartView,
    CheckoutView,
    UserOrderListView,
    OrderDetailsView,
    VendorOrderListView,
    VendorOrderUpdateView,
    VendorStatsView,
    GuestCartView,
    MergeGuestCartView,
    checkout


)

urlpatterns = [
    # Cart endpoints
    path("", CartView.as_view(), name='cart'),
    path("add/", AddToCartView.as_view(), name='add-to-cart'),
    path("items/<int:item_id>/", UpdateCartItemView.as_view(), name='update-cart-item'),
    path("items/<int:item_id>/remove/", RemoveFromCartView.as_view(), name='remove-from-cart'),
    path("clear/", ClearCartView.as_view(), name='clear-cart'),

    # Order endpoints
    path("checkout/", CheckoutView.as_view(), name='checkout'),
    path("orders/", UserOrderListView.as_view(), name='user-orders'),
    path("orders/<int:pk>/", OrderDetailsView.as_view(), name='order-details'),

    # Vendor endpoints
    path("vendor/orders/", VendorOrderListView.as_view(), name='vendor-orders'),
    path("vendor/orders/<int:pk>/", VendorOrderUpdateView.as_view(), name='vendor-order-update'),
    path("vendor/stats/", VendorStatsView.as_view(), name='vendor-stats'),

    #Guest Cart
    path('guest-cart/', GuestCartView.as_view(), name='guest-cart'),
    path('merge-guest-cart/', MergeGuestCartView.as_view(), name='merge-guest-cart'),
    path('checkout/', checkout, name='checkout'),
]