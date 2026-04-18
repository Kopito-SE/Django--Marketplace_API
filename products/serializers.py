from rest_framework import serializers
from .models import Product
from reviews.models import Review
from django.db.models import Avg


class ProductSerializer(serializers.ModelSerializer):

    def get_average_rating(self, obj):
        avg = Review.objects.filter(product=obj).aggregate(avg=Avg("rating"))["avg"]
        return avg if avg else 0


    def get_review_count(self, obj):
        return Review.objects.filter(product=obj).count()


    average_rating =serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "stock",
            "category",
            "image",
            "average_rating",
            "review_count",
            "created_at"

        ]
        read_only_fields =["id","created_at"] #Prevents clients from modifying this fields when sending data to the API

