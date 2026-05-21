import json
from django.db import transaction
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .utils import stk_push

import logging

from orders.tasks import send_order_confirmation_email
logger = logging.getLogger(__name__)


class MpesaPaymentView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            phone = request.data.get("phone")
            amount = request.data.get("amount")
            cart_id = request.data.get("cart_id")
            reference = request.data.get("reference")

            if not phone:
                return Response(
                    {"error": "Phone number is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not amount:
                return Response(
                    {"error": "Amount is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not cart_id:
                return Response(
                    {"error": "Cart ID is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not reference:
                return Response(
                    {"error": "Reference is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from orders.models import Cart
            from .models import PaymentTransaction

            try:
                cart = Cart.objects.get(
                    id=cart_id,
                    user=request.user
                )
            except Cart.DoesNotExist:
                return Response(
                    {"error": "Cart not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Make STK push request FIRST
            response = stk_push(
                phone=phone,
                amount=amount,
                reference=reference
            )

            # Check if STK push was successful
            if response.get("ResponseCode") != "0":
                return Response(
                    {
                        "error": response.get("ResponseDescription", "Failed to initiate payment"),
                        "ResponseCode": response.get("ResponseCode")
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ONLY create payment record if STK push succeeded
            checkout_id = response.get("CheckoutRequestID")

            payment = PaymentTransaction.objects.create(
                user=request.user,
                cart=cart,
                reference=reference,
                amount=amount,
                phone_number=phone,
                checkout_request_id=checkout_id,
                status="pending"  # Always pending initially
            )

            # Return success response that frontend expects
            return Response({
                "ResponseCode": "0",
                "ResponseDescription": "Success. Request accepted for processing",
                "CheckoutRequestID": checkout_id,
                "CustomerMessage": "Payment prompt sent to your phone",
                "status": "pending"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Payment error: {str(e)}")
            return Response(
                {"error": "Payment processing failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MpesaCallbackView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        print("==== CALLBACK RECEIVED ====")
        print(json.dumps(request.data, indent=2))

        try:
            from payments.models import PaymentTransaction
            from orders.models import Order, OrderItem

            body = request.data.get("Body", {})
            stk_callback = body.get("stkCallback", {})

            checkout_id = stk_callback.get("CheckoutRequestID")
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")

            print(f"🔍 Processing callback: {checkout_id}")

            # Find payment transaction
            try:
                payment = PaymentTransaction.objects.get(
                    checkout_request_id=checkout_id
                )
            except PaymentTransaction.DoesNotExist:
                print("❌ PaymentTransaction not found")
                return Response(
                    {"message": "Payment transaction not found"},
                    status=status.HTTP_200_OK
                )

            print(f"✅ Found PaymentTransaction #{payment.id}")

            # Prevent duplicate processing
            if payment.status == "completed":
                print("⚠️ Payment already processed")
                return Response(
                    {"message": "Already processed"},
                    status=status.HTTP_200_OK
                )

            # PAYMENT SUCCESS
            if str(result_code) == "0":
                with transaction.atomic():

                 metadata = stk_callback.get(
                     "CallbackMetadata",
                     {}
                 ).get("Item", [])

                 meta_dict = {
                     item["Name"]: item.get("Value")
                     for item in metadata
                 }

                 transaction_id = meta_dict.get("MpesaReceiptNumber")
                 amount = meta_dict.get("Amount")
                 phone = meta_dict.get("PhoneNumber")

                 print("✅ PAYMENT SUCCESSFUL")
                 print(f"Transaction ID: {transaction_id}")

                 # Update payment transaction
                 payment.status = "completed"
                 payment.transaction_id = transaction_id
                 payment.save()

                 cart = payment.cart
                 cart_items = cart.items.all()

                 if not cart_items.exists():
                     print("❌ Cart is empty")
                     return Response(
                         {"message": "Cart is empty"},
                         status=status.HTTP_200_OK
                     )

                 # Create order
                 order = Order.objects.create(
                     user=payment.user,
                     total_price=payment.amount,
                     payment_status="paid",
                     transaction_id=transaction_id,
                     status="processing"
                 )

                 print(f"🛒 Created Order #{order.id}")

                 total_price = 0

                 # Create order items
                 for cart_item in cart_items:
                     product = cart_item.product
                     quantity = cart_item.quantity
                     price = product.price

                     OrderItem.objects.create(
                         order=order,
                         product=product,
                         quantity=quantity,
                         price=price
                     )

                     # Reduce stock
                     if product.stock < quantity:
                         raise Exception(
                             f"Insufficient stock for {product.name}"
                         )
                     product.stock -= quantity
                     product.save()

                     total_price += price * quantity

                 order.total_price = total_price
                 order.save()


                 transaction.on_commit(
                     lambda: send_order_confirmation_email.delay(
                         payment.user.email,
                         order.id
                     )
                 )

                 # Link payment to order
                 payment.order = order
                 payment.save()

                 # Clear cart
                 cart_items.delete()

                 print(f"💰 Order #{order.id} marked as PAID")
                 print("🧹 Cart cleared")

            else:
                print(f"❌ Payment failed: {result_desc}")
                # Mark as failed
                payment.status = "failed"
                payment.failure_reason = result_desc
                payment.save()

            return Response(
                {"ResultCode": 0, "ResultDesc": "Callback processed successfully"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            print(f"🔥 Callback error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"ResultCode": 1, "ResultDesc": "Error processing callback"},
                status=status.HTTP_200_OK
            )


class PaymentStatusView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, checkout_request_id):
        try:
            from payments.models import PaymentTransaction

            print(f"🔍 Checking status for: {checkout_request_id}")

            try:
                payment = PaymentTransaction.objects.get(
                    checkout_request_id=checkout_request_id,
                    user=request.user
                )
            except PaymentTransaction.DoesNotExist:
                print("❌ Payment transaction not found")
                return Response(
                    {
                        "status": "pending",
                        "message": "Awaiting payment"
                    },
                    status=status.HTTP_200_OK
                )

            print(f"✅ Payment status: {payment.status}")

            # Return consistent response format
            if payment.status == "completed":
                return Response({
                    "status": "completed",
                    "success": True,
                    "message": "Payment successful",
                    "transaction_id": payment.transaction_id
                })

            elif payment.status == "failed":
                return Response({
                    "status": "failed",
                    "success": False,
                    "message": payment.failure_reason or "Payment failed"
                })

            else:  # pending
                return Response({
                    "status": "pending",
                    "success": None,
                    "message": "Awaiting payment confirmation. Check your phone for M-Pesa prompt."
                })

        except Exception as e:
            print(f"🔥 Status check error: {str(e)}")
            return Response(
                {
                    "status": "failed",
                    "success": False,
                    "error": str(e)
                },
                status=status.HTTP_200_OK
            )