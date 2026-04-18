from celery import shared_task

@shared_task
def send_order_confirmation_email(user_email, order_id):
    print(f"Sending email to {user_email} for order {order_id}")