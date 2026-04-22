from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_otp_mail(user_mail, code):

    subject = "Verify your Account"

    message = f"""
    Your verification code is: {code}
    Expires in 5 minutes
    """
    send_mail(
        subject,
        message,
        None,
        [user_mail],
        fail_silently=False,
    )

