from django.utils import timezone
from .models import LedgerEntry, Transaction, BankAccount

def create_ledger_entry(date, description, amount, transaction_type, reference_number=None, 
                       supplier=None, customer=None, purchase=None, delivery=None, 
                       commitment=None, created_by=None, payment_method=None, bank_account=None):
    """
    Create a ledger entry and optionally a bank transaction
    """
    # Create the ledger entry
    ledger_entry = LedgerEntry.objects.create(
        date=date,
        description=description,
        amount=amount,
        transaction_type=transaction_type,
        reference_number=reference_number,
        supplier=supplier,
        customer=customer,
        purchase=purchase,
        delivery=delivery,
        commitment=commitment,
        created_by=created_by
    )
    
    # If this transaction involves a bank account, create a bank transaction
    if bank_account and payment_method == 'bank_transfer':
        # Determine transaction type
        if transaction_type in ['income', 'sale']:
            bank_transaction_type = 'deposit'
        elif transaction_type in ['expense', 'purchase', 'operational']:
            bank_transaction_type = 'withdrawal'
        else:
            bank_transaction_type = 'transfer'
        
        # Create the bank transaction
        bank_transaction = Transaction.objects.create(
            bank_account=bank_account,
            transaction_type=bank_transaction_type,
            amount=amount,
            date=date,
            description=description,
            reference_number=reference_number,
            ledger_entry=ledger_entry
        )
        
        # Update bank account balance
        if bank_transaction_type == 'deposit':
            bank_account.current_balance += amount
        elif bank_transaction_type == 'withdrawal':
            bank_account.current_balance -= amount
        bank_account.save()
    
    return ledger_entry 