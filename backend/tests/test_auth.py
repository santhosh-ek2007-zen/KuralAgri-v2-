import pytest
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User, FarmerProfile, BuyerProfile
from common.models import AuditLog


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_register_farmer(api_client):
    payload = {
        "phone": "9876543210",
        "password": "StrongPassword123",
        "full_name": "Ravi Kumar",
        "role": "FARMER",
        "profile": {
            "village": "Cumbum",
            "district": "Theni",
            "latitude": "9.7345",
            "longitude": "77.2876",
            "self_delivery_capable": False
        }
    }
    response = api_client.post('/api/v1/auth/register/', payload, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    data = response.data
    assert "access" in data
    assert "refresh" in data
    assert data["user"]["phone"] == "9876543210"
    assert data["user"]["role"] == "FARMER"
    assert data["user"]["farmer_profile"]["village"] == "Cumbum"

    # Verify audit log
    audit = AuditLog.objects.filter(action="AUTH_REGISTER", entity_type="User").first()
    assert audit is not None
    assert audit.user_email is None or audit.user_email == ''


@pytest.mark.django_db
def test_register_buyer(api_client):
    payload = {
        "phone": "9100000001",
        "password": "StrongPassword123",
        "full_name": "Theni Fresh Mart",
        "role": "BUYER",
        "profile": {
            "organisation": "Theni Fresh Mart",
            "buyer_type": "PREMIUM",
            "accepted_grades": ["A"],
            "daily_capacity_kg": "2000.00",
            "district": "Theni",
            "latitude": "9.9457",
            "longitude": "77.4779"
        }
    }
    response = api_client.post('/api/v1/auth/register/', payload, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    data = response.data
    assert data["user"]["buyer_profile"]["organisation"] == "Theni Fresh Mart"


@pytest.mark.django_db
def test_duplicate_phone_rejected(api_client):
    payload = {
        "phone": "9876543210",
        "password": "StrongPassword123",
        "full_name": "Ravi Kumar",
        "role": "FARMER"
    }
    r1 = api_client.post('/api/v1/auth/register/', payload, format='json')
    assert r1.status_code == status.HTTP_201_CREATED

    r2 = api_client.post('/api/v1/auth/register/', payload, format='json')
    assert r2.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in r2.data


@pytest.mark.django_db
def test_login_success_and_me_endpoint(api_client):
    user = User.objects.create_user(
        phone="9000000001",
        password="DemoPassword123",
        full_name="Meena Lakshmi",
        role="FARMER"
    )
    FarmerProfile.objects.create(
        user=user,
        village="Uthamapalayam",
        district="Theni",
        latitude=9.9252,
        longitude=78.1198
    )

    login_resp = api_client.post('/api/v1/auth/login/', {
        "phone": "9000000001",
        "password": "DemoPassword123"
    }, format='json')
    assert login_resp.status_code == status.HTTP_200_OK
    token = login_resp.data["access"]
    refresh = login_resp.data["refresh"]

    # Verify /auth/me/
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    me_resp = api_client.get('/api/v1/auth/me/')
    assert me_resp.status_code == status.HTTP_200_OK
    assert me_resp.data["full_name"] == "Meena Lakshmi"

    # Verify logout blacklisting
    logout_resp = api_client.post('/api/v1/auth/logout/', {"refresh": refresh}, format='json')
    assert logout_resp.status_code == status.HTTP_204_NO_CONTENT
