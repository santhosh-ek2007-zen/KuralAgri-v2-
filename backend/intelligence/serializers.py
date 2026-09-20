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


class PriceRecommendationSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.name', read_only=True)

    class Meta:
        model = PriceRecommendation
        fields = [
            'id', 'crop', 'crop_name', 'grade', 'region',
            'recommended_min', 'recommended_max', 'benchmark_price',
            'floor_price', 'minimum_viable_price', 'buyer_ceiling',
            'confidence', 'explanation', 'summary', 'created_at'
        ]
