from decimal import Decimal
from django.db import models
from common.models import BaseModel


class QualityCheck(BaseModel):
    """
    Intake or handover quality inspection record.
    Gates consolidation and triggers settlement or rejection recovery.
    """
    STAGE_CHOICES = [
        ('INTAKE', 'Farmer Intake Collection'),
        ('HANDOVER', 'Buyer Handover Inspection'),
    ]
    REJECTION_REASON_CHOICES = [
        ('GRADE_MISMATCH', 'Grade Specification Mismatch'),
        ('QUANTITY_SHORT', 'Quantity Shortfall / Deficit'),
        ('SPOILAGE', 'Spoilage / Visible Decay'),
        ('OTHER', 'Other Inspection Failure'),
    ]

    lot = models.ForeignKey('matching.Lot', related_name='quality_checks', on_delete=models.CASCADE)
    contribution = models.ForeignKey(
        'matching.LotContribution',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='quality_checks'
    )
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    declared_grade = models.CharField(max_length=10)
    verified_grade = models.CharField(max_length=10)
    declared_qty_kg = models.DecimalField(max_digits=10, decimal_places=2)
    verified_qty_kg = models.DecimalField(max_digits=10, decimal_places=2)
    accepted_qty_kg = models.DecimalField(max_digits=10, decimal_places=2)
    rejected_qty_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    rejection_reason = models.CharField(max_length=40, choices=REJECTION_REASON_CHOICES, null=True, blank=True)
    photo_url = models.CharField(max_length=500, null=True, blank=True)
    checked_by = models.ForeignKey('users.User', on_delete=models.PROTECT)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.stage} check for Lot {self.lot.lot_code}: accepted {self.accepted_qty_kg}kg, rejected {self.rejected_qty_kg}kg"


class RecoveryEvent(BaseModel):
    """
    Tracks produce rescued from post-harvest waste or buyer rejection.
    Matches rejected produce to secondary buyers or processors.
    """
    TRIGGER_CHOICES = [
        ('BUYER_REJECTION', 'Buyer Rejection at Handover'),
        ('GRADE_DOWNGRADE', 'Intake Grade Downgrade'),
        ('NO_PREMIUM_BUYER', 'No Premium Buyer Found Before Shelf-Life Expiry'),
    ]
    OUTCOME_CHOICES = [
        ('SECONDARY_BUYER', 'Sold to Secondary Market / Buyer'),
        ('PROCESSOR', 'Sold to Food Processing Unit'),
        ('WASTE', 'Physical Spoilage / Waste'),
        ('PENDING', 'Pending Recovery Match'),
    ]

    source_lot = models.ForeignKey('matching.Lot', related_name='recovery_source_events', on_delete=models.CASCADE)
    recovery_lot = models.ForeignKey('matching.Lot', null=True, blank=True, on_delete=models.SET_NULL, related_name='recovery_events')
    trigger = models.CharField(max_length=30, choices=TRIGGER_CHOICES)
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2)
    original_value = models.DecimalField(max_digits=12, decimal_places=2)
    recovered_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    outcome = models.CharField(max_length=30, choices=OUTCOME_CHOICES, default='PENDING')
    remaining_shelf_life_hours = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"Recovery {self.trigger}: {self.quantity_kg}kg -> {self.outcome} (₹{self.recovered_value})"
