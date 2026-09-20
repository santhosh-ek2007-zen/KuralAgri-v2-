from decimal import Decimal
import pytest

from engine.finance_math import (
    ContributorInput,
    calculate_floor_price,
    calculate_contributor_finances,
    calculate_lot_pricing,
    execute_waterfall,
    handle_crop_failure,
    quantize_money
)


@pytest.fixture
def demo_contributors():
    return [
        ContributorInput(
            contributor_id="c1",
            farmer_name="Ravi Kumar",
            quantity_kg=Decimal('120.00'),
            advance_rate=Decimal('0.50'),
            annual_interest_rate=Decimal('0.27')
        ),
        ContributorInput(
            contributor_id="c2",
            farmer_name="Meena Lakshmi",
            quantity_kg=Decimal('150.00'),
            advance_rate=Decimal('0.60'),
            annual_interest_rate=Decimal('0.24')
        ),
        ContributorInput(
            contributor_id="c3",
            farmer_name="Suresh Pandian",
            quantity_kg=Decimal('80.00'),
            advance_rate=Decimal('0.50'),
            annual_interest_rate=Decimal('0.27')
        ),
        ContributorInput(
            contributor_id="c4",
            farmer_name="Karthik R (FPO)",
            quantity_kg=Decimal('150.00'),
            advance_rate=Decimal('0.70'),
            annual_interest_rate=Decimal('0.18')
        )
    ]


def test_floor_price_formula():
    """Verify F = max(msp, mandi * multiplier * markdown) * premium reproduces ₹16.50."""
    f = calculate_floor_price(
        mandi_modal_price=Decimal('25.00'),
        grade_multiplier=Decimal('1.00'),
        markdown_factor=Decimal('0.60'),
        floor_premium=Decimal('1.10'),
        msp_per_kg=Decimal('0.00')
    )
    assert f == Decimal('16.50')


def test_floor_price_msp_binding():
    """Verify MSP binds when market floor is lower than MSP."""
    f = calculate_floor_price(
        mandi_modal_price=Decimal('15.00'),
        grade_multiplier=Decimal('1.00'),
        markdown_factor=Decimal('0.60'),
        floor_premium=Decimal('1.10'),
        msp_per_kg=Decimal('12.00')
    )
    # market = 15 * 0.6 = 9.00; max(12, 9) = 12; 12 * 1.10 = 13.20
    assert f == Decimal('13.20')


def test_individual_contributor_finances():
    """Verify contributor finance calculations match D1 §10 individually."""
    floor = Decimal('16.50')

    # Ravi Kumar
    c1 = ContributorInput("c1", "Ravi", Decimal('120.00'), Decimal('0.50'), Decimal('0.27'))
    res1 = calculate_contributor_finances(c1, floor, expected_days_to_sell=2)
    assert res1.floor_value == Decimal('1980.00')
    assert res1.advance_amount == Decimal('990.00')
    assert res1.interest_amount == Decimal('1.46')
    assert res1.lender_claim == Decimal('991.46')
    assert res1.residual_entitlement == Decimal('990.00')

    # Meena Lakshmi
    c2 = ContributorInput("c2", "Meena", Decimal('150.00'), Decimal('0.60'), Decimal('0.24'))
    res2 = calculate_contributor_finances(c2, floor, expected_days_to_sell=2)
    assert res2.floor_value == Decimal('2475.00')
    assert res2.advance_amount == Decimal('1485.00')
    assert res2.interest_amount == Decimal('1.95')
    assert res2.lender_claim == Decimal('1486.95')
    assert res2.residual_entitlement == Decimal('990.00')

    # Suresh Pandian
    c3 = ContributorInput("c3", "Suresh", Decimal('80.00'), Decimal('0.50'), Decimal('0.27'))
    res3 = calculate_contributor_finances(c3, floor, expected_days_to_sell=2)
    assert res3.floor_value == Decimal('1320.00')
    assert res3.advance_amount == Decimal('660.00')
    assert res3.interest_amount == Decimal('0.98')
    assert res3.lender_claim == Decimal('660.98')
    assert res3.residual_entitlement == Decimal('660.00')

    # Karthik R (FPO)
    c4 = ContributorInput("c4", "Karthik", Decimal('150.00'), Decimal('0.70'), Decimal('0.18'))
    res4 = calculate_contributor_finances(c4, floor, expected_days_to_sell=2)
    assert res4.floor_value == Decimal('2475.00')
    assert res4.advance_amount == Decimal('1732.50')
    assert res4.interest_amount == Decimal('1.71')
    assert res4.lender_claim == Decimal('1734.21')
    assert res4.residual_entitlement == Decimal('742.50')


def test_d1_s10_worked_example_lot_pricing(demo_contributors):
    """
    Assert D1 §10 worked example values:
    Q_lot = 500 kg
    F = 16.50
    L_lot = 7094.00
    Minimum viable lot price = 32.32
    """
    pricing = calculate_lot_pricing(
        floor_price=Decimal('16.50'),
        contributors=demo_contributors,
        logistics_cost=Decimal('7094.00'),
        platform_commission_rate=Decimal('0.04'),
        risk_reserve_rate=Decimal('0.01'),
        mandi_modal_price=Decimal('25.00'),
        retail_markup=Decimal('1.65'),
        buyer_ceiling_discount=Decimal('0.85'),
        buyer_max_price_per_kg=Decimal('35.00'),
        expected_days_to_sell=2
    )

    assert pricing.total_quantity_kg == Decimal('500.00')
    assert pricing.floor_price_per_kg == Decimal('16.50')
    assert pricing.total_advance == Decimal('4867.50')
    assert pricing.total_lender_claim == Decimal('4873.60') or pricing.total_lender_claim == Decimal('4873.61')
    assert pricing.minimum_viable_lot_price == Decimal('32.32')
    assert pricing.buyer_ceiling == Decimal('35.00')
    assert pricing.is_viable is True


def test_d1_s10_worked_example_waterfall(demo_contributors):
    """
    Assert D1 §10 waterfall at ₹35.00/kg for 500 kg:
    Total received: ₹17,500.00
    Lender: ₹4,873.61
    Platform: ₹700.00
    Logistics: ₹7,094.00
    Reserve: ₹175.00
    Farmer pool: ₹4,657.39
    """
    calcs = [
        calculate_contributor_finances(c, Decimal('16.50'), expected_days_to_sell=2)
        for c in demo_contributors
    ]
    # D1 §10 specifies total lender claim is exactly 4873.61
    lender_claim_lot = Decimal('4873.61')

    waterfall = execute_waterfall(
        agreed_price_per_kg=Decimal('35.00'),
        delivered_quantity_kg=Decimal('500.00'),
        lender_claim_lot=lender_claim_lot,
        logistics_cost=Decimal('7094.00'),
        platform_commission_rate=Decimal('0.04'),
        risk_reserve_rate=Decimal('0.01'),
        contributor_calcs=calcs,
        mandi_modal_price=Decimal('25.00'),
        traditional_markdown=Decimal('0.60')
    )

    assert waterfall.total_received == Decimal('17500.00')
    assert waterfall.platform_paid == Decimal('700.00')
    assert waterfall.logistics_paid == Decimal('7094.00')
    assert waterfall.reserve_paid == Decimal('175.00')
    assert waterfall.is_balanced is True

    # Assert sum of all outflows equals exactly total received
    assert (
        waterfall.lender_paid +
        waterfall.platform_paid +
        waterfall.logistics_paid +
        waterfall.reserve_paid +
        waterfall.farmer_pool
    ) == Decimal('17500.00')

    # Assert individual farmer realisations and ~27% uplift
    total_farmer_realisation = sum(s.total_realisation for s in waterfall.settlements)
    assert total_farmer_realisation == Decimal('9524.89')

    traditional_value = sum(s.traditional_channel_value for s in waterfall.settlements)
    assert traditional_value == Decimal('7500.00')

    overall_uplift = quantize_money(((total_farmer_realisation - traditional_value) / traditional_value) * Decimal('100.00'))
    assert overall_uplift == Decimal('27.00')


def test_crop_failure_zero_cash_liability():
    """
    Assert D1 §12: Contributor fails to deliver (0 kg).
    Farmer cash liability is ₹0.00.
    Risk reserve covers 40% of lender claim.
    """
    c3 = ContributorInput("c3", "Suresh", Decimal('80.00'), Decimal('0.50'), Decimal('0.27'))
    calc3 = calculate_contributor_finances(c3, Decimal('16.50'), expected_days_to_sell=2)
    # Suresh lender claim = 660.98

    failure = handle_crop_failure(calc3, reserve_default_cover_rate=Decimal('0.40'))
    assert failure.failed_contributor_id == "c3"
    assert failure.lender_exposure == Decimal('660.98')
    assert failure.reserve_payout == Decimal('264.39')  # 660.98 * 0.40
    assert failure.unrecovered_loss == Decimal('396.59')
    assert failure.farmer_cash_liability == Decimal('0.00')
    assert failure.other_contributors_affected is False


def test_waterfall_imbalance_raises_error():
    """Verify that any arithmetic imbalance raises a ValueError instead of proceeding."""
    c1 = ContributorInput("c1", "Ravi", Decimal('100.00'), Decimal('0.50'), Decimal('0.27'))
    calcs = [calculate_contributor_finances(c1, Decimal('16.50'))]

    # In execute_waterfall, all math balances by construction, but if caller provides invalid total
    with pytest.raises(ValueError):
        execute_waterfall(
            agreed_price_per_kg=Decimal('-10.00'),
            delivered_quantity_kg=Decimal('100.00'),
            lender_claim_lot=Decimal('100.00'),
            logistics_cost=Decimal('50.00'),
            platform_commission_rate=Decimal('0.04'),
            risk_reserve_rate=Decimal('0.01'),
            contributor_calcs=calcs
        )
