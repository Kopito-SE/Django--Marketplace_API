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
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MpesaPaymentView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            phone = request.data.get("phone")
            amount = request.data.get("amount")
            order_id = request.data.get("order_id")

            print(f"📱 Payment request - Phone: {phone}, Amount: {amount}, Order ID: {order_id}")

            # Validate input
            if not phone:
                return Response({"error": "Phone number is required"}, status=status.HTTP_400_BAD_REQUEST)

            if not amount or float(amount) <= 0:
                return Response({"error": "Valid amount is required"}, status=status.HTTP_400_BAD_REQUEST)

            if not order_id:
                return Response({"error": "Order ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            # Try to get the order
            try:
                order = Order.objects.get(id=order_id, user=request.user)
                print(f"✅ Found Order #{order.id}")
            except Order.DoesNotExist:
                return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

            # IMPORTANT: Save the order ID in session for callback reference
            request.session['pending_order_id'] = order.id

            # Call STK Push
            response = stk_push(phone, amount, order_id)

            if not response:
                return Response({"error": "Failed to initiate payment"}, status=status.HTTP_400_BAD_REQUEST)

            # Extract CheckoutRequestID
            checkout_id = response.get("CheckoutRequestID")
            response_code = response.get("ResponseCode")

            print(f"📝 STK Push Response - Code: {response_code}, Checkout ID: {checkout_id}")

            # Save to order IMMEDIATELY
            if response_code == "0" and checkout_id:
                order.checkout_request_id = checkout_id
                order.payment_status = "pending"
                order.save()
                print(f"💾 IMMEDIATELY Saved CheckoutRequestID '{checkout_id}' to Order #{order.id}")
                return Response(response, status=status.HTTP_200_OK)
            else:
                error_msg = response.get("ResponseDescription", "Payment initiation failed")
                return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"🔥 Payment error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MpesaCallbackView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        print("==== CALLBACK RECEIVED ====")
        print(json.dumps(request.data, indent=2))

        try:
            body = request.data.get("Body", {})
            stk_callback = body.get("stkCallback", {})

            merchant_request_id = stk_callback.get("MerchantRequestID")
            checkout_id = stk_callback.get("CheckoutRequestID")
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")

            print(f"🔍 Processing callback for CheckoutRequestID: '{checkout_id}'")
            print(f"   ResultCode: {result_code}, ResultDesc: {result_desc}")

            # Method 1: Try to find order by checkout_request_id
            order = None

            # Try exact match first
            try:
                order = Order.objects.get(checkout_request_id=checkout_id)
                print(f"✅ Found Order #{order.id} by checkout_request_id")
            except Order.DoesNotExist:
                print(f"⚠️ Order not found by checkout_request_id, trying alternative methods...")

                # Method 2: Look for orders created in the last 5 minutes without checkout_id
                time_threshold = datetime.now() - timedelta(minutes=5)
                pending_orders = Order.objects.filter(
                    created_at__gte=time_threshold,
                    payment_status='pending'
                ).order_by('-created_at')

                if pending_orders.exists():
                    order = pending_orders.first()
                    print(f"📍 Found recent pending Order #{order.id} - will assign CheckoutRequestID")
                    order.checkout_request_id = checkout_id
                    order.save()
                    print(f"💾 Assigned CheckoutRequestID to Order #{order.id}")
                else:
                    # Method 3: Extract order_id from AccountReference
                    account_ref = stk_callback.get("AccountReference", "")
                    if "Order" in account_ref:
                        try:
                            order_id = int(account_ref.replace("Order", ""))
                            order = Order.objects.get(id=order_id)
                            order.checkout_request_id = checkout_id
                            order.save()
                            print(f"📍 Found Order #{order.id} from AccountReference")
                        except (ValueError, Order.DoesNotExist) as e:
                            print(f"❌ Failed to extract order from AccountReference: {e}")

            if not order:
                print(f"❌ No order found for CheckoutRequestID: '{checkout_id}'")
                print(f"   This payment will need to be reconciled manually")
                return Response({"message": "Order not found, but payment was recorded"}, status=status.HTTP_200_OK)

            print(f"✅ Processing payment for Order #{order.id}")

            # Check if already processed
            if order.payment_status == "paid":
                print("⚠️ Order already marked as paid")
                return Response({"message": "Already processed"}, status=status.HTTP_200_OK)

            # Process based on result code
            if result_code == "0" or result_code == 0:
                # Payment successful
                metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
                meta_dict = {item["Name"]: item.get("Value") for item in metadata}

                transaction_id = meta_dict.get("MpesaReceiptNumber")
                amount = meta_dict.get("Amount")
                phone = meta_dict.get("PhoneNumber")

                print(f"✅✅✅ PAYMENT SUCCESSFUL! ✅✅✅")
                print(f"   Transaction ID: {transaction_id}")
                print(f"   Amount: {amount}")
                print(f"   Phone: {phone}")

                # Update order
                order.payment_status = "paid"
                order.transaction_id = transaction_id
                order.status = "processing"
                order.save()

                print(f"💰💰💰 Order #{order.id} marked as PAID! 💰💰💰")

            else:
                # Payment failed
                print(f"❌ Payment failed - ResultCode: {result_code}, Description: {result_desc}")

                order.payment_status = "failed"
                order.failure_reason = result_desc
                order.save()

            return Response({"message": "Callback processed successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"🔥 Callback error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({"message": "Error processing callback"},
                            status=status.HTTP_200_OK)  # Always return 200 to M-Pesa


class PaymentStatusView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, checkout_request_id):
        """Check payment status from M-Pesa"""
        try:
            print(f"🔍 Checking status for: {checkout_request_id}")

            # First check local database
            try:
                order = Order.objects.get(checkout_request_id=checkout_request_id, user=request.user)
                print(f"✅ Found order #{order.id} with status: {order.payment_status}")

                if order.payment_status == "paid":
                    return Response({
                        "status": "completed",
                        "ResultCode": "0",
                        "ResultDesc": "Payment completed successfully",
                        "CheckoutRequestID": checkout_request_id,
                        "Amount": str(order.total_price),
                        "MpesaReceiptNumber": order.transaction_id,
                    })
                elif order.payment_status == "failed":
                    return Response({
                        "status": "failed",
                        "ResultCode": "1037",
                        "ResultDesc": getattr(order, 'failure_reason', 'Payment failed'),
                        "CheckoutRequestID": checkout_request_id,
                    })
                elif order.payment_status == "pending":
                    # Still pending, check with M-Pesa
                    result = query_payment_status(checkout_request_id)
                    if result and result.get('ResultCode') == '0':
                        # Update order if paid
                        order.payment_status = "paid"
                        order.save()
                        return Response({
                            "status": "completed",
                            "ResultCode": "0",
                            "ResultDesc": "Payment completed",
                            "CheckoutRequestID": checkout_request_id,
                        })
                    return Response({
                        "status": "pending",
                        "ResultCode": "1037",
                        "ResultDesc": "Payment pending. Please check your phone.",
                        "CheckoutRequestID": checkout_request_id,
                    })

            except Order.DoesNotExist:
                print(f"⚠️ Order not found locally for: {checkout_request_id}")

                # Try to find by recent orders
                time_threshold = datetime.now() - timedelta(minutes=10)
                recent_orders = Order.objects.filter(
                    user=request.user,
                    created_at__gte=time_threshold,
                    payment_status='pending'
                ).order_by('-created_at')

                if recent_orders.exists():
                    order = recent_orders.first()
                    print(f"📍 Found recent Order #{order.id}, linking with CheckoutRequestID")
                    order.checkout_request_id = checkout_request_id
                    order.save()

                    return Response({
                        "status": "pending",
                        "ResultCode": "1037",
                        "ResultDesc": "Payment pending. Please check your phone.",
                        "CheckoutRequestID": checkout_request_id,
                    })

            # Query M-Pesa API for status
            result = query_payment_status(checkout_request_id)

            if not result:
                return Response({
                    "status": "pending",
                    "ResultCode": "1037",
                    "ResultDesc": "Payment pending. Please check your phone.",
                    "CheckoutRequestID": checkout_request_id,
                })

            result_code = result.get('ResultCode')
            result_desc = result.get('ResultDesc')

            if result_code == '0':
                status_val = 'completed'
            elif result_code == '1037':
                status_val = 'pending'
            else:
                status_val = 'failed'

            return Response({
                'status': status_val,
                'ResultCode': result_code,
                'ResultDesc': result_desc,
                'CheckoutRequestID': result.get('CheckoutRequestID'),
                'Amount': result.get('Amount'),
                'MpesaReceiptNumber': result.get('MpesaReceiptNumber'),
            })

        except Exception as e:
            print(f"🔥 Status check error: {str(e)}")
            return Response({
                'status': 'pending',
                'error': str(e),
            }, status=status.HTTP_200_OK)