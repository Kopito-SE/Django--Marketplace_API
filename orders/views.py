from rest_framework import generics, permissions
from twisted.python.compat import items

from .models import Cart, CartItem, Order, OrderItem
from .serializers import CartSerializer, OrderSerializer, OrderItemSerializer
from products.models import Product
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response


class CartView(generics.RetrieveAPIView):

    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart


class AddToCartView(generics.CreateAPIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):

        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity", 1)

        # Convert quantity to integer for validation
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValidationError("Quantity must be a valid number")


        if quantity <= 0:
            raise ValidationError("Quantity must be positive")


        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError("Product not found")


        if product.stock < quantity:
            raise ValidationError(f"Insufficient stock. Only {product.stock} available")
       

        cart, created = Cart.objects.get_or_create(user=request.user)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product
        )

        if not created:
            item.quantity += quantity  # Now using integer variable
        else:
            item.quantity = quantity

        item.save()

        return Response({"message": "Product added to cart"})
class CheckoutView(generics.CreateAPIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):

        try:
            cart = request.user.cart

        except Cart.DoesNotExist:
            raise ValidationError("Cart is empty")

        if not cart.items.exists():
            raise ValidationError("Cart is empty")

        total_price = 0

        order = Order.objects.create(
            user=request.user,
            total_price=0
        )

        for item in cart.items.all():
            product  = item.product

            if product.stock < item.quantity:
                raise ValidationError(f"Not enough stock for {product.name}")

            product.stock -= item.quantity
            product.save()

            price = item.product.price
            total_price += price * item.quantity

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=price
            )

        order.total_price = total_price
        order.save()

        # Clear cart
        cart.items.all().delete()

        return Response({
            "message": "Order created successfully",
            "order_id": order.pk
        })
class UserOrderListView(generics.ListAPIView):

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

class OrderDetailsView(generics.RetrieveAPIView):

    serializer_class = OrderSerializer
    permission_classes  = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

class VendorOrderListView(generics.ListAPIView):

    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        user = self.request.user

        #Check if User is a Vendor
        if not hasattr(user, "vendor_profile"):
            raise ValidationError("You are not a vendor")

        vendor = getattr(user,"vendor_profile")

        return OrderItem.objects.filter(
            product__vendor=vendor
        )

class VendorOrderUpdateView(generics.UpdateAPIView):

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        user = self.request.user

        if not hasattr(user, "vendor_profile"):
            raise ValidationError("You are not a Vendor")

        vendor =hasattr(user,"vendor_profile")

        return Order.objects.filter(
            items__product__vendor = vendor
        ).distinct()