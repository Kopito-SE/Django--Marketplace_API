from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem

class CartItemSerializer(serializers.ModelSerializer):
    #Product Details

    product_name = serializers.CharField(source='product.name', read_only=True)
    product_details = serializers.CharField(source='product.description', read_only=True)
    product_price = serializers.DecimalField(source='product.price', read_only=True, max_digits=10, decimal_places=2 )
    product_image = serializers.ImageField(source='product.image')
    line_total = serializers.SerializerMethodField()


    class Meta:
        model =CartItem
        fields =[
            "id",
            "product",
            "quantity",
            "product_name",
            "product_price",
            "product_image",
            "product_details",
            "line_total"
        ]
    def get_line_total(self, obj):
        """Calculate Line Total=quantity * product_price"""
        return obj.quantity * obj.product.price
class CartSerializer(serializers.ModelSerializer):

    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ["id","items"]

class OrderItemSerializer(serializers.ModelSerializer):
    payment = serializers.CharField(source="order.payment_status", read_only=True)
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
            "price",
            "payment",


        ]

class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id","total_price", "status", "created_at","items"]
        read_only_fields = ["id", "total_price", "created_at", "items"]

# Adding Guest add to Cart Feature
class MergeGuestCartSerializer(serializers.Serializer):
    """Serializer for merging guest cart items"""
    items = serializers.ListField(

        child=serializers.ListField(),
        required=True

    )
    def validate_items(self, value):
        """Validate each guest cart item has required fields"""
        for item in value:
            if 'product_id' not in item:
                raise serializers.ValidationError("Each Item must Have a product")

            if 'quantity' not in item:
                raise serializers.ValidationError("Item Must Have Quantity")

            if item['quantity'] < 1:
                raise serializers.ValidationError("Quantity Must Be More than 1")
        return value

