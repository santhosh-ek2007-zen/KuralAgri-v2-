from decimal import Decimal
from django.db import models
from django.utils import timezone
from common.models import BaseModel


class Listing(BaseModel):
    """
    Produce supply offered by a farmer or FPO.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('RESERVED', 'Reserved'),
        ('IN_LOT', 'In Lot'),
        ('COLLECTED', 'Collected'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    ]

    farmer = models.ForeignKey('users.FarmerProfile', related_name='listings', on_delete=models.CASCADE)
    crop = models.ForeignKey('catalog.Crop', related_name='listings', on_delete=models.PROTECT)
    grade = models.CharField(max_length=10, db_index=True)
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2)
    reserved_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    harvest_datetime = models.DateTimeField()
    usable_life_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('36.00'))
    remaining_shelf_life_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    village = models.CharField(max_length=100)
    district = models.CharField(max_length=100, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    self_delivery = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['crop', 'grade', 'status']),
            models.Index(fields=['district', 'status']),
        ]

    def __str__(self):
        return f"{self.farmer.user.full_name}: {self.quantity_kg}kg {self.crop.name} [{self.grade}] ({self.status})"

    @property
    def available_kg(self) -> Decimal:
        return max(Decimal('0.00'), self.quantity_kg - self.reserved_kg)

    def update_shelf_life(self):
        """Compute remaining shelf life = usable_life_hours - hours_since_harvest."""
        now = timezone.now()
        elapsed_hours = Decimal(str((now - self.harvest_datetime).total_seconds() / 3600.0))
        remaining = self.usable_life_hours - elapsed_hours
        self.remaining_shelf_life_hours = max(Decimal('0.00'), remaining)
        if self.remaining_shelf_life_hours <= Decimal('0.00') and self.status == 'ACTIVE':
            self.status = 'EXPIRED'
        return self.remaining_shelf_life_hours


class BuyerOrder(BaseModel):
    """
    Bulk demand requirement posted by a buyer.
    """
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('MATCHED', 'Matched'),
        ('FULFILLED', 'Fulfilled'),
        ('CANCELLED', 'Cancelled'),
    ]

    order_code = models.CharField(max_length=30, unique=True, db_index=True)
    buyer = models.ForeignKey('users.BuyerProfile', related_name='orders', on_delete=models.CASCADE)
    crop = models.ForeignKey('catalog.Crop', related_name='orders', on_delete=models.PROTECT)
    grade = models.CharField(max_length=10, db_index=True)
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_deadline = models.DateTimeField()
    max_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sourcing_preference = models.CharField(
        max_length=20,
        choices=[('SINGLE_SOURCE', 'Single Source'), ('AGGREGATED', 'Aggregated')],
        default='AGGREGATED'
    )
    allow_partial = models.BooleanField(default=False)
    min_acceptable_quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    delivery_district = models.CharField(max_length=100)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_code}: {self.quantity_kg}kg {self.crop.name} [{self.grade}] for {self.buyer.organisation}"
