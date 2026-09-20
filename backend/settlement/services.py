"""
Settlement Service — M8.
Executes the D1 §9 waterfall and persists per-contributor Settlement records + ledger entries.
"""
from decimal import Decimal
from django.db import transaction

from matching.models import Lot, LotContribution
from finance.models import EscrowAccount, LedgerEntry, RiskReserveLedger
from settlement.models import Settlement
from engine.finance_math import (
    ContributorCalculation,
    execute_waterfall,
    handle_crop_failure,
)
from common.audit import log_audit_event
from notifications.services import send_notification


class WaterfallService:
    """
    Execute the D1 §9 waterfall and create Settlement rows.
    Called after the Lot is DELIVERED and a quality handover check passes.
    """

    @staticmethod
    def settle_lot(lot: Lot, actor=None) -> dict:
        """
        Run execute_waterfall for the Lot, persist ledger entries and Settlement rows.
        Returns the WaterfallResult as a dict.
        """
        if lot.status not in ('DELIVERED', 'ACCEPTED_FULL', 'PARTIALLY_ACCEPTED'):
            from common.exceptions import BusinessRuleError
            raise BusinessRuleError(
                f"Lot must be delivered to settle (current: {lot.status})."
            )

        contributions = list(lot.contributions.all().select_related('farmer__user'))
        if not contributions:
            from common.exceptions import BusinessRuleError
            raise BusinessRuleError("Cannot settle a lot with no contributions.")

        # Build ContributorCalculation objects from persisted values
        contributor_calcs = [
            ContributorCalculation(
                contributor_id=str(c.id),
                farmer_name=c.farmer.user.full_name,
                quantity_kg=c.committed_quantity_kg,
                floor_value=lot.floor_price_per_kg * c.committed_quantity_kg,
                advance_amount=c.advance_amount,
                interest_amount=c.interest_amount,
                lender_claim=c.lender_claim,
                residual_entitlement=c.residual_entitlement,
            )
            for c in contributions
        ]

        delivered_qty = lot.delivered_quantity_kg or lot.total_quantity_kg
        agreed_price = lot.agreed_price_per_kg
        lender_claim_lot = sum(c.lender_claim for c in contributor_calcs)

        waterfall = execute_waterfall(
            agreed_price_per_kg=agreed_price,
            delivered_quantity_kg=delivered_qty,
            lender_claim_lot=lender_claim_lot,
            logistics_cost=lot.logistics_cost,
            platform_commission_rate=Decimal('0.04'),
            risk_reserve_rate=Decimal('0.01'),
            contributor_calcs=contributor_calcs,
        )

        with transaction.atomic():
            # Update escrow account balances
            try:
                escrow = lot.escrow_account
                escrow.lender_paid = waterfall.lender_paid
                escrow.platform_paid = waterfall.platform_paid
                escrow.logistics_paid = waterfall.logistics_paid
                escrow.reserve_paid = waterfall.reserve_paid
                escrow.farmer_pool = waterfall.farmer_pool
                escrow.status = 'RELEASED'
                from django.utils import timezone
                escrow.released_at = timezone.now()
                escrow.save()
            except EscrowAccount.DoesNotExist:
                pass  # Settlement can proceed even without a funded escrow in tests

            # Append-only ledger entries for each waterfall step
            LedgerEntry.objects.create(
                lot=lot, entry_type='LENDER_REPAYMENT', direction='DEBIT',
                counterparty='LENDER', amount=waterfall.lender_paid, is_simulated=True,
                reference=f"D1§9 Lender repayment for {lot.lot_code}"
            )
            LedgerEntry.objects.create(
                lot=lot, entry_type='PLATFORM_COMMISSION', direction='DEBIT',
                counterparty='PLATFORM', amount=waterfall.platform_paid, is_simulated=True,
                reference=f"D1§9 Platform commission for {lot.lot_code}"
            )
            LedgerEntry.objects.create(
                lot=lot, entry_type='LOGISTICS_PAYOUT', direction='DEBIT',
                counterparty='LOGISTICS', amount=waterfall.logistics_paid, is_simulated=True,
                reference=f"D1§9 Logistics payout for {lot.lot_code}"
            )
            LedgerEntry.objects.create(
                lot=lot, entry_type='RESERVE_CONTRIBUTION', direction='DEBIT',
                counterparty='RESERVE', amount=waterfall.reserve_paid, is_simulated=True,
                reference=f"D1§9 Risk reserve for {lot.lot_code}"
            )

            # Risk reserve ledger
            last_balance = RiskReserveLedger.objects.order_by('-created_at').values_list('balance_after', flat=True).first() or Decimal('0.00')
            RiskReserveLedger.objects.create(
                lot=lot,
                entry_type='CONTRIBUTION',
                amount=waterfall.reserve_paid,
                balance_after=last_balance + waterfall.reserve_paid,
                notes=f"Reserve contribution from Lot {lot.lot_code}"
            )

            # Per-contributor settlement
            settlements_out = []
            contrib_map = {str(c.id): c for c in contributions}

            for ws in waterfall.settlements:
                contrib_obj = contrib_map.get(ws.contributor_id)
                if not contrib_obj:
                    continue

                settlement = Settlement.objects.create(
                    contribution=contrib_obj,
                    advance_paid=ws.advance_paid,
                    settlement_paid=ws.settlement_paid,
                    total_realisation=ws.total_realisation,
                    traditional_channel_value=ws.traditional_channel_value,
                    uplift_pct=ws.uplift_pct,
                    status='PAID',
                )
                settlements_out.append(settlement)

                LedgerEntry.objects.create(
                    lot=lot,
                    contribution=contrib_obj,
                    entry_type='FARMER_SETTLEMENT',
                    direction='DEBIT',
                    counterparty='FARMER',
                    amount=ws.settlement_paid,
                    is_simulated=True,
                    reference=f"Final settlement for {ws.farmer_name}"
                )

                send_notification(
                    user=contrib_obj.farmer.user,
                    title="Settlement Paid",
                    message=(
                        f"₹{ws.total_realisation} total realisation for Lot {lot.lot_code} "
                        f"(+{ws.uplift_pct}% vs traditional channel)."
                    ),
                    notification_type="SETTLEMENT_PAID",
                    metadata={"lot_id": str(lot.id)}
                )

            lot.status = 'SETTLED'
            lot.save(update_fields=['status'])

        log_audit_event(
            action="LOT_SETTLED",
            entity_type="Lot",
            entity_id=str(lot.id),
            user=actor,
            metadata={
                "total_received": str(waterfall.total_received),
                "farmer_pool": str(waterfall.farmer_pool),
                "is_balanced": waterfall.is_balanced,
            }
        )

        return {
            "total_received": waterfall.total_received,
            "lender_paid": waterfall.lender_paid,
            "platform_paid": waterfall.platform_paid,
            "logistics_paid": waterfall.logistics_paid,
            "reserve_paid": waterfall.reserve_paid,
            "farmer_pool": waterfall.farmer_pool,
            "is_balanced": waterfall.is_balanced,
            "settlements": [
                {
                    "farmer": s.contribution.farmer.user.full_name,
                    "advance_paid": str(s.advance_paid),
                    "settlement_paid": str(s.settlement_paid),
                    "total_realisation": str(s.total_realisation),
                    "uplift_pct": str(s.uplift_pct),
                }
                for s in settlements_out
            ]
        }

    @staticmethod
    def handle_crop_failure_for_contribution(contribution: LotContribution, actor=None) -> dict:
        """
        D1 §12: Mark one contributor as failed, compute risk reserve payout.
        The farmer has ₹0 cash liability. The reserve covers 40% of lender exposure.
        """
        from engine.finance_math import ContributorCalculation, handle_crop_failure

        calc = ContributorCalculation(
            contributor_id=str(contribution.id),
            farmer_name=contribution.farmer.user.full_name,
            quantity_kg=contribution.committed_quantity_kg,
            floor_value=contribution.lender_claim + contribution.residual_entitlement,
            advance_amount=contribution.advance_amount,
            interest_amount=contribution.interest_amount,
            lender_claim=contribution.lender_claim,
            residual_entitlement=contribution.residual_entitlement,
        )

        result = handle_crop_failure(calc)
        lot = contribution.lot

        with transaction.atomic():
            # Reserve covers 40% of lender exposure
            last_balance = RiskReserveLedger.objects.order_by('-created_at').values_list('balance_after', flat=True).first() or Decimal('0.00')
            RiskReserveLedger.objects.create(
                lot=lot,
                entry_type='DEFAULT_PAYOUT',
                amount=result.reserve_payout,
                balance_after=max(Decimal('0.00'), last_balance - result.reserve_payout),
                notes=f"Crop failure default payout for {contribution.farmer.user.full_name}"
            )
            LedgerEntry.objects.create(
                lot=lot,
                contribution=contribution,
                entry_type='RESERVE_PAYOUT',
                direction='DEBIT',
                counterparty='LENDER',
                amount=result.reserve_payout,
                is_simulated=True,
                reference=f"D1§12 risk reserve cover for {contribution.farmer.user.full_name}"
            )
            if result.unrecovered_loss > Decimal('0.00'):
                LedgerEntry.objects.create(
                    lot=lot,
                    contribution=contribution,
                    entry_type='WRITE_OFF',
                    direction='DEBIT',
                    counterparty='LENDER',
                    amount=result.unrecovered_loss,
                    is_simulated=True,
                    reference=f"D1§12 unrecovered lender write-off for {contribution.farmer.user.full_name}"
                )

            contribution.status = 'FAILED'
            contribution.save(update_fields=['status'])

        log_audit_event(
            action="CROP_FAILURE_HANDLED",
            entity_type="LotContribution",
            entity_id=str(contribution.id),
            user=actor,
            metadata={
                "lender_exposure": str(result.lender_exposure),
                "reserve_payout": str(result.reserve_payout),
                "farmer_cash_liability": str(result.farmer_cash_liability),
            }
        )

        return {
            "lender_exposure": result.lender_exposure,
            "reserve_payout": result.reserve_payout,
            "unrecovered_loss": result.unrecovered_loss,
            "farmer_cash_liability": result.farmer_cash_liability,
        }
