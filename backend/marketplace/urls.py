from django.urls import path
from .views import (
    ListingListCreateView,
    ListingDetailView,
    BuyerOrderListCreateView,
    BuyerOrderDetailView
)

urlpatterns = [
    path('listings/', ListingListCreateView.as_view(), name='listing-list-create'),
    path('listings/<uuid:pk>/', ListingDetailView.as_view(), name='listing-detail'),
    path('buyer-orders/', BuyerOrderListCreateView.as_view(), name='buyer-order-list-create'),
    path('buyer-orders/<uuid:pk>/', BuyerOrderDetailView.as_view(), name='buyer-order-detail'),
]
