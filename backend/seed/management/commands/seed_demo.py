"""
KuralAgri Demo Seed Command — §16 Dataset
python manage.py seed_demo          (idempotent)
python manage.py seed_demo --reset  (wipes transactional tables first)

Reproduces D1 §10 worked example exactly:
  F = ₹16.50, L_lot = ₹7,094.00, MVP = ₹32.32
  Waterfall at ₹35.00: 4873.61 / 700.00 / 7094.00 / 175.00 / 4657.39
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed KuralAgri demo dataset (§16). Use --reset to clear transactional data first."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Wipe transactional tables before seeding")

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_transactional()

        with transaction.atomic():
            self._seed_platform_settings()
            self._seed_rate_card()
            tiers = self._seed_advance_tiers()
            regions = self._seed_regions()
            crops = self._seed_crops(regions)
            self._seed_market_history(crops, regions)
            hubs = self._seed_aggregation_points(regions)
            fpos = self._seed_fpos(regions)
            farmers = self._seed_farmers(fpos, tiers)
            buyers = self._seed_buyers()
            vehicles = self._seed_vehicles(hubs, regions)
            self._seed_admin()
            listings = self._seed_listings(farmers, crops)
            self._seed_buyer_orders(buyers, crops)
            self._seed_historical_settled_lots(farmers, buyers, crops, hubs)

        self.stdout.write(self.style.SUCCESS("[OK] Demo dataset seeded successfully."))
        self.stdout.write("    Admin login:   9200000000 / Demo@1234")
        self.stdout.write("    Farmer logins: 9000000001-9000000008 / Demo@1234")
        self.stdout.write("    Buyer logins:  9100000001-9100000005 / Demo@1234")

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def _reset_transactional(self):
        from settlement.models import Settlement
        from quality.models import QualityCheck, RecoveryEvent
        from finance.models import EscrowAccount, LedgerEntry, Advance, RiskReserveLedger
        from logistics.models import Route, RouteStop, DestinationCandidate, LogisticsCostBreakdown, Vehicle, LogisticsRateCard
        from matching.models import Lot, LotContribution
        from marketplace.models import Listing, BuyerOrder
        from intelligence.models import MandiPrice, WeatherSnapshot, DemandHistory, MarketSnapshot, DemandForecast, PriceRecommendation
        from notifications.models import Notification
        from common.models import AuditLog

        models_to_clear = [
            Settlement, QualityCheck, RecoveryEvent,
            Advance, LedgerEntry, EscrowAccount, RiskReserveLedger,
            RouteStop, Route, DestinationCandidate, LogisticsCostBreakdown,
            LotContribution, Lot,
            BuyerOrder, Listing,
            PriceRecommendation, DemandForecast, MarketSnapshot,
            DemandHistory, WeatherSnapshot, MandiPrice,
            Notification, AuditLog,
        ]
        for model in models_to_clear:
            model.objects.all().delete()

        from users.models import User, FPO
        # Delete non-superusers
        User.objects.filter(is_superuser=False).delete()
        FPO.objects.all().delete()

        from catalog.models import AggregationPoint, CropGradeParam, AdvanceTier
        for m in [Vehicle, LogisticsRateCard, AggregationPoint, CropGradeParam, AdvanceTier]:
            m.objects.all().delete()

        self.stdout.write(self.style.WARNING("  [RESET] Transactional tables cleared."))

    # ------------------------------------------------------------------
    # Reference data
    # ------------------------------------------------------------------

    def _seed_platform_settings(self):
        from catalog.models import PlatformSettings
        settings = PlatformSettings.get_settings()
        settings.platform_fee_pct = Decimal("4.00")
        settings.risk_reserve_pct = Decimal("1.00")
        settings.platform_commission_rate = Decimal("0.0400")
        settings.risk_reserve_rate = Decimal("0.0100")
        settings.floor_premium = Decimal("1.10")
        settings.ceiling_discount = Decimal("0.85")
        settings.reserve_default_cover_rate = Decimal("0.40")
        settings.floor_price_discount_pct = Decimal("15.00")
        settings.advance_tenure_days_max = 14
        settings.demo_mode = True
        settings.save()

        # Seed opening risk-reserve balance
        from finance.models import RiskReserveLedger
        if not RiskReserveLedger.objects.exists():
            RiskReserveLedger.objects.create(
                entry_type="OPENING_BALANCE",
                amount=Decimal("25000.00"),
                balance_after=Decimal("25000.00"),
                notes="Demo opening balance §16.1",
            )

        self.stdout.write("  [OK] Platform settings")

    def _seed_rate_card(self):
        from logistics.models import LogisticsRateCard
        LogisticsRateCard.objects.get_or_create(
            code="PILOT_V1",
            defaults={
                "collection_rate_per_kg_km": Decimal("1.20"),
                "handling_fee_per_kg": Decimal("0.30"),
                "trunk_tier_1_rate": Decimal("0.80"),
                "trunk_tier_2_rate": Decimal("0.45"),
                "trunk_tier_3_rate": Decimal("0.25"),
                "trunk_tier_4_rate": Decimal("0.15"),
                "safety_buffer_hours": Decimal("2.00"),
                "road_distance_factor": Decimal("1.35"),
                "average_speed_kmph": Decimal("35.00"),
            }
        )
        self.stdout.write("  [OK] Rate card PILOT_V1")

    def _seed_advance_tiers(self):
        from catalog.models import AdvanceTier
        tier_data = [
            ("NEW",      0,  0,     Decimal("50.00"), Decimal("27.00")),
            ("T1_3",     1,  3,     Decimal("60.00"), Decimal("24.00")),
            ("T4_10",    4,  10,    Decimal("65.00"), Decimal("21.00")),
            ("T10_PLUS", 11, 99999, Decimal("70.00"), Decimal("18.00")),
        ]
        tier_objs = {}
        for code, min_o, max_o, rate_pct, interest_pct in tier_data:
            tier, _ = AdvanceTier.objects.get_or_create(
                code=code,
                defaults={
                    "min_completed_orders": min_o,
                    "max_completed_orders": max_o,
                    "max_advance_pct": rate_pct,
                    "interest_rate_pct": interest_pct,
                }
            )
            tier_objs[code] = tier
        self.stdout.write("  [OK] Advance tiers")
        return tier_objs

    def _seed_regions(self):
        from catalog.models import Region
        region_data = [
            ("Theni", "Tamil Nadu", "Theni"),
            ("Madurai", "Tamil Nadu", "Madurai"),
            ("Dindigul", "Tamil Nadu", "Dindigul"),
            ("Trichy", "Tamil Nadu", "Tiruchirappalli"),
            ("Chennai", "Tamil Nadu", "Chennai"),
            ("Kancheepuram", "Tamil Nadu", "Kancheepuram"),
        ]
        regions = {}
        for name, state, district in region_data:
            r, _ = Region.objects.get_or_create(name=name, state=state, district=district)
            regions[name] = r
        self.stdout.write(f"  [OK] {len(regions)} regions")
        return regions

    def _seed_crops(self, regions):
        from catalog.models import Crop, CropGradeParam
        crop_data = [
            # name, category, msp, markdown, class, days, life_h, urgency, retail_markup
            ("Tomato",       "VEGETABLE", "0.00",  "0.60", "A", 2,  36,  "0.40", "1.65"),
            ("Brinjal",      "VEGETABLE", "0.00",  "0.60", "A", 2,  48,  "0.35", "1.60"),
            ("Green Chilli", "VEGETABLE", "0.00",  "0.62", "B", 7,  120, "0.30", "1.70"),
            ("Banana",       "FRUIT",     "0.00",  "0.58", "B", 7,  168, "0.25", "1.55"),
            ("Onion",        "VEGETABLE", "12.00", "0.65", "C", 30, 720, "0.15", "1.50"),
        ]
        # grade params: A=1.0 PREMIUM, B=0.80 SECONDARY, C=0.65 PROCESSOR
        grade_params = [
            ("A", Decimal("1.00"), Decimal("1.00"), Decimal("2.00")),
            ("B", Decimal("0.80"), Decimal("0.80"), Decimal("1.50")),
            ("C", Decimal("0.65"), Decimal("0.65"), Decimal("1.20")),
        ]
        crops = {}
        for name, cat, msp, markdown, cls, days, life_h, urgency, retail in crop_data:
            crop, _ = Crop.objects.get_or_create(
                name=name,
                defaults={
                    "category": cat,
                    "msp_per_kg": Decimal(msp),
                    "markdown_factor": Decimal(markdown),
                    "perishability_class": cls,
                    "default_shelf_life_days": life_h // 24 or 1,
                    "min_shelf_life_days": 1,
                    "usable_life_hours": life_h,
                    "urgency_rate_per_kg": Decimal(urgency),
                    "retail_markup": Decimal(retail),
                    "days_to_sell": days,
                }
            )
            for grade, size_min, size_max, weight_min in grade_params:
                CropGradeParam.objects.get_or_create(
                    crop=crop, grade=grade,
                    param_name="size_mm",
                    defaults={
                        "min_value": size_min * 20,
                        "max_value": size_max * 80,
                    }
                )
            crops[name] = crop
        self.stdout.write(f"  [OK] {len(crops)} crops + grade params")
        return crops

    def _seed_aggregation_points(self, regions):
        from catalog.models import AggregationPoint
        hubs = {}
        hub_data = [
            ("Cumbum Valley FPO Collection Centre", "Theni", "9.7200", "77.2800", "50.00", "0.30"),
            ("Usilampatti Collection Society", "Madurai", "9.8000", "77.4900", "30.00", "0.32"),
        ]
        for name, region_name, lat, lng, capacity, handling in hub_data:
            hub, _ = AggregationPoint.objects.get_or_create(
                name=name,
                defaults={
                    "region": regions[region_name],
                    "latitude": Decimal(lat),
                    "longitude": Decimal(lng),
                    "capacity_mt": Decimal(capacity),
                    "handling_rate_per_kg": Decimal(handling),
                }
            )
            hubs[region_name] = hub
        self.stdout.write(f"  [OK] {len(hubs)} aggregation points")
        return hubs

    def _seed_fpos(self, regions):
        from users.models import User, FPO
        fpos = {}
        fpo_data = [
            ("Cumbum Valley Farmers Producer Co.", "9000000099", "Theni", 42),
            ("Vaigai Agri FPO", "9000000098", "Madurai", 31),
        ]
        for name, phone, region_name, members in fpo_data:
            user, _ = User.objects.get_or_create(
                phone=phone,
                defaults={"full_name": name, "role": "FPO", "is_active": True}
            )
            if not user.has_usable_password():
                user.set_password("Demo@1234")
                user.save()
            fpo, _ = FPO.objects.get_or_create(
                name=name,
                defaults={
                    "district": region_name,
                    "members_count": members,
                    "registration_number": f"REG-{phone[-4:]}",
                }
            )
            fpos[name] = fpo
        self.stdout.write(f"  [OK] {len(fpos)} FPOs")
        return fpos

    def _seed_farmers(self, fpos, tiers):
        from users.models import User, FarmerProfile
        cumbum_fpo = fpos.get("Cumbum Valley Farmers Producer Co.")
        vaigai_fpo = fpos.get("Vaigai Agri FPO")

        farmer_data = [
            # phone, name, village, district, fpo, completed_orders, tier_code, self_delivery, lat, lng
            ("9000000001", "Ravi Kumar",     "Cumbum",          "Theni",   None,        0,  "NEW",      False, "9.7200", "77.2800"),
            ("9000000002", "Meena Lakshmi",  "Uthamapalayam",   "Theni",   None,        2,  "T1_3",     False, "9.8050", "77.3400"),
            ("9000000003", "Suresh Pandian", "Bodinayakanur",   "Theni",   None,        0,  "NEW",      False, "10.0104","77.3507"),
            ("9000000004", "Karthik R",      "Chinnamanur",     "Theni",   cumbum_fpo, 14,  "T10_PLUS", False, "9.8398", "77.3827"),
            ("9000000005", "Anitha S",       "Andipatti",       "Theni",   cumbum_fpo,  6,  "T4_10",    True,  "9.9730", "77.6080"),
            ("9000000006", "Murugan V",      "Periyakulam",     "Theni",   None,        1,  "T1_3",     False, "10.1200","77.5400"),
            ("9000000007", "Selvi M",        "Usilampatti",     "Madurai", vaigai_fpo,  9,  "T4_10",    False, "9.8000", "77.4900"),
            ("9000000008", "Ganesh K",       "Melur",           "Madurai", vaigai_fpo,  3,  "T1_3",     False, "10.0400","78.3400"),
        ]
        farmers = {}
        for phone, name, village, district, fpo, orders, tier_code, self_deliv, lat, lng in farmer_data:
            user, _ = User.objects.get_or_create(
                phone=phone,
                defaults={"full_name": name, "role": "FARMER", "is_active": True}
            )
            user.set_password("Demo@1234")
            user.save()
            profile, _ = FarmerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "village": village,
                    "district": district,
                    "fpo": fpo,
                    "completed_orders": orders,
                    "current_tier": tiers.get(tier_code),
                    "self_delivery_capable": self_deliv,
                    "latitude": Decimal(lat),
                    "longitude": Decimal(lng),
                }
            )
            farmers[phone] = profile
        self.stdout.write(f"  [OK] {len(farmers)} farmers")
        return farmers

    def _seed_buyers(self):
        from users.models import User, BuyerProfile
        buyer_data = [
            # phone, name, org, type, grades, district, lat, lng, capacity, price
            ("9100000001", "Theni Fresh Mart",       "Theni Fresh Mart",        "PREMIUM",   ["A"],      "Theni",        "9.9457",  "77.4779",  "2000.00", "35.00"),
            ("9100000002", "Madurai Green Basket",   "Madurai Green Basket",    "PREMIUM",   ["A","B"],  "Madurai",      "9.9252",  "78.1198",  "3000.00", "36.00"),
            ("9100000003", "Chennai Metro Grocers",  "Chennai Metro Grocers",   "PREMIUM",   ["A"],      "Chennai",      "13.0827", "80.2707",  "8000.00", "38.00"),
            ("9100000004", "Sri Anandha Hotels",     "Sri Anandha Hotels",      "SECONDARY", ["A","B"],  "Theni",        "9.8800",  "77.3500",  "400.00",  "22.00"),
            ("9100000005", "Kodai Foods Processing", "Kodai Foods Processing",  "PROCESSOR", ["B","C"],  "Theni",        "9.9100",  "77.4200",  "5000.00", "14.00"),
        ]
        buyers = {}
        for phone, name, org, btype, grades, district, lat, lng, capacity, price in buyer_data:
            user, _ = User.objects.get_or_create(
                phone=phone,
                defaults={"full_name": name, "role": "BUYER", "is_active": True}
            )
            user.set_password("Demo@1234")
            user.save()
            profile, _ = BuyerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "organisation": org,
                    "buyer_type": btype,
                    "accepted_grades": grades,
                    "district": district,
                    "latitude": Decimal(lat),
                    "longitude": Decimal(lng),
                    "daily_capacity_kg": Decimal(capacity),
                    "indicative_price_per_kg": Decimal(price),
                }
            )
            buyers[phone] = profile
        self.stdout.write(f"  [OK] {len(buyers)} buyers")
        return buyers

    def _seed_vehicles(self, hubs, regions):
        from logistics.models import Vehicle
        vehicle_data = [
            # reg, type, capacity, cost_per_km, base_location, lat, lng
            ("TN59AB1234", "MINI_TRUCK", "1000.00", "18.00", "Theni",   "9.9457",  "77.4779"),
            ("TN59CD5678", "TRUCK",      "3000.00", "28.00", "Theni",   "9.9457",  "77.4779"),
            ("TN58EF9012", "MINI_TRUCK", "1200.00", "19.00", "Madurai", "9.9252",  "78.1198"),
            ("TN59GH3456", "TEMPO",      "600.00",  "14.00", "Theni",   "9.9457",  "77.4779"),
        ]
        vehicles = {}
        for reg, vtype, cap, cost, base, lat, lng in vehicle_data:
            v, _ = Vehicle.objects.get_or_create(
                registration_number=reg,
                defaults={
                    "vehicle_type": vtype,
                    "capacity_kg": Decimal(cap),
                    "cost_per_km": Decimal(cost),
                    "base_location": base,
                    "latitude": Decimal(lat),
                    "longitude": Decimal(lng),
                    "is_available": True,
                }
            )
            vehicles[reg] = v
        self.stdout.write(f"  [OK] {len(vehicles)} vehicles")
        return vehicles

    def _seed_admin(self):
        from users.models import User
        admin, _ = User.objects.get_or_create(
            phone="9200000000",
            defaults={
                "full_name": "KuralAgri Admin",
                "role": "ADMIN",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            }
        )
        admin.set_password("Demo@1234")
        admin.save()
        self.stdout.write("  [OK] Admin user (9200000000)")

    # ------------------------------------------------------------------
    # Market history (120 days, deterministic)
    # ------------------------------------------------------------------

    def _seed_market_history(self, crops, regions):
        from intelligence.models import MandiPrice, WeatherSnapshot, DemandHistory

        rng = random.Random(42)  # fixed seed for determinism
        now = timezone.now()
        base_prices = {
            "Theni": {"Tomato": 22.0, "Brinjal": 18.0, "Green Chilli": 55.0, "Banana": 20.0, "Onion": 15.0},
            "Madurai": {"Tomato": 24.0, "Brinjal": 20.0, "Green Chilli": 58.0, "Banana": 22.0, "Onion": 16.0},
            "Dindigul": {"Tomato": 23.0, "Brinjal": 19.0, "Green Chilli": 56.0, "Banana": 21.0, "Onion": 15.5},
            "Trichy": {"Tomato": 24.5, "Brinjal": 21.0, "Green Chilli": 60.0, "Banana": 23.0, "Onion": 17.0},
            "Chennai": {"Tomato": 27.0, "Brinjal": 24.0, "Green Chilli": 65.0, "Banana": 26.0, "Onion": 19.0},
            "Kancheepuram": {"Tomato": 26.0, "Brinjal": 23.0, "Green Chilli": 63.0, "Banana": 25.0, "Onion": 18.0},
        }

        mandi_to_create = []
        weather_to_create = []
        demand_to_create = []

        for day_offset in range(120, 0, -1):
            date = (now - timedelta(days=day_offset)).date()
            days_from_end = day_offset  # 120=oldest, 1=most recent

            for region_name, region in regions.items():
                # Weather: last 3 days in Theni = HEAVY_RAIN / HIGH risk
                if region_name == "Theni" and days_from_end <= 3:
                    condition = "HEAVY_RAIN"
                    risk = "HIGH"
                else:
                    conditions = ["CLEAR", "RAIN", "HEAVY_RAIN"]
                    condition = rng.choice(conditions)
                    risk = rng.choice(["LOW", "LOW", "MEDIUM", "HIGH"])

                if not WeatherSnapshot.objects.filter(region=region, recorded_date=date).exists():
                    weather_to_create.append(WeatherSnapshot(
                        region=region, recorded_date=date,
                        condition=condition, risk_level=risk,
                        temperature_c=Decimal(str(round(rng.uniform(22, 36), 1))),
                        rainfall_mm=Decimal("45.00") if condition == "HEAVY_RAIN" else Decimal(str(round(rng.uniform(0, 15), 1))),
                    ))

                for crop_name, crop in crops.items():
                    base = base_prices.get(region_name, {}).get(crop_name, 20.0)

                    # Tomato upward trend in last 10 days: Theni +11%, Chennai +10%
                    if crop_name == "Tomato" and days_from_end <= 10:
                        if region_name == "Theni":
                            base = 22.5 + (10 - days_from_end) * 0.25   # 22.5->25.0
                        elif region_name == "Chennai":
                            base = 25.2 + (10 - days_from_end) * 0.28   # 25.2->28.0

                    noise = rng.uniform(-0.08, 0.08)
                    price = max(5.0, base * (1 + noise))

                    # Arrivals: Theni tomato declining 18% over last 7 days
                    base_arrivals = rng.uniform(500, 5000)
                    if crop_name == "Tomato" and region_name == "Theni" and days_from_end <= 7:
                        decline = 1 - (7 - days_from_end) * 0.026   # ~18% over 7 days
                        base_arrivals = base_arrivals * decline

                    if not MandiPrice.objects.filter(region=region, crop=crop, recorded_date=date).exists():
                        mandi_to_create.append(MandiPrice(
                            region=region, crop=crop, recorded_date=date,
                            modal_price=Decimal(str(round(price, 2))),
                            min_price=Decimal(str(round(price * 0.88, 2))),
                            max_price=Decimal(str(round(price * 1.12, 2))),
                            arrivals_kg=Decimal(str(round(base_arrivals, 2))),
                        ))

                    # Demand history — Chennai tomato trending up -> 8500kg HIGH
                    base_demand = 3000 if region_name == "Chennai" and crop_name == "Tomato" else rng.uniform(500, 3000)
                    if crop_name == "Tomato" and region_name == "Chennai" and days_from_end <= 30:
                        base_demand += (30 - days_from_end) * 185   # trending to 8500
                    demand_qty = max(100, base_demand * rng.uniform(0.92, 1.08))

                    if not DemandHistory.objects.filter(region=region, crop=crop, recorded_date=date).exists():
                        demand_to_create.append(DemandHistory(
                            region=region, crop=crop, recorded_date=date,
                            quantity_demanded_kg=Decimal(str(round(demand_qty, 0))),
                        ))

        MandiPrice.objects.bulk_create(mandi_to_create, ignore_conflicts=True)
        WeatherSnapshot.objects.bulk_create(weather_to_create, ignore_conflicts=True)
        DemandHistory.objects.bulk_create(demand_to_create, ignore_conflicts=True)
        self.stdout.write(f"  [OK] Market history: {len(mandi_to_create)} mandi prices, {len(weather_to_create)} weather, {len(demand_to_create)} demand records")

    # ------------------------------------------------------------------
    # Transactional seed
    # ------------------------------------------------------------------

    def _seed_listings(self, farmers, crops):
        from marketplace.models import Listing
        tomato = crops["Tomato"]
        now = timezone.now()
        # All harvested 26h ago -> 10h remaining (36h life - 26h elapsed)
        harvest_dt = now - timedelta(hours=26)

        listing_data = [
            # phone, grade, qty, lat, lng, village, dist_to_hub_km, status, self_deliv
            ("9000000001", "A", "120.00", "9.7200", "77.2800", "Cumbum",        3,  "ACTIVE", False),
            ("9000000002", "A", "150.00", "9.8050", "77.3400", "Uthamapalayam", 4,  "ACTIVE", False),
            ("9000000003", "A", "80.00",  "10.0104","77.3507", "Bodinayakanur", 2,  "ACTIVE", False),
            ("9000000004", "A", "150.00", "9.8398", "77.3827", "Chinnamanur",   5,  "ACTIVE", False),
            ("9000000006", "B", "200.00", "10.1200","77.5400", "Periyakulam",   6,  "ACTIVE", False),
            ("9000000005", "A", "300.00", "9.9730", "77.6080", "Andipatti",     7,  "ACTIVE", True),
        ]
        listings = {}
        for phone, grade, qty, lat, lng, village, dist, status, self_deliv in listing_data:
            farmer = farmers[phone]
            existing = Listing.objects.filter(farmer=farmer, crop=tomato, status=status).first()
            if not existing:
                listing = Listing.objects.create(
                    farmer=farmer, crop=tomato, grade=grade,
                    quantity_kg=Decimal(qty),
                    harvest_datetime=harvest_dt,
                    usable_life_hours=Decimal("36.00"),
                    village=village, district="Theni",
                    latitude=Decimal(lat), longitude=Decimal(lng),
                    self_delivery=self_deliv,
                    status=status,
                )
                listing.update_shelf_life()
                listing.save()
                listings[phone] = listing
            else:
                listings[phone] = existing

        self.stdout.write(f"  [OK] {len(listings)} active listings (L1-L6)")
        return listings

    def _seed_buyer_orders(self, buyers, crops):
        from marketplace.models import BuyerOrder
        tomato = crops["Tomato"]
        now = timezone.now()

        # Primary 500kg Grade-A order — BUY-2026-014
        BuyerOrder.objects.get_or_create(
            order_code="BUY-2026-014",
            defaults={
                "buyer": buyers["9100000001"],
                "crop": tomato,
                "grade": "A",
                "quantity_kg": Decimal("500.00"),
                "delivery_deadline": now + timedelta(days=2),
                "max_price_per_kg": Decimal("35.00"),
                "sourcing_preference": "AGGREGATED",
                "allow_partial": True,
                "min_acceptable_quantity_kg": Decimal("400.00"),
                "delivery_district": "Theni",
                "delivery_latitude": Decimal("9.9457"),
                "delivery_longitude": Decimal("77.4779"),
                "status": "OPEN",
            }
        )

        # Open Grade-B order from Sri Anandha Hotels (for recovery path demo)
        BuyerOrder.objects.get_or_create(
            order_code="BUY-2026-015",
            defaults={
                "buyer": buyers["9100000004"],
                "crop": tomato,
                "grade": "B",
                "quantity_kg": Decimal("150.00"),
                "delivery_deadline": now + timedelta(days=3),
                "max_price_per_kg": Decimal("22.00"),
                "sourcing_preference": "SINGLE_SOURCE",
                "allow_partial": True,
                "min_acceptable_quantity_kg": Decimal("50.00"),
                "delivery_district": "Theni",
                "delivery_latitude": Decimal("9.8800"),
                "delivery_longitude": Decimal("77.3500"),
                "status": "OPEN",
            }
        )

        self.stdout.write("  [OK] 2 buyer orders (BUY-2026-014, BUY-2026-015)")

    def _seed_historical_settled_lots(self, farmers, buyers, crops, hubs):
        """
        Create 2 historical SETTLED lots so dashboards, tier calculations
        and the risk-reserve balance are not empty on first load.
        """
        from matching.models import Lot, LotContribution
        from finance.models import LedgerEntry
        from settlement.models import Settlement

        if Lot.objects.filter(status="SETTLED").exists():
            self.stdout.write("  [OK] Historical lots already seeded")
            return

        tomato = crops["Tomato"]
        theni_hub = hubs.get("Theni")
        buyer = buyers["9100000001"]
        now = timezone.now()

        for i, (lot_code, f_phone, qty, agreed) in enumerate([
            ("LOT-HIST-001", "9000000001", Decimal("80.00"),  Decimal("28.00")),
            ("LOT-HIST-002", "9000000002", Decimal("100.00"), Decimal("30.00")),
        ]):
            farmer = farmers[f_phone]
            lot = Lot.objects.create(
                lot_code=lot_code,
                crop=tomato,
                grade="A",
                total_quantity_kg=qty,
                delivered_quantity_kg=qty,
                floor_price_per_kg=Decimal("16.50"),
                logistics_cost=Decimal("1500.00"),
                agreed_price_per_kg=agreed,
                minimum_viable_price_per_kg=Decimal("32.32"),
                aggregation_point=theni_hub,
                status="SETTLED",
                created_at=now - timedelta(days=15 + i * 5),
            )
            contrib = LotContribution.objects.create(
                lot=lot,
                farmer=farmer,
                listing=None,
                committed_quantity_kg=qty,
                delivered_quantity_kg=qty,
                advance_amount=(Decimal("16.50") * qty * Decimal("0.50")).quantize(Decimal("0.01")),
                interest_amount=Decimal("2.50"),
                lender_claim=(Decimal("16.50") * qty * Decimal("0.50") + Decimal("2.50")).quantize(Decimal("0.01")),
                residual_entitlement=(Decimal("16.50") * qty * Decimal("0.50")).quantize(Decimal("0.01")),
                status="SETTLED",
            )
            total_received = (agreed * qty).quantize(Decimal("0.01"))
            LedgerEntry.objects.create(
                lot=lot, entry_type="BUYER_DEPOSIT", direction="CREDIT",
                counterparty="BUYER", amount=total_received, is_simulated=True,
                reference=f"Historical lot {lot_code}"
            )
            Settlement.objects.create(
                contribution=contrib,
                advance_paid=contrib.advance_amount,
                settlement_paid=(total_received * Decimal("0.27")).quantize(Decimal("0.01")),
                total_realisation=(total_received * Decimal("0.60")).quantize(Decimal("0.01")),
                traditional_channel_value=(Decimal("25.00") * qty * Decimal("0.60")).quantize(Decimal("0.01")),
                uplift_pct=Decimal("27.00"),
                status="PAID",
            )

        self.stdout.write("  [OK] 2 historical settled lots")
