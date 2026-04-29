#Get Access Tokens

import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth
import base64
from datetime import datetime

from orders.models import Order


def get_mpesa_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(
        url,
        auth=HTTPBasicAuth(
            settings.MPESA_CONSUMER_KEY,
            settings.MPESA_CONSUMER_SECRET
        )
    )
    return response.json().get("access_token")
def stk_push(phone, amount, order_id):

    token = get_mpesa_token()
    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode()
    ).decode()
    print("CALLBACK URL:", settings.MPESA_CALLBACK_URL)

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": f"Order {order_id}",
        "TransactionDesc": "Payment for order"
    }
    headers = {
        "Authorization":f"Bearer {token}"
    }
    print("PAYLOAD:", payload)

    response = requests.post(url, json=payload, headers=headers)
    result = response.json()

    #Save the CheckoutRequestID to the order
    if result.get("ResponseCode") == "0":
        try:
            order = Order.objects.get(id=order_id)
            order.checkout_request_id = result.get("CheckoutRequestID")
            order.save()
            print(f"✅ Saved CheckoutRequestID '{order.checkout_request_id}' to Order #{order_id}")
        except Order.DoesNotExist:
            print(f"❌ Order #{order_id} not found when trying to save CheckoutRequestID")

    return result