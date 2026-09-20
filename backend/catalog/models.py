from decimal import Decimal
from django.db import models
from common.models import BaseModel


class Crop(BaseModel):
    """
    Agricultural commodities traded on the KuralAgri platform (§16.1).
    """
    CATEGORY_CHOICES = [
        ('VEGETABLE', 'Vegetable'),
        ('FRUIT', 'Fruit'),
        ('GRAIN', 'Grain'),
        ('PULSE', 'Pulse'),
        ('SPICE', 'Spice'),
    ]

    name = models.CharField(max_length=100, unique=True, db_index=True)
    scientific_name = models.CharField(max_length=150, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='VEGETABLE')
    msp_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    markdown_factor = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.60'))
    perishability_class = models.CharField(max_length=10, default='A')  # A, B, C
    usable_life_hours = models.PositiveIntegerField(default=36)
    urgency_rate_per_kg = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.40'))
    retail_markup = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.65'))
    days_to_sell = models.PositiveIntegerField(default=2)
    default_shelf_life_days = models.PositiveIntegerField(default=7)
    min_shelf_life_days = models.PositiveIntegerField(default=2)
    storage_conditions = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CropGradeParam(BaseModel):
    """
    Defines grading parameters (Grade A, B, C) for a given crop.
    """
    GRADE_CHOICES = [
        ('A', 'Grade A'),
        ('B', 'Grade B'),
        ('C', 'Grade C'),
    ]

    crop = models.ForeignKey(Crop, related_name='grade_params', on_delete=models.CASCADE)
    grade = models.CharField(max_length=10, choices=GRADE_CHOICES, db_index=True)
    param_name = models.CharField(max_length=100)  # e.g., 'size_mm', 'brix', 'defect_pct_max'
    min_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ('crop', 'grade', 'param_name')
        ordering = ['crop', 'grade', 'param_name']

    def __str__(self):
        return f"{self.crop.name} - Grade {self.grade} - {self.param_name}"


class Region(BaseModel):
    """
    Geographical growing and distribution region.
    """
    name = models.CharField(max_length=100, unique=True)
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    climate_zone = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['state', 'district', 'name']

    def __str__(self):
        return f"{self.name} ({self.district}, {self.state})"


class AggregationPoint(BaseModel):
    """
    Physical hub/depot where farmers drop off produce and lots are aggregated.
    """
    name = models.CharField(max_length=150)
    region = models.ForeignKey(Region, related_name='aggregation_points', on_delete=models.PROTECT)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    capacity_mt = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('100.00'))
    handling_rate_per_kg = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.30'))
    has_cold_storage = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.region.name}"


class RateCard(BaseModel):
    """
    Standard reference price card per crop, grade, and effective date.
    """
    crop = models.ForeignKey(Crop, related_name='rate_cards', on_delete=models.PROTECT)
    grade = models.CharField(max_length=10, choices=CropGradeParam.GRADE_CHOICES)
    base_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField(db_index=True)
    is_current = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['crop', 'grade', 'is_current']),
        ]

    def __str__(self):
        return f"{self.crop.name} [{self.grade}] @ ₹{self.base_price_per_kg}/kg"


class AdvanceTier(BaseModel):
    """
    Tiered configuration for farmer advance disbursals based on completed orders / rating.
    """
    code = models.CharField(max_length=20, default='NEW', db_index=True)
    min_completed_orders = models.PositiveIntegerField(default=0)
    max_completed_orders = models.PositiveIntegerField(default=0)
    fpo_rating_min = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    fpo_rating_max = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('5.00'))
    max_advance_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('50.00'))  # e.g., 50.00 for 50%
    interest_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('27.00'))  # e.g., 27.00 for 27%

    class Meta:
        ordering = ['min_completed_orders']

    def __str__(self):
        return f"Tier {self.code} [{self.min_completed_orders}-{self.max_completed_orders} orders]: max {self.max_advance_pct}%, {self.interest_rate_pct}% interest"


class PlatformSettings(BaseModel):
    """
    Singleton system parameters: platform fee %, risk reserve %, floor discount %, advance max tenure (§16.1).
    """
    platform_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('4.00'))
    risk_reserve_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.00'))
    platform_commission_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0400'))
    risk_reserve_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0100'))
    floor_premium = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.10'))
    ceiling_discount = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.85'))
    reserve_default_cover_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.40'))
    floor_price_discount_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('15.00'))
    advance_tenure_days_max = models.PositiveIntegerField(default=14)
    demo_mode = models.BooleanField(default=True)

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(
            id='00000000-0000-0000-0000-000000000001',
            defaults={
                'platform_fee_pct': Decimal('4.00'),
                'risk_reserve_pct': Decimal('1.00'),
                'platform_commission_rate': Decimal('0.0400'),
                'risk_reserve_rate': Decimal('0.0100'),
                'floor_premium': Decimal('1.10'),
                'ceiling_discount': Decimal('0.85'),
                'reserve_default_cover_rate': Decimal('0.40'),
                'floor_price_discount_pct': Decimal('15.00'),
                'advance_tenure_days_max': 14,
                'demo_mode': True,
            }
        )
        return obj

    def __str__(self):
        return f"PlatformSettings(Fee={self.platform_fee_pct}%, Reserve={self.risk_reserve_pct}%)"
