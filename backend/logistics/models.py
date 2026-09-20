from decimal import Decimal
from django.db import models
from common.models import BaseModel


class LogisticsRateCard(BaseModel):
    """Configuration for collection, handling, trunk rates, and speed."""
    code = models.CharField(max_length=50, unique=True, default='PILOT_V1')
    collection_rate_per_kg_km = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('1.20'))
    handling_fee_per_kg = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.30'))
    trunk_tier_1_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.80'))  # <500kg
    trunk_tier_2_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.45'))  # 500-1999kg
    trunk_tier_3_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.25'))  # 2000-4999kg
    trunk_tier_4_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.15'))  # >=5000kg
    safety_buffer_hours = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('2.00'))
    road_distance_factor = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('1.35'))
    average_speed_kmph = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('35.00'))
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"RateCard {self.code}"


class Vehicle(BaseModel):
    """Transport vehicle for rural collection and trunk delivery."""
    VEHICLE_TYPE_CHOICES = [
        ('TEMPO', 'Tempo (up to 600kg)'),
        ('MINI_TRUCK', 'Mini Truck (up to 1,200kg)'),
        ('TRUCK', 'Heavy Truck (up to 3,000kg)'),
    ]
    registration_number = models.CharField(max_length=30, unique=True)
    vehicle_type = models.CharField(max_length=30, choices=VEHICLE_TYPE_CHOICES)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_km = models.DecimalField(max_digits=6, decimal_places=2)
    base_location = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.registration_number} ({self.vehicle_type}, {self.capacity_kg}kg)"


class DestinationCandidate(BaseModel):
    """
    Evaluated prospective destination for a Lot.
    Keeps both feasible and infeasible options for judicial inspection.
    """
    lot = models.ForeignKey('matching.Lot', related_name='destination_candidates', on_delete=models.CASCADE)
    buyer = models.ForeignKey('users.BuyerProfile', on_delete=models.CASCADE)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    travel_time_hours = models.DecimalField(max_digits=6, decimal_places=2)
    gross_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    logistics_cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    net_return_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    is_feasible = models.BooleanField(default=True)
    rejection_reason = models.CharField(max_length=50, null=True, blank=True)  # SHELF_LIFE, CAPACITY, UNECONOMIC, DEADLINE, GRADE
    is_selected = models.BooleanField(default=False)

    class Meta:
        ordering = ['-net_return_per_kg']


class Route(BaseModel):
    """Optimized pickup and trunk delivery route planned by OR-Tools."""
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('DISPATCHED', 'Dispatched'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    lot = models.ForeignKey('matching.Lot', related_name='routes', on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    total_distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    total_duration_hours = models.DecimalField(max_digits=6, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    solver = models.CharField(max_length=40, default='OR_TOOLS')
    eta = models.DateTimeField()
    meets_deadline = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')

    def __str__(self):
        return f"Route {self.id} for Lot {self.lot.lot_code} ({self.status})"


class RouteStop(BaseModel):
    """Waypoints on the route: Pickups, Aggregation Hubs, and Buyer Delivery."""
    STOP_TYPE_CHOICES = [
        ('PICKUP', 'Farmer Pickup'),
        ('AGGREGATION', 'Aggregation Hub Drop'),
        ('DELIVERY', 'Final Buyer Delivery'),
    ]
    route = models.ForeignKey(Route, related_name='stops', on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField()
    stop_type = models.CharField(max_length=20, choices=STOP_TYPE_CHOICES)
    contribution = models.ForeignKey('matching.LotContribution', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=150)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    planned_eta = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['sequence']
        unique_together = ('route', 'sequence')


class LogisticsCostBreakdown(BaseModel):
    """Detailed audit of L_lot components."""
    lot = models.OneToOneField('matching.Lot', related_name='cost_breakdown', on_delete=models.CASCADE)
    collection_cost = models.DecimalField(max_digits=10, decimal_places=2)
    handling_cost = models.DecimalField(max_digits=10, decimal_places=2)
    transport_cost = models.DecimalField(max_digits=10, decimal_places=2)
    urgency_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_logistics_cost = models.DecimalField(max_digits=10, decimal_places=2)
    direct_cost_comparison = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    consolidation_saving = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
