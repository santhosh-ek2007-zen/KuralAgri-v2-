from decimal import Decimal
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from users.models import User, FarmerProfile, BuyerProfile
from catalog.models import Crop, Region, PlatformSettings, CropGradeParam


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_data():
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

    farmer_user = User.objects.create_user(
        phone="9000000001",
        password="DemoPassword123",
        full_name="Ravi Kumar",
        role="FARMER"
    )
    farmer_profile = FarmerProfile.objects.create(
        user=farmer_user,
        village="Cumbum",
        district="Theni",
        latitude=Decimal('9.7345'),
        longitude=Decimal('77.2876')
    )

    buyer_user = User.objects.create_user(
        phone="9100000001",
        password="DemoPassword123",
        full_name="Theni Fresh Mart",
        role="BUYER"
    )
    buyer_profile = BuyerProfile.objects.create(
        user=buyer_user,
        organisation="Theni Fresh Mart",
        buyer_type="PREMIUM",
        accepted_grades=["A"],
        daily_capacity_kg=Decimal('2000.00'),
        district="Theni",
        latitude=Decimal('9.9457'),
        longitude=Decimal('77.4779')
    )

    return {
        "region": region,
        "crop": crop,
        "farmer_user": farmer_user,
        "farmer_profile": farmer_profile,
        "buyer_user": buyer_user,
        "buyer_profile": buyer_profile
    }


@pytest.mark.django_db
def test_create_listing_with_price_intelligence(api_client, test_data):
    api_client.force_authenticate(user=test_data["farmer_user"])

    harvest_dt = (timezone.now() - timedelta(hours=26)).isoformat()
    payload = {
        "crop": str(test_data["crop"].id),
        "grade": "A",
        "quantity_kg": "120.00",
        "harvest_datetime": harvest_dt,
        "usable_life_hours": "36.00",
        "village": "Cumbum",
        "district": "Theni",
        "latitude": "9.7345",
        "longitude": "77.2876",
        "self_delivery": False
    }

    response = api_client.post('/api/v1/marketplace/listings/', payload, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    data = response.data

    assert data["grade"] == "A"
    assert Decimal(data["quantity_kg"]) == Decimal('120.00')
    # Usable life was 36h, elapsed is 26h -> remaining shelf life should be ~10h
    remaining_shelf_life = Decimal(str(data["remaining_shelf_life_hours"]))
    assert Decimal('9.5') <= remaining_shelf_life <= Decimal('10.5')

    # Verify price recommendation is auto-attached with explainability
    rec = data["price_recommendation"]
    assert rec is not None
    assert Decimal(rec["floor_price"]) == Decimal('16.50')
    assert len(rec["explanation"]) > 0


@pytest.mark.django_db
def test_buyer_order_creation(api_client, test_data):
    api_client.force_authenticate(user=test_data["buyer_user"])

    deadline = (timezone.now() + timedelta(days=2)).isoformat()
    payload = {
        "crop": str(test_data["crop"].id),
        "grade": "A",
        "quantity_kg": "500.00",
        "delivery_deadline": deadline,
        "max_price_per_kg": "35.00",
        "sourcing_preference": "AGGREGATED",
        "allow_partial": True,
        "min_acceptable_quantity_kg": "400.00",
        "delivery_district": "Theni",
        "delivery_latitude": "9.9457",
        "delivery_longitude": "77.4779"
    }

    response = api_client.post('/api/v1/marketplace/buyer-orders/', payload, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    data = response.data
    assert data["order_code"].startswith("BUY-")
    assert Decimal(data["quantity_kg"]) == Decimal('500.00')
    assert data["status"] == "OPEN"
