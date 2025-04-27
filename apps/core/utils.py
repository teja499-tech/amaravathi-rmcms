from django.db.models import Q, Sum
from datetime import datetime, timedelta
from django.utils import timezone
from collections import defaultdict
from itertools import groupby
from operator import itemgetter

from apps.customers.models import CustomerPayment
from apps.suppliers.models import SupplierPayment
from apps.expenses.models import Expense, Salary


def get_cash_bank_transactions(start_date=None, end_date=None, payment_mode=None):
    """
    Fetch all cash and bank transactions from various models between the given dates
    and organize them into a unified format for cash/bank book reporting.
    
    Args:
        start_date: Starting date for transactions (inclusive)
        end_date: Ending date for transactions (inclusive)
        payment_mode: Filter by payment mode ('Cash', 'Bank', None for all)
    
    Returns:
        List of transaction dictionaries sorted by date
    """
    today = timezone.now().date()
    
    # Default dates if not provided
    if not start_date:
        start_date = today.replace(day=1)  # First day of current month
    if not end_date:
        end_date = today
    
    # Ensure end_date includes the full day
    end_date_inclusive = datetime.combine(end_date, datetime.max.time())
    if timezone.is_naive(end_date_inclusive):
        end_date_inclusive = timezone.make_aware(end_date_inclusive)
    
    transactions = []
    
    # Filter condition for payment mode
    mode_filter = {}
    if payment_mode:
        mode_filter = {'payment_mode': payment_mode}
    
    # Customer Payments (Receipts)
    customer_payments = CustomerPayment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date_inclusive,
        **mode_filter
    ).select_related('customer', 'delivery')
    
    for payment in customer_payments:
        description = f"Receipt from {payment.customer.name}"
        if payment.delivery:
            description += f" for Invoice #{payment.delivery.invoice_number}"
        
        transactions.append({
            'date': payment.payment_date,
            'description': description,
            'reference': f"Rcpt#{payment.id}",
            'type': 'receipt',
            'receipt_amount': payment.amount_paid,
            'payment_amount': 0,
            'payment_mode': payment.payment_mode,
            'source_type': 'customer_payment',
            'source_id': payment.id
        })
    
    # Supplier Payments (Payments)
    supplier_payments = SupplierPayment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date_inclusive,
        **mode_filter
    ).select_related('supplier', 'purchase')
    
    for payment in supplier_payments:
        description = f"Payment to {payment.supplier.name}"
        if payment.purchase:
            description += f" for Invoice #{payment.purchase.invoice_number}"
        
        transactions.append({
            'date': payment.payment_date,
            'description': description,
            'reference': f"Pay#{payment.id}",
            'type': 'payment',
            'receipt_amount': 0,
            'payment_amount': payment.amount_paid,
            'payment_mode': payment.payment_mode,
            'source_type': 'supplier_payment',
            'source_id': payment.id
        })
    
    # Expenses (Payments)
    expense_filter = Q(date__gte=start_date, date__lte=end_date_inclusive)
    if payment_mode:
        expense_filter &= Q(payment_mode=payment_mode)
    
    expenses = Expense.objects.filter(expense_filter).select_related('category')
    
    for expense in expenses:
        transactions.append({
            'date': expense.date,
            'description': f"Expense: {expense.category.name} - {expense.description}",
            'reference': f"Exp#{expense.id}",
            'type': 'payment',
            'receipt_amount': 0,
            'payment_amount': expense.amount,
            'payment_mode': expense.payment_mode,
            'source_type': 'expense',
            'source_id': expense.id
        })
    
    # Salaries (Payments)
    salary_filter = Q(paid_on__gte=start_date, paid_on__lte=end_date_inclusive)
    if payment_mode:
        salary_filter &= Q(payment_mode=payment_mode)
    
    salaries = Salary.objects.filter(salary_filter).select_related('employee')
    
    for salary in salaries:
        month_str = salary.month.strftime('%B %Y')
        transactions.append({
            'date': salary.paid_on,
            'description': f"Salary to {salary.employee.name} for {month_str}",
            'reference': f"Sal#{salary.id}",
            'type': 'payment',
            'receipt_amount': 0,
            'payment_amount': salary.amount,
            'payment_mode': salary.payment_mode,
            'source_type': 'salary',
            'source_id': salary.id
        })
    
    # Sort all transactions by date
    transactions.sort(key=lambda x: x['date'])
    
    return transactions


def get_opening_balance(start_date, payment_mode=None):
    """
    Calculate opening balance by getting all transactions before start_date
    
    Args:
        start_date: The date for which opening balance is needed
        payment_mode: Filter by payment mode ('Cash', 'Bank', None for all)
    
    Returns:
        Opening balance amount
    """
    # Get all transactions before start_date
    transactions = get_cash_bank_transactions(
        end_date=start_date - timedelta(days=1),
        payment_mode=payment_mode
    )
    
    # Calculate balance
    total_receipts = sum(t['receipt_amount'] for t in transactions)
    total_payments = sum(t['payment_amount'] for t in transactions)
    
    # You might want to add an initial base amount from your settings
    initial_balance = 0  # Replace with actual initial balance if needed
    
    return initial_balance + total_receipts - total_payments


def prepare_day_wise_entries(transactions, start_date, end_date, opening_balance):
    """
    Group transactions by date and calculate daily totals and running balances
    
    Args:
        transactions: List of transaction dictionaries
        start_date: Starting date
        end_date: Ending date
        opening_balance: Opening balance for start_date
    
    Returns:
        Tuple containing:
            - Dictionary of day-wise entries with totals
            - Total receipts for the period
            - Total payments for the period
            - Closing balance
    """
    # Group transactions by date
    day_wise = defaultdict(list)
    for txn in transactions:
        day_str = txn['date'].strftime('%Y-%m-%d')
        day_wise[day_str].append(txn)
    
    # Calculate daily totals and running balance
    day_wise_entries = []
    running_balance = opening_balance
    total_receipts = 0
    total_payments = 0
    
    # Ensure we have entries for all days in the range
    current_date = start_date
    while current_date <= end_date:
        day_str = current_date.strftime('%Y-%m-%d')
        
        # Get transactions for this day or use empty list
        day_transactions = day_wise.get(day_str, [])
        
        # Calculate daily totals
        day_receipts = sum(t['receipt_amount'] for t in day_transactions)
        day_payments = sum(t['payment_amount'] for t in day_transactions)
        day_net_flow = day_receipts - day_payments
        
        # Update running totals
        total_receipts += day_receipts
        total_payments += day_payments
        running_balance += day_net_flow
        
        # Only include days with transactions
        if day_transactions:
            day_wise_entries.append((
                day_str,
                {
                    'date': current_date,
                    'transactions': day_transactions,
                    'total_receipts': day_receipts,
                    'total_payments': day_payments,
                    'net_flow': day_net_flow,
                    'closing_balance': running_balance
                }
            ))
        
        current_date += timedelta(days=1)
    
    closing_balance = opening_balance + total_receipts - total_payments
    
    return day_wise_entries, total_receipts, total_payments, closing_balance 