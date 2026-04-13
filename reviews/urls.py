from django.urls import path
from .views import CreateReviewView,ProductReviewListView
urlpatterns = [
    path("<int:product_id>/", ProductReviewListView.as_view(), name = "product-reviews"),
    path("<int:product_id>/create/", CreateReviewView.as_view(),name="create-review"),

]