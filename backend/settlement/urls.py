from django.urls import path
from settlement.views import LotSettleView, CropFailureView, SettlementListView

urlpatterns = [
    path('lots/<uuid:lot_id>/settle/', LotSettleView.as_view(), name='lot-settle'),
    path('lots/<uuid:lot_id>/settlements/', SettlementListView.as_view(), name='settlement-list'),
    path('contributions/<uuid:contribution_id>/mark-failed/', CropFailureView.as_view(), name='contribution-mark-failed'),
]
