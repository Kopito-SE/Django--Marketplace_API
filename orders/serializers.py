from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem

class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model =CartItem
        fields =["id","product","quantity"]

class CartSerializer(serializers.ModelSerializer):

    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ["id","items"]

class OrderItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(source="product.name",read_only=True)
    order_id = serializers.IntegerField(source="order.id", read_only=True)

    class Meta:
        model = OrderItem
        fields =[
            "order_id",
            "product",
            "product_id",
            "product_name",
            "quantity",
            "price"
        ]

class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id","total_price", "status", "created_at","items"]
        read_only_fields = ["id", "total_price", "created_at", "items"]

