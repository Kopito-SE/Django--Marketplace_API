from rest_framework import generics, permissions, status
from twisted.python.compat import items
from django.shortcuts import get_object_or_404

from .models import Cart, CartItem, Order, OrderItem
from .serializers import CartSerializer, OrderSerializer, OrderItemSerializer, CartItemSerializer
from products.models import Product
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .tasks import send_order_confirmation_email
from django.db.models import Sum, Count
from django.db.models import F

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


class UpdateCartItemView(generics.UpdateAPIView):
    """Update cart item quantity"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartItemSerializer

    def get_object(self):
        item_id = self.kwargs.get('item_id')
        cart_item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=self.request.user
        )
        return cart_item

    def patch(self, request, *args, **kwargs):
        cart_item = self.get_object()
        quantity = request.data.get("quantity")

        if quantity is None:
            return Response(
                {"error": "Quantity is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert quantity to integer for validation
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValidationError("Quantity must be a valid number")

        if quantity <= 0:
            # If quantity is 0 or less, delete the item
            cart_item.delete()
            # Return updated cart
            cart = Cart.objects.get(user=request.user)
            serializer = CartSerializer(cart)
            return Response(serializer.data)

        # Check stock availability
        if cart_item.product.stock < quantity:
            raise ValidationError(
                f"Insufficient stock. Only {cart_item.product.stock} available"
            )

        cart_item.quantity = quantity
        cart_item.save()

        # Return updated cart
        cart = Cart.objects.get(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        """Handle DELETE requests to remove cart item"""
        cart_item = self.get_object()
        cart_item.delete()

        # Return updated cart
        cart = Cart.objects.get(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class RemoveFromCartView(generics.DestroyAPIView):
    """Remove item from cart"""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        item_id = self.kwargs.get('item_id')
        cart_item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user
        )
        cart_item.delete()

        # Return updated cart
        cart = Cart.objects.get(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class ClearCartView(generics.DestroyAPIView):
    """Clear entire cart"""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()
        return Response(
            {"message": "Cart cleared successfully"},
            status=status.HTTP_200_OK
        )


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
            product = item.product

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

        send_order_confirmation_email.delay(
            request.user.email,
            order.pk
        )

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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class VendorOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer  # Change to OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Check if User is a Vendor
        if not hasattr(user, "vendor_profile"):
            raise ValidationError("You are not a vendor")

        vendor = user.vendor_profile

        # Get all order items for products belonging to this vendor
        order_items = OrderItem.objects.filter(
            product__vendor=vendor
        ).select_related('order', 'product')

        # Get unique order IDs
        order_ids = order_items.values_list('order_id', flat=True).distinct()

        # Return Order objects (not OrderItems) with prefetched items for efficiency
        return Order.objects.filter(
            id__in=order_ids
        ).prefetch_related(
            'items',  # Prefetch order items
            'items__product'  # Prefetch product details for each item
        ).order_by('-created_at')  # Most recent first


class VendorOrderUpdateView(generics.UpdateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if not hasattr(user, "vendor_profile"):
            raise ValidationError("You are not a Vendor")

        vendor = user.vendor_profile

        return Order.objects.filter(
            items__product__vendor=vendor
        ).distinct()


class VendorStatsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if not hasattr(user, "vendor_profile"):
            raise ValidationError("You are not a Vendor")

        vendor = user.vendor_profile

        order_items = OrderItem.objects.filter(
            product__vendor=vendor
        )
        stats = order_items.aggregate(
            total_orders=Count("order", distinct=True),
            total_revenue=Sum(F("price") * F("quantity")),
            total_products_sold=Sum("quantity")
        )

        return Response({
            "total_orders": stats["total_orders"] or 0,
            "total_revenue": stats["total_revenue"] or 0,
            "total_products_sold": stats["total_products_sold"] or 0
        })
















