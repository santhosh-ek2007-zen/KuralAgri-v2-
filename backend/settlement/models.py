from decimal import Decimal
from django.db import models
from common.models import BaseModel


class Settlement(BaseModel):
    """
    Final payout record for each delivering contributor in an accepted Lot.
    Records advance, final settlement, total realization, and traditional channel uplift.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Disbursal'),
        ('PAID', 'Settlement Paid'),
        ('FAILED', 'Payment Failed'),
    ]

    contribution = models.OneToOneField(
        'matching.LotContribution',
        related_name='settlement_record',
        on_delete=models.CASCADE
    )
    advance_paid = models.DecimalField(max_digits=12, decimal_places=2)
    settlement_paid = models.DecimalField(max_digits=12, decimal_places=2)
    total_realisation = models.DecimalField(max_digits=12, decimal_places=2)
    traditional_channel_value = models.DecimalField(max_digits=12, decimal_places=2)
    uplift_pct = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PAID')

    def __str__(self):
        return f"Settlement ₹{self.total_realisation} for {self.contribution.farmer.user.full_name} (+{self.uplift_pct}%)"
