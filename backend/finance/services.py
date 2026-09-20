"""
Finance & Escrow Services — M8.
EscrowService: fund escrow, release advances.
AdvanceService: disburse and track per-contributor advances.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from matching.models import Lot, LotContribution
from finance.models import EscrowAccount, LedgerEntry, Advance, RiskReserveLedger
from engine.finance_math import (
    ContributorCalculation,
    execute_waterfall,
    handle_crop_failure,
)
from common.audit import log_audit_event
from notifications.services import send_notification


class EscrowService:
    """
    Manages the simulated escrow lifecycle for a Lot.
    All money movement is append-only LedgerEntry rows.
    """

    @staticmethod
    def fund_escrow(lot: Lot, funded_by_user=None) -> EscrowAccount:
        """
        Simulate buyer escrow deposit: agreed_price * total_quantity.
        Creates or updates EscrowAccount and writes a BUYER_DEPOSIT ledger entry.
        """
        if lot.status not in ('ACCEPTED',):
            from common.exceptions import BusinessRuleError
            raise BusinessRuleError(
                f"Lot must be in ACCEPTED status to fund escrow (current: {lot.status})."
            )

        total_due = (lot.agreed_price_per_kg or Decimal('0.00')) * lot.total_quantity_kg

        with transaction.atomic():
            escrow, created = EscrowAccount.objects.get_or_create(
                lot=lot,
                defaults={'total_received': Decimal('0.00'), 'status': 'PENDING'}
            )

            escrow.total_received = total_due
            escrow.status = 'FUNDED'
            escrow.funded_at = timezone.now()
            escrow.save(update_fields=['total_received', 'status', 'funded_at'])

            LedgerEntry.objects.create(
                lot=lot,
                entry_type='BUYER_DEPOSIT',
                direction='CREDIT',
                counterparty='BUYER',
                amount=total_due,
                is_simulated=True,
                reference=f"Escrow fund for {lot.lot_code}"
            )

            lot.status = 'ESCROW_FUNDED'
            lot.save(update_fields=['status'])

        log_audit_event(
            action="ESCROW_FUNDED",
            entity_type="EscrowAccount",
            entity_id=str(escrow.id),
            user=funded_by_user,
            metadata={"lot_id": str(lot.id), "amount": str(total_due)}
        )

        if lot.buyer_order:
            send_notification(
                user=lot.buyer_order.buyer.user,
                title="Escrow Funded",
                message=f"Escrow of ₹{total_due} for Lot {lot.lot_code} has been funded.",
                notification_type="ESCROW_FUNDED",
                metadata={"lot_id": str(lot.id)}
            )

        return escrow

    @staticmethod
    def release_advances(lot: Lot, actor=None) -> list:
        """
        Disburse point-of-sale advances to all contributing farmers at Lot confirmation.
        Creates Advance record + ADVANCE_DISBURSAL ledger entry per contributor.
        """
        if lot.status not in ('ESCROW_FUNDED',):
            from common.exceptions import BusinessRuleError
            raise BusinessRuleError(
                f"Escrow must be funded before releasing advances (status: {lot.status})."
            )

        disbursed = []
        with transaction.atomic():
            for contrib in lot.contributions.all().select_related('farmer__user'):
                if hasattr(contrib, 'advance_record'):
                    continue  # Already disbursed

                advance_obj = Advance.objects.create(
                    contribution=contrib,
                    principal=contrib.advance_amount,
                    advance_rate=Decimal('0.50'),   # resolved from tier in LotService
                    annual_interest_rate=Decimal('0.27'),
                    days_outstanding=2,
                    interest=contrib.interest_amount,
                    total_claim=contrib.lender_claim,
                    status='DISBURSED',
                )
                LedgerEntry.objects.create(
                    lot=lot,
                    contribution=contrib,
                    entry_type='ADVANCE_DISBURSAL',
                    direction='DEBIT',
                    counterparty='FARMER',
                    amount=contrib.advance_amount,
                    is_simulated=True,
                    reference=f"Advance for {contrib.farmer.user.full_name}"
                )
                disbursed.append(advance_obj)

                send_notification(
                    user=contrib.farmer.user,
                    title="Advance Disbursed",
                    message=f"₹{contrib.advance_amount} advance has been credited for Lot {lot.lot_code}.",
                    notification_type="ADVANCE_DISBURSED",
                    metadata={"lot_id": str(lot.id)}
                )

        log_audit_event(
            action="ADVANCES_RELEASED",
            entity_type="Lot",
            entity_id=str(lot.id),
            user=actor,
            metadata={"advances_count": len(disbursed)}
        )

        return disbursed
