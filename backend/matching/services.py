"""
Matching & Lot Formation Service implementing D2 §5 & D1 §2, §7, §11.
Provides greedy scored matching, shortfall policy enforcement, and Lot creation.
"""
import uuid
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from django.utils import timezone
from django.db import transaction

from marketplace.models import Listing, BuyerOrder
from matching.models import Lot, LotContribution
from catalog.models import Crop, Region, AggregationPoint, PlatformSettings
from common.audit import log_audit_event
from notifications.services import send_notification
from engine.finance_math import (
    ContributorInput,
    calculate_floor_price,
    calculate_lot_pricing,
    LotPricingResult
)
from engine.pricing import recommend_price


class MatchingService:
    @staticmethod
    def match_supply_for_order(
        order: BuyerOrder,
        aggregation_point: Optional[AggregationPoint] = None,
        max_contributors: int = 6
    ) -> Dict[str, Any]:
        """
        Score and greedily allocate active listings for a buyer requirement.
        Enforces shortfall policies (WAIT / PARTIAL / REJECT) per D1 §11.
        """
        # 1. Candidate selection
        candidates = Listing.objects.filter(
            crop=order.crop,
            grade=order.grade,
            status='ACTIVE'
        ).select_related('farmer__user', 'crop')

        scored_candidates = []
        now = timezone.now()

        hub_lat = float(aggregation_point.latitude) if aggregation_point else float(order.delivery_latitude)
        hub_lng = float(aggregation_point.longitude) if aggregation_point else float(order.delivery_longitude)

        for listing in candidates:
            listing.update_shelf_life()
            if listing.available_kg <= Decimal('0.00'):
                continue
            if listing.remaining_shelf_life_hours and listing.remaining_shelf_life_hours < Decimal('4.00'):
                continue

            # Distance heuristic (in km approx from lat/lng diff)
            lat_diff = float(listing.latitude) - hub_lat
            lng_diff = float(listing.longitude) - hub_lng
            distance_km = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111.0

            # 1. Distance score (0.35)
            distance_score = max(0.0, 1.0 - min(distance_km / 50.0, 1.0))

            # 2. Quantity fit score (0.25)
            qty_avail = float(listing.available_kg)
            target_qty = float(order.quantity_kg)
            qty_diff = abs(qty_avail - target_qty)
            quantity_fit_score = max(0.0, 1.0 - min(qty_diff / target_qty, 1.0))

            # 3. Shelf-life score (0.20)
            shelf_life_h = float(listing.remaining_shelf_life_hours or 24.0)
            shelf_life_score = min(shelf_life_h / 48.0, 1.0)

            # 4. Farmer Tier score (0.20)
            tier_score = 0.50
            if listing.farmer.completed_orders >= 10:
                tier_score = 1.00
            elif listing.farmer.completed_orders >= 4:
                tier_score = 0.85
            elif listing.farmer.completed_orders >= 1:
                tier_score = 0.70

            total_score = (
                0.35 * distance_score +
                0.25 * quantity_fit_score +
                0.20 * shelf_life_score +
                0.20 * tier_score
            )

            scored_candidates.append({
                "listing": listing,
                "distance_km": round(distance_km, 2),
                "total_score": round(total_score, 4),
                "available_kg": listing.available_kg
            })

        # Sort candidates descending by total score
        scored_candidates.sort(key=lambda x: x["total_score"], reverse=True)

        # Greedy allocation
        allocated_contributions = []
        needed_kg = order.quantity_kg
        total_allocated_kg = Decimal('0.00')

        for item in scored_candidates[:max_contributors]:
            if needed_kg <= Decimal('0.00'):
                break
            listing = item["listing"]
            alloc = min(listing.available_kg, needed_kg)
            if alloc > Decimal('0.00'):
                allocated_contributions.append({
                    "listing": listing,
                    "allocated_kg": alloc,
                    "distance_km": item["distance_km"],
                    "match_score": Decimal(str(item["total_score"] * 100)).quantize(Decimal('0.01'))
                })
                total_allocated_kg += alloc
                needed_kg -= alloc

        # 2. Shortfall Policy Evaluation (D1 §11)
        shortfall_kg = order.quantity_kg - total_allocated_kg
        is_fulfilled = total_allocated_kg >= order.quantity_kg

        policy_decision = "FULFILLED"
        if not is_fulfilled:
            deadline_remaining_hours = (order.delivery_deadline - now).total_seconds() / 3600.0
            if order.allow_partial and order.min_acceptable_quantity_kg and total_allocated_kg >= order.min_acceptable_quantity_kg:
                policy_decision = "PARTIAL"
            elif deadline_remaining_hours > 24.0:
                policy_decision = "WAIT"
            else:
                policy_decision = "REJECT"

        return {
            "order": order,
            "is_fulfilled": is_fulfilled,
            "policy_decision": policy_decision,
            "total_allocated_kg": total_allocated_kg,
            "shortfall_kg": max(Decimal('0.00'), shortfall_kg),
            "contributions": allocated_contributions
        }


class LotService:
    @staticmethod
    def form_lot_from_match(
        order: BuyerOrder,
        match_result: Dict[str, Any],
        logistics_cost: Decimal = Decimal('7094.00'),
        aggregation_point: Optional[AggregationPoint] = None
    ) -> Lot:
        """
        Form and price a proposed Lot from matched contributions.
        """
        contributions_data = match_result["contributions"]
        if not contributions_data:
            raise ValueError("Cannot form a Lot with zero contributions.")

        total_qty = match_result["total_allocated_kg"]

        with transaction.atomic():
            lot_code = f"LOT-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"

            # Compute Floor Price for the lot
            floor = calculate_floor_price(
                mandi_modal_price=Decimal('25.00'),
                grade_multiplier=Decimal('1.00') if order.grade == 'A' else (Decimal('0.80') if order.grade == 'B' else Decimal('0.65')),
                markdown_factor=Decimal('0.60'),
                floor_premium=Decimal('1.10')
            )

            # Build ContributorInputs for pure python financial pricing
            contributor_inputs = []
            for c_data in contributions_data:
                listing = c_data["listing"]
                farmer = listing.farmer
                # Tier rate mapping: NEW: 50%@27%, T1_3: 60%@24%, T4_10: 65%@21%, T10_PLUS: 70%@18%
                if farmer.completed_orders >= 10:
                    adv_rate, int_rate = Decimal('0.70'), Decimal('0.18')
                elif farmer.completed_orders >= 4:
                    adv_rate, int_rate = Decimal('0.65'), Decimal('0.21')
                elif farmer.completed_orders >= 1:
                    adv_rate, int_rate = Decimal('0.60'), Decimal('0.24')
                else:
                    adv_rate, int_rate = Decimal('0.50'), Decimal('0.27')

                contributor_inputs.append(ContributorInput(
                    contributor_id=str(listing.id),
                    farmer_name=farmer.user.full_name,
                    quantity_kg=c_data["allocated_kg"],
                    advance_rate=adv_rate,
                    annual_interest_rate=int_rate,
                    self_delivery=listing.self_delivery
                ))

            pricing_res: LotPricingResult = calculate_lot_pricing(
                floor_price=floor,
                contributors=contributor_inputs,
                logistics_cost=logistics_cost,
                platform_commission_rate=Decimal('0.04'),
                risk_reserve_rate=Decimal('0.01'),
                mandi_modal_price=Decimal('25.00'),
                buyer_max_price_per_kg=order.max_price_per_kg,
                expected_days_to_sell=2
            )

            # Recommend price bounded by [min_viable, buyer_ceiling]
            rec = recommend_price(
                mandi_benchmark=Decimal('25.00'),
                grade=order.grade,
                grade_multiplier=Decimal('1.00') if order.grade == 'A' else Decimal('0.80'),
                floor_price=floor,
                minimum_viable_price=pricing_res.minimum_viable_lot_price,
                buyer_ceiling=order.max_price_per_kg,
                quantity_kg=total_qty
            )

            lot = Lot.objects.create(
                lot_code=lot_code,
                buyer_order=order,
                crop=order.crop,
                grade=order.grade,
                total_quantity_kg=total_qty,
                floor_price_per_kg=floor,
                minimum_viable_price_per_kg=pricing_res.minimum_viable_lot_price,
                agreed_price_per_kg=order.max_price_per_kg or pricing_res.minimum_viable_lot_price,
                logistics_cost=logistics_cost,
                status='PROPOSED',
                aggregation_point=aggregation_point
            )

            # Create LotContribution records & reserve listing quantities
            for idx, c_data in enumerate(contributions_data):
                listing = c_data["listing"]
                calc = pricing_res.contributions[idx]

                LotContribution.objects.create(
                    lot=lot,
                    listing=listing,
                    farmer=listing.farmer,
                    committed_quantity_kg=c_data["allocated_kg"],
                    advance_amount=calc.advance_amount,
                    interest_amount=calc.interest_amount,
                    lender_claim=calc.lender_claim,
                    residual_entitlement=calc.residual_entitlement,
                    status='PENDING',
                    match_score=c_data["match_score"]
                )

                listing.reserved_kg += c_data["allocated_kg"]
                listing.status = 'RESERVED'
                listing.save(update_fields=['reserved_kg', 'status'])

            order.status = 'MATCHED'
            order.save(update_fields=['status'])

            log_audit_event(
                action="LOT_FORMED",
                entity_type="Lot",
                entity_id=str(lot.id),
                user=order.buyer.user,
                metadata={
                    "lot_code": lot.lot_code,
                    "order_id": str(order.id),
                    "total_quantity_kg": str(total_qty),
                    "contributors_count": len(contributions_data)
                }
            )

            # Notify contributing farmers
            for c_data in contributions_data:
                send_notification(
                    user=c_data["listing"].farmer.user,
                    title="Produce Matched to Lot",
                    message=f"{c_data['allocated_kg']} kg of your {order.crop.name} has been matched into Lot {lot.lot_code}.",
                    notification_type="LOT_MATCHED",
                    metadata={"lot_id": str(lot.id)}
                )

            return lot
