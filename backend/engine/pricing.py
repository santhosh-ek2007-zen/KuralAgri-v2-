"""
Pricing Recommendation Engine — Pure Python Implementation.
No Django or database imports.
Implements D2 §3 & §7:
Emits defensible recommended price range constrained by farmer floor and minimum viable price,
along with structured explanation factors for explainability.
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any

TWO_PLACES = Decimal('0.01')


def quantize_money(val: Decimal) -> Decimal:
    return Decimal(str(val)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class ExplanationFactor:
    factor: str
    effect: str   # e.g. "+6.0%", "Floor Bound", etc.
    detail: str


@dataclass
class PriceRecommendationOutput:
    recommended_min_per_kg: Decimal
    recommended_max_per_kg: Decimal
    benchmark_price_per_kg: Decimal
    floor_price_per_kg: Decimal
    minimum_viable_price_per_kg: Optional[Decimal]
    ceiling_price_per_kg: Optional[Decimal]
    confidence: str  # HIGH, MEDIUM, LOW
    explanation: List[Dict[str, str]]
    summary: str


def recommend_price(
    mandi_benchmark: Decimal,
    grade: str,
    grade_multiplier: Decimal,
    floor_price: Decimal,
    minimum_viable_price: Optional[Decimal] = None,
    buyer_ceiling: Optional[Decimal] = None,
    demand_signal: str = 'NORMAL',       # HIGH, NORMAL, LOW
    supply_signal: str = 'NORMAL',       # HIGH, NORMAL, LOW
    quantity_kg: Decimal = Decimal('100.00'),
    weather_risk: str = 'LOW',           # HIGH, MEDIUM, LOW
    perishability_class: str = 'A',
    market_confidence: str = 'MEDIUM',
    forecast_confidence: str = 'MEDIUM'
) -> PriceRecommendationOutput:
    """
    Compute price recommendation range with complete explainability factors.
    """
    factors: List[Dict[str, str]] = []

    # 1. Base benchmark and grade multiplier
    base = mandi_benchmark * grade_multiplier
    factors.append({
        "factor": "Mandi Benchmark",
        "effect": f"₹{quantize_money(mandi_benchmark)}/kg",
        "detail": f"Reference modal price for region."
    })
    if grade != 'A':
        factors.append({
            "factor": f"Grade {grade} Multiplier",
            "effect": f"×{grade_multiplier}",
            "detail": f"Grade adjustment relative to reference Grade A."
        })

    # 2. Demand adjustment
    demand_adj = Decimal('0.00')
    if demand_signal == 'HIGH':
        demand_adj = Decimal('0.06')
        factors.append({"factor": "High Market Demand", "effect": "+6.0%", "detail": "Recent buyer order volume exceeds historical baseline."})
    elif demand_signal == 'LOW':
        demand_adj = Decimal('-0.05')
        factors.append({"factor": "Low Market Demand", "effect": "-5.0%", "detail": "Subdued buyer requirement activity."})

    # 3. Supply adjustment
    supply_adj = Decimal('0.00')
    if supply_signal == 'LOW':
        supply_adj = Decimal('0.04')
        factors.append({"factor": "Constrained Supply", "effect": "+4.0%", "detail": "Mandi arrivals and active listings down significantly."})
    elif supply_signal == 'HIGH':
        supply_adj = Decimal('-0.04')
        factors.append({"factor": "Surplus Supply", "effect": "-4.0%", "detail": "Elevated arrivals in regional aggregation hubs."})

    # 4. Quantity bulk premium
    quantity_adj = Decimal('0.00')
    if quantity_kg >= Decimal('500.00'):
        quantity_adj = Decimal('0.02')
        factors.append({"factor": "Bulk Order Premium", "effect": "+2.0%", "detail": "Lot size >= 500 kg provides commercial aggregation efficiency."})

    # 5. Weather urgency
    urgency_adj = Decimal('0.00')
    if weather_risk == 'HIGH' and perishability_class == 'A':
        urgency_adj = Decimal('0.02')
        factors.append({"factor": "Perishability / Weather Urgency", "effect": "+2.0%", "detail": "Heavy weather forecast accelerates immediate off-take demand."})

    total_adj = demand_adj + supply_adj + quantity_adj + urgency_adj
    # Clamp to [-0.12, +0.15]
    total_adj = max(Decimal('-0.12'), min(Decimal('0.15'), total_adj))

    centre = base * (Decimal('1.00') + total_adj)
    raw_min = centre * Decimal('0.95')
    raw_max = centre * Decimal('1.05')

    lower_bound = floor_price
    if minimum_viable_price is not None and minimum_viable_price > lower_bound:
        lower_bound = minimum_viable_price

    factors.append({
        "factor": "Protected Floor Price",
        "effect": f"₹{quantize_money(floor_price)}/kg",
        "detail": "Guaranteed minimum farmer realization."
    })

    logistics_pushed = False
    if minimum_viable_price is not None and minimum_viable_price > raw_max:
        logistics_pushed = True
        factors.append({
            "factor": "Minimum Viable Price Constraint",
            "effect": f"₹{quantize_money(minimum_viable_price)}/kg",
            "detail": "Logistics cost and financing raised the viable price above the market band."
        })

    # Final range determination
    final_min = max(raw_min, lower_bound)
    final_max = max(raw_max, lower_bound)

    if buyer_ceiling is not None:
        final_max = min(final_max, buyer_ceiling)

    # Determine confidence
    conf_map = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
    rev_conf = {3: 'HIGH', 2: 'MEDIUM', 1: 'LOW'}
    combined_score = min(conf_map.get(market_confidence, 2), conf_map.get(forecast_confidence, 2))
    if logistics_pushed and combined_score > 1:
        combined_score -= 1
    confidence = rev_conf[combined_score]

    summary = f"Recommended: ₹{quantize_money(final_min)}–₹{quantize_money(final_max)}/kg based on mandi modal ₹{quantize_money(mandi_benchmark)} with {confidence} confidence."

    return PriceRecommendationOutput(
        recommended_min_per_kg=quantize_money(final_min),
        recommended_max_per_kg=quantize_money(final_max),
        benchmark_price_per_kg=quantize_money(mandi_benchmark),
        floor_price_per_kg=quantize_money(floor_price),
        minimum_viable_price_per_kg=quantize_money(minimum_viable_price) if minimum_viable_price else None,
        ceiling_price_per_kg=quantize_money(buyer_ceiling) if buyer_ceiling else None,
        confidence=confidence,
        explanation=factors,
        summary=summary
    )
