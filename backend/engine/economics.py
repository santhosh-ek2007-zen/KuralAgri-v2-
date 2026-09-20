"""
Transport Economics & Destination Viability Engine — Pure Python.
No Django imports.
Implements D3 §3, §4, §5, §11 on top of D1 §5.3:
Calculates logistics cost (L_lot), evaluates feasibility gates, and ranks destinations by net return.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional

TWO_PLACES = Decimal('0.01')


def quantize_money(val: Decimal) -> Decimal:
    return Decimal(str(val)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class ContributorPickupInput:
    contributor_id: str
    quantity_kg: Decimal
    collection_distance_km: Decimal
    self_delivery: bool = False


@dataclass
class LogisticsCostResult:
    collection_cost: Decimal
    handling_cost: Decimal
    transport_cost: Decimal
    urgency_cost: Decimal
    total_logistics_cost: Decimal
    trunk_rate_per_kg_km: Decimal
    logistics_cost_per_kg: Decimal


@dataclass
class DestinationCandidateInput:
    destination_id: str
    buyer_name: str
    channel: str                     # PREMIUM, SECONDARY, PROCESSOR
    accepted_grades: List[str]
    daily_capacity_kg: Decimal
    min_order_kg: Decimal
    gross_price_per_kg: Decimal
    road_distance_km: Decimal


@dataclass
class EvaluatedDestination:
    destination_id: str
    buyer_name: str
    channel: str
    gross_price_per_kg: Decimal
    logistics_cost: Decimal
    logistics_cost_per_kg: Decimal
    net_return_per_kg: Decimal
    distance_km: Decimal
    travel_time_hours: Decimal
    is_feasible: bool
    rejection_reason: Optional[str]  # GRADE, CAPACITY, SHELF_LIFE, DEADLINE, UNECONOMIC


def get_trunk_tier_rate(quantity_kg: Decimal) -> Decimal:
    """
    Tier lookup per D1 §5.3 / RateCard PILOT_V1:
    < 500 kg: ₹0.80
    500–1,999 kg: ₹0.45
    2,000–4,999 kg: ₹0.25
    >= 5,000 kg: ₹0.15
    """
    if quantity_kg < Decimal('500.00'):
        return Decimal('0.80')
    elif quantity_kg < Decimal('2000.00'):
        return Decimal('0.45')
    elif quantity_kg < Decimal('5000.00'):
        return Decimal('0.25')
    else:
        return Decimal('0.15')


def calculate_logistics_cost(
    lot_quantity_kg: Decimal,
    trunk_distance_km: Decimal,
    contributors: List[ContributorPickupInput],
    collection_rate_per_kg_km: Decimal = Decimal('1.20'),
    handling_fee_per_kg: Decimal = Decimal('0.30'),
    urgency_premium_per_kg: Decimal = Decimal('0.00')
) -> LogisticsCostResult:
    """
    D1 §5.3 Single Source of Truth for Logistics Cost:
    L_lot = Σ collection_cost_i + handling_cost + transport_cost + urgency_cost
    """
    # 1. Collection cost
    collection_total = Decimal('0.00')
    for c in contributors:
        if not c.self_delivery:
            c_cost = c.quantity_kg * c.collection_distance_km * collection_rate_per_kg_km
            collection_total += c_cost

    # 2. Handling cost
    handling_total = lot_quantity_kg * handling_fee_per_kg

    # 3. Transport trunk cost
    trunk_rate = get_trunk_tier_rate(lot_quantity_kg)
    transport_total = lot_quantity_kg * trunk_distance_km * trunk_rate

    # 4. Urgency cost
    urgency_total = lot_quantity_kg * urgency_premium_per_kg

    total = collection_total + handling_total + transport_total + urgency_total
    per_kg = (total / lot_quantity_kg) if lot_quantity_kg > 0 else Decimal('0.00')

    return LogisticsCostResult(
        collection_cost=quantize_money(collection_total),
        handling_cost=quantize_money(handling_total),
        transport_cost=quantize_money(transport_total),
        urgency_cost=quantize_money(urgency_total),
        total_logistics_cost=quantize_money(total),
        trunk_rate_per_kg_km=trunk_rate,
        logistics_cost_per_kg=quantize_money(per_kg)
    )


def evaluate_and_rank_destinations(
    lot_quantity_kg: Decimal,
    grade: str,
    remaining_shelf_life_hours: Decimal,
    contributors: List[ContributorPickupInput],
    candidates: List[DestinationCandidateInput],
    safety_buffer_hours: Decimal = Decimal('2.00'),
    avg_speed_kmph: Decimal = Decimal('35.00'),
    platform_rate: Decimal = Decimal('0.04'),
    reserve_rate: Decimal = Decimal('0.01'),
    hours_to_deadline: Optional[Decimal] = None
) -> List[EvaluatedDestination]:
    """
    D3 §3, §4, §11:
    Filters candidates by feasibility gates and ranks feasible candidates by net return.
    """
    results: List[EvaluatedDestination] = []

    for c in candidates:
        travel_time = c.road_distance_km / avg_speed_kmph

        # Compute cost for this destination
        cost_res = calculate_logistics_cost(
            lot_quantity_kg=lot_quantity_kg,
            trunk_distance_km=c.road_distance_km,
            contributors=contributors
        )

        l_per_kg = cost_res.logistics_cost_per_kg
        multiplier = Decimal('1.00') - platform_rate - reserve_rate
        net_return = (c.gross_price_per_kg - l_per_kg) * multiplier

        # Feasibility check
        is_feasible = True
        rejection_reason = None

        if grade not in c.accepted_grades:
            is_feasible = False
            rejection_reason = "GRADE"
        elif lot_quantity_kg > c.daily_capacity_kg or lot_quantity_kg < c.min_order_kg:
            is_feasible = False
            rejection_reason = "CAPACITY"
        elif (travel_time + safety_buffer_hours) > remaining_shelf_life_hours:
            is_feasible = False
            rejection_reason = "SHELF_LIFE"
        elif hours_to_deadline is not None and travel_time > hours_to_deadline:
            is_feasible = False
            rejection_reason = "DEADLINE"
        elif net_return <= Decimal('0.00'):
            is_feasible = False
            rejection_reason = "UNECONOMIC"

        results.append(EvaluatedDestination(
            destination_id=c.destination_id,
            buyer_name=c.buyer_name,
            channel=c.channel,
            gross_price_per_kg=quantize_money(c.gross_price_per_kg),
            logistics_cost=cost_res.total_logistics_cost,
            logistics_cost_per_kg=l_per_kg,
            net_return_per_kg=quantize_money(net_return),
            distance_km=quantize_money(c.road_distance_km),
            travel_time_hours=quantize_money(travel_time),
            is_feasible=is_feasible,
            rejection_reason=rejection_reason
        ))

    # Rank: feasible first, sorted descending by net_return_per_kg
    results.sort(key=lambda d: (1 if d.is_feasible else 0, d.net_return_per_kg), reverse=True)
    return results
