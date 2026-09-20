from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import (
    Crop,
    Region,
    AggregationPoint,
    RateCard,
    AdvanceTier,
    PlatformSettings
)
from .serializers import (
    CropSerializer,
    RegionSerializer,
    AggregationPointSerializer,
    RateCardSerializer,
    AdvanceTierSerializer,
    PlatformSettingsSerializer
)


class CropListView(generics.ListAPIView):
    """List all active crops and their grade parameters."""
    permission_classes = [AllowAny]
    queryset = Crop.objects.filter(is_active=True).prefetch_related('grade_params')
    serializer_class = CropSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category']
    search_fields = ['name', 'scientific_name']


class CropDetailView(generics.RetrieveAPIView):
    """Get single crop details."""
    permission_classes = [AllowAny]
    queryset = Crop.objects.filter(is_active=True).prefetch_related('grade_params')
    serializer_class = CropSerializer


class RegionListView(generics.ListAPIView):
    """List agricultural regions."""
    permission_classes = [AllowAny]
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    filterset_fields = ['state', 'district']
    search_fields = ['name', 'district', 'state']


class AggregationPointListView(generics.ListAPIView):
    """List active aggregation points / collection hubs."""
    permission_classes = [AllowAny]
    queryset = AggregationPoint.objects.filter(is_active=True).select_related('region')
    serializer_class = AggregationPointSerializer
    filterset_fields = ['region', 'has_cold_storage']
    search_fields = ['name', 'region__name']


class RateCardListView(generics.ListAPIView):
    """List current rate cards for crops and grades."""
    permission_classes = [AllowAny]
    queryset = RateCard.objects.filter(is_current=True).select_related('crop')
    serializer_class = RateCardSerializer
    filterset_fields = ['crop', 'grade']


class AdvanceTierListView(generics.ListAPIView):
    """List advance credit rating tiers."""
    permission_classes = [AllowAny]
    queryset = AdvanceTier.objects.all()
    serializer_class = AdvanceTierSerializer


class PlatformSettingsView(APIView):
    """Get active platform settings (fee, reserve, floor discount)."""
    permission_classes = [AllowAny]

    def get(self, request):
        settings_obj = PlatformSettings.get_settings()
        return Response(PlatformSettingsSerializer(settings_obj).data)
