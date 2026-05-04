from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Vendor(models.Model):
    owner =models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="vendor_profile"
    )
    store_name = models.CharField(max_length=255)
    store_description = models.TextField(blank=True)
    store_address = models.TextField(blank=True)
    store_phone = models.IntegerField(null=True)
    store_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.store_name
