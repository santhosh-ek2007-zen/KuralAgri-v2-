from decimal import Decimal
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from users.models import User, FarmerProfile, BuyerProfile
from catalog.models import Crop, Region, PlatformSettings, CropGradeParam
from marketplace.models import Listing, BuyerOrder


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def matching_test_data():
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

    # 4 Farmers per demo scenario: Ravi (120kg), Meena (150kg), Suresh (80kg), Karthik (150kg)
    farmers = [
        ("9000000001", "Ravi Kumar", "Cumbum", 0, Decimal('120.00')),
        ("9000000002", "Meena Lakshmi", "Uthamapalayam", 2, Decimal('150.00')),
        ("9000000003", "Suresh Pandian", "Bodinayakanur", 0, Decimal('80.00')),
        ("9000000004", "Karthik R", "Chinnamanur", 14, Decimal('150.00')),
    ]

    listings = []
    harvest_dt = timezone.now() - timedelta(hours=26)

    for phone, name, village, orders, qty in farmers:
        user = User.objects.create_user(phone=phone, password="DemoPassword123", full_name=name, role="FARMER")
        profile = FarmerProfile.objects.create(
            user=user,
            village=village,
            district="Theni",
            completed_orders=orders,
            latitude=Decimal('9.9457'),
            longitude=Decimal('77.4779')
        )
        listing = Listing.objects.create(
            farmer=profile,
            crop=crop,
            grade="A",
            quantity_kg=qty,
            harvest_datetime=harvest_dt,
            usable_life_hours=Decimal('36.00'),
            village=village,
            district="Theni",
            latitude=Decimal('9.9457'),
            longitude=Decimal('77.4779'),
            status='ACTIVE'
        )
        listing.update_shelf_life()
        listing.save()
        listings.append(listing)

    # Buyer: Theni Fresh Mart
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

    # Buyer order: 500 kg
    order = BuyerOrder.objects.create(
        order_code="BUY-2026-014",
        buyer=buyer_profile,
        crop=crop,
        grade="A",
        quantity_kg=Decimal('500.00'),
        delivery_deadline=timezone.now() + timedelta(days=2),
        max_price_per_kg=Decimal('35.00'),
        sourcing_preference="AGGREGATED",
        allow_partial=True,
        min_acceptable_quantity_kg=Decimal('400.00'),
        delivery_district="Theni",
        delivery_latitude=Decimal('9.9457'),
        delivery_longitude=Decimal('77.4779')
    )

    return {
        "order": order,
        "buyer_user": buyer_user,
        "listings": listings
    }


@pytest.mark.django_db
def test_matching_evaluates_and_allocates_500kg(api_client, matching_test_data):
    api_client.force_authenticate(user=matching_test_data["buyer_user"])
    order = matching_test_data["order"]

    resp = api_client.post(f'/api/v1/matching/orders/{order.id}/match/')
    assert resp.status_code == status.HTTP_200_OK
    data = resp.data

    assert data["is_fulfilled"] is True
    assert Decimal(data["total_allocated_kg"]) == Decimal('500.00')
    assert len(data["contributions"]) == 4


@pytest.mark.django_db
def test_lot_formation_and_acceptance(api_client, matching_test_data):
    api_client.force_authenticate(user=matching_test_data["buyer_user"])
    order = matching_test_data["order"]

    # 1. Form Lot
    resp = api_client.post(f'/api/v1/matching/orders/{order.id}/form-lot/')
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.data

    lot_id = data["id"]
    assert data["lot_code"].startswith("LOT-")
    assert Decimal(data["total_quantity_kg"]) == Decimal('500.00')
    assert Decimal(data["floor_price_per_kg"]) == Decimal('16.50')
    assert Decimal(data["minimum_viable_price_per_kg"]) == Decimal('32.32')
    assert data["status"] == "PROPOSED"

    # 2. Reject acceptance below minimum viable price
    reject_resp = api_client.post(f'/api/v1/matching/lots/{lot_id}/accept/', {"agreed_price": "30.00"}, format='json')
    assert reject_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # 3. Accept at valid agreed price ₹35.00
    accept_resp = api_client.post(f'/api/v1/matching/lots/{lot_id}/accept/', {"agreed_price": "35.00"}, format='json')
    assert accept_resp.status_code == status.HTTP_200_OK
    assert accept_resp.data["status"] == "ACCEPTED"
    assert Decimal(accept_resp.data["agreed_price_per_kg"]) == Decimal('35.00')
