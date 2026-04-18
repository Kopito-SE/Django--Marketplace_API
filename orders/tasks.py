from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_order_confirmation_email(user_email, order_id):
    subject = f"Order #{order_id} Confirmation"

    message = f"""
    Order placed successfully!
     
    Your order ID is {order_id}.
    Your items are being processed.
    
     
    """
    send_mail(
        subject,
        message,
        None, #uses DEFAULT_FROM_MAIL
        [user_email],
        fail_silently=False,
    )