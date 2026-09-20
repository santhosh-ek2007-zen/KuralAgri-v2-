from django.urls import path
from .views import (
    MatchOrderView,
    FormLotView,
    LotListView,
    LotDetailView,
    AcceptLotView
)

urlpatterns = [
    path('orders/<uuid:pk>/match/', MatchOrderView.as_view(), name='matching-order-match'),
    path('orders/<uuid:pk>/form-lot/', FormLotView.as_view(), name='matching-order-form-lot'),
    path('lots/', LotListView.as_view(), name='lot-list'),
    path('lots/<uuid:pk>/', LotDetailView.as_view(), name='lot-detail'),
    path('lots/<uuid:pk>/accept/', AcceptLotView.as_view(), name='lot-accept'),
]
