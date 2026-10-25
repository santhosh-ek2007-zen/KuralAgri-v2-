from rest_framework import serializers
from .models import MarketSnapshot, DemandForecast, PriceRecommendation, MandiPrice


class MandiPriceSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = MandiPrice
        fields = [
            'id', 'crop', 'crop_name', 'region', 'region_name',
            'modal_price', 'min_price', 'max_price', 'arrivals_kg', 'recorded_date'
        ]


class MarketSnapshotSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = MarketSnapshot
        fields = [
            'id', 'crop', 'crop_name', 'region', 'region_name', 'snapshot_date',
            'benchmark_price', 'price_trend', 'price_change_pct',
            'supply_signal', 'demand_signal', 'weather_risk', 'explanation'
        ]


class DemandForecastSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = DemandForecast
        fields = [
            'id', 'crop', 'crop_name', 'region', 'region_name', 'forecast_date',
            'horizon_days', 'forecast_quantity_kg', 'daily_average_kg',
            'per_day_series', 'demand_level', 'confidence', 'explanation'
        ]


CONFIDENCE_TO_PCT = {'HIGH': 90, 'MEDIUM': 72, 'LOW': 50}


class PriceRecommendationSerializer(serializers.ModelSerializer):
    """
    Returns the shape expected by the FarmerView frontend component:
      price_range        : [min_str, max_str]
      recommended_price  : midpoint string
      mandi_benchmark    : benchmark_price field
      floor_price        : floor_price field
      confidence_pct     : numeric (0-100)
      explanation_bullets: flat list of human-readable strings
    """
    price_range = serializers.SerializerMethodField()
    recommended_price = serializers.SerializerMethodField()
    mandi_benchmark = serializers.SerializerMethodField()
    confidence_pct = serializers.SerializerMethodField()
    explanation_bullets = serializers.SerializerMethodField()

    class Meta:
        model = PriceRecommendation
        fields = [
            'id', 'crop', 'grade', 'region',
            'floor_price',
            'recommended_price',
            'price_range',
            'mandi_benchmark',
            'confidence_pct',
            'explanation_bullets',
            'summary',
            'created_at',
        ]

    def get_price_range(self, obj):
        return [str(obj.recommended_min), str(obj.recommended_max)]

    def get_recommended_price(self, obj):
        mid = (obj.recommended_min + obj.recommended_max) / 2
        return str(round(mid, 2))

    def get_mandi_benchmark(self, obj):
        return str(obj.benchmark_price)

    def get_confidence_pct(self, obj):
        return CONFIDENCE_TO_PCT.get(obj.confidence, 72)

    def get_explanation_bullets(self, obj):
        bullets = []
        for item in (obj.explanation or []):
            if isinstance(item, dict):
                factor = item.get('factor', '')
                effect = item.get('effect', '')
                detail = item.get('detail', '')
                if factor and effect:
                    bullets.append(f"{factor}: {effect} — {detail}" if detail else f"{factor}: {effect}")
                elif detail:
                    bullets.append(detail)
            elif isinstance(item, str):
                bullets.append(item)
        return bullets
