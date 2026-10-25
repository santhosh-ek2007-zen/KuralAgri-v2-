from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404

from catalog.models import Crop, Region
from .models import MandiPrice
from .serializers import (
    MarketSnapshotSerializer,
    DemandForecastSerializer,
    PriceRecommendationSerializer,
    MandiPriceSerializer
)
from .services import (
    MarketIntelligenceService,
    DemandForecastService,
    PricingService
)


class MarketIntelligenceView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        crop_id = request.query_params.get('crop')
        region_id = request.query_params.get('region')

        if not crop_id:
            crop = Crop.objects.filter(is_active=True).first()
        else:
            crop = get_object_or_404(Crop, id=crop_id)

        if not region_id:
            region = Region.objects.first()
        else:
            region = get_object_or_404(Region, id=region_id)

        if not crop or not region:
            return Response({'error': {'code': 'NOT_FOUND', 'message': 'Crop or Region not found.'}}, status=status.HTTP_404_NOT_FOUND)

        snapshot = MarketIntelligenceService.get_market_snapshot(crop, region)
        return Response(MarketSnapshotSerializer(snapshot).data)


class DemandForecastView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        crop_id = request.data.get('crop')
        region_id = request.data.get('region')
        horizon_days = int(request.data.get('horizon_days', 7))

        crop = get_object_or_404(Crop, id=crop_id)
        region = get_object_or_404(Region, id=region_id)

        forecast = DemandForecastService.get_forecast(crop, region, horizon_days=horizon_days)
        return Response(DemandForecastSerializer(forecast).data)


class PriceRecommendationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        crop_id = request.data.get('crop')
        if not crop_id:
            return Response(
                {'error': {'code': 'MISSING_CROP', 'message': 'crop ID is required.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        grade = request.data.get('grade', 'A')
        region_id = request.data.get('region')

        # quantity_kg may arrive as string or number from the frontend
        try:
            quantity_kg = Decimal(str(request.data.get('quantity_kg', '100.00')))
        except Exception:
            quantity_kg = Decimal('100.00')

        # harvest_datetime is sent by the frontend for context but not needed
        # by the pricing engine directly — it is used to compute remaining
        # shelf life on the listing model when the listing is later created.
        # We accept it here and silently discard it.

        mvp = (
            Decimal(str(request.data['minimum_viable_price']))
            if 'minimum_viable_price' in request.data
            else None
        )
        ceiling = (
            Decimal(str(request.data['buyer_ceiling']))
            if 'buyer_ceiling' in request.data
            else None
        )

        crop = get_object_or_404(Crop, id=crop_id)
        region = get_object_or_404(Region, id=region_id) if region_id else Region.objects.first()

        if region is None:
            return Response(
                {'error': {'code': 'NO_REGION', 'message': 'No region found. Please seed region data.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        rec = PricingService.get_price_recommendation(
            crop=crop,
            grade=grade,
            region=region,
            quantity_kg=quantity_kg,
            minimum_viable_price=mvp,
            buyer_ceiling=ceiling,
        )
        return Response(PriceRecommendationSerializer(rec).data)


class MandiHistoryView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = MandiPriceSerializer

    def get_queryset(self):
        qs = MandiPrice.objects.all().select_related('crop', 'region')
        crop_id = self.request.query_params.get('crop')
        region_id = self.request.query_params.get('region')
        if crop_id:
            qs = qs.filter(crop_id=crop_id)
        if region_id:
            qs = qs.filter(region_id=region_id)
        return qs[:60]
