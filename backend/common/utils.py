"""
Common utilities for numerical precision and money formatting.
Enforces Decimal(12, 2) rounding HALF_UP across all operations.
"""
from decimal import Decimal, ROUND_HALF_UP

TWO_PLACES = Decimal('0.01')


def round_money(val) -> Decimal:
    """
    Round a monetary amount to 2 decimal places using ROUND_HALF_UP.
    Guarantees no floating-point drift.
    """
    if val is None:
        return Decimal('0.00')
    if isinstance(val, (int, str)):
        d = Decimal(str(val))
    elif isinstance(val, float):
        d = Decimal(str(val))
    elif isinstance(val, Decimal):
        d = val
    else:
        d = Decimal(str(val))
    return d.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def format_inr(val) -> str:
    """Format decimal as INR currency string, e.g. ₹1,23,456.78"""
    d = round_money(val)
    return f"₹{d:,.2f}"
