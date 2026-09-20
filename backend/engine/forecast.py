"""
Demand Forecasting Engine — Pure Python Implementation.
No Django or database imports.
Implements D2 §2:
Seasonal-naive with trend and multiplicative environmental adjustments (SEASONAL_NAIVE_V1).
Produces 7-day demand projections and daily series breakdown with complete explainability.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np


@dataclass
class DemandForecastOutput:
    forecast_total_kg: float
    daily_average_kg: float
    per_day_series: List[Dict[str, Any]]
    demand_level: str  # HIGH, NORMAL, LOW
    confidence: str    # HIGH, MEDIUM, LOW
    factors: List[Dict[str, str]]
    method: str        # SEASONAL_NAIVE_V1 | FALLBACK_AVERAGE


def compute_demand_forecast(
    historical_daily_demand: List[float],
    horizon_days: int = 7,
    month: int = 9,
    crop_category: str = 'VEGETABLE',
    weather_condition: str = 'CLEAR'
) -> DemandForecastOutput:
    """
    Generate seasonal-naive demand forecast with trend and environmental factors.
    """
    factors: List[Dict[str, str]] = []
    n_days = len(historical_daily_demand)

    if n_days < 14:
        # Fallback average
        base_avg = float(np.mean(historical_daily_demand)) if n_days > 0 else 500.0
        total = base_avg * horizon_days
        factors.append({
            "factor": "Sparse Data Fallback",
            "effect": f"{base_avg:.1f} kg/day",
            "detail": f"History has only {n_days} days (minimum 14 required for trend)."
        })
        per_day = [{"day_offset": i + 1, "predicted_demand_kg": round(base_avg, 2)} for i in range(horizon_days)]
        return DemandForecastOutput(
            forecast_total_kg=round(total, 2),
            daily_average_kg=round(base_avg, 2),
            per_day_series=per_day,
            demand_level="NORMAL",
            confidence="LOW",
            factors=factors,
            method="FALLBACK_AVERAGE"
        )

    # 1. Base daily demand (last 28 days)
    recent_window = historical_daily_demand[-28:] if n_days >= 28 else historical_daily_demand
    base_daily = float(np.mean(recent_window))
    factors.append({
        "factor": "28-Day Baseline Demand",
        "effect": f"{base_daily:.1f} kg/day",
        "detail": "Trailing 4-week mean daily consumption."
    })

    # 2. Trend factor (last 7 days vs previous 21 days)
    if n_days >= 28:
        mean_7 = float(np.mean(historical_daily_demand[-7:]))
        mean_prev_21 = float(np.mean(historical_daily_demand[-28:-7]))
        raw_trend = (mean_7 / mean_prev_21) if mean_prev_21 > 0 else 1.0
        trend_factor = float(np.clip(raw_trend, 0.80, 1.25))
    else:
        trend_factor = 1.0

    trend_pct = (trend_factor - 1.0) * 100.0
    factors.append({
        "factor": "Demand Trend",
        "effect": f"{trend_pct:+.1f}%",
        "detail": f"Short-term 7-day velocity relative to baseline."
    })

    # 3. Seasonal index (month-based)
    # Seasonal peak for vegetables typically late monsoon / winter (Nov-Feb)
    seasonal_multipliers = {
        1: 1.15, 2: 1.10, 3: 1.00, 4: 0.90, 5: 0.85, 6: 0.90,
        7: 0.95, 8: 1.00, 9: 1.05, 10: 1.10, 11: 1.20, 12: 1.25
    }
    seasonal_index = seasonal_multipliers.get(month, 1.0)
    seasonal_pct = (seasonal_index - 1.0) * 100.0
    if abs(seasonal_pct) > 0.01:
        factors.append({
            "factor": "Monthly Seasonality",
            "effect": f"{seasonal_pct:+.1f}%",
            "detail": f"Historical consumption pattern for month {month}."
        })

    # 4. Weather factor
    weather_multipliers = {
        'CLEAR': 1.00,
        'RAIN': 0.95,
        'HEAVY_RAIN': 0.88,
        'HEATWAVE': 0.92
    }
    weather_factor = weather_multipliers.get(weather_condition.upper(), 1.00)
    weather_pct = (weather_factor - 1.0) * 100.0
    if abs(weather_pct) > 0.01:
        factors.append({
            "factor": "Weather Condition",
            "effect": f"{weather_pct:+.1f}%",
            "detail": f"Adjustment for {weather_condition} condition."
        })

    total_forecast = base_daily * horizon_days * trend_factor * seasonal_index * weather_factor
    daily_avg = total_forecast / horizon_days

    # 5. Demand level determination (compare against 7-day rolling totals)
    if n_days >= 35:
        rolling_7 = [sum(historical_daily_demand[i:i+7]) for i in range(len(historical_daily_demand) - 7)]
        p75 = float(np.percentile(rolling_7, 75))
        p25 = float(np.percentile(rolling_7, 25))
        if total_forecast >= p75:
            demand_level = 'HIGH'
        elif total_forecast <= p25:
            demand_level = 'LOW'
        else:
            demand_level = 'NORMAL'
    else:
        demand_level = 'NORMAL'

    # 6. Confidence
    if n_days >= 60:
        confidence = 'HIGH'
    elif n_days >= 28:
        confidence = 'MEDIUM'
    else:
        confidence = 'LOW'

    # Per-day series with slight weekly pattern (weekend bump)
    per_day = []
    day_weights = [0.95, 0.95, 1.00, 1.00, 1.05, 1.10, 0.95]
    for i in range(horizon_days):
        w = day_weights[i % 7]
        d_val = daily_avg * w
        per_day.append({
            "day_offset": i + 1,
            "predicted_demand_kg": round(d_val, 2)
        })

    return DemandForecastOutput(
        forecast_total_kg=round(total_forecast, 2),
        daily_average_kg=round(daily_avg, 2),
        per_day_series=per_day,
        demand_level=demand_level,
        confidence=confidence,
        factors=factors,
        method="SEASONAL_NAIVE_V1"
    )
