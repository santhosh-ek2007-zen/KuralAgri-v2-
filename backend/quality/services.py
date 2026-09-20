"""
Quality & Recovery Service — M9.
QualityService: intake check gate, handover check gate.
RecoveryService: find secondary buyer/processor for rejected produce.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from matching.models import Lot, LotContribution
from quality.models import QualityCheck, RecoveryEvent
from users.models import BuyerProfile
from common.audit import log_audit_event
from notifications.services import send_notification


class QualityService:

    @staticmethod
    def intake_check(
        lot: Lot,
        contribution: LotContribution,
        declared_grade: str,
        verified_grade: str,
        declared_qty_kg: Decimal,
        verified_qty_kg: Decimal,
        checked_by,
        notes: str = "",
        photo_url: str = None,
    ) -> QualityCheck:
        """
        INTAKE stage: verify grade and quantity before consolidation.
        If grade mismatch or quantity shortfall, reject that contribution.
        """
        accepted_qty = verified_qty_kg if verified_grade == declared_grade else Decimal('0.00')
        rejected_qty = declared_qty_kg - accepted_qty
        rejection_reason = None

        if verified_grade != declared_grade:
            rejection_reason = 'GRADE_MISMATCH'
        elif verified_qty_kg < declared_qty_kg * Decimal('0.95'):
            rejection_reason = 'QUANTITY_SHORT'

        with transaction.atomic():
            qc = QualityCheck.objects.create(
                lot=lot,
                contribution=contribution,
                stage='INTAKE',
                declared_grade=declared_grade,
                verified_grade=verified_grade,
                declared_qty_kg=declared_qty_kg,
                verified_qty_kg=verified_qty_kg,
                accepted_qty_kg=accepted_qty,
                rejected_qty_kg=rejected_qty,
                rejection_reason=rejection_reason,
                photo_url=photo_url,
                checked_by=checked_by,
                notes=notes,
            )

            if rejection_reason:
                contribution.status = 'FAILED'
                contribution.delivered_quantity_kg = Decimal('0.00')
                contribution.save(update_fields=['status', 'delivered_quantity_kg'])

                send_notification(
                    user=contribution.farmer.user,
                    title="Quality Check Failed",
                    message=f"Your contribution to Lot {lot.lot_code} failed intake check: {rejection_reason}.",
                    notification_type="QUALITY_FAILED",
                    metadata={"lot_id": str(lot.id)}
                )
            else:
                contribution.delivered_quantity_kg = verified_qty_kg
                contribution.status = 'COLLECTED'
                contribution.save(update_fields=['delivered_quantity_kg', 'status'])

        log_audit_event(
            action="QUALITY_INTAKE_CHECK",
            entity_type="QualityCheck",
            entity_id=str(qc.id),
            user=checked_by,
            metadata={
                "lot_id": str(lot.id),
                "contribution_id": str(contribution.id),
                "result": "PASSED" if not rejection_reason else rejection_reason,
            }
        )

        return qc

    @staticmethod
    def handover_check(
        lot: Lot,
        verified_grade: str,
        verified_qty_kg: Decimal,
        checked_by,
        notes: str = "",
    ) -> QualityCheck:
        """
        HANDOVER stage: buyer inspects the lot at delivery.
        If accepted_qty < total_qty => PARTIALLY_ACCEPTED, else ACCEPTED_FULL.
        """
        declared_qty = lot.total_quantity_kg
        accepted_qty = min(verified_qty_kg, declared_qty)
        rejected_qty = declared_qty - accepted_qty
        rejection_reason = 'SPOILAGE' if rejected_qty > Decimal('0.00') else None

        with transaction.atomic():
            qc = QualityCheck.objects.create(
                lot=lot,
                contribution=None,
                stage='HANDOVER',
                declared_grade=lot.grade,
                verified_grade=verified_grade,
                declared_qty_kg=declared_qty,
                verified_qty_kg=verified_qty_kg,
                accepted_qty_kg=accepted_qty,
                rejected_qty_kg=rejected_qty,
                rejection_reason=rejection_reason,
                checked_by=checked_by,
                notes=notes,
            )

            lot.delivered_quantity_kg = accepted_qty
            if rejected_qty > Decimal('0.00'):
                lot.status = 'PARTIALLY_ACCEPTED'
            else:
                lot.status = 'ACCEPTED_FULL'
            lot.save(update_fields=['delivered_quantity_kg', 'status'])

            if lot.buyer_order:
                send_notification(
                    user=lot.buyer_order.buyer.user,
                    title="Lot Handover Completed",
                    message=f"Lot {lot.lot_code}: {accepted_qty}kg accepted, {rejected_qty}kg rejected.",
                    notification_type="HANDOVER_COMPLETE",
                    metadata={"lot_id": str(lot.id)}
                )

        log_audit_event(
            action="QUALITY_HANDOVER_CHECK",
            entity_type="QualityCheck",
            entity_id=str(qc.id),
            user=checked_by,
            metadata={
                "lot_id": str(lot.id),
                "accepted_qty": str(accepted_qty),
                "rejected_qty": str(rejected_qty),
                "lot_status": lot.status,
            }
        )

        return qc


class RecoveryService:
    """
    D3 §6, §13: Find secondary buyers or processors for rejected/grade-downgraded produce.
    Implements the SUPPLY_PUSH rejection recovery path.
    """

    CHANNEL_GRADE_MAP = {
        'A': ['PREMIUM', 'SECONDARY', 'PROCESSOR'],
        'B': ['SECONDARY', 'PROCESSOR'],
        'C': ['PROCESSOR'],
    }

    @staticmethod
    def find_recovery_destination(
        source_lot: Lot,
        quantity_kg: Decimal,
        remaining_shelf_life_hours: Decimal,
        grade: str = 'B',
        trigger: str = 'BUYER_REJECTION',
    ) -> RecoveryEvent:
        """
        Search for secondary buyers or processors that can absorb rejected produce
        within remaining shelf life. Creates a RecoveryEvent record.
        """
        from engine.economics import (
            DestinationCandidateInput,
            ContributorPickupInput,
            evaluate_and_rank_destinations,
        )
        from engine.routing import haversine_km

        # Accepted channel priority for grade
        accepted_channels = RecoveryService.CHANNEL_GRADE_MAP.get(grade, ['PROCESSOR'])

        # Find candidate buyers
        buyers = BuyerProfile.objects.filter(buyer_type__in=accepted_channels)

        hub_lat = float(source_lot.aggregation_point.latitude) if source_lot.aggregation_point else 9.9457
        hub_lng = float(source_lot.aggregation_point.longitude) if source_lot.aggregation_point else 77.4779

        candidate_inputs = []
        for b in buyers:
            if grade not in (b.accepted_grades or ['A']):
                continue
            dist = haversine_km(hub_lat, hub_lng, float(b.latitude), float(b.longitude))
            # Use indicative or discounted price for secondary channels
            price = b.indicative_price_per_kg if hasattr(b, 'indicative_price_per_kg') and b.indicative_price_per_kg else (
                Decimal('18.00') if b.buyer_type == 'SECONDARY' else Decimal('10.00')
            )
            candidate_inputs.append(DestinationCandidateInput(
                destination_id=str(b.id),
                buyer_name=b.organisation,
                channel=b.buyer_type,
                accepted_grades=b.accepted_grades or ['A', 'B', 'C'],
                daily_capacity_kg=b.daily_capacity_kg,
                min_order_kg=Decimal('50.00'),
                gross_price_per_kg=price,
                road_distance_km=Decimal(str(dist)),
            ))

        pickup_inputs = [ContributorPickupInput("recovery", quantity_kg, Decimal('2.00'))]

        outcome = 'PENDING'
        recovered_value = Decimal('0.00')
        recovery_lot = None

        if candidate_inputs:
            evaluated = evaluate_and_rank_destinations(
                lot_quantity_kg=quantity_kg,
                grade=grade,
                remaining_shelf_life_hours=remaining_shelf_life_hours,
                contributors=pickup_inputs,
                candidates=candidate_inputs,
            )
            feasible = [e for e in evaluated if e.is_feasible]

            if feasible:
                best = feasible[0]
                channel = best.channel
                recovered_value = best.net_return_per_kg * quantity_kg
                outcome = 'SECONDARY_BUYER' if channel in ('PREMIUM', 'SECONDARY') else 'PROCESSOR'

        if not feasible if candidate_inputs else True:
            # Nothing feasible → waste
            outcome = 'WASTE'
            recovered_value = Decimal('0.00')

        original_value = (source_lot.agreed_price_per_kg or Decimal('0.00')) * quantity_kg

        with transaction.atomic():
            event = RecoveryEvent.objects.create(
                source_lot=source_lot,
                recovery_lot=recovery_lot,
                trigger=trigger,
                quantity_kg=quantity_kg,
                original_value=original_value,
                recovered_value=recovered_value,
                outcome=outcome,
                remaining_shelf_life_hours=remaining_shelf_life_hours,
            )

        log_audit_event(
            action="RECOVERY_ATTEMPTED",
            entity_type="RecoveryEvent",
            entity_id=str(event.id),
            metadata={
                "lot_id": str(source_lot.id),
                "quantity_kg": str(quantity_kg),
                "outcome": outcome,
                "recovered_value": str(recovered_value),
            }
        )

        return event
