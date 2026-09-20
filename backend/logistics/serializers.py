from rest_framework import serializers
from logistics.models import (
    LogisticsRateCard,
    Vehicle,
    DestinationCandidate,
    Route,
    RouteStop,
    LogisticsCostBreakdown
)


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            'id',
            'registration_number',
            'vehicle_type',
            'capacity_kg',
            'cost_per_km',
            'base_location',
            'latitude',
            'longitude',
            'is_available',
        ]


class RouteStopSerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source='contribution.farmer.user.full_name', read_only=True, default='')

    class Meta:
        model = RouteStop
        fields = [
            'id',
            'sequence',
            'stop_type',
            'contribution',
            'farmer_name',
            'name',
            'latitude',
            'longitude',
            'quantity_kg',
            'planned_eta',
            'completed_at',
        ]


class RouteSerializer(serializers.ModelSerializer):
    vehicle = VehicleSerializer(read_only=True)
    stops = RouteStopSerializer(many=True, read_only=True)
    lot_code = serializers.CharField(source='lot.lot_code', read_only=True)

    class Meta:
        model = Route
        fields = [
            'id',
            'lot',
            'lot_code',
            'vehicle',
            'total_distance_km',
            'total_duration_hours',
            'total_cost',
            'solver',
            'eta',
            'meets_deadline',
            'status',
            'stops',
            'created_at',
        ]


class DestinationCandidateSerializer(serializers.ModelSerializer):
    buyer_name = serializers.CharField(source='buyer.organisation', read_only=True)
    buyer_type = serializers.CharField(source='buyer.buyer_type', read_only=True)

    class Meta:
        model = DestinationCandidate
        fields = [
            'id',
            'lot',
            'buyer',
            'buyer_name',
            'buyer_type',
            'distance_km',
            'travel_time_hours',
            'gross_price_per_kg',
            'logistics_cost_per_kg',
            'net_return_per_kg',
            'is_feasible',
            'rejection_reason',
            'is_selected',
        ]


class LogisticsCostBreakdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogisticsCostBreakdown
        fields = [
            'id',
            'lot',
            'collection_cost',
            'handling_cost',
            'transport_cost',
            'urgency_cost',
            'total_logistics_cost',
            'direct_cost_comparison',
            'consolidation_saving',
        ]
