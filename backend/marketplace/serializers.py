from rest_framework import serializers
from .models import Listing, BuyerOrder
from catalog.serializers import CropSerializer


class ListingSerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source='farmer.user.full_name', read_only=True)
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    available_kg = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    price_recommendation = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id',
            'farmer',
            'farmer_name',
            'crop',
            'crop_name',
            'grade',
            'quantity_kg',
            'reserved_kg',
            'available_kg',
            'harvest_datetime',
            'usable_life_hours',
            'remaining_shelf_life_hours',
            'village',
            'district',
            'latitude',
            'longitude',
            'self_delivery',
            'status',
            'expires_at',
            'price_recommendation',
            'created_at',
        ]
        read_only_fields = ['id', 'farmer', 'reserved_kg', 'remaining_shelf_life_hours', 'created_at']

    def get_price_recommendation(self, obj):
        rec = obj.pricerecommendation_set.order_by('-created_at').first()
        if rec:
            from intelligence.serializers import PriceRecommendationSerializer
            return PriceRecommendationSerializer(rec).data
        return None


class BuyerOrderSerializer(serializers.ModelSerializer):
    buyer_organisation = serializers.CharField(source='buyer.organisation', read_only=True)
    crop_name = serializers.CharField(source='crop.name', read_only=True)

    class Meta:
        model = BuyerOrder
        fields = [
            'id',
            'order_code',
            'buyer',
            'buyer_organisation',
            'crop',
            'crop_name',
            'grade',
            'quantity_kg',
            'delivery_deadline',
            'max_price_per_kg',
            'sourcing_preference',
            'allow_partial',
            'min_acceptable_quantity_kg',
            'delivery_district',
            'delivery_latitude',
            'delivery_longitude',
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'order_code', 'buyer', 'status', 'created_at']
