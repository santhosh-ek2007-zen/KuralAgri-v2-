from rest_framework import serializers
from .models import (
    Crop,
    CropGradeParam,
    Region,
    AggregationPoint,
    RateCard,
    AdvanceTier,
    PlatformSettings
)


class CropGradeParamSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropGradeParam
        fields = ['id', 'grade', 'param_name', 'min_value', 'max_value', 'description']


class CropSerializer(serializers.ModelSerializer):
    grade_params = CropGradeParamSerializer(many=True, read_only=True)

    class Meta:
        model = Crop
        fields = [
            'id',
            'name',
            'scientific_name',
            'category',
            'default_shelf_life_days',
            'min_shelf_life_days',
            'storage_conditions',
            'is_active',
            'grade_params',
        ]


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name', 'state', 'district', 'climate_zone']


class AggregationPointSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)
    state = serializers.CharField(source='region.state', read_only=True)
    district = serializers.CharField(source='region.district', read_only=True)

    class Meta:
        model = AggregationPoint
        fields = [
            'id',
            'name',
            'region',
            'region_name',
            'state',
            'district',
            'latitude',
            'longitude',
            'capacity_mt',
            'has_cold_storage',
            'is_active',
        ]


class RateCardSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.name', read_only=True)

    class Meta:
        model = RateCard
        fields = [
            'id',
            'crop',
            'crop_name',
            'grade',
            'base_price_per_kg',
            'effective_date',
            'is_current',
        ]


class AdvanceTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvanceTier
        fields = [
            'id',
            'fpo_rating_min',
            'fpo_rating_max',
            'max_advance_pct',
            'interest_rate_pct',
        ]


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = [
            'platform_fee_pct',
            'risk_reserve_pct',
            'floor_price_discount_pct',
            'advance_tenure_days_max',
        ]
