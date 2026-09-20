from rest_framework import serializers
from .models import Lot, LotContribution


class LotContributionSerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source='farmer.user.full_name', read_only=True)
    farmer_phone = serializers.CharField(source='farmer.user.phone', read_only=True)
    village = serializers.CharField(source='farmer.village', read_only=True)
    district = serializers.CharField(source='farmer.district', read_only=True)

    class Meta:
        model = LotContribution
        fields = [
            'id',
            'lot',
            'listing',
            'farmer',
            'farmer_name',
            'farmer_phone',
            'village',
            'district',
            'committed_quantity_kg',
            'delivered_quantity_kg',
            'advance_amount',
            'interest_amount',
            'lender_claim',
            'residual_entitlement',
            'status',
            'match_score',
            'created_at',
        ]


class LotSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    buyer_organisation = serializers.CharField(source='buyer_order.buyer.organisation', read_only=True)
    contributions = LotContributionSerializer(many=True, read_only=True)

    class Meta:
        model = Lot
        fields = [
            'id',
            'lot_code',
            'buyer_order',
            'buyer_organisation',
            'crop',
            'crop_name',
            'grade',
            'total_quantity_kg',
            'delivered_quantity_kg',
            'floor_price_per_kg',
            'minimum_viable_price_per_kg',
            'agreed_price_per_kg',
            'logistics_cost',
            'status',
            'parent_lot',
            'selected_destination_id',
            'aggregation_point',
            'contributions',
            'created_at',
        ]
        read_only_fields = [
            'id', 'lot_code', 'floor_price_per_kg', 'minimum_viable_price_per_kg',
            'created_at', 'contributions'
        ]
