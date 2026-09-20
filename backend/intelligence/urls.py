from django.urls import path
from .views import (
    MarketIntelligenceView,
    DemandForecastView,
    PriceRecommendationView,
    MandiHistoryView
)

urlpatterns = [
    path('market/', MarketIntelligenceView.as_view(), name='intelligence-market'),
    path('forecast/', DemandForecastView.as_view(), name='intelligence-forecast'),
    path('price-recommendation/', PriceRecommendationView.as_view(), name='intelligence-price-recommendation'),
    path('mandi-history/', MandiHistoryView.as_view(), name='intelligence-mandi-history'),
]
