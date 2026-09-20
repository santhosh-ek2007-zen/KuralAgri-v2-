from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from decimal import Decimal

from matching.models import Lot, LotContribution
from quality.models import QualityCheck, RecoveryEvent
from quality.services import QualityService, RecoveryService


class QualityCheckView(views.APIView):
    """POST /api/v1/quality/lots/{lot_id}/quality-check/ — Submit intake or handover check."""
    permission_classes = [IsAuthenticated]

    def post(self, request, lot_id):
        lot = get_object_or_404(Lot, id=lot_id)
        stage = request.data.get('stage', 'HANDOVER')
        verified_grade = request.data.get('verified_grade', lot.grade)
        verified_qty = Decimal(str(request.data.get('verified_qty_kg', lot.total_quantity_kg)))
        notes = request.data.get('notes', '')

        try:
            if stage == 'INTAKE':
                contribution_id = request.data.get('contribution_id')
                if not contribution_id:
                    return Response({"error": "contribution_id required for INTAKE stage"}, status=400)
                contribution = get_object_or_404(LotContribution, id=contribution_id, lot=lot)
                declared_grade = request.data.get('declared_grade', contribution.listing.grade)
                declared_qty = Decimal(str(request.data.get('declared_qty_kg', contribution.committed_quantity_kg)))
                qc = QualityService.intake_check(
                    lot=lot, contribution=contribution,
                    declared_grade=declared_grade, verified_grade=verified_grade,
                    declared_qty_kg=declared_qty, verified_qty_kg=verified_qty,
                    checked_by=request.user, notes=notes,
                    photo_url=request.data.get('photo_url'),
                )
            else:
                qc = QualityService.handover_check(
                    lot=lot, verified_grade=verified_grade, verified_qty_kg=verified_qty,
                    checked_by=request.user, notes=notes,
                )

            return Response({
                "id": str(qc.id),
                "stage": qc.stage,
                "declared_grade": qc.declared_grade,
                "verified_grade": qc.verified_grade,
                "accepted_qty_kg": str(qc.accepted_qty_kg),
                "rejected_qty_kg": str(qc.rejected_qty_kg),
                "rejection_reason": qc.rejection_reason,
                "lot_status": lot.status,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class RecoveryView(views.APIView):
    """POST /api/v1/quality/lots/{lot_id}/recover/ — Search for secondary/processor buyer for rejected produce."""
    permission_classes = [IsAuthenticated]

    def post(self, request, lot_id):
        lot = get_object_or_404(Lot, id=lot_id)
        quantity_kg = Decimal(str(request.data.get('quantity_kg', '0')))
        remaining_shelf_life_hours = Decimal(str(request.data.get('remaining_shelf_life_hours', '6')))
        grade = request.data.get('grade', 'B')
        trigger = request.data.get('trigger', 'BUYER_REJECTION')

        if quantity_kg <= Decimal('0'):
            return Response({"error": "quantity_kg must be positive"}, status=400)

        event = RecoveryService.find_recovery_destination(
            source_lot=lot,
            quantity_kg=quantity_kg,
            remaining_shelf_life_hours=remaining_shelf_life_hours,
            grade=grade,
            trigger=trigger,
        )

        return Response({
            "id": str(event.id),
            "trigger": event.trigger,
            "quantity_kg": str(event.quantity_kg),
            "original_value": str(event.original_value),
            "recovered_value": str(event.recovered_value),
            "outcome": event.outcome,
            "remaining_shelf_life_hours": str(event.remaining_shelf_life_hours),
        }, status=status.HTTP_200_OK)


class QualityCheckListView(views.APIView):
    """GET /api/v1/quality/lots/{lot_id}/checks/ — History of quality checks for a lot."""
    permission_classes = [IsAuthenticated]

    def get(self, request, lot_id):
        lot = get_object_or_404(Lot, id=lot_id)
        checks = QualityCheck.objects.filter(lot=lot).select_related('checked_by', 'contribution__farmer__user')
        return Response([
            {
                "id": str(c.id),
                "stage": c.stage,
                "declared_grade": c.declared_grade,
                "verified_grade": c.verified_grade,
                "accepted_qty_kg": str(c.accepted_qty_kg),
                "rejected_qty_kg": str(c.rejected_qty_kg),
                "rejection_reason": c.rejection_reason,
                "checked_by": c.checked_by.full_name,
                "created_at": c.created_at.isoformat(),
            }
            for c in checks
        ])
