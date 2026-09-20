from decimal import Decimal
from django.db import models
from common.models import BaseModel


class EscrowAccount(BaseModel):
    """
    Escrow account created for each active Lot.
    Tracks received buyer funds and payouts through the waterfall.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Funding'),
        ('FUNDED', 'Funded'),
        ('RELEASED', 'Released / Settled'),
        ('REFUNDED', 'Refunded'),
    ]
    lot = models.OneToOneField('matching.Lot', related_name='escrow_account', on_delete=models.CASCADE)
    total_received = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    lender_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    platform_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    logistics_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    reserve_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    farmer_pool = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    funded_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Escrow for Lot {self.lot.lot_code} (₹{self.total_received}, {self.status})"


class LedgerEntry(BaseModel):
    """
    Append-only immutable financial audit ledger.
    Never updated, never deleted.
    """
    ENTRY_TYPE_CHOICES = [
        ('BUYER_DEPOSIT', 'Buyer Escrow Deposit'),
        ('ADVANCE_DISBURSAL', 'Farmer Advance Disbursal'),
        ('INTEREST_ACCRUAL', 'Advance Interest Accrual'),
        ('LENDER_REPAYMENT', 'Lender Principal & Interest Repayment'),
        ('PLATFORM_COMMISSION', 'Platform Commission Fee'),
        ('LOGISTICS_PAYOUT', 'Logistics & Handling Payout'),
        ('RESERVE_CONTRIBUTION', 'Risk Reserve Contribution'),
        ('FARMER_SETTLEMENT', 'Farmer Final Settlement'),
        ('RESERVE_PAYOUT', 'Risk Reserve Default Coverage'),
        ('WRITE_OFF', 'Lender Unrecovered Write-off'),
        ('REFUND', 'Buyer Refund'),
    ]
    lot = models.ForeignKey('matching.Lot', null=True, blank=True, on_delete=models.SET_NULL, related_name='ledger_entries')
    contribution = models.ForeignKey('matching.LotContribution', null=True, blank=True, on_delete=models.SET_NULL, related_name='ledger_entries')
    entry_type = models.CharField(max_length=30, choices=ENTRY_TYPE_CHOICES, db_index=True)
    direction = models.CharField(max_length=10, choices=[('CREDIT', 'Credit'), ('DEBIT', 'Debit')])
    counterparty = models.CharField(max_length=30)  # BUYER, FARMER, FPO, LENDER, PLATFORM, LOGISTICS, RESERVE
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_simulated = models.BooleanField(default=True)
    reference = models.CharField(max_length=100, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['lot', 'occurred_at']),
            models.Index(fields=['entry_type', 'occurred_at']),
        ]

    def __str__(self):
        return f"[{self.occurred_at}] {self.entry_type} {self.direction} ₹{self.amount} ({self.counterparty})"


class Advance(BaseModel):
    """
    Point-of-sale advance loan disbursed to a contributing farmer at Lot confirmation.
    """
    STATUS_CHOICES = [
        ('DISBURSED', 'Disbursed'),
        ('REPAID', 'Repaid'),
        ('DEFAULTED', 'Defaulted'),
        ('WRITTEN_OFF', 'Written Off'),
    ]
    contribution = models.OneToOneField('matching.LotContribution', related_name='advance_record', on_delete=models.CASCADE)
    principal = models.DecimalField(max_digits=10, decimal_places=2)
    advance_rate = models.DecimalField(max_digits=5, decimal_places=2)
    annual_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    days_outstanding = models.PositiveIntegerField(default=2)
    interest = models.DecimalField(max_digits=10, decimal_places=2)
    total_claim = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DISBURSED')
    disbursed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Advance ₹{self.principal} for {self.contribution.farmer.user.full_name} ({self.status})"


class RiskReserveLedger(BaseModel):
    """
    Movement and running balance of the platform risk reserve fund.
    """
    lot = models.ForeignKey('matching.Lot', null=True, blank=True, on_delete=models.SET_NULL)
    entry_type = models.CharField(max_length=30)  # CONTRIBUTION | DEFAULT_PAYOUT
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Reserve {self.entry_type}: ₹{self.amount} -> Balance: ₹{self.balance_after}"
