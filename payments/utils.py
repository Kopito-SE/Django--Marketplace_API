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
def stk_push(phone, amount, reference):

    token = get_mpesa_token()

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password = base64.b64encode(
        (
            settings.MPESA_SHORTCODE
            + settings.MPESA_PASSKEY
            + timestamp
        ).encode()
    ).decode()

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
        "AccountReference": reference,
        "TransactionDesc": "Marketplace Payment"
    }
    headers = {
        "Authorization":f"Bearer {token}"
    }
    response = requests.post(

        url,
        json=payload,
        headers=headers
    )

    return response.json()


def query_payment_status(checkout_request_id):
    """
    Query the status of an STK Push transaction from M-Pesa
    """
    token = get_mpesa_token()
    url = "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query"

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode()
    ).decode()

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id
    }

    headers = {
        "Authorization": f"Bearer {token}"
    }

    print(f"🔍 Querying payment status for: {checkout_request_id}")
    response = requests.post(url, json=payload, headers=headers)
    result = response.json()

    print(f"📊 Query result: {result}")
    return result