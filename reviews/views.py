from rest_framework import generics, permissions
from .models import Review
from .serializers import ReviewSerializer
from products.models import Product
from rest_framework.exceptions import ValidationError

class CreateReviewView(generics.CreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        product_id = self.kwargs.get("product_id")

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError("Product not found")
        #Prevent Duplicate Review
        if Review.objects.filter(user=self.request.user, product=product).exists():
            raise ValidationError("You already reviewed this Product")
        serializer.save(user=self.request.user, product=product)
class ProductReviewListView(generics.ListAPIView):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        product_id = self.kwargs.get("product_id")
        return Review.objects.filter(product_id=product_id)



