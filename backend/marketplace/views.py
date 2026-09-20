import uuid
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .models import Listing, BuyerOrder
from .serializers import ListingSerializer, BuyerOrderSerializer
from common.permissions import IsFarmer, IsBuyer, IsOwnerOrAdmin
from common.audit import log_audit_event
from notifications.services import send_notification


class ListingListCreateView(generics.ListCreateAPIView):
    serializer_class = ListingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['crop', 'grade', 'district', 'status']
    search_fields = ['village', 'district', 'crop__name']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsFarmer()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        qs = Listing.objects.all().select_related('farmer__user', 'crop')

        # If user is a farmer requesting "mine"
        if user.is_authenticated and self.request.query_params.get('mine') == 'true':
            return qs.filter(farmer__user=user)

        # Lazy sweep shelf-life for active listings
        active_listings = qs.filter(status='ACTIVE')
        for l in active_listings[:20]:
            l.update_shelf_life()
            l.save(update_fields=['remaining_shelf_life_hours', 'status'])

        return qs.filter(status='ACTIVE')

    def perform_create(self, serializer):
        user = self.request.user
        farmer_profile = getattr(user, 'farmer_profile', None)
        if not farmer_profile:
            from users.models import FarmerProfile
            farmer_profile = FarmerProfile.objects.create(
                user=user,
                village="Default Village",
                district="Theni",
                latitude=9.9457,
                longitude=77.4779
            )

        listing = serializer.save(farmer=farmer_profile)
        listing.update_shelf_life()
        listing.save(update_fields=['remaining_shelf_life_hours', 'status'])

        # Auto-generate price recommendation for the listing
        from catalog.models import Region
        from intelligence.services import PricingService
        region = Region.objects.filter(district=listing.district).first() or Region.objects.first()
        if region:
            PricingService.get_price_recommendation(
                crop=listing.crop,
                grade=listing.grade,
                region=region,
                quantity_kg=listing.quantity_kg,
                listing=listing
            )

        log_audit_event(
            action="LISTING_CREATED",
            entity_type="Listing",
            entity_id=str(listing.id),
            user=user,
            metadata={
                "crop": listing.crop.name,
                "grade": listing.grade,
                "quantity_kg": str(listing.quantity_kg)
            }
        )

        send_notification(
            user=user,
            title="Produce Listed Successfully",
            message=f"Your listing for {listing.quantity_kg} kg of {listing.crop.name} [{listing.grade}] is now ACTIVE.",
            notification_type="LISTING_CREATED",
            metadata={"listing_id": str(listing.id)}
        )


class ListingDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    queryset = Listing.objects.all().select_related('farmer__user', 'crop')
    serializer_class = ListingSerializer

    def get_object(self):
        obj = super().get_object()
        obj.update_shelf_life()
        obj.save(update_fields=['remaining_shelf_life_hours', 'status'])
        return obj


class BuyerOrderListCreateView(generics.ListCreateAPIView):
    serializer_class = BuyerOrderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['crop', 'grade', 'status']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsBuyer()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = BuyerOrder.objects.all().select_related('buyer__user', 'crop')
        if not user.is_staff and user.role == 'BUYER':
            return qs.filter(buyer__user=user)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        buyer_profile = getattr(user, 'buyer_profile', None)
        if not buyer_profile:
            from users.models import BuyerProfile
            buyer_profile = BuyerProfile.objects.create(
                user=user,
                organisation=user.full_name,
                daily_capacity_kg=1000.00,
                district="Theni",
                latitude=9.9457,
                longitude=77.4779
            )

        order_code = f"BUY-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
        order = serializer.save(buyer=buyer_profile, order_code=order_code)

        log_audit_event(
            action="ORDER_CREATED",
            entity_type="BuyerOrder",
            entity_id=str(order.id),
            user=user,
            metadata={
                "order_code": order.order_code,
                "crop": order.crop.name,
                "quantity_kg": str(order.quantity_kg)
            }
        )


class BuyerOrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    queryset = BuyerOrder.objects.all().select_related('buyer__user', 'crop')
    serializer_class = BuyerOrderSerializer
