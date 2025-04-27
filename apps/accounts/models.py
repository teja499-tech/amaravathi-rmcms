from django.db import models
from django.conf import settings
from apps.core.models import BaseModel
from apps.suppliers.models import Supplier, Purchase
from apps.customers.models import Customer, Delivery


class LedgerEntry(BaseModel):
    """
    Model for ledger entries (general accounting transactions).
    """
    TRANSACTION_TYPES = (
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('transfer', 'Transfer'),
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('adjustment', 'Adjustment'),
        ('operational', 'Operational'),
    )
    
    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    reference_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Optional relationships
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    purchase = models.ForeignKey(Purchase, on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    delivery = models.ForeignKey(Delivery, on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    commitment = models.ForeignKey('commitments.OperationalCommitment', on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    
    # User who created the entry
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='ledger_entries')
    
    def __str__(self):
        return f"{self.date} - {self.description} - {self.amount}"


class BankAccount(BaseModel):
    """
    Model for bank accounts.
    """
    name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=100)
    branch = models.CharField(max_length=100, blank=True, null=True)
    initial_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Only set current_balance when creating a new account
            self.current_balance = self.initial_balance
        super().save(*args, **kwargs)


class Transaction(BaseModel):
    """
    Model for financial transactions.
    """
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer', 'Transfer'),
    )
    
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions')
    destination_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=255)
    reference_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Links to relevant models
    ledger_entry = models.OneToOneField(LedgerEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='transaction')
    
    def __str__(self):
        return f"{self.transaction_type} - {self.bank_account} - {self.amount}" 