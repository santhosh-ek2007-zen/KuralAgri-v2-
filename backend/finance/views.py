from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from matching.models import Lot, LotContribution
from finance.models import EscrowAccount, LedgerEntry, Advance
from finance.services import EscrowService
from common.permissions import IsPlatformAdmin


class EscrowFundView(views.APIView):
    """POST /api/v1/finance/lots/{lot_id}/escrow/fund/ — Simulate buyer escrow deposit."""
    permission_classes = [IsAuthenticated]

    def post(self, request, lot_id):
        lot = get_object_or_404(Lot, id=lot_id)
        try:
            escrow = EscrowService.fund_escrow(lot, funded_by_user=request.user)
            return Response({
                "status": "funded",
                "lot_id": str(lot.id),
                "lot_code": lot.lot_code,
                "total_received": str(escrow.total_received),
                "escrow_status": escrow.status,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class AdvanceReleaseView(views.APIView):
    """POST /api/v1/finance/lots/{lot_id}/advances/release/ — Release advances to all contributors."""
    permission_classes = [IsAuthenticated]

    def post(self, request, lot_id):
        lot = get_object_or_404(Lot, id=lot_id)
        try:
            advances = EscrowService.release_advances(lot, actor=request.user)
            return Response({
                "advances_disbursed": len(advances),
                "details": [
                    {
                        "contribution_id": str(a.contribution_id),
                        "farmer": a.contribution.farmer.user.full_name,
                        "principal": str(a.principal),
                        "interest": str(a.interest),
                        "total_claim": str(a.total_claim),
                    }
                    for a in advances
                ]
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class LedgerView(views.APIView):
    """GET /api/v1/finance/lots/{lot_id}/ledger/ or /api/v1/finance/ledger/ — Financial audit trail."""
    permission_classes = [IsAuthenticated]

    def get(self, request, lot_id=None):
        if lot_id:
            lot = get_object_or_404(Lot, id=lot_id)
            entries = LedgerEntry.objects.filter(lot=lot).order_by('occurred_at')
        else:
            entries = LedgerEntry.objects.all().order_by('-occurred_at')[:100]
        return Response([
            {
                "occurred_at": e.occurred_at.isoformat(),
                "entry_type": e.entry_type,
                "direction": e.direction,
                "counterparty": e.counterparty,
                "amount": str(e.amount),
                "is_simulated": e.is_simulated,
                "reference": e.reference,
            }
            for e in entries
        ])
