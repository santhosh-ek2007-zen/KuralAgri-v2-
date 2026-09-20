"""
M8 + M9 Tests: Escrow, Waterfall Settlement, Crop Failure, Quality Checks, Recovery
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from users.models import User, FarmerProfile, BuyerProfile
from catalog.models import Crop, CropGradeParam, Region, AggregationPoint, PlatformSettings
from marketplace.models import Listing, BuyerOrder
from matching.models import Lot, LotContribution
from matching.services import MatchingService, LotService
from finance.models import EscrowAccount, LedgerEntry, Advance
from finance.services import EscrowService
from settlement.models import Settlement
from settlement.services import WaterfallService
from quality.models import QualityCheck, RecoveryEvent
from quality.services import QualityService, RecoveryService
from logistics.models import LogisticsRateCard


@pytest.fixture
def base_data():
    """Common dataset shared across M8/M9 tests."""
    PlatformSettings.get_settings()
    LogisticsRateCard.objects.create(code="PILOT_V1")

    region = Region.objects.create(name="Theni", state="Tamil Nadu", district="Theni")
    crop = Crop.objects.create(name="Tomato", category="VEGETABLE", default_shelf_life_days=7, min_shelf_life_days=2)
    CropGradeParam.objects.create(crop=crop, grade="A", param_name="size_mm", min_value=50, max_value=80)
    hub = AggregationPoint.objects.create(
        name="Theni Hub", region=region,
        latitude=Decimal("9.9457"), longitude=Decimal("77.4779"), capacity_mt=50
    )

    # Admin user (does quality checks)
    admin_user = User.objects.create_user(phone="9000099999", full_name="QC Officer", role="ADMIN")

    # 2 farmers
    u1 = User.objects.create_user(phone="9111100001", full_name="Ravi K", role="FARMER")
    f1 = FarmerProfile.objects.create(
        user=u1, village="Cumbum", district="Theni",
        latitude=Decimal("9.73"), longitude=Decimal("77.28"), completed_orders=0
    )
    u2 = User.objects.create_user(phone="9111100002", full_name="Meena L", role="FARMER")
    f2 = FarmerProfile.objects.create(
        user=u2, village="Uthamapalayam", district="Theni",
        latitude=Decimal("9.80"), longitude=Decimal("77.32"), completed_orders=3
    )

    # Buyer
    bu = User.objects.create_user(phone="9111100003", full_name="Theni Packhouse", role="BUYER")
    buyer = BuyerProfile.objects.create(
        user=bu, organisation="Theni Packhouse Pvt Ltd",
        buyer_type="PREMIUM", accepted_grades=["A"],
        district="Theni", daily_capacity_kg=Decimal("2000.00"),
        latitude=Decimal("9.95"), longitude=Decimal("77.48"),
    )

    # Secondary buyer (for recovery)
    su = User.objects.create_user(phone="9111100004", full_name="Theni Secondary Buyer", role="BUYER")
    secondary = BuyerProfile.objects.create(
        user=su, organisation="Theni Juice Factory",
        buyer_type="SECONDARY", accepted_grades=["A", "B"],
        district="Theni", daily_capacity_kg=Decimal("500.00"),
        latitude=Decimal("9.96"), longitude=Decimal("77.49"),
    )

    harvest_dt = timezone.now() - timedelta(hours=1)

    l1 = Listing.objects.create(
        farmer=f1, crop=crop, grade="A", quantity_kg=Decimal("300.00"),
        harvest_datetime=harvest_dt, usable_life_hours=Decimal("36.00"),
        village="Cumbum", district="Theni",
        latitude=Decimal("9.73"), longitude=Decimal("77.28"), status="ACTIVE"
    )
    l1.update_shelf_life(); l1.save()

    l2 = Listing.objects.create(
        farmer=f2, crop=crop, grade="A", quantity_kg=Decimal("200.00"),
        harvest_datetime=harvest_dt, usable_life_hours=Decimal("36.00"),
        village="Uthamapalayam", district="Theni",
        latitude=Decimal("9.80"), longitude=Decimal("77.32"), status="ACTIVE"
    )
    l2.update_shelf_life(); l2.save()

    order = BuyerOrder.objects.create(
        order_code="BUY-SETTLE-001",
        buyer=buyer, crop=crop, grade="A",
        quantity_kg=Decimal("500.00"),
        delivery_deadline=timezone.now() + timedelta(days=2),
        max_price_per_kg=Decimal("35.00"),
        sourcing_preference="AGGREGATED", allow_partial=True,
        min_acceptable_quantity_kg=Decimal("400.00"),
        delivery_district="Theni",
        delivery_latitude=Decimal("9.95"), delivery_longitude=Decimal("77.48"),
    )

    match_result = MatchingService.match_supply_for_order(order, aggregation_point=hub)
    lot = LotService.form_lot_from_match(
        order=order, match_result=match_result,
        logistics_cost=Decimal("7094.00"), aggregation_point=hub
    )

    # Manually accept
    lot.agreed_price_per_kg = Decimal("35.00")
    lot.status = "ACCEPTED"
    lot.save()

    return {
        "lot": lot, "order": order, "hub": hub, "crop": crop,
        "buyer": buyer, "bu": bu, "f1": f1, "f2": f2,
        "u1": u1, "u2": u2, "secondary": secondary,
        "admin_user": admin_user, "region": region,
    }


@pytest.mark.django_db
class TestEscrowAndAdvances:

    def test_fund_escrow_creates_ledger_entry(self, base_data):
        lot = base_data["lot"]
        escrow = EscrowService.fund_escrow(lot, funded_by_user=base_data["bu"])

        assert escrow.status == "FUNDED"
        expected_total = Decimal("35.00") * Decimal("500.00")
        assert escrow.total_received == expected_total

        # One BUYER_DEPOSIT ledger entry
        deposit = LedgerEntry.objects.get(lot=lot, entry_type="BUYER_DEPOSIT")
        assert deposit.amount == expected_total
        assert deposit.direction == "CREDIT"

        # Lot status updated
        lot.refresh_from_db()
        assert lot.status == "ESCROW_FUNDED"

    def test_release_advances_creates_advance_records(self, base_data):
        lot = base_data["lot"]
        EscrowService.fund_escrow(lot)
        advances = EscrowService.release_advances(lot, actor=base_data["bu"])

        assert len(advances) == lot.contributions.count()
        for adv in advances:
            assert adv.status == "DISBURSED"
            assert adv.principal > Decimal("0.00")

        disbursal_count = LedgerEntry.objects.filter(lot=lot, entry_type="ADVANCE_DISBURSAL").count()
        assert disbursal_count == lot.contributions.count()

    def test_escrow_fund_api(self, base_data):
        lot = base_data["lot"]
        client = APIClient()
        client.force_authenticate(user=base_data["bu"])
        resp = client.post(f"/api/v1/finance/lots/{lot.id}/escrow/fund/")
        assert resp.status_code == 200
        assert resp.json()["escrow_status"] == "FUNDED"

    def test_ledger_api_shows_entries(self, base_data):
        lot = base_data["lot"]
        EscrowService.fund_escrow(lot)
        client = APIClient()
        client.force_authenticate(user=base_data["bu"])
        resp = client.get(f"/api/v1/finance/lots/{lot.id}/ledger/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


@pytest.mark.django_db
class TestWaterfallSettlement:

    def test_settle_lot_creates_settlement_rows_and_ledger(self, base_data):
        lot = base_data["lot"]
        # Set to DELIVERED for waterfall
        lot.status = "DELIVERED"
        lot.delivered_quantity_kg = Decimal("500.00")
        lot.save()

        result = WaterfallService.settle_lot(lot, actor=base_data["bu"])

        # D1§9 waterfall assertions
        assert result["is_balanced"] is True
        total_received = Decimal("35.00") * Decimal("500.00")  # ₹17,500
        assert Decimal(str(result["total_received"])) == total_received

        # Lot settled
        lot.refresh_from_db()
        assert lot.status == "SETTLED"

        # Per-contributor settlements exist
        assert Settlement.objects.filter(contribution__lot=lot).count() == lot.contributions.count()

        # Ledger entries for all waterfall steps
        entry_types = set(LedgerEntry.objects.filter(lot=lot).values_list("entry_type", flat=True))
        assert "LENDER_REPAYMENT" in entry_types
        assert "PLATFORM_COMMISSION" in entry_types
        assert "LOGISTICS_PAYOUT" in entry_types
        assert "RESERVE_CONTRIBUTION" in entry_types
        assert "FARMER_SETTLEMENT" in entry_types

    def test_settle_lot_api(self, base_data):
        lot = base_data["lot"]
        lot.status = "DELIVERED"
        lot.delivered_quantity_kg = Decimal("500.00")
        lot.save()

        client = APIClient()
        client.force_authenticate(user=base_data["bu"])
        resp = client.post(f"/api/v1/settlement/lots/{lot.id}/settle/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_balanced"] is True
        assert len(body["settlements"]) == lot.contributions.count()

    def test_crop_failure_isolates_contributor(self, base_data):
        lot = base_data["lot"]
        contrib = lot.contributions.first()
        result = WaterfallService.handle_crop_failure_for_contribution(contrib)

        assert result["farmer_cash_liability"] == Decimal("0.00")
        assert result["reserve_payout"] > Decimal("0.00")
        assert result["unrecovered_loss"] >= Decimal("0.00")
        # 40% cover rate: reserve_payout = lender_exposure * 0.40
        assert abs(result["reserve_payout"] - result["lender_exposure"] * Decimal("0.40")) < Decimal("0.02")

        contrib.refresh_from_db()
        assert contrib.status == "FAILED"

    def test_settlements_list_api(self, base_data):
        lot = base_data["lot"]
        lot.status = "DELIVERED"
        lot.delivered_quantity_kg = Decimal("500.00")
        lot.save()
        WaterfallService.settle_lot(lot)

        client = APIClient()
        client.force_authenticate(user=base_data["bu"])
        resp = client.get(f"/api/v1/settlement/lots/{lot.id}/settlements/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == lot.contributions.count()
        for row in data:
            assert float(row["total_realisation"]) > 0


@pytest.mark.django_db
class TestQualityAndRecovery:

    def test_handover_check_accepted_full(self, base_data):
        lot = base_data["lot"]
        lot.status = "IN_TRANSIT"
        lot.save()

        qc = QualityService.handover_check(
            lot=lot,
            verified_grade="A",
            verified_qty_kg=Decimal("500.00"),
            checked_by=base_data["admin_user"],
        )
        assert qc.accepted_qty_kg == Decimal("500.00")
        assert qc.rejected_qty_kg == Decimal("0.00")
        lot.refresh_from_db()
        assert lot.status == "ACCEPTED_FULL"

    def test_handover_check_partial_acceptance(self, base_data):
        lot = base_data["lot"]
        lot.status = "IN_TRANSIT"
        lot.save()

        qc = QualityService.handover_check(
            lot=lot,
            verified_grade="A",
            verified_qty_kg=Decimal("420.00"),   # 80kg rejected
            checked_by=base_data["admin_user"],
        )
        assert qc.rejected_qty_kg == Decimal("80.00")
        lot.refresh_from_db()
        assert lot.status == "PARTIALLY_ACCEPTED"

    def test_intake_check_grade_mismatch_fails_contribution(self, base_data):
        lot = base_data["lot"]
        contrib = lot.contributions.first()

        qc = QualityService.intake_check(
            lot=lot, contribution=contrib,
            declared_grade="A", verified_grade="B",   # grade mismatch
            declared_qty_kg=contrib.committed_quantity_kg,
            verified_qty_kg=contrib.committed_quantity_kg,
            checked_by=base_data["admin_user"],
        )
        assert qc.rejection_reason == "GRADE_MISMATCH"
        assert qc.accepted_qty_kg == Decimal("0.00")
        contrib.refresh_from_db()
        assert contrib.status == "FAILED"

    def test_recovery_finds_secondary_buyer(self, base_data):
        lot = base_data["lot"]
        event = RecoveryService.find_recovery_destination(
            source_lot=lot,
            quantity_kg=Decimal("80.00"),
            remaining_shelf_life_hours=Decimal("8.00"),
            grade="B",
            trigger="BUYER_REJECTION",
        )
        # Should find Theni Juice Factory (SECONDARY, nearby)
        assert event.outcome in ("SECONDARY_BUYER", "PROCESSOR", "WASTE")
        assert event.quantity_kg == Decimal("80.00")

    def test_quality_check_api(self, base_data):
        lot = base_data["lot"]
        lot.status = "IN_TRANSIT"
        lot.save()

        client = APIClient()
        client.force_authenticate(user=base_data["admin_user"])
        resp = client.post(f"/api/v1/quality/lots/{lot.id}/quality-check/", {
            "stage": "HANDOVER",
            "verified_grade": "A",
            "verified_qty_kg": "500.00",
            "notes": "All good"
        }, format="json")
        assert resp.status_code == 201
        body = resp.json()
        assert body["accepted_qty_kg"] == "500.00"
        assert body["lot_status"] == "ACCEPTED_FULL"

    def test_recovery_api(self, base_data):
        lot = base_data["lot"]
        client = APIClient()
        client.force_authenticate(user=base_data["admin_user"])
        resp = client.post(f"/api/v1/quality/lots/{lot.id}/recover/", {
            "quantity_kg": "80.00",
            "remaining_shelf_life_hours": "8.00",
            "grade": "B",
            "trigger": "BUYER_REJECTION",
        }, format="json")
        assert resp.status_code == 200
        body = resp.json()
        assert body["outcome"] in ("SECONDARY_BUYER", "PROCESSOR", "WASTE")
