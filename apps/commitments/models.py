from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.core.models import BaseModel
from apps.core.utils.storage import upload_to_supabase, get_file_from_supabase, delete_file_from_supabase
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import LedgerEntry

class CommitmentCategory(BaseModel):
    """
    Categories for operational commitments (e.g., EMI, Lease, Insurance, Utilities)
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Commitment Category'
        verbose_name_plural = 'Commitment Categories'
        ordering = ['name']


class OperationalCommitment(BaseModel):
    """
    Model for tracking recurring operational commitments like EMIs, leases, insurance, etc.
    """
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly'),
        ('one_time', 'One Time'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
    ]
    
    TYPE_CHOICES = [
        ('emi', 'EMI'),
        ('lease', 'Lease'),
        ('insurance', 'Insurance'),
        ('maintenance', 'Maintenance Contract'),
        ('utilities', 'Utilities'),
        ('rent', 'Rent'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=200)
    commitment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')
    category = models.ForeignKey(CommitmentCategory, on_delete=models.SET_NULL, null=True, related_name='commitments')
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Contract details
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="Contract/Policy number")
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True, help_text="Leave blank for indefinite commitments")
    
    # Payment details
    payment_frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    payment_day = models.PositiveIntegerField(default=1, help_text="Day of the month when payment is due")
    next_payment_date = models.DateField()
    current_payment_is_paid = models.BooleanField(default=False, help_text="Whether the current due payment has been made")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True)
    
    # Contact information
    payee_name = models.CharField(max_length=200, help_text="Institution/company to pay")
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    
    # Document storage
    contract_document_url = models.URLField(blank=True, null=True, help_text="URL to the contract document in Supabase")
    contract_document_path = models.CharField(max_length=255, blank=True, null=True, help_text="Path to the document in Supabase")
    
    # Notes
    notes = models.TextField(blank=True, null=True, help_text="Additional notes, terms and conditions")
    
    def __str__(self):
        return f"{self.title} - {self.amount} ({self.get_payment_frequency_display()})"
    
    def get_next_payment_date(self, from_date=None):
        """
        Calculate the next payment date based on the frequency
        """
        if from_date is None:
            from_date = timezone.now().date()
            
        if self.next_payment_date > from_date:
            return self.next_payment_date
            
        # Calculate the next payment date
        from dateutil.relativedelta import relativedelta
        import calendar
        
        current_date = self.next_payment_date
        
        if self.payment_frequency == 'monthly':
            next_date = current_date + relativedelta(months=1)
        elif self.payment_frequency == 'quarterly':
            next_date = current_date + relativedelta(months=3)
        elif self.payment_frequency == 'half_yearly':
            next_date = current_date + relativedelta(months=6)
        elif self.payment_frequency == 'yearly':
            next_date = current_date + relativedelta(years=1)
        elif self.payment_frequency == 'one_time':
            return None  # No next payment for one-time commitments
        
        # Adjust day of month if necessary
        day = min(self.payment_day, calendar.monthrange(next_date.year, next_date.month)[1])
        next_date = next_date.replace(day=day)
        
        return next_date
    
    def update_next_payment_date(self):
        """
        Update the next payment date after a payment
        """
        next_date = self.get_next_payment_date()
        
        if next_date:
            self.next_payment_date = next_date
            self.current_payment_is_paid = False  # Reset payment status for new period
            self.save(update_fields=['next_payment_date', 'current_payment_is_paid'])
        
        return self.next_payment_date
    
    def save(self, *args, **kwargs):
        """
        Override save to ensure next_payment_date is set
        """
        # If next_payment_date is not set, initialize it based on start_date
        if not self.next_payment_date:
            self.next_payment_date = self.start_date
        
        super().save(*args, **kwargs)
    
    def upload_contract_document(self, file):
        """
        Upload contract document to Supabase storage
        """
        if not file:
            return None
        
        # Upload file to Supabase
        result = upload_to_supabase(
            file=file,
            folder=f"commitments/contracts/{self.commitment_type}"
        )
        
        if result.get('success'):
            self.contract_document_url = result.get('public_url')
            self.contract_document_path = result.get('path')
            self.save(update_fields=['contract_document_url', 'contract_document_path'])
        
        return result
    
    def get_contract_document_url(self):
        """
        Get the contract document URL from Supabase
        """
        if not self.contract_document_path:
            return None
        
        # Refresh the URL from Supabase (in case it changed)
        result = get_file_from_supabase(path=self.contract_document_path)
        
        if result.get('success'):
            updated_url = result.get('public_url')
            if updated_url != self.contract_document_url:
                self.contract_document_url = updated_url
                self.save(update_fields=['contract_document_url'])
            return updated_url
        
        return self.contract_document_url
    
    def delete_contract_document(self):
        """
        Delete the contract document from Supabase
        """
        if not self.contract_document_path:
            return {'success': False, 'error': 'No document path specified'}
        
        result = delete_file_from_supabase(path=self.contract_document_path)
        
        if result.get('success'):
            self.contract_document_url = None
            self.contract_document_path = None
            self.save(update_fields=['contract_document_url', 'contract_document_path'])
        
        return result
    
    @property
    def is_due_soon(self):
        """Check if payment is due within the next 7 days"""
        today = timezone.now().date()
        return (self.next_payment_date - today).days <= 7 and (self.next_payment_date - today).days >= 0
    
    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        today = timezone.now().date()
        return self.next_payment_date < today
    
    class Meta:
        ordering = ['next_payment_date', 'title']
        verbose_name = 'Operational Commitment'
        verbose_name_plural = 'Operational Commitments'


class CommitmentPayment(BaseModel):
    """
    Track individual payments made for operational commitments
    """
    PAYMENT_MODES = [
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
        ('BANK', 'Bank Transfer'),
        ('UPI', 'UPI'),
        ('AUTO_DEBIT', 'Auto Debit'),
        ('OTHER', 'Other'),
    ]
    
    commitment = models.ForeignKey(OperationalCommitment, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_mode = models.CharField(max_length=15, choices=PAYMENT_MODES, default='BANK')
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="Transaction ID, Cheque Number, etc.")
    remarks = models.TextField(blank=True, null=True)
    
    # Receipt details
    receipt_number = models.CharField(max_length=100, blank=True, null=True)
    receipt_file = models.FileField(upload_to='receipts/commitments/', blank=True, null=True)
    receipt_url = models.URLField(blank=True, null=True, help_text="URL to the receipt in Supabase")
    receipt_file_path = models.CharField(max_length=255, blank=True, null=True, help_text="Path to the receipt in Supabase")
    
    # Link to ledger entry
    ledger_entry = models.OneToOneField(LedgerEntry, on_delete=models.SET_NULL, null=True, blank=True, 
                                       related_name='commitment_payment')
    
    def __str__(self):
        return f"Payment of ₹{self.amount_paid} for {self.commitment.title} on {self.payment_date}"
    
    def save(self, *args, **kwargs):
        """
        Override save to update the commitment's next payment date
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # If this is a new payment, update the commitment's payment status and next payment date
        if is_new:
            commitment = self.commitment
            commitment.current_payment_is_paid = True
            commitment.save(update_fields=['current_payment_is_paid'])
            commitment.update_next_payment_date()
    
    def upload_receipt(self, file):
        """
        Upload receipt to Supabase storage
        """
        if not file:
            return None
        
        # Upload file to Supabase
        result = upload_to_supabase(
            file=file,
            folder=f"commitments/receipts/{self.commitment.commitment_type}"
        )
        
        if result.get('success'):
            self.receipt_url = result.get('public_url')
            self.receipt_file_path = result.get('path')
            self.save(update_fields=['receipt_url', 'receipt_file_path'])
        
        return result
    
    def get_receipt_url(self):
        """
        Get the receipt URL from Supabase
        """
        if not self.receipt_file_path:
            return None
        
        # Refresh the URL from Supabase (in case it changed)
        result = get_file_from_supabase(path=self.receipt_file_path)
        
        if result.get('success'):
            updated_url = result.get('public_url')
            if updated_url != self.receipt_url:
                self.receipt_url = updated_url
                self.save(update_fields=['receipt_url'])
            return updated_url
        
        return self.receipt_url
    
    def delete_receipt(self):
        """
        Delete the receipt from Supabase
        """
        if not self.receipt_file_path:
            return {'success': False, 'error': 'No receipt path specified'}
        
        result = delete_file_from_supabase(path=self.receipt_file_path)
        
        if result.get('success'):
            self.receipt_url = None
            self.receipt_file_path = None
            self.save(update_fields=['receipt_url', 'receipt_file_path'])
        
        return result
    
    class Meta:
        ordering = ['-payment_date', '-created_at']
        verbose_name = 'Commitment Payment'
        verbose_name_plural = 'Commitment Payments'


@receiver(post_save, sender=CommitmentPayment)
def create_ledger_entry_for_payment(sender, instance, created, **kwargs):
    """
    Create a ledger entry when a commitment payment is made
    """
    if created and not instance.ledger_entry:
        # Create a new ledger entry
        ledger_entry = LedgerEntry.objects.create(
            date=instance.payment_date,
            description=f"Payment for {instance.commitment.title} ({instance.commitment.get_commitment_type_display()})",
            amount=instance.amount_paid,
            transaction_type='operational',
            reference_number=instance.reference_number,
            commitment=instance.commitment
        )
        
        # Link the ledger entry to this payment
        instance.ledger_entry = ledger_entry
        instance.save(update_fields=['ledger_entry'])
        
        return ledger_entry
