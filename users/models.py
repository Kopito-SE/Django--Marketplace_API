from django.contrib.auth.models import AbstractUser
from django.db import models
import random
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):

    USER_ROLES = (
        ("customer", "Customer"),
        ("vendor", "Vendor"),
        ("admin", "Admin"),
    )

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=USER_ROLES, default="customer")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class EmailOTP(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="otp"
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)

    def generate_code(self):
        self.code = str(random.randint(100000,999999))






















