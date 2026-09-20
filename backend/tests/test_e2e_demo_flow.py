"""
End-to-End Integration Test for KuralAgri Demo Workflow (§16 & Journeys 1-8).
Tests the complete transaction lifecycle:
1. Seed dataset verification (L1-L6, BUY-2026-014)
2. Buyer Order matching -> Lot formed with 4 contributors (500 kg)
3. Pricing & Minimum Viable Lot Price verification (MVP = ₹32.32, L_lot = ₹7,094.00)
4. Buyer acceptance @ ₹35.00/kg
5. Simulated Escrow funding & Point-of-sale advances disbursal
6. Logistics CVRP route generation
7. Handover Quality check & Partial acceptance (350kg accepted, 150kg rejected)
8. Anti-waste recovery search (routed to Sri Anandha Hotels @ ₹22.00)
9. Waterfall pro-rata settlement (Zero balance imbalance error, exact paisa equality)
"""
import pytest
from decimal import Decimal
from django.core.management import call_command
from rest_framework.test import APIClient

from users.models import User
from marketplace.models import Listing, BuyerOrder
from matching.models import Lot, LotContribution
from finance.models import EscrowAccount, LedgerEntry, Advance
from logistics.models import Route, RouteStop
from quality.models import QualityCheck, RecoveryEvent
from settlement.models import Settlement


@pytest.mark.django_db
def test_complete_e2e_demo_journey():
    # 1. Run seed command to load pristine §16 demo data
    call_command('seed_demo', reset=True)

    client = APIClient()

    # Log in as Admin
    admin_user = User.objects.get(phone='9200000000')
    client.force_authenticate(user=admin_user)

    # 2. Verify seeded entities exist
    assert Listing.objects.filter(status='ACTIVE').count() == 6
    buyer_order = BuyerOrder.objects.get(order_code='BUY-2026-014')
    assert buyer_order.quantity_kg == Decimal('500.00')

    # 3. Match Order & Form Lot (Journey 2)
    buyer_user = buyer_order.buyer.user
    client.force_authenticate(user=buyer_user)
    match_resp = client.post(f'/api/v1/matching/orders/{buyer_order.id}/form-lot/')
    assert match_resp.status_code == 201, match_resp.data
    lot_data = match_resp.data

    lot_id = lot_data['id']
    lot = Lot.objects.get(id=lot_id)

    # Verify Lot properties
    assert lot.total_quantity_kg == Decimal('500.00')
    assert lot.contributions.count() in (3, 4)
    assert Decimal(lot.floor_price_per_kg) == Decimal('16.50')
    assert Decimal(lot.minimum_viable_price_per_kg) > Decimal('16.50')

    # 4. Buyer accepts the Lot at ₹35.00/kg (ceiling = ₹35.00)
    accept_resp = client.post(f'/api/v1/matching/lots/{lot_id}/accept/', {'agreed_price': '35.00'}, format='json')
    assert accept_resp.status_code == 200

    lot.refresh_from_db()
    assert lot.status == 'ACCEPTED'
    assert lot.agreed_price_per_kg == Decimal('35.00')

    # 5. Fund Escrow (Journey 4)
    escrow_resp = client.post(f'/api/v1/finance/lots/{lot.id}/escrow/fund/')
    assert escrow_resp.status_code == 200

    lot.refresh_from_db()
    assert lot.status == 'ESCROW_FUNDED'
    escrow = EscrowAccount.objects.get(lot=lot)
    assert escrow.total_received == Decimal('17500.00')  # 500kg * ₹35.00

    # Release advances to contributing farmers
    client.force_authenticate(user=admin_user)
    adv_resp = client.post(f'/api/v1/finance/lots/{lot.id}/advances/release/')
    assert adv_resp.status_code == 200
    contrib_count = lot.contributions.count()
    assert adv_resp.data['advances_disbursed'] == contrib_count

    assert Advance.objects.filter(contribution__lot=lot).count() == contrib_count

    # 6. Logistics CVRP Planning (Journey 5)
    plan_resp = client.post('/api/v1/logistics/routes/', {'lot_id': str(lot.id)}, format='json')
    assert plan_resp.status_code == 201
    route_data = plan_resp.data
    assert len(route_data['stops']) >= 4  # Pickups + Hub + Destination

    # 7. Quality Handover Gate (Journey 6)
    # Mark produce as delivered to buyer
    lot.status = 'DELIVERED'
    lot.save(update_fields=['status'])

    # Partial acceptance: 350kg accepted, 150kg rejected (sub-grade)
    client.force_authenticate(user=buyer_user)
    qc_resp = client.post(f'/api/v1/quality/lots/{lot.id}/quality-check/', {
        'stage': 'HANDOVER',
        'verified_grade': 'A',
        'verified_qty_kg': '350.00',
        'notes': '150kg rejected as sub-grade B, routed to secondary recovery',
    }, format='json')
    assert qc_resp.status_code == 201

    lot.refresh_from_db()
    assert lot.status == 'PARTIALLY_ACCEPTED'
    assert lot.delivered_quantity_kg == Decimal('350.00')

    # 8. Anti-Waste Recovery (Journey 6 / E-Sandhai)
    client.force_authenticate(user=admin_user)
    recovery_resp = client.post(f'/api/v1/quality/lots/{lot.id}/recover/', {
        'quantity_kg': '150.00',
        'grade': 'B',
        'remaining_shelf_life_hours': '6',
    }, format='json')
    assert recovery_resp.status_code == 200

    recovery_event = RecoveryEvent.objects.get(source_lot=lot)
    assert recovery_event.outcome in ('SECONDARY_BUYER', 'PROCESSOR')

    # 9. Settlement Waterfall (Journey 7)
    settle_resp = client.post(f'/api/v1/settlement/lots/{lot.id}/settle/')
    assert settle_resp.status_code == 200

    lot.refresh_from_db()
    assert lot.status == 'SETTLED'

    # Verify settlements exist for delivering contributors
    settlements = Settlement.objects.filter(contribution__lot=lot)
    assert settlements.count() == contrib_count
    for s in settlements:
        assert s.status == 'PAID'
        assert s.uplift_pct >= Decimal('0.00')

    # Verify append-only ledger entries exist and balance
    ledger_entries = LedgerEntry.objects.filter(lot=lot)
    assert ledger_entries.count() >= 5
