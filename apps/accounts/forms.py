from django import forms
from .models import LedgerEntry, Transaction, BankAccount

class TransactionFilterForm(forms.Form):
    """
    Form for filtering transactions in the unified ledger view
    """
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by description or reference...'})
    )
    entity = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by customer, supplier or payee name...'})
    )
    transaction_type = forms.ChoiceField(
        required=False,
        choices=(('', 'All Types'),) + LedgerEntry.TRANSACTION_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class BankAccountForm(forms.ModelForm):
    """
    Form for adding and updating bank accounts
    """
    class Meta:
        model = BankAccount
        fields = ['name', 'account_number', 'bank_name', 'branch', 'initial_balance', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
            'initial_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class TransactionForm(forms.ModelForm):
    """
    Form for adding and updating bank transactions
    """
    class Meta:
        model = Transaction
        fields = ['bank_account', 'transaction_type', 'amount', 'date', 'description', 'reference_number']
        widgets = {
            'bank_account': forms.Select(attrs={'class': 'form-control'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class LedgerEntryForm(forms.ModelForm):
    """
    Form for adding and updating ledger entries (cash transactions)
    """
    class Meta:
        model = LedgerEntry
        fields = ['date', 'description', 'amount', 'transaction_type', 'reference_number']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
        } 