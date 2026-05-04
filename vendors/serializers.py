from rest_framework import serializers
from .models import Vendor

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields=[
            "id",
            "store_name",
            "store_description",
            "store_address",
            "store_phone",
            "store_email",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"]
