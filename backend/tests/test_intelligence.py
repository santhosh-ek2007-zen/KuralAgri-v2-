from decimal import Decimal
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from catalog.models import Crop, Region, PlatformSettings, CropGradeParam
from intelligence.models import MandiPrice, WeatherSnapshot, DemandHistory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def intelligence_data():
    PlatformSettings.get_settings()
    region = Region.objects.create(name="Theni", state="Tamil Nadu", district="Theni")
    crop = Crop.objects.create(
        name="Tomato",
        category="VEGETABLE",
        default_shelf_life_days=7,
        min_shelf_life_days=2
    )
    CropGradeParam.objects.create(
        crop=crop,
        grade="A",
        param_name="size_mm",
        min_value=Decimal('50.00'),
        max_value=Decimal('80.00')
    )

    # Seed 30 days of mandi prices with >5% jump in the final 7 days (e.g., ₹22.00 -> ₹25.00)
    today = timezone.now().date()
    for i in range(30):
        d = today - timedelta(days=29 - i)
        # First 20 days at 22.00, last 7 days at 25.00
        price = Decimal('25.00') if i >= 23 else Decimal('22.00')
        MandiPrice.objects.create(
            crop=crop,
            region=region,
            modal_price=price,
            min_price=price - Decimal('2.00'),
            max_price=price + Decimal('2.00'),
            arrivals_kg=Decimal('1000.00'),
            recorded_date=d
        )

    # Weather: HEAVY_RAIN / HIGH risk
    WeatherSnapshot.objects.create(
        region=region,
        recorded_date=today,
        condition="HEAVY_RAIN",
        temperature_c=Decimal('26.00'),
        rainfall_mm=Decimal('45.00'),
        risk_level="HIGH"
    )

    # 30 days demand history
    for i in range(30):
        d = today - timedelta(days=29 - i)
        DemandHistory.objects.create(
            crop=crop,
            region=region,
            recorded_date=d,
            quantity_demanded_kg=Decimal('1200.00')
        )

    return {"crop": crop, "region": region}


@pytest.mark.django_db
def test_market_intelligence_api(api_client, intelligence_data):
    crop = intelligence_data["crop"]
    region = intelligence_data["region"]

    resp = api_client.get(f'/api/v1/intelligence/market/?crop={crop.id}&region={region.id}')
    assert resp.status_code == status.HTTP_200_OK
    data = resp.data

    assert Decimal(data["benchmark_price"]) == Decimal('25.00')
    assert data["price_trend"] == "INCREASING"
    assert data["weather_risk"] == "HIGH"


@pytest.mark.django_db
def test_demand_forecast_api(api_client, intelligence_data):
    crop = intelligence_data["crop"]
    region = intelligence_data["region"]

    payload = {
        "crop": str(crop.id),
        "region": str(region.id),
        "horizon_days": 7
    }
    resp = api_client.post('/api/v1/intelligence/forecast/', payload, format='json')
    assert resp.status_code == status.HTTP_200_OK
    data = resp.data

    assert data["horizon_days"] == 7
    assert Decimal(data["forecast_quantity_kg"]) > Decimal('5000.00')
    assert len(data["per_day_series"]) == 7
    assert len(data["explanation"]) > 0


@pytest.mark.django_db
def test_price_recommendation_api(api_client, intelligence_data):
    crop = intelligence_data["crop"]
    region = intelligence_data["region"]

    payload = {
        "crop": str(crop.id),
        "grade": "A",
        "region": str(region.id),
        "quantity_kg": "500.00",
        "buyer_ceiling": "35.00"
    }
    resp = api_client.post('/api/v1/intelligence/price-recommendation/', payload, format='json')
    assert resp.status_code == status.HTTP_200_OK
    data = resp.data

    assert Decimal(data["benchmark_price"]) == Decimal('25.00')
    assert Decimal(data["floor_price"]) == Decimal('16.50')
    assert Decimal(data["recommended_min"]) >= Decimal('16.50')
    assert Decimal(data["recommended_max"]) <= Decimal('35.00')
    assert len(data["explanation"]) > 0
