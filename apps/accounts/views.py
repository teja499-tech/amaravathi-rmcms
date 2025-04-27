from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Q, F
from django.contrib import messages

from apps.users.utils import admin_required, accountant_required, viewer_required
from apps.customers.models import Delivery
from apps.expenses.models import Expense, Salary
from apps.suppliers.models import Purchase
from .models import LedgerEntry, BankAccount, Transaction
from .forms import TransactionFilterForm, BankAccountForm, TransactionForm, LedgerEntryForm

# Add view classes and functions here 

@viewer_required
def profit_loss_report(request):
    """
    Profit/Loss report view showing income vs. expenses
    """
    # Default to last 30 days if no date range specified
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get filter parameters
    filter_start_date = request.GET.get('start_date')
    filter_end_date = request.GET.get('end_date')
    
    # Apply date filters if provided
    if filter_start_date:
        start_date = datetime.strptime(filter_start_date, '%Y-%m-%d').date()
    if filter_end_date:
        end_date = datetime.strptime(filter_end_date, '%Y-%m-%d').date()
    
    # Get all deliveries (income) in date range
    deliveries = Delivery.objects.filter(date__gte=start_date, date__lte=end_date)
    total_income = sum(delivery.total_amount for delivery in deliveries)
    
    # Get all expenses in date range
    expenses = Expense.objects.filter(date__gte=start_date, date__lte=end_date)
    total_expenses = sum(expense.amount for expense in expenses)
    
    # Get all salaries in date range
    salaries = Salary.objects.filter(paid_on__gte=start_date, paid_on__lte=end_date)
    total_salaries = sum(salary.amount for salary in salaries)
    
    # Get all purchases in date range
    purchases = Purchase.objects.filter(date__gte=start_date, date__lte=end_date)
    total_purchases = sum(purchase.total_amount for purchase in purchases)
    
    # Calculate totals
    total_outflow = total_expenses + total_salaries + total_purchases
    net_profit = total_income - total_outflow
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_salaries': total_salaries,
        'total_purchases': total_purchases,
        'total_outflow': total_outflow,
        'net_profit': net_profit,
        'is_profit': net_profit >= 0,
    }
    
    return render(request, 'accounts/profit_loss.html', context)

@admin_required
def settings_view(request):
    """
    System settings view
    """
    # This is a placeholder for now
    context = {
        'title': 'System Settings',
    }
    
    return render(request, 'accounts/settings.html', context) 

@viewer_required
def unified_ledger_view(request):
    """
    Unified ledger view showing all financial transactions across the system
    """
    # Default to last 30 days if no date range specified
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Initialize form with request data or defaults
    form = TransactionFilterForm(request.GET or None)
    
    # Set up base query
    queryset = LedgerEntry.objects.all().order_by('-date', '-created_at')
    
    # Apply filters if form is valid
    if form.is_valid():
        data = form.cleaned_data
        
        # Date range filter
        if data.get('start_date'):
            start_date = data['start_date']
            queryset = queryset.filter(date__gte=start_date)
        
        if data.get('end_date'):
            end_date = data['end_date']
            queryset = queryset.filter(date__lte=end_date)
        
        # Search filter (description or reference)
        if data.get('search'):
            search_term = data['search']
            queryset = queryset.filter(
                Q(description__icontains=search_term) | 
                Q(reference_number__icontains=search_term)
            )
        
        # Transaction type filter
        if data.get('transaction_type'):
            queryset = queryset.filter(transaction_type=data['transaction_type'])
            
        # Entity filter (customer, supplier, commitment)
        if data.get('entity'):
            entity = data.get('entity')
            queryset = queryset.filter(
                Q(customer__name__icontains=entity) |
                Q(supplier__name__icontains=entity) |
                Q(commitment__payee_name__icontains=entity)
            )
    else:
        # Apply default date range if form not submitted
        queryset = queryset.filter(date__gte=start_date, date__lte=end_date)
    
    # Calculate totals for summary cards
    inflow_types = ['income', 'sale']
    outflow_types = ['expense', 'purchase', 'operational']
    
    total_inflow = queryset.filter(transaction_type__in=inflow_types).aggregate(Sum('amount'))['amount__sum'] or 0
    total_outflow = queryset.filter(transaction_type__in=outflow_types).aggregate(Sum('amount'))['amount__sum'] or 0
    net_cash_flow = total_inflow - total_outflow
    transaction_count = queryset.count()
    
    context = {
        'form': form,
        'transactions': queryset,
        'start_date': start_date,
        'end_date': end_date,
        'total_inflow': total_inflow,
        'total_outflow': total_outflow,
        'net_cash_flow': net_cash_flow,
        'transaction_count': transaction_count,
    }
    
    return render(request, 'accounts/unified_ledger.html', context)

@viewer_required
def cash_book_view(request):
    """
    Cash book view showing all cash transactions
    """
    # Default to last 30 days if no date range specified
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Initialize form with request data or defaults
    form = TransactionFilterForm(request.GET or None)
    
    # Set up base query - filter for cash transactions
    # For this example, we're assuming cash transactions are in LedgerEntry
    # and don't have an associated bank account transaction
    queryset = LedgerEntry.objects.filter(
        Q(transaction__isnull=True)  # No bank transaction
    ).order_by('-date', '-created_at')
    
    # Apply filters if form is valid
    if form.is_valid():
        data = form.cleaned_data
        
        # Date range filter
        if data.get('start_date'):
            start_date = data['start_date']
            queryset = queryset.filter(date__gte=start_date)
        
        if data.get('end_date'):
            end_date = data['end_date']
            queryset = queryset.filter(date__lte=end_date)
        
        # Search filter (description or reference)
        if data.get('search'):
            search_term = data['search']
            queryset = queryset.filter(
                Q(description__icontains=search_term) | 
                Q(reference_number__icontains=search_term)
            )
        
        # Transaction type filter
        if data.get('transaction_type'):
            queryset = queryset.filter(transaction_type=data['transaction_type'])
    else:
        # Apply default date range if form not submitted
        queryset = queryset.filter(date__gte=start_date, date__lte=end_date)
    
    # Calculate totals for summary cards
    inflow_types = ['income', 'sale']
    outflow_types = ['expense', 'purchase']
    
    total_inflow = queryset.filter(transaction_type__in=inflow_types).aggregate(Sum('amount'))['amount__sum'] or 0
    total_outflow = queryset.filter(transaction_type__in=outflow_types).aggregate(Sum('amount'))['amount__sum'] or 0
    net_cash_flow = total_inflow - total_outflow
    transaction_count = queryset.count()
    
    context = {
        'form': form,
        'transactions': queryset,
        'start_date': start_date,
        'end_date': end_date,
        'total_inflow': total_inflow,
        'total_outflow': total_outflow,
        'net_cash_flow': net_cash_flow,
        'transaction_count': transaction_count,
        'book_type': 'Cash Book',
    }
    
    return render(request, 'accounts/book_view.html', context)

@viewer_required
def bank_book_view(request):
    """
    Bank book view showing all bank transactions
    """
    # Default to last 30 days if no date range specified
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get bank account filter if provided
    bank_account_id = request.GET.get('bank_account')
    
    # Initialize form with request data or defaults
    form = TransactionFilterForm(request.GET or None)
    
    # Set up base query - get all bank transactions
    queryset = Transaction.objects.all().order_by('-date', '-created_at')
    
    # Apply bank account filter if provided
    if bank_account_id:
        queryset = queryset.filter(bank_account_id=bank_account_id)
    
    # Apply filters if form is valid
    if form.is_valid():
        data = form.cleaned_data
        
        # Date range filter
        if data.get('start_date'):
            start_date = data['start_date']
            queryset = queryset.filter(date__gte=start_date)
        
        if data.get('end_date'):
            end_date = data['end_date']
            queryset = queryset.filter(date__lte=end_date)
        
        # Search filter (description or reference)
        if data.get('search'):
            search_term = data['search']
            queryset = queryset.filter(
                Q(description__icontains=search_term) | 
                Q(reference_number__icontains=search_term)
            )
        
        # Transaction type filter
        if data.get('transaction_type'):
            # Map LedgerEntry transaction type to bank Transaction type if needed
            # This depends on your specific business logic
            queryset = queryset.filter(transaction_type=data['transaction_type'])
    else:
        # Apply default date range if form not submitted
        queryset = queryset.filter(date__gte=start_date, date__lte=end_date)
    
    # Get all bank accounts for the dropdown filter
    bank_accounts = BankAccount.objects.filter(is_active=True)
    
    # Calculate totals for summary cards
    inflow_types = ['deposit']
    outflow_types = ['withdrawal']
    
    total_inflow = queryset.filter(transaction_type__in=inflow_types).aggregate(Sum('amount'))['amount__sum'] or 0
    total_outflow = queryset.filter(transaction_type__in=outflow_types).aggregate(Sum('amount'))['amount__sum'] or 0
    net_cash_flow = total_inflow - total_outflow
    transaction_count = queryset.count()
    
    context = {
        'form': form,
        'transactions': queryset,
        'start_date': start_date,
        'end_date': end_date,
        'total_inflow': total_inflow,
        'total_outflow': total_outflow,
        'net_cash_flow': net_cash_flow,
        'transaction_count': transaction_count,
        'bank_accounts': bank_accounts,
        'selected_bank_account': bank_account_id,
        'book_type': 'Bank Book',
    }
    
    return render(request, 'accounts/bank_book.html', context)

@admin_required
def bank_account_list(request):
    """List all bank accounts"""
    bank_accounts = BankAccount.objects.all().order_by('-is_active', 'name')
    context = {
        'bank_accounts': bank_accounts
    }
    return render(request, 'accounts/bank_account_list.html', context)

@admin_required
def bank_account_create(request):
    """Create a new bank account"""
    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bank account created successfully.')
            return redirect('accounts:bank_account_list')
    else:
        form = BankAccountForm()
    
    context = {
        'form': form,
        'title': 'Add Bank Account'
    }
    return render(request, 'accounts/bank_account_form.html', context)

@admin_required
def bank_account_update(request, pk):
    """Update an existing bank account"""
    bank_account = get_object_or_404(BankAccount, pk=pk)
    
    if request.method == 'POST':
        form = BankAccountForm(request.POST, instance=bank_account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bank account updated successfully.')
            return redirect('accounts:bank_account_list')
    else:
        form = BankAccountForm(instance=bank_account)
    
    context = {
        'form': form,
        'bank_account': bank_account,
        'title': 'Edit Bank Account'
    }
    return render(request, 'accounts/bank_account_form.html', context)

@admin_required
def bank_account_delete(request, pk):
    """Delete a bank account"""
    bank_account = get_object_or_404(BankAccount, pk=pk)
    
    if request.method == 'POST':
        bank_account.delete()
        messages.success(request, 'Bank account deleted successfully.')
        return redirect('accounts:bank_account_list')
    
    context = {
        'bank_account': bank_account
    }
    return render(request, 'accounts/bank_account_confirm_delete.html', context)

@accountant_required
def transaction_create(request):
    """Create a new bank transaction"""
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save()
            
            # Update bank account balance
            bank_account = transaction.bank_account
            if transaction.transaction_type == 'deposit':
                bank_account.current_balance += transaction.amount
            elif transaction.transaction_type == 'withdrawal':
                bank_account.current_balance -= transaction.amount
            bank_account.save()
            
            # Create corresponding ledger entry
            transaction_type = 'income' if transaction.transaction_type == 'deposit' else 'expense'
            ledger_entry = LedgerEntry.objects.create(
                date=transaction.date,
                description=transaction.description,
                amount=transaction.amount,
                transaction_type=transaction_type,
                reference_number=transaction.reference_number,
                created_by=request.user
            )
            
            # Link ledger entry to transaction
            transaction.ledger_entry = ledger_entry
            transaction.save()
            
            messages.success(request, 'Transaction created successfully.')
            return redirect('accounts:bank_book')
    else:
        form = TransactionForm()
    
    context = {
        'form': form,
        'title': 'Add Bank Transaction'
    }
    return render(request, 'accounts/transaction_form.html', context)

@accountant_required
def transaction_update(request, pk):
    """Update an existing bank transaction"""
    transaction = get_object_or_404(Transaction, pk=pk)
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            # Revert old impact on bank balance
            bank_account = transaction.bank_account
            if transaction.transaction_type == 'deposit':
                bank_account.current_balance -= transaction.amount
            elif transaction.transaction_type == 'withdrawal':
                bank_account.current_balance += transaction.amount
            
            # Save updated transaction
            updated_transaction = form.save()
            
            # Apply new impact on bank balance
            if updated_transaction.transaction_type == 'deposit':
                bank_account.current_balance += updated_transaction.amount
            elif updated_transaction.transaction_type == 'withdrawal':
                bank_account.current_balance -= updated_transaction.amount
            bank_account.save()
            
            # Update linked ledger entry if exists
            if transaction.ledger_entry:
                ledger_entry = transaction.ledger_entry
                ledger_entry.date = updated_transaction.date
                ledger_entry.description = updated_transaction.description
                ledger_entry.amount = updated_transaction.amount
                ledger_entry.transaction_type = 'income' if updated_transaction.transaction_type == 'deposit' else 'expense'
                ledger_entry.reference_number = updated_transaction.reference_number
                ledger_entry.save()
            
            messages.success(request, 'Transaction updated successfully.')
            return redirect('accounts:bank_book')
    else:
        form = TransactionForm(instance=transaction)
    
    context = {
        'form': form,
        'transaction': transaction,
        'title': 'Edit Bank Transaction'
    }
    return render(request, 'accounts/transaction_form.html', context)

@accountant_required
def transaction_delete(request, pk):
    """Delete a bank transaction"""
    transaction = get_object_or_404(Transaction, pk=pk)
    
    if request.method == 'POST':
        # Revert impact on bank balance
        bank_account = transaction.bank_account
        if transaction.transaction_type == 'deposit':
            bank_account.current_balance -= transaction.amount
        elif transaction.transaction_type == 'withdrawal':
            bank_account.current_balance += transaction.amount
        bank_account.save()
        
        # Delete linked ledger entry if exists
        if transaction.ledger_entry:
            transaction.ledger_entry.delete()
        
        # Delete transaction
        transaction.delete()
        
        messages.success(request, 'Transaction deleted successfully.')
        return redirect('accounts:bank_book')
    
    context = {
        'transaction': transaction
    }
    return render(request, 'accounts/transaction_confirm_delete.html', context)

@accountant_required
def cash_transaction_create(request):
    """Create a new cash transaction (ledger entry)"""
    if request.method == 'POST':
        form = LedgerEntryForm(request.POST)
        if form.is_valid():
            ledger_entry = form.save(commit=False)
            ledger_entry.created_by = request.user
            ledger_entry.save()
            
            messages.success(request, 'Cash transaction created successfully.')
            return redirect('accounts:cash_book')
    else:
        form = LedgerEntryForm()
    
    context = {
        'form': form,
        'title': 'Add Cash Transaction'
    }
    return render(request, 'accounts/cash_transaction_form.html', context)

@accountant_required
def cash_transaction_update(request, pk):
    """Update an existing cash transaction"""
    ledger_entry = get_object_or_404(LedgerEntry, pk=pk)
    
    if request.method == 'POST':
        form = LedgerEntryForm(request.POST, instance=ledger_entry)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cash transaction updated successfully.')
            return redirect('accounts:cash_book')
    else:
        form = LedgerEntryForm(instance=ledger_entry)
    
    context = {
        'form': form,
        'ledger_entry': ledger_entry,
        'title': 'Edit Cash Transaction'
    }
    return render(request, 'accounts/cash_transaction_form.html', context)

@accountant_required
def cash_transaction_delete(request, pk):
    """Delete a cash transaction"""
    ledger_entry = get_object_or_404(LedgerEntry, pk=pk)
    
    if request.method == 'POST':
        ledger_entry.delete()
        messages.success(request, 'Cash transaction deleted successfully.')
        return redirect('accounts:cash_book')
    
    context = {
        'ledger_entry': ledger_entry
    }
    return render(request, 'accounts/cash_transaction_confirm_delete.html', context) 