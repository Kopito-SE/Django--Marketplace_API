from django.urls import path
from payments.views import MpesaPaymentView, MpesaCallbackView, PaymentStatusView

urlpatterns = [
    path("pay/", MpesaPaymentView.as_view(),name="mpesa-pay"),
    path("callback/", MpesaCallbackView.as_view(), name="mpesa-callback"),
    path("status/<str:checkout_request_id>/", PaymentStatusView.as_view(), name="payment-status")
]