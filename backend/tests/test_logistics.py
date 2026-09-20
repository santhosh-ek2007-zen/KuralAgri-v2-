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
from logistics.models import LogisticsRateCard, Vehicle, Route
from logistics.services import LogisticsCostService, DestinationService, RoutingService
from engine.economics import (
    calculate_logistics_cost,
    ContributorPickupInput,
    evaluate_and_rank_destinations,
    DestinationCandidateInput,
)


@pytest.mark.django_db
class TestLogisticsEngineAndAPIs:
    """M7: Logistics feasibility, routing, and API tests."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        PlatformSettings.get_settings()

        self.region = Region.objects.create(
            name="Theni", state="Tamil Nadu", district="Theni"
        )
        self.crop = Crop.objects.create(
            name="Tomato",
            category="VEGETABLE",
            default_shelf_life_days=7,
            min_shelf_life_days=2,
        )
        CropGradeParam.objects.create(
            crop=self.crop, grade="A", param_name="size_mm",
            min_value=Decimal("50.00"), max_value=Decimal("80.00"),
        )
        self.hub = AggregationPoint.objects.create(
            name="Theni Hub", region=self.region,
            latitude=Decimal("9.9457"), longitude=Decimal("77.4779"),
            capacity_mt=Decimal("50.00"),
        )
        self.rate_card = LogisticsRateCard.objects.create(code="PILOT_V1")

        # Farmer 1 — Chinnamanur, 12 km south-west of Theni
        self.user_f1 = User.objects.create_user(
            phone="9876500001", full_name="Farmer One", role="FARMER"
        )
        self.profile_f1 = FarmerProfile.objects.create(
            user=self.user_f1, village="Chinnamanur", district="Theni",
            latitude=Decimal("9.8398"), longitude=Decimal("77.3827"),
            completed_orders=0,
        )

        # Farmer 2 — Bodinayakanur, 8 km north of Theni
        self.user_f2 = User.objects.create_user(
            phone="9876500002", full_name="Farmer Two", role="FARMER"
        )
        self.profile_f2 = FarmerProfile.objects.create(
            user=self.user_f2, village="Bodinayakanur", district="Theni",
            latitude=Decimal("10.0104"), longitude=Decimal("77.3507"),
            completed_orders=2,
        )

        # Premium buyer near Theni (~2 km away)
        self.user_b_local = User.objects.create_user(
            phone="9876500004", full_name="Theni Local Buyer", role="BUYER"
        )
        self.buyer_local = BuyerProfile.objects.create(
            user=self.user_b_local, organisation="Theni Local Market",
            buyer_type="PREMIUM", accepted_grades=["A"],
            district="Theni", daily_capacity_kg=Decimal("2000.00"),
            latitude=Decimal("9.9500"), longitude=Decimal("77.4800"),
        )

        harvest_dt = timezone.now() - timedelta(hours=1)

        self.l1 = Listing.objects.create(
            farmer=self.profile_f1, crop=self.crop, grade="A",
            quantity_kg=Decimal("300.00"), harvest_datetime=harvest_dt,
            usable_life_hours=Decimal("36.00"),
            village="Chinnamanur", district="Theni",
            latitude=Decimal("9.8398"), longitude=Decimal("77.3827"),
            status="ACTIVE",
        )
        self.l1.update_shelf_life()
        self.l1.save()

        self.l2 = Listing.objects.create(
            farmer=self.profile_f2, crop=self.crop, grade="A",
            quantity_kg=Decimal("200.00"), harvest_datetime=harvest_dt,
            usable_life_hours=Decimal("36.00"),
            village="Bodinayakanur", district="Theni",
            latitude=Decimal("10.0104"), longitude=Decimal("77.3507"),
            status="ACTIVE",
        )
        self.l2.update_shelf_life()
        self.l2.save()

        self.order = BuyerOrder.objects.create(
            order_code="BUY-LOGISTICS-001",
            buyer=self.buyer_local, crop=self.crop, grade="A",
            quantity_kg=Decimal("500.00"),
            delivery_deadline=timezone.now() + timedelta(days=2),
            max_price_per_kg=Decimal("40.00"),
            sourcing_preference="AGGREGATED",
            allow_partial=False,
            delivery_district="Theni",
            delivery_latitude=Decimal("9.9500"),
            delivery_longitude=Decimal("77.4800"),
        )

        self.vehicle = Vehicle.objects.create(
            registration_number="TN60AB1234", vehicle_type="MINI_TRUCK",
            capacity_kg=Decimal("1200.00"), cost_per_km=Decimal("15.00"),
            base_location="Theni",
            latitude=Decimal("9.9457"), longitude=Decimal("77.4779"),
        )

    # ------------------------------------------------------------------ #
    # Pure-engine tests (no DB writes beyond setup)                        #
    # ------------------------------------------------------------------ #

    def test_pure_economics_logistics_cost_tiers(self):
        """Trunk-rate tiers: 500 kg uses ₹0.45/kg/km band."""
        contributors = [
            ContributorPickupInput("c1", Decimal("300.00"), Decimal("5.00")),
            ContributorPickupInput("c2", Decimal("200.00"), Decimal("6.00")),
        ]
        res = calculate_logistics_cost(
            lot_quantity_kg=Decimal("500.00"),
            trunk_distance_km=Decimal("20.00"),
            contributors=contributors,
        )
        # trunk = 500 * 20 * 0.45 = 4500
        # collection = 300*5*1.2 + 200*6*1.2 = 1800+1440 = 3240
        # handling = 500 * 0.30 = 150
        # total = 7890
        assert res.trunk_rate_per_kg_km == Decimal("0.45")
        assert res.transport_cost == Decimal("4500.00")
        assert res.collection_cost == Decimal("3240.00")
        assert res.handling_cost == Decimal("150.00")
        assert res.total_logistics_cost == Decimal("7890.00")

    def test_pure_economics_feasibility_filter(self):
        """Chennai (~480 km) must be rejected by SHELF_LIFE; Theni (~25 km) must be feasible."""
        candidates = [
            DestinationCandidateInput(
                destination_id="buyer_chennai",
                buyer_name="Chennai Wholesaler",
                channel="PREMIUM",
                accepted_grades=["A"],
                daily_capacity_kg=Decimal("1000.00"),
                min_order_kg=Decimal("100.00"),
                gross_price_per_kg=Decimal("40.00"),
                road_distance_km=Decimal("480.00"),
                # travel_time = 480/35 ≈ 13.7 h; +2h buffer = 15.7 h > 10 h shelf life → SHELF_LIFE
            ),
            DestinationCandidateInput(
                destination_id="buyer_theni",
                buyer_name="Theni Local Packhouse",
                channel="PREMIUM",
                accepted_grades=["A"],
                daily_capacity_kg=Decimal("1000.00"),
                min_order_kg=Decimal("100.00"),
                gross_price_per_kg=Decimal("35.00"),
                road_distance_km=Decimal("25.00"),
                # travel_time = 25/35 ≈ 0.71 h; +2h = 2.71 h < 10 h → feasible
            ),
        ]
        pickups = [
            ContributorPickupInput("c1", Decimal("300.00"), Decimal("5.00")),
            ContributorPickupInput("c2", Decimal("200.00"), Decimal("6.00")),
        ]
        evaluated = evaluate_and_rank_destinations(
            lot_quantity_kg=Decimal("500.00"),
            grade="A",
            remaining_shelf_life_hours=Decimal("10.00"),
            contributors=pickups,
            candidates=candidates,
        )

        assert len(evaluated) == 2
        # Feasible one must be ranked first
        assert evaluated[0].destination_id == "buyer_theni"
        assert evaluated[0].is_feasible is True
        assert evaluated[0].net_return_per_kg > Decimal("0.00")

        assert evaluated[1].destination_id == "buyer_chennai"
        assert evaluated[1].is_feasible is False
        assert evaluated[1].rejection_reason == "SHELF_LIFE"

    def test_pure_economics_uneconomic_gate(self):
        """A destination where net return ≤ 0 is flagged UNECONOMIC."""
        candidates = [
            DestinationCandidateInput(
                destination_id="loss_buyer",
                buyer_name="Far Away Depot",
                channel="SECONDARY",
                accepted_grades=["A"],
                daily_capacity_kg=Decimal("1000.00"),
                min_order_kg=Decimal("100.00"),
                gross_price_per_kg=Decimal("5.00"),   # too low
                road_distance_km=Decimal("300.00"),
            ),
        ]
        pickups = [ContributorPickupInput("c1", Decimal("500.00"), Decimal("5.00"))]
        evaluated = evaluate_and_rank_destinations(
            lot_quantity_kg=Decimal("500.00"),
            grade="A",
            remaining_shelf_life_hours=Decimal("20.00"),
            contributors=pickups,
            candidates=candidates,
        )
        assert evaluated[0].is_feasible is False
        assert evaluated[0].rejection_reason == "UNECONOMIC"

    # ------------------------------------------------------------------ #
    # Service + API tests (DB writes)                                      #
    # ------------------------------------------------------------------ #

    def _form_test_lot(self) -> Lot:
        """Helper: run matching + lot formation for the two test listings."""
        match_result = MatchingService.match_supply_for_order(
            order=self.order,
            aggregation_point=self.hub,
        )
        assert match_result["is_fulfilled"] or match_result["total_allocated_kg"] >= Decimal("400.00")
        lot = LotService.form_lot_from_match(
            order=self.order,
            match_result=match_result,
            logistics_cost=Decimal("7890.00"),
            aggregation_point=self.hub,
        )
        return lot

    def test_logistics_cost_service_creates_breakdown(self):
        lot = self._form_test_lot()
        breakdown = LogisticsCostService.calculate_cost_for_lot(lot)
        assert breakdown.total_logistics_cost > Decimal("0.00")
        assert breakdown.collection_cost > Decimal("0.00")
        assert breakdown.handling_cost > Decimal("0.00")

    def test_routing_service_creates_route_with_stops(self):
        lot = self._form_test_lot()
        route = RoutingService.plan_route(lot, vehicle=self.vehicle)

        assert route is not None
        assert route.vehicle.registration_number == "TN60AB1234"
        assert route.total_distance_km > Decimal("0.00")
        # Stops: depot(BASE) + 2 pickups + 1 delivery = 4
        assert route.stops.count() == 4

    def test_route_list_api(self):
        lot = self._form_test_lot()
        RoutingService.plan_route(lot, vehicle=self.vehicle)

        client = APIClient()
        client.force_authenticate(user=self.user_f1)
        resp = client.get(f"/api/v1/logistics/routes/?lot_id={lot.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["vehicle"]["registration_number"] == "TN60AB1234"
        stops = data[0]["stops"]
        assert len(stops) == 4
        stop_types = [s["stop_type"] for s in stops]
        assert "PICKUP" in stop_types
        assert "DELIVERY" in stop_types

    def test_route_plan_api(self):
        lot = self._form_test_lot()
        client = APIClient()
        client.force_authenticate(user=self.user_b_local)
        resp = client.post("/api/v1/logistics/routes/", {"lot_id": str(lot.id)}, format="json")
        assert resp.status_code == 201
        assert resp.json()["total_distance_km"] is not None

    def test_logistics_cost_api(self):
        lot = self._form_test_lot()
        LogisticsCostService.calculate_cost_for_lot(lot)

        client = APIClient()
        client.force_authenticate(user=self.user_f1)
        resp = client.get(f"/api/v1/logistics/cost/?lot_id={lot.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert "total_logistics_cost" in body
        assert float(body["total_logistics_cost"]) > 0
