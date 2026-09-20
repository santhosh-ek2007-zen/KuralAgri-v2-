"""
Intelligence domain services implementing D2 specifications.
Orchestrates Market Intelligence, Demand Forecasting, and Price Recommendation.
"""
from decimal import Decimal
from typing import Dict, Any, Optional, List
from django.utils import timezone
from datetime import timedelta

from catalog.models import Crop, Region, CropGradeParam, PlatformSettings
from intelligence.models import (
    MandiPrice,
    WeatherSnapshot,
    DemandHistory,
    MarketSnapshot,
    DemandForecast,
    PriceRecommendation
)
from marketplace.models import BuyerOrder, Listing
from engine.forecast import compute_demand_forecast, DemandForecastOutput
from engine.pricing import recommend_price, PriceRecommendationOutput
from engine.finance_math import calculate_floor_price


class MarketIntelligenceService:
    @staticmethod
    def get_market_snapshot(crop: Crop, region: Region, as_of_date=None) -> MarketSnapshot:
        if as_of_date is None:
            as_of_date = timezone.now().date()

        prices_qs = MandiPrice.objects.filter(
            crop=crop,
            region=region,
            recorded_date__lte=as_of_date
        ).order_by('-recorded_date')

        prices_count = prices_qs.count()
        explanation = []

        if prices_count == 0:
            # Fallback benchmark
            benchmark = Decimal('25.00')
            trend = 'STABLE'
            change_pct = Decimal('0.00')
            supply_signal = 'NORMAL'
            explanation.append({
                "factor": "No Historical Price Data",
                "effect": f"₹{benchmark}/kg",
                "detail": "Default reference modal benchmark applied."
            })
        else:
            latest = prices_qs.first()
            benchmark = latest.modal_price

            # 7-day vs previous 7-day trend
            recent_7 = list(prices_qs[:7])
            prev_7 = list(prices_qs[7:14])

            if len(recent_7) > 0 and len(prev_7) > 0:
                mean_recent = sum((p.modal_price for p in recent_7)) / Decimal(str(len(recent_7)))
                mean_prev = sum((p.modal_price for p in prev_7)) / Decimal(str(len(prev_7)))
                if mean_prev > Decimal('0.00'):
                    change_pct = ((mean_recent - mean_prev) / mean_prev) * Decimal('100.00')
                else:
                    change_pct = Decimal('0.00')

                if change_pct > Decimal('5.00'):
                    trend = 'INCREASING'
                elif change_pct < Decimal('-5.00'):
                    trend = 'DECREASING'
                else:
                    trend = 'STABLE'
            else:
                change_pct = Decimal('0.00')
                trend = 'STABLE'

            # Arrivals supply signal
            if len(recent_7) > 0 and len(prev_7) > 0:
                arr_recent = sum((p.arrivals_kg for p in recent_7)) / Decimal(str(len(recent_7)))
                arr_prev = sum((p.arrivals_kg for p in prev_7)) / Decimal(str(len(prev_7)))
                arr_change = ((arr_recent - arr_prev) / arr_prev * Decimal('100.00')) if arr_prev > 0 else Decimal('0.00')
                if arr_change < Decimal('-10.00'):
                    supply_signal = 'LOW'
                elif arr_change > Decimal('10.00'):
                    supply_signal = 'HIGH'
                else:
                    supply_signal = 'NORMAL'
            else:
                supply_signal = 'NORMAL'

        # Demand signal: compare open orders in next 7 days vs baseline
        next_7_orders = BuyerOrder.objects.filter(
            crop=crop,
            status='OPEN',
            delivery_deadline__lte=timezone.now() + timedelta(days=7)
        )
        total_open_qty = sum((o.quantity_kg for o in next_7_orders), Decimal('0.00'))

        # Check demand history
        history_qs = DemandHistory.objects.filter(crop=crop, region=region).order_by('-recorded_date')[:28]
        if history_qs.exists():
            mean_demand = sum((h.quantity_demanded_kg for h in history_qs)) / Decimal(str(history_qs.count()))
            expected_7d = mean_demand * Decimal('7.00')
            if expected_7d > 0:
                ratio = total_open_qty / expected_7d
                if ratio > Decimal('1.20'):
                    demand_signal = 'HIGH'
                elif ratio < Decimal('0.80'):
                    demand_signal = 'LOW'
                else:
                    demand_signal = 'NORMAL'
            else:
                demand_signal = 'NORMAL'
        else:
            demand_signal = 'HIGH' if total_open_qty > Decimal('500.00') else 'NORMAL'

        # Weather risk
        weather = WeatherSnapshot.objects.filter(region=region, recorded_date__lte=as_of_date).order_by('-recorded_date').first()
        weather_risk = weather.risk_level if weather else 'LOW'

        return MarketSnapshot.objects.create(
            crop=crop,
            region=region,
            benchmark_price=benchmark,
            price_trend=trend,
            price_change_pct=change_pct.quantize(Decimal('0.01')),
            supply_signal=supply_signal,
            demand_signal=demand_signal,
            weather_risk=weather_risk,
            explanation=explanation
        )


class DemandForecastService:
    @staticmethod
    def get_forecast(crop: Crop, region: Region, horizon_days: int = 7) -> DemandForecast:
        # Fetch up to 120 days demand history
        history = list(DemandHistory.objects.filter(crop=crop, region=region).order_by('recorded_date').values_list('quantity_demanded_kg', flat=True))
        daily_series = [float(q) for q in history]

        weather = WeatherSnapshot.objects.filter(region=region).order_by('-recorded_date').first()
        weather_cond = weather.condition if weather else 'CLEAR'

        month = timezone.now().month
        output: DemandForecastOutput = compute_demand_forecast(
            historical_daily_demand=daily_series,
            horizon_days=horizon_days,
            month=month,
            crop_category=crop.category,
            weather_condition=weather_cond
        )

        return DemandForecast.objects.create(
            crop=crop,
            region=region,
            horizon_days=horizon_days,
            forecast_quantity_kg=Decimal(str(output.forecast_total_kg)),
            daily_average_kg=Decimal(str(output.daily_average_kg)),
            per_day_series=output.per_day_series,
            demand_level=output.demand_level,
            confidence=output.confidence,
            explanation=output.factors
        )


class PricingService:
    @staticmethod
    def get_price_recommendation(
        crop: Crop,
        grade: str,
        region: Region,
        quantity_kg: Decimal,
        listing: Optional[Listing] = None,
        minimum_viable_price: Optional[Decimal] = None,
        buyer_ceiling: Optional[Decimal] = None
    ) -> PriceRecommendation:
        # 1. Market snapshot
        snapshot = MarketIntelligenceService.get_market_snapshot(crop, region)

        # 2. Demand forecast
        forecast = DemandForecastService.get_forecast(crop, region, horizon_days=7)

        # 3. Grade multiplier
        grade_param = CropGradeParam.objects.filter(crop=crop, grade=grade).first()
        grade_multiplier = Decimal('1.00') if grade == 'A' else (Decimal('0.80') if grade == 'B' else Decimal('0.65'))

        # 4. Protected Floor price (D1 §4 via engine)
        settings = PlatformSettings.get_settings()
        floor_premium = Decimal('1.10')
        markdown = Decimal('0.60')

        floor_price = calculate_floor_price(
            mandi_modal_price=snapshot.benchmark_price,
            grade_multiplier=grade_multiplier,
            markdown_factor=markdown,
            floor_premium=floor_premium,
            msp_per_kg=Decimal('0.00')
        )

        # 5. Pure Python pricing recommendation
        pricing_output: PriceRecommendationOutput = recommend_price(
            mandi_benchmark=snapshot.benchmark_price,
            grade=grade,
            grade_multiplier=grade_multiplier,
            floor_price=floor_price,
            minimum_viable_price=minimum_viable_price,
            buyer_ceiling=buyer_ceiling,
            demand_signal=snapshot.demand_signal,
            supply_signal=snapshot.supply_signal,
            quantity_kg=quantity_kg,
            weather_risk=snapshot.weather_risk,
            perishability_class='A',
            market_confidence='MEDIUM',
            forecast_confidence=forecast.confidence
        )

        rec = PriceRecommendation.objects.create(
            crop=crop,
            grade=grade,
            region=region,
            listing=listing,
            recommended_min=pricing_output.recommended_min_per_kg,
            recommended_max=pricing_output.recommended_max_per_kg,
            benchmark_price=pricing_output.benchmark_price_per_kg,
            floor_price=pricing_output.floor_price_per_kg,
            minimum_viable_price=pricing_output.minimum_viable_price_per_kg,
            buyer_ceiling=pricing_output.ceiling_price_per_kg,
            confidence=pricing_output.confidence,
            explanation=pricing_output.explanation,
            summary=pricing_output.summary
        )
        return rec
