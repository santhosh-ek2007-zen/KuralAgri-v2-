from django.urls import path
from quality.views import QualityCheckView, RecoveryView, QualityCheckListView

urlpatterns = [
    path('lots/<uuid:lot_id>/quality-check/', QualityCheckView.as_view(), name='quality-check'),
    path('lots/<uuid:lot_id>/recover/', RecoveryView.as_view(), name='recovery'),
    path('lots/<uuid:lot_id>/checks/', QualityCheckListView.as_view(), name='quality-check-list'),
]
