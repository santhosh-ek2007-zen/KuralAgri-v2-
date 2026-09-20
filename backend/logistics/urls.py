from django.urls import path
from logistics.views import (
    VehicleListView,
    RouteListView,
    RouteDetailView,
    DestinationCandidateListView,
    LogisticsCostView
)

urlpatterns = [
    path('vehicles/', VehicleListView.as_view(), name='vehicle-list'),
    path('routes/', RouteListView.as_view(), name='route-list'),
    path('routes/<uuid:pk>/', RouteDetailView.as_view(), name='route-detail'),
    path('candidates/', DestinationCandidateListView.as_view(), name='destination-candidate-list'),
    path('cost/', LogisticsCostView.as_view(), name='logistics-cost'),
]
