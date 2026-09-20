from django.urls import path
from finance.views import EscrowFundView, AdvanceReleaseView, LedgerView

urlpatterns = [
    path('ledger/', LedgerView.as_view(), name='global-ledger'),
    path('lots/<uuid:lot_id>/escrow/fund/', EscrowFundView.as_view(), name='escrow-fund'),
    path('lots/<uuid:lot_id>/advances/release/', AdvanceReleaseView.as_view(), name='advance-release'),
    path('lots/<uuid:lot_id>/ledger/', LedgerView.as_view(), name='lot-ledger'),
]
