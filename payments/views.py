import json

from django.shortcuts import render

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .utils import stk_push
from orders.models import Order

class MpesaPaymentView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated]
    def post(self, request):

        phone = request.data.get("phone")
        amount = request.data.get("amount")
        order_id = request.data.get("order_id")

        #Call stk Push
        response = stk_push(phone, amount, order_id)
        #Extract CheckoutRequestID
        checkout_id = response.get("CheckoutRequestID")

        if not checkout_id:
            return Response({"error":"Failed to Initiate Payment"}, status=400)

        #Save it in Orders
        order = Order.objects.get(id=order_id)
        order.checkout_request_id = checkout_id
        order.save()

        return Response(response)

class MpesaCallbackView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        print("==== Callback Received ====")
        print(json.dumps(request.data, indent=2))

        try:
            stk_callback = request.data["Body"]["stkCallback"]

            checkout_id = stk_callback.get("CheckoutRequestID")
            result_code = stk_callback.get("ResultCode")

            print(f"Looking for CheckoutRequestID: '{checkout_id}'")

            # 🔥 Get the order FIRST
            try:
                order = Order.objects.get(checkout_request_id=checkout_id)
                print(f"✅ Found Order #{order.pk}")
            except Order.DoesNotExist:
                print(f"❌ No order found with checkout_request_id: '{checkout_id}'")
                return Response({"message": "Order not found"}, status=404)

            # 🔁 Prevent duplicate processing
            if order.payment_status == "paid":
                print("⚠️ Callback already processed")
                return Response({"message": "Already processed"})

            # ✅ SUCCESS CASE
            if result_code == 0:
                metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])

                # Convert list → dict (safer)
                meta_dict = {
                    item["Name"]: item.get("Value")
                    for item in metadata
                }

                transaction_id = meta_dict.get("MpesaReceiptNumber")
                amount = meta_dict.get("Amount")
                phone = meta_dict.get("PhoneNumber")

                if not transaction_id:
                    print("❌ Transaction ID missing in metadata")

                # 🔥 Update order
                order.payment_status = "paid"
                order.transaction_id = transaction_id
                order.status = "processing"
                order.save()

                print(f"✅ Payment saved for Order #{order.pk}")

            # ❌ FAILURE CASE
            else:
                print(f"❌ Payment failed with ResultCode: {result_code}")

                order.payment_status = "failed"
                order.save()

        except Exception as e:
            print(f"🔥 Callback error: {str(e)}")
            import traceback
            traceback.print_exc()

        return Response({"message": "Callback processed"})