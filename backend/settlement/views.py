from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from matching.models import Lot, LotContribution
from settlement.models import Settlement
from settlement.services import WaterfallService


class LotSettleView(views.APIView):
    """POST /api/v1/settlement/lots/{lot_id}/settle/ — Execute D1§9 waterfall and create settlement rows."""
    permission_classes = [IsAuthenticated]

    def post(self, request, lot_id):
        lot = get_object_or_404(Lot, id=lot_id)
        try:
            result = WaterfallService.settle_lot(lot, actor=request.user)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class CropFailureView(views.APIView):
    """POST /api/v1/settlement/contributions/{contribution_id}/mark-failed/ — D1§12 crop failure."""
    permission_classes = [IsAuthenticated]

    def post(self, request, contribution_id):
        contribution = get_object_or_404(LotContribution, id=contribution_id)
        try:
            result = WaterfallService.handle_crop_failure_for_contribution(
                contribution, actor=request.user
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class SettlementListView(views.APIView):
    """GET /api/v1/settlement/lots/{lot_id}/settlements/ — Per-contributor settlement details."""
    permission_classes = [IsAuthenticated]

    def get(self, request, lot_id):
        lot = get_object_or_404(Lot, id=lot_id)
        settlements = Settlement.objects.filter(
            contribution__lot=lot
        ).select_related('contribution__farmer__user')

        return Response([
            {
                "farmer": s.contribution.farmer.user.full_name,
                "contribution_id": str(s.contribution_id),
                "advance_paid": str(s.advance_paid),
                "settlement_paid": str(s.settlement_paid),
                "total_realisation": str(s.total_realisation),
                "traditional_channel_value": str(s.traditional_channel_value),
                "uplift_pct": str(s.uplift_pct),
                "status": s.status,
            }
            for s in settlements
        ])
