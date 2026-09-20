from decimal import Decimal
from django.db import models
from common.models import BaseModel


class MandiPrice(BaseModel):
    """Historical and daily mandi price and arrival observations."""
    crop = models.ForeignKey('catalog.Crop', related_name='mandi_prices', on_delete=models.CASCADE)
    region = models.ForeignKey('catalog.Region', related_name='mandi_prices', on_delete=models.CASCADE)
    modal_price = models.DecimalField(max_digits=10, decimal_places=2)
    min_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_price = models.DecimalField(max_digits=10, decimal_places=2)
    arrivals_kg = models.DecimalField(max_digits=12, decimal_places=2)
    recorded_date = models.DateField(db_index=True)

    class Meta:
        ordering = ['-recorded_date']
        indexes = [
            models.Index(fields=['crop', 'region', 'recorded_date']),
        ]

    def __str__(self):
        return f"{self.crop.name} in {self.region.name} on {self.recorded_date}: ₹{self.modal_price}"


class WeatherSnapshot(BaseModel):
    """Regional weather records and agricultural risk level."""
    RISK_CHOICES = [
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
    ]
    region = models.ForeignKey('catalog.Region', related_name='weather_snapshots', on_delete=models.CASCADE)
    recorded_date = models.DateField(db_index=True)
    condition = models.CharField(max_length=50, default='CLEAR')  # CLEAR, RAIN, HEAVY_RAIN, HEATWAVE
    temperature_c = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('28.00'))
    rainfall_mm = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES, default='LOW')

    class Meta:
        ordering = ['-recorded_date']
        indexes = [
            models.Index(fields=['region', 'recorded_date']),
        ]

    def __str__(self):
        return f"{self.region.name} weather on {self.recorded_date}: {self.condition} ({self.risk_level})"


class DemandHistory(BaseModel):
    """Historical aggregate demand observation."""
    crop = models.ForeignKey('catalog.Crop', related_name='demand_history', on_delete=models.CASCADE)
    region = models.ForeignKey('catalog.Region', related_name='demand_history', on_delete=models.CASCADE)
    recorded_date = models.DateField(db_index=True)
    quantity_demanded_kg = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['-recorded_date']
        indexes = [
            models.Index(fields=['crop', 'region', 'recorded_date']),
        ]

    def __str__(self):
        return f"{self.crop.name} in {self.region.name} on {self.recorded_date}: {self.quantity_demanded_kg}kg"


class MarketSnapshot(BaseModel):
    """Computed state snapshot of market signals for a crop in a region."""
    crop = models.ForeignKey('catalog.Crop', on_delete=models.CASCADE)
    region = models.ForeignKey('catalog.Region', on_delete=models.CASCADE)
    snapshot_date = models.DateField(auto_now_add=True)
    benchmark_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_trend = models.CharField(max_length=20)  # INCREASING, DECREASING, STABLE
    price_change_pct = models.DecimalField(max_digits=6, decimal_places=2)
    supply_signal = models.CharField(max_length=20)  # HIGH, NORMAL, LOW
    demand_signal = models.CharField(max_length=20)  # HIGH, NORMAL, LOW
    weather_risk = models.CharField(max_length=20)   # HIGH, MEDIUM, LOW
    explanation = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at']


class DemandForecast(BaseModel):
    """Computed demand projection."""
    crop = models.ForeignKey('catalog.Crop', on_delete=models.CASCADE)
    region = models.ForeignKey('catalog.Region', on_delete=models.CASCADE)
    forecast_date = models.DateField(auto_now_add=True)
    horizon_days = models.PositiveIntegerField(default=7)
    forecast_quantity_kg = models.DecimalField(max_digits=12, decimal_places=2)
    daily_average_kg = models.DecimalField(max_digits=10, decimal_places=2)
    per_day_series = models.JSONField(default=list, blank=True)
    demand_level = models.CharField(max_length=20)  # HIGH, NORMAL, LOW
    confidence = models.CharField(max_length=20)    # HIGH, MEDIUM, LOW
    explanation = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at']


class PriceRecommendation(BaseModel):
    """Computed price guidance with complete factors for explainability."""
    crop = models.ForeignKey('catalog.Crop', on_delete=models.CASCADE)
    grade = models.CharField(max_length=10)
    region = models.ForeignKey('catalog.Region', on_delete=models.CASCADE)
    listing = models.ForeignKey('marketplace.Listing', on_delete=models.CASCADE, null=True, blank=True)
    lot = models.ForeignKey('matching.Lot', on_delete=models.CASCADE, null=True, blank=True)
    recommended_min = models.DecimalField(max_digits=10, decimal_places=2)
    recommended_max = models.DecimalField(max_digits=10, decimal_places=2)
    benchmark_price = models.DecimalField(max_digits=10, decimal_places=2)
    floor_price = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_viable_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    buyer_ceiling = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    confidence = models.CharField(max_length=20)
    explanation = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
