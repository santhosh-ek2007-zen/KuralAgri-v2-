from decimal import Decimal
from django.db import models
from common.models import BaseModel


class Lot(BaseModel):
    """
    Consolidated aggregation of produce contributions from one or more farmers/FPOs,
    fulfilling a bulk buyer order with guaranteed single crop and single grade.
    """
    STATUS_CHOICES = [
        ('PROPOSED', 'Proposed'),
        ('ACCEPTED', 'Accepted'),
        ('ESCROW_FUNDED', 'Escrow Funded'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('ACCEPTED_FULL', 'Accepted in Full'),
        ('PARTIALLY_ACCEPTED', 'Partially Accepted'),
        ('SETTLED', 'Settled'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]

    lot_code = models.CharField(max_length=30, unique=True, db_index=True)
    buyer_order = models.ForeignKey(
        'marketplace.BuyerOrder',
        related_name='lots',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    crop = models.ForeignKey('catalog.Crop', related_name='lots', on_delete=models.PROTECT)
    grade = models.CharField(max_length=10, db_index=True)
    total_quantity_kg = models.DecimalField(max_digits=10, decimal_places=2)
    delivered_quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    floor_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_viable_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    agreed_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    logistics_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='PROPOSED', db_index=True)
    parent_lot = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='recovery_children')
    selected_destination_id = models.UUIDField(null=True, blank=True)
    aggregation_point = models.ForeignKey('catalog.AggregationPoint', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['crop', 'grade', 'status']),
        ]

    def __str__(self):
        return f"{self.lot_code}: {self.total_quantity_kg}kg {self.crop.name} [{self.grade}] ({self.status})"


class LotContribution(BaseModel):
    """
    Individual farmer contribution to a consolidated Lot.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMMITTED', 'Committed'),
        ('COLLECTED', 'Collected'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
        ('SETTLED', 'Settled'),
    ]

    lot = models.ForeignKey(Lot, related_name='contributions', on_delete=models.CASCADE)
    listing = models.ForeignKey('marketplace.Listing', related_name='contributions', on_delete=models.PROTECT, null=True, blank=True)
    farmer = models.ForeignKey('users.FarmerProfile', related_name='contributions', on_delete=models.PROTECT)
    committed_quantity_kg = models.DecimalField(max_digits=10, decimal_places=2)
    delivered_quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    interest_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    lender_claim = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    residual_entitlement = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    match_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Lot {self.lot.lot_code} - {self.farmer.user.full_name} ({self.committed_quantity_kg}kg)"
