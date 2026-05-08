import json
from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .utils import stk_push, query_payment_status
from orders.models import Order
import logging

logger = logging.getLogger(__name__)


class MpesaPaymentView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone = request.data.get("phone")
        amount = request.data.get("amount")
        order_id = request.data.get("order_id")

        # Call stk Push
        response = stk_push(phone, amount, order_id)
        # Extract CheckoutRequestID
        checkout_id = response.get("CheckoutRequestID")

        if not checkout_id:
            return Response({"error": "Failed to Initiate Payment"}, status=400)

        # Save it in Orders
        try:
            order = Order.objects.get(id=order_id)
            order.checkout_request_id = checkout_id
            order.payment_status = "pending"
            order.save()
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

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

            # Get the order FIRST
            try:
                order = Order.objects.get(checkout_request_id=checkout_id)
                print(f"✅ Found Order #{order.pk}")
            except Order.DoesNotExist:
                print(f"❌ No order found with checkout_request_id: '{checkout_id}'")
                return Response({"message": "Order not found"}, status=404)

            # Prevent duplicate processing
            if order.payment_status == "paid":
                print("⚠️ Callback already processed")
                return Response({"message": "Already processed"})

            # SUCCESS CASE
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

                # Update order
                order.payment_status = "paid"
                order.transaction_id = transaction_id
                order.status = "processing"
                order.save()

                print(f"✅ Payment saved for Order #{order.pk}")

            # FAILURE CASE
            else:
                print(f"❌ Payment failed with ResultCode: {result_code}")
                result_desc = stk_callback.get("ResultDesc", "Payment failed")

                order.payment_status = "failed"
                order.failure_reason = result_desc
                order.save()

        except Exception as e:
            print(f"🔥 Callback error: {str(e)}")
            import traceback
            traceback.print_exc()

        return Response({"message": "Callback processed"})


# NEW: Add this endpoint for checking payment status
class PaymentStatusView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, checkout_request_id):
        """
        Check payment status from M-Pesa
        """
        try:
            # First check if we have the order locally
            try:
                order = Order.objects.get(checkout_request_id=checkout_request_id, user=request.user)

                # If already paid or failed, return local status
                if order.payment_status == "paid":
                    return Response({
                        "status": "completed",
                        "ResultCode": "0",
                        "ResultDesc": "Payment completed successfully",
                        "CheckoutRequestID": checkout_request_id,
                        "Amount": str(order.total_price),
                        "MpesaReceiptNumber": order.transaction_id,
                        "TransactionDate": order.updated_at.strftime("%Y%m%d%H%M%S") if order.updated_at else None
                    })
                elif order.payment_status == "failed":
                    return Response({
                        "status": "failed",
                        "ResultCode": "1037",
                        "ResultDesc": getattr(order, 'failure_reason', 'Payment failed'),
                        "CheckoutRequestID": checkout_request_id
                    })
            except Order.DoesNotExist:
                # Order not found in local DB
                pass

            # If not resolved locally, query M-Pesa API
            result = query_payment_status(checkout_request_id)

            # Extract status information
            result_code = result.get('ResultCode')
            result_desc = result.get('ResultDesc')

            # Determine status based on ResultCode
            if result_code == '0':
                status = 'completed'
                # Update local order if found
                if 'order' in locals() and order:
                    order.payment_status = "paid"
                    if result.get('MpesaReceiptNumber'):
                        order.transaction_id = result.get('MpesaReceiptNumber')
                    order.save()
            elif result_code == '1037':
                status = 'pending'  # Still waiting for user input
            else:
                status = 'failed'
                # Update local order if found
                if 'order' in locals() and order:
                    order.payment_status = "failed"
                    order.failure_reason = result_desc
                    order.save()

            return Response({
                'status': status,
                'ResultCode': result_code,
                'ResultDesc': result_desc,
                'CheckoutRequestID': result.get('CheckoutRequestID'),
                'Amount': result.get('Amount'),
                'MpesaReceiptNumber': result.get('MpesaReceiptNumber'),
                'TransactionDate': result.get('TransactionDate')
            })

        except Exception as e:
            return Response({
                'error': str(e),
                'status': 'error'
            }, status=400)

