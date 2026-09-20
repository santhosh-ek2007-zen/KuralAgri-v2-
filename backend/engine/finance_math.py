"""
KuralAgri Financial Engine — Pure Python Implementation.
No Django or database imports allowed.
Implements the exact formulas from D1 §4, §5, §7, §8, §9, §10, §12.
All currency arithmetic is Decimal with ROUND_HALF_UP.
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict

TWO_PLACES = Decimal('0.01')
FOUR_PLACES = Decimal('0.0001')


def quantize_money(val: Decimal) -> Decimal:
    """Quantize to 2 decimal places with ROUND_HALF_UP."""
    return Decimal(str(val)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class ContributorInput:
    contributor_id: str
    farmer_name: str
    quantity_kg: Decimal
    advance_rate: Decimal        # e.g., Decimal('0.50') for 50%
    annual_interest_rate: Decimal  # e.g., Decimal('0.27') for 27%
    self_delivery: bool = False


@dataclass
class ContributorCalculation:
    contributor_id: str
    farmer_name: str
    quantity_kg: Decimal
    floor_value: Decimal          # V_i = F * Q_i
    advance_amount: Decimal       # A_i = V_i * advance_rate
    interest_amount: Decimal      # I_i = A_i * r * d / 365
    lender_claim: Decimal         # A_i + I_i
    residual_entitlement: Decimal # N_i = V_i - A_i


@dataclass
class ContributorSettlement:
    contributor_id: str
    farmer_name: str
    advance_paid: Decimal
    settlement_paid: Decimal
    total_realisation: Decimal
    traditional_channel_value: Decimal
    uplift_pct: Decimal


@dataclass
class LotPricingResult:
    floor_price_per_kg: Decimal
    total_quantity_kg: Decimal
    total_floor_value: Decimal
    total_advance: Decimal
    total_interest: Decimal
    total_lender_claim: Decimal
    total_residual_entitlement: Decimal
    logistics_cost: Decimal
    logistics_cost_per_kg: Decimal
    interest_per_kg: Decimal
    minimum_viable_lot_price: Decimal
    retail_ceiling: Decimal
    buyer_ceiling: Decimal
    is_viable: bool
    contributions: List[ContributorCalculation] = field(default_factory=list)


@dataclass
class WaterfallResult:
    total_received: Decimal
    lender_paid: Decimal
    platform_paid: Decimal
    logistics_paid: Decimal
    reserve_paid: Decimal
    farmer_pool: Decimal
    is_balanced: bool
    settlements: List[ContributorSettlement] = field(default_factory=list)


@dataclass
class CropFailureResult:
    failed_contributor_id: str
    lender_exposure: Decimal
    reserve_payout: Decimal
    unrecovered_loss: Decimal
    farmer_cash_liability: Decimal
    other_contributors_affected: bool


def calculate_floor_price(
    mandi_modal_price: Decimal,
    grade_multiplier: Decimal,
    markdown_factor: Decimal,
    floor_premium: Decimal,
    msp_per_kg: Decimal = Decimal('0.00')
) -> Decimal:
    """
    D1 §4:
    grade_benchmark = mandi_modal_price * grade_multiplier
    F = max(msp, grade_benchmark * markdown_factor) * floor_premium
    """
    grade_benchmark = mandi_modal_price * grade_multiplier
    market_floor = grade_benchmark * markdown_factor
    base = max(msp_per_kg, market_floor)
    raw_floor = base * floor_premium
    return quantize_money(raw_floor)


def calculate_contributor_finances(
    contributor: ContributorInput,
    floor_price: Decimal,
    expected_days_to_sell: int = 2
) -> ContributorCalculation:
    """
    Per-contributor calculations (D1 §4 & §10):
    V_i = F * Q_i
    A_i = V_i * advance_rate
    I_i = A_i * r_i * d / 365
    lender_claim_i = A_i + I_i
    N_i = V_i - A_i
    """
    v_i = quantize_money(floor_price * contributor.quantity_kg)
    a_i = quantize_money(v_i * contributor.advance_rate)
    
    # Interest: A_i * r * d / 365
    days = Decimal(str(expected_days_to_sell))
    days_in_year = Decimal('365')
    raw_interest = (a_i * contributor.annual_interest_rate * days) / days_in_year
    i_i = quantize_money(raw_interest)
    
    lender_claim_i = a_i + i_i
    n_i = v_i - a_i

    return ContributorCalculation(
        contributor_id=contributor.contributor_id,
        farmer_name=contributor.farmer_name,
        quantity_kg=contributor.quantity_kg,
        floor_value=v_i,
        advance_amount=a_i,
        interest_amount=i_i,
        lender_claim=lender_claim_i,
        residual_entitlement=n_i
    )


def calculate_lot_pricing(
    floor_price: Decimal,
    contributors: List[ContributorInput],
    logistics_cost: Decimal,
    platform_commission_rate: Decimal = Decimal('0.04'),
    risk_reserve_rate: Decimal = Decimal('0.01'),
    mandi_modal_price: Decimal = Decimal('25.00'),
    retail_markup: Decimal = Decimal('1.65'),
    buyer_ceiling_discount: Decimal = Decimal('0.85'),
    buyer_max_price_per_kg: Optional[Decimal] = None,
    expected_days_to_sell: int = 2
) -> LotPricingResult:
    """
    D1 §7 & §10:
    minimum_viable_lot_price = (F + I_lot/Q_lot + L_lot/Q_lot) / (1 - platform_rate - reserve_rate)
    """
    calcs = [
        calculate_contributor_finances(c, floor_price, expected_days_to_sell)
        for c in contributors
    ]

    total_q = sum((c.quantity_kg for c in calcs), Decimal('0'))
    if total_q <= Decimal('0'):
        raise ValueError("Total quantity must be greater than zero.")

    total_v = sum((c.floor_value for c in calcs), Decimal('0'))
    total_a = sum((c.advance_amount for c in calcs), Decimal('0'))
    total_i = sum((c.interest_amount for c in calcs), Decimal('0'))
    total_lender_claim = sum((c.lender_claim for c in calcs), Decimal('0'))
    total_n = sum((c.residual_entitlement for c in calcs), Decimal('0'))

    interest_per_kg = total_i / total_q
    logistics_per_kg = logistics_cost / total_q

    denominator = Decimal('1.00') - platform_commission_rate - risk_reserve_rate
    if denominator <= Decimal('0'):
        raise ValueError("Sum of platform and reserve rates cannot equal or exceed 100%.")

    numerator = floor_price + interest_per_kg + logistics_per_kg
    min_viable = quantize_money(numerator / denominator)

    retail_ceiling = quantize_money(mandi_modal_price * retail_markup * buyer_ceiling_discount)
    buyer_ceiling = min(retail_ceiling, buyer_max_price_per_kg) if buyer_max_price_per_kg is not None else retail_ceiling
    is_viable = min_viable <= buyer_ceiling

    return LotPricingResult(
        floor_price_per_kg=floor_price,
        total_quantity_kg=total_q,
        total_floor_value=total_v,
        total_advance=total_a,
        total_interest=total_i,
        total_lender_claim=total_lender_claim,
        total_residual_entitlement=total_n,
        logistics_cost=logistics_cost,
        logistics_cost_per_kg=quantize_money(logistics_per_kg),
        interest_per_kg=quantize_money(interest_per_kg),
        minimum_viable_lot_price=min_viable,
        retail_ceiling=retail_ceiling,
        buyer_ceiling=buyer_ceiling,
        is_viable=is_viable,
        contributions=calcs
    )


def execute_waterfall(
    agreed_price_per_kg: Decimal,
    delivered_quantity_kg: Decimal,
    lender_claim_lot: Decimal,
    logistics_cost: Decimal,
    platform_commission_rate: Decimal,
    risk_reserve_rate: Decimal,
    contributor_calcs: List[ContributorCalculation],
    mandi_modal_price: Decimal = Decimal('25.00'),
    traditional_markdown: Decimal = Decimal('0.60')
) -> WaterfallResult:
    """
    D1 §9:
    Priority order:
    1. Lender claim (A_lot + I_lot)
    2. Platform commission
    3. Logistics payout
    4. Risk reserve
    5. Farmer pool (split pro-rata by N_i / N_lot)

    Strict assertion:
    lender_paid + platform_paid + logistics_paid + reserve_paid + farmer_pool == total_received
    """
    if agreed_price_per_kg <= Decimal('0') or delivered_quantity_kg <= Decimal('0'):
        raise ValueError("Agreed price and delivered quantity must be strictly positive.")

    total_received = quantize_money(agreed_price_per_kg * delivered_quantity_kg)
    if total_received <= Decimal('0'):
        raise ValueError("Total received must be strictly positive.")

    remaining = total_received

    # 1. Lender
    lender_paid = min(lender_claim_lot, remaining)
    remaining -= lender_paid

    # 2. Platform commission
    platform_paid = min(quantize_money(total_received * platform_commission_rate), remaining)
    remaining -= platform_paid

    # 3. Logistics
    logistics_paid = min(logistics_cost, remaining)
    remaining -= logistics_paid

    # 4. Risk reserve
    reserve_paid = min(quantize_money(total_received * risk_reserve_rate), remaining)
    remaining -= reserve_paid

    # 5. Farmer pool
    farmer_pool = remaining

    # Assert balance
    outflows = lender_paid + platform_paid + logistics_paid + reserve_paid + farmer_pool
    if outflows != total_received:
        raise ValueError(f"Waterfall imbalance: received ₹{total_received}, outflows ₹{outflows}")

    # Pro-rata distribution of farmer pool by residual entitlement N_i
    n_lot = sum((c.residual_entitlement for c in contributor_calcs), Decimal('0'))
    settlements: List[ContributorSettlement] = []

    if n_lot > Decimal('0') and farmer_pool > Decimal('0'):
        allocated_so_far = Decimal('0.00')
        sorted_indices = sorted(
            range(len(contributor_calcs)),
            key=lambda idx: contributor_calcs[idx].residual_entitlement,
            reverse=True
        )

        settlement_amounts = [Decimal('0.00')] * len(contributor_calcs)
        for idx in range(len(contributor_calcs)):
            c = contributor_calcs[idx]
            raw_share = (farmer_pool * c.residual_entitlement) / n_lot
            settlement_amounts[idx] = quantize_money(raw_share)
            allocated_so_far += settlement_amounts[idx]

        # Assign any rounding discrepancy (paisa) to the largest residual entitlement
        discrepancy = farmer_pool - allocated_so_far
        if discrepancy != Decimal('0.00') and sorted_indices:
            settlement_amounts[sorted_indices[0]] += discrepancy

        for idx, c in enumerate(contributor_calcs):
            s_i = settlement_amounts[idx]
            total_realisation = c.advance_amount + s_i
            trad_val = quantize_money(c.quantity_kg * mandi_modal_price * traditional_markdown)
            uplift_pct = Decimal('0.00')
            if trad_val > Decimal('0.00'):
                uplift_pct = quantize_money(((total_realisation - trad_val) / trad_val) * Decimal('100.00'))

            settlements.append(ContributorSettlement(
                contributor_id=c.contributor_id,
                farmer_name=c.farmer_name,
                advance_paid=c.advance_amount,
                settlement_paid=s_i,
                total_realisation=total_realisation,
                traditional_channel_value=trad_val,
                uplift_pct=uplift_pct
            ))
    else:
        for c in contributor_calcs:
            trad_val = quantize_money(c.quantity_kg * mandi_modal_price * traditional_markdown)
            settlements.append(ContributorSettlement(
                contributor_id=c.contributor_id,
                farmer_name=c.farmer_name,
                advance_paid=c.advance_amount,
                settlement_paid=Decimal('0.00'),
                total_realisation=c.advance_amount,
                traditional_channel_value=trad_val,
                uplift_pct=Decimal('0.00')
            ))

    return WaterfallResult(
        total_received=total_received,
        lender_paid=lender_paid,
        platform_paid=platform_paid,
        logistics_paid=logistics_paid,
        reserve_paid=reserve_paid,
        farmer_pool=farmer_pool,
        is_balanced=True,
        settlements=settlements
    )


def handle_crop_failure(
    failed_calc: ContributorCalculation,
    reserve_default_cover_rate: Decimal = Decimal('0.40')
) -> CropFailureResult:
    """
    D1 §12:
    Failed contributor delivers 0 kg.
    Lender exposure = lender_claim_i
    Risk reserve covers: exposure * reserve_default_cover_rate (40%)
    Unrecovered lender loss = exposure - reserve_payout
    Farmer cash liability = ₹0.00 (Protected!)
    """
    exposure = failed_calc.lender_claim
    reserve_payout = quantize_money(exposure * reserve_default_cover_rate)
    unrecovered_loss = exposure - reserve_payout

    return CropFailureResult(
        failed_contributor_id=failed_calc.contributor_id,
        lender_exposure=exposure,
        reserve_payout=reserve_payout,
        unrecovered_loss=unrecovered_loss,
        farmer_cash_liability=Decimal('0.00'),
        other_contributors_affected=False
    )
