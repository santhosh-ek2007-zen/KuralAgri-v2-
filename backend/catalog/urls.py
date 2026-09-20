from django.urls import path
from .views import (
    CropListView,
    CropDetailView,
    RegionListView,
    AggregationPointListView,
    RateCardListView,
    AdvanceTierListView,
    PlatformSettingsView
)

urlpatterns = [
    path('crops/', CropListView.as_view(), name='crop-list'),
    path('crops/<uuid:pk>/', CropDetailView.as_view(), name='crop-detail'),
    path('regions/', RegionListView.as_view(), name='region-list'),
    path('aggregation-points/', AggregationPointListView.as_view(), name='aggregation-point-list'),
    path('rate-cards/', RateCardListView.as_view(), name='rate-card-list'),
    path('advance-tiers/', AdvanceTierListView.as_view(), name='advance-tier-list'),
    path('platform-settings/', PlatformSettingsView.as_view(), name='platform-settings'),
]
