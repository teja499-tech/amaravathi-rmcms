from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum, Count, F, Case, When, Value, IntegerField, DecimalField, BooleanField
from django.db import connection
from django.conf import settings
from datetime import datetime, date, timedelta
from calendar import monthrange
import json
import os
import csv
import xlwt
from io import BytesIO
import tempfile
import pdfkit
from decimal import Decimal
from collections import defaultdict
import calendar
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.core.management import call_command
from django.urls import reverse_lazy, reverse
from django.db.models import Sum, Count, F, Q, Value
from django.db.models.functions import Coalesce
from django.contrib import messages

from apps.customers.models import Customer, Delivery, CustomerPayment
from apps.suppliers.models import Supplier, Purchase, SupplierPayment
from apps.expenses.models import Expense, ExpenseCategory
from apps.expenses.models import Salary
from employees.models import Employee, SalaryRecord
from apps.accounts.models import BankAccount, LedgerEntry
from apps.users.utils import viewer_required
from apps.commitments.models import OperationalCommitment, CommitmentPayment
from apps.materials.models import Material
from apps.customers.models import ConcreteDelivery, MixRatio
from apps.materials.models import PurchaseOrder


@login_required
def home(request):
    """
    Home page view
    """
    return render(request, 'core/home.html')


@csrf_exempt
def health_check(request):
    """
    Health check endpoint for monitoring the application
    """
    # Check database connection
    db_status = "ok"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            if row is None:
                db_status = "error"
    except Exception as e:
        db_status = str(e)

    # Return health status
    status = {
        "status": "ok",
        "database": db_status,
        "version": "1.0.0"
    }
    
    return JsonResponse(status)


class TransactionEntry:
    """Helper class to standardize transaction entries from different sources"""
    def __init__(self, date, transaction_type, entity_name, amount, mode, remarks, is_inflow, reference_id=None):
        self.date = date
        self.transaction_type = transaction_type
        self.entity_name = entity_name
        self.amount = amount
        self.mode = mode
        self.remarks = remarks
        self.is_inflow = is_inflow  # True for cash-in, False for cash-out
        self.reference_id = reference_id


@viewer_required
def unified_ledger(request):
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search = request.GET.get('search')
    transaction_type = request.GET.get('transaction_type')
    payment_mode = request.GET.get('payment_mode')
    entity_name = request.GET.get('entity_name')
    
    # Track active filters for display
    active_filters = []
    
    # Default to last 30 days if no dates provided
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    else:
        active_filters.append(f"From: {start_date}")
        
    if not end_date:
        end_date = timezone.now().strftime('%Y-%m-%d')
    else:
        active_filters.append(f"To: {end_date}")
        
    if transaction_type:
        type_labels = {
            'customer_payment': 'Customer Payments',
            'supplier_payment': 'Supplier Payments',
            'expense': 'Expenses',
            'salary': 'Salaries',
            'commitment': 'Operational Commitments'
        }
        active_filters.append(f"Type: {type_labels.get(transaction_type, transaction_type)}")
        
    if payment_mode:
        active_filters.append(f"Payment Mode: {payment_mode}")
        
    if entity_name:
        active_filters.append(f"Entity: {entity_name}")
        
    if search:
        active_filters.append(f"Search: {search}")
    
    # Convert string dates to datetime objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Prepare transaction lists from different sources
    all_transactions = []
    
    # Customer Payments (inflow)
    if not transaction_type or transaction_type == 'customer_payment':
        customer_payments = CustomerPayment.objects.filter(
            payment_date__gte=start_date_obj,
            payment_date__lte=end_date_obj
        )
        
        # Apply entity name filter
        if entity_name:
            customer_payments = customer_payments.filter(
                customer__name__icontains=entity_name
            )
        
        # Apply payment mode filter
        if payment_mode:
            customer_payments = customer_payments.filter(
                payment_mode=payment_mode
            )
        
        if search:
            customer_payments = customer_payments.filter(
                Q(delivery__invoice_number__icontains=search) |
                Q(reference_number__icontains=search) |
                Q(remarks__icontains=search)
            )
        
        for payment in customer_payments:
            all_transactions.append({
                'id': payment.id,
                'date': payment.payment_date,
                'description': f"Payment from {payment.customer.name}" + (f" for {payment.delivery.invoice_number}" if payment.delivery else ""),
                'reference': payment.reference_number or f"Receipt #{payment.id}",
                'type': 'customer_payment',
                'payment_mode': payment.get_payment_mode_display(),
                'inflow': payment.amount_paid,
                'outflow': None
            })
    
    # Supplier Payments (outflow)
    if not transaction_type or transaction_type == 'supplier_payment':
        supplier_payments = SupplierPayment.objects.filter(
            payment_date__gte=start_date_obj,
            payment_date__lte=end_date_obj
        )
        
        # Apply entity name filter
        if entity_name:
            supplier_payments = supplier_payments.filter(
                supplier__name__icontains=entity_name
            )
        
        # Apply payment mode filter
        if payment_mode:
            supplier_payments = supplier_payments.filter(
                payment_mode=payment_mode
            )
        
        if search:
            supplier_payments = supplier_payments.filter(
                Q(purchase__invoice_number__icontains=search) |
                Q(reference_number__icontains=search) |
                Q(remarks__icontains=search)
            )
        
        for payment in supplier_payments:
            all_transactions.append({
                'id': payment.id,
                'date': payment.payment_date,
                'description': f"Payment to {payment.supplier.name}" + (f" for {payment.purchase.invoice_number}" if payment.purchase else ""),
                'reference': payment.reference_number or f"Payment #{payment.id}",
                'type': 'supplier_payment',
                'payment_mode': payment.get_payment_mode_display(),
                'inflow': None,
                'outflow': payment.amount_paid
            })
    
    # Expenses (outflow)
    if not transaction_type or transaction_type == 'expense':
        expenses = Expense.objects.filter(
            date__gte=start_date_obj,
            date__lte=end_date_obj
        )
        
        # Apply payment mode filter
        if payment_mode:
            expenses = expenses.filter(
                payment_method=payment_mode
            )
        
        if search:
            expenses = expenses.filter(
                Q(description__icontains=search) |
                Q(category__name__icontains=search)
            )
        
        for expense in expenses:
            # Skip expenses if entity filter is applied but doesn't match
            if entity_name and (not hasattr(expense, 'vehicle') or not expense.vehicle or 
                               entity_name.lower() not in expense.vehicle.name.lower()):
                continue
                
            all_transactions.append({
                'id': expense.id,
                'date': expense.date,
                'description': f"Expense: {expense.description}",
                'reference': f"Expense #{expense.id}",
                'type': 'expense',
                'payment_mode': expense.get_payment_method_display() if hasattr(expense, 'get_payment_method_display') else 'Cash',
                'inflow': None,
                'outflow': expense.amount
            })
    
    # Salaries (outflow)
    if not transaction_type or transaction_type == 'salary':
        salaries = Salary.objects.filter(
            paid_on__gte=start_date_obj,
            paid_on__lte=end_date_obj
        )
        
        # Apply entity name filter
        if entity_name:
            salaries = salaries.filter(
                employee__name__icontains=entity_name
            )
        
        # Apply payment mode filter (assuming default is cash for salaries)
        if payment_mode and payment_mode != 'CASH':
            salaries = salaries.none()  # Exclude all salaries if filtering for non-cash
        
        if search:
            salaries = salaries.filter(
                Q(employee__name__icontains=search) |
                Q(notes__icontains=search)
            )
        
        for salary in salaries:
            all_transactions.append({
                'id': salary.id,
                'date': salary.paid_on,
                'description': f"Salary paid to {salary.employee.name} for {salary.month}",
                'reference': f"Salary #{salary.id}",
                'type': 'salary',
                'payment_mode': 'Cash',  # Default for salaries
                'inflow': None,
                'outflow': salary.amount
            })
    
    # Commitment Payments (outflow)
    if not transaction_type or transaction_type == 'commitment':
        commitment_payments = CommitmentPayment.objects.filter(
            payment_date__gte=start_date_obj,
            payment_date__lte=end_date_obj
        )
        
        # Apply entity name filter
        if entity_name:
            commitment_payments = commitment_payments.filter(
                commitment__payee_name__icontains=entity_name
            )
        
        # Apply payment mode filter
        if payment_mode:
            commitment_payments = commitment_payments.filter(
                payment_mode=payment_mode
            )
        
        if search:
            commitment_payments = commitment_payments.filter(
                Q(commitment__title__icontains=search) |
                Q(reference_number__icontains=search) |
                Q(remarks__icontains=search)
            )
        
        for payment in commitment_payments:
            all_transactions.append({
                'id': payment.id,
                'date': payment.payment_date,
                'description': f"Payment for {payment.commitment.title} ({payment.commitment.get_commitment_type_display()})",
                'reference': payment.reference_number or f"Commitment #{payment.id}",
                'type': 'commitment',
                'payment_mode': payment.get_payment_mode_display(),
                'inflow': None,
                'outflow': payment.amount_paid
            })
    
    # Sort all transactions by date (newest first)
    all_transactions = sorted(all_transactions, key=lambda t: t['date'], reverse=True)
    
    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = 50
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Calculate totals for summary cards
    total_inflow = sum(t['inflow'] or 0 for t in all_transactions)
    total_outflow = sum(t['outflow'] or 0 for t in all_transactions)
    net_cash_flow = total_inflow - total_outflow
    transaction_count = len(all_transactions)
    
    # Get paginated transactions
    paginated_transactions = all_transactions[start_idx:end_idx]
    total_pages = (transaction_count + per_page - 1) // per_page  # Ceiling division
    
    # Generate a reasonable page range for pagination display
    if total_pages <= 5:
        page_range = range(1, total_pages + 1)
    else:
        if page <= 3:
            page_range = range(1, 6)
        elif page >= total_pages - 2:
            page_range = range(total_pages - 4, total_pages + 1)
        else:
            page_range = range(page - 2, page + 3)
    
    context = {
        'transactions': paginated_transactions,
        'start_date': start_date,
        'end_date': end_date,
        'search': search,
        'transaction_type': transaction_type,
        'payment_mode': payment_mode,
        'entity_name': entity_name,
        'active_filters': active_filters,
        'total_inflow': total_inflow,
        'total_outflow': total_outflow,
        'net_cash_flow': net_cash_flow,
        'transaction_count': transaction_count,
        'current_page': page,
        'total_pages': total_pages,
        'has_previous': page > 1,
        'has_next': page < total_pages,
        'previous_page': page - 1,
        'next_page': page + 1,
        'page_range': page_range,
    }
    
    return render(request, 'core/unified_ledger.html', context)


@login_required
def dashboard_view(request):
    """Dashboard view with summary of key business metrics."""
    today_date = timezone.now().date()
    today = timezone.now()  # Full datetime object that can be formatted with time
    
    # Initialize lists for dues
    customer_dues = []
    supplier_dues = []
    
    # Get counts of active entities
    active_customers_count = Customer.objects.filter(is_active=True).count()
    
    # Count both regular and concrete deliveries
    regular_deliveries_count = Delivery.objects.count()
    concrete_deliveries_count = ConcreteDelivery.objects.count()
    deliveries_count = regular_deliveries_count + concrete_deliveries_count
    
    active_suppliers_count = Supplier.objects.filter(is_active=True).count()
    expenses_count = Expense.objects.count()
    
    # Calculate cash flow data for charts
    cash_flow_data = get_cashflow_data(today_date - timedelta(days=180), today_date)
    
    # Get this month's summary
    first_day_current_month = today_date.replace(day=1)
    month_summary = get_month_summary(first_day_current_month, today_date)
    
    # Get last 6 months data for the chart
    months_data = []
    for i in range(5, -1, -1):
        month_date = (today_date.replace(day=1) - timedelta(days=1)).replace(day=1)
        month_date = month_date.replace(month=(today_date.month - i) % 12 or 12, 
                                        year=today_date.year - ((today_date.month - i - 1) // 12))
        next_month = month_date.replace(month=month_date.month % 12 + 1, 
                                        year=month_date.year + (month_date.month // 12))
        if next_month.month == 1:
            next_month = next_month.replace(year=next_month.year + 1)
        
        month_end = (next_month - timedelta(days=1))
        month_data = get_month_summary(month_date, month_end)
        months_data.append({
            'month': month_date.strftime('%b %Y'),
            'inflow': month_data['total_inflow'],
            'outflow': month_data['total_outflow'],
            'net': month_data['net_cash_flow']
        })
    
    # Get bank balances
    bank_accounts = BankAccount.objects.filter(is_active=True)
    bank_balances = bank_accounts.aggregate(total=Sum('current_balance'))['total'] or 0
    
    # Estimate cash in hand (simplified)
    cash_in_hand = 0  # You would need to implement logic to track actual cash
    
    # Calculate dues for the heatmap
    # Customer dues
    upcoming_customer_dues = {}
    
    # Regular deliveries
    regular_customer_payments_due = Delivery.objects.filter(
        received_amount__lt=F('total_amount'),
        customer__is_active=True
    )
    
    # Process regular deliveries
    for delivery in regular_customer_payments_due:
        due_amount = delivery.total_amount - delivery.received_amount
        # Check if there's a related payment with a due date
        payment_with_due_date = CustomerPayment.objects.filter(delivery=delivery).order_by('-due_date').first()
        due_date = payment_with_due_date.due_date if payment_with_due_date and payment_with_due_date.due_date else today_date
        
        # Skip if due date is more than 30 days in future
        if (due_date - today_date).days > 30:
            continue
            
        date_str = due_date.strftime('%Y-%m-%d')
        if date_str in upcoming_customer_dues:
            upcoming_customer_dues[date_str] += due_amount
        else:
            upcoming_customer_dues[date_str] = due_amount
    
    # Concrete deliveries
    concrete_customer_payments_due = ConcreteDelivery.objects.filter(
        received_amount__lt=F('total_amount'),
        customer__is_active=True
    ).order_by('delivery_date')
    
    # Process concrete deliveries
    for delivery in concrete_customer_payments_due[:5]:  # Limit to 5 for display
        due_amount = delivery.total_amount - delivery.received_amount
        due_date = delivery.due_date if delivery.due_date else delivery.delivery_date
        # We'll collect all dues later, so no need to append here
        
    # Supplier dues
    upcoming_supplier_dues = {}
    
    # Legacy Purchase model
    supplier_payments_due = Purchase.objects.filter(
        paid_amount__lt=F('total_amount'),
        supplier__is_active=True
    )
    
    for purchase in supplier_payments_due:
        due_amount = purchase.total_amount - purchase.paid_amount
        due_date = purchase.due_date if hasattr(purchase, 'due_date') else today_date
        
        # Skip if due date is more than 30 days in future
        if (due_date - today_date).days > 30:
            continue
            
        date_str = due_date.strftime('%Y-%m-%d')
        if date_str in upcoming_supplier_dues:
            upcoming_supplier_dues[date_str] += due_amount
        else:
            upcoming_supplier_dues[date_str] = due_amount
    
    # Commitment dues (EMIs, etc.)
    upcoming_commitment_dues = {}
    commitment_payments_due = OperationalCommitment.objects.filter(
        status='active',
        is_active=True,
        next_payment_date__lte=today_date + timedelta(days=30)
    )
    
    for commitment in commitment_payments_due:
        due_date = commitment.next_payment_date
        date_str = due_date.strftime('%Y-%m-%d')
        if date_str in upcoming_commitment_dues:
            upcoming_commitment_dues[date_str] += commitment.amount
        else:
            upcoming_commitment_dues[date_str] = commitment.amount
    
    # Combine all dues for the heatmap
    all_dues = {}
    for date_str, amount in upcoming_customer_dues.items():
        all_dues[date_str] = {
            'customer': amount,
            'supplier': upcoming_supplier_dues.get(date_str, 0),
            'commitment': upcoming_commitment_dues.get(date_str, 0),
            'total': amount + upcoming_supplier_dues.get(date_str, 0) + upcoming_commitment_dues.get(date_str, 0)
        }
    
    for date_str, amount in upcoming_supplier_dues.items():
        if date_str not in all_dues:
            all_dues[date_str] = {
                'customer': 0,
                'supplier': amount,
                'commitment': upcoming_commitment_dues.get(date_str, 0),
                'total': amount + upcoming_commitment_dues.get(date_str, 0)
            }
    
    for date_str, amount in upcoming_commitment_dues.items():
        if date_str not in all_dues:
            all_dues[date_str] = {
                'customer': 0,
                'supplier': 0,
                'commitment': amount,
                'total': amount
            }
    
    # Format data for the heatmap
    heatmap_data = []
    for date_str, data in all_dues.items():
        heatmap_data.append({
            'date': date_str,
            'customer': data['customer'],
            'supplier': data['supplier'],
            'commitment': data['commitment'],
            'total': data['total']
        })
    
    # Sort heatmap data by date
    heatmap_data.sort(key=lambda x: x['date'])
    
    # Prepare context for the template
    context = {
        'active_customers_count': active_customers_count,
        'deliveries_count': deliveries_count,
        'active_suppliers_count': active_suppliers_count,
        'expenses_count': expenses_count,
        'cash_flow_data': cash_flow_data,
        'month_summary': month_summary,
        'months_data': months_data,
        'heatmap_data': heatmap_data,
        'bank_balances': bank_balances,
        'cash_in_hand': cash_in_hand,
        'today': today,
    }
    
    # Add due alerts (logic adapted from the original view)
    # Customer payments due
    regular_deliveries_due = Delivery.objects.filter(
        received_amount__lt=F('total_amount'),
        customer__is_active=True
    ).order_by('date')
    
    # Get a list of customer dues for display
    # Reusing the customer_dues list that was initialized at the top
    for delivery in regular_deliveries_due[:5]:  # Limit to 5 for display
        payment = CustomerPayment.objects.filter(delivery=delivery).order_by('-due_date').first()
        due_date = payment.due_date if payment and payment.due_date else delivery.date
        customer_dues.append({
            'customer': delivery.customer,
            'due_date': due_date,
            'amount': delivery.total_amount - delivery.received_amount,
            'invoice': delivery.invoice_number
        })
    
    # Get concrete delivery dues
    concrete_deliveries_due = ConcreteDelivery.objects.filter(
        received_amount__lt=F('total_amount'),
        customer__is_active=True
    ).order_by('delivery_date')
    
    for delivery in concrete_deliveries_due[:5]:  # Limit to 5 for display
        due_date = delivery.due_date if delivery.due_date else delivery.delivery_date
        customer_dues.append({
            'customer': delivery.customer,
            'due_date': due_date,
            'amount': delivery.total_amount - delivery.received_amount,
            'invoice': delivery.invoice_number
        })
    
    # Sort by due date and limit to 5
    customer_dues = sorted(customer_dues, key=lambda x: x['due_date'])[:5]
    
    # Get supplier dues for display
    # Reusing the supplier_dues list initialized at the top
    
    # Legacy Purchase model dues
    for purchase in supplier_payments_due[:5]:  # Limit to 5 for display
        supplier_dues.append({
            'supplier': purchase.supplier,
            'due_date': purchase.due_date if purchase.due_date else today_date,
            'balance': purchase.total_amount - purchase.paid_amount,
            'invoice': purchase.invoice_number
        })
    
    # PurchaseOrder model dues
    purchase_orders_due = PurchaseOrder.objects.filter(
        supplier__is_active=True
    ).order_by('purchase_date')
    
    for po in purchase_orders_due:
        balance = po.balance
        if balance <= 0:
            continue
            
        supplier_dues.append({
            'supplier': po.supplier,
            'due_date': po.due_date if po.due_date else today_date,
            'balance': balance,
            'invoice': f"PO-{po.id}"
        })
    
    # Sort by due date and limit to 5
    supplier_dues = sorted(supplier_dues, key=lambda x: x['due_date'])[:5]
    
    # Add to context
    context['customer_dues'] = customer_dues
    context['supplier_dues'] = supplier_dues
    
    # Salary dues
    salary_dues = []
    
    # Get salary records due
    salary_records_due = SalaryRecord.objects.filter(
        is_paid=False
    ).order_by('due_date')
    
    for salary in salary_records_due[:5]:
        salary_dues.append({
            'employee': salary.employee,
            'due_date': salary.due_date,
            'amount': salary.amount
        })
    
    context['salary_dues'] = salary_dues
    
    return render(request, 'dashboard.html', context)


def get_cashflow_data(start_date, end_date):
    """
    Get cash flow data for charting
    """
    # Initialize data structure
    data = {
        'labels': [],
        'inflow': [],
        'outflow': [],
        'net': []
    }
    
    # Create date range
    date_range = [(start_date + timedelta(days=i)) for i in range((end_date - start_date).days + 1)]
    
    # Initialize daily totals
    daily_inflow = defaultdict(float)
    daily_outflow = defaultdict(float)
    
    # Get customer payments (inflow)
    customer_payments = CustomerPayment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date
    )
    
    for payment in customer_payments:
        day_str = payment.payment_date.strftime('%Y-%m-%d')
        # Convert Decimal to float
        daily_inflow[day_str] += float(payment.amount_paid)
    
    # Get supplier payments (outflow)
    supplier_payments = SupplierPayment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date
    )
    
    for payment in supplier_payments:
        day_str = payment.payment_date.strftime('%Y-%m-%d')
        # Convert Decimal to float
        daily_outflow[day_str] += float(payment.amount_paid)
    
    # Get expenses (outflow)
    expenses = Expense.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    )
    
    for expense in expenses:
        day_str = expense.date.strftime('%Y-%m-%d')
        # Convert Decimal to float
        daily_outflow[day_str] += float(expense.amount)
    
    # Get salaries (outflow)
    salaries = Salary.objects.filter(
        paid_on__gte=start_date,
        paid_on__lte=end_date
    )
    
    for salary in salaries:
        day_str = salary.paid_on.strftime('%Y-%m-%d')
        # Convert Decimal to float
        daily_outflow[day_str] += float(salary.amount)
    
    # Convert to chart data format
    for day in date_range:
        day_str = day.strftime('%Y-%m-%d')
        display_date = day.strftime('%d %b')
        
        inflow = daily_inflow.get(day_str, 0)
        outflow = daily_outflow.get(day_str, 0)
        net = inflow - outflow
        
        data['labels'].append(display_date)
        data['inflow'].append(inflow)
        data['outflow'].append(outflow)
        data['net'].append(net)
    
    return data


def get_month_summary(start_date, end_date):
    """
    Get cash flow summary for the current month
    """
    # Initialize summary
    summary = {
        'total_inflow': 0,
        'total_outflow': 0,
        'net_cash_flow': 0,  # Changed from net_cashflow to net_cash_flow
    }
    
    # Get customer payments (inflow)
    customer_payments = CustomerPayment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date
    ).aggregate(total=Sum('amount_paid'))
    
    summary['total_inflow'] = customer_payments['total'] or 0
    
    # Get supplier payments (outflow)
    supplier_payments = SupplierPayment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date
    ).aggregate(total=Sum('amount_paid'))
    
    supplier_outflow = supplier_payments['total'] or 0
    
    # Get expenses (outflow)
    expenses = Expense.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))
    
    expense_outflow = expenses['total'] or 0
    
    # Get salaries (outflow)
    salaries = Salary.objects.filter(
        paid_on__gte=start_date,
        paid_on__lte=end_date
    ).aggregate(total=Sum('amount'))
    
    salary_outflow = salaries['total'] or 0
    
    # Calculate totals
    summary['total_outflow'] = supplier_outflow + expense_outflow + salary_outflow
    summary['net_cash_flow'] = summary['total_inflow'] - summary['total_outflow']  # Changed from net_cashflow to net_cash_flow
    
    return summary


def get_material_shortage_projections(today):
    """
    Calculate projected material shortages based on delivery patterns
    
    For each raw material:
    - Check average daily consumption (from ConcreteDelivery over past 15 days)
    - Project days remaining based on current stock
    - If projected shortage within 7 days → trigger low inventory alert
    """
    from apps.materials.models import Material
    from apps.customers.models import ConcreteDelivery, MixRatio
    from django.db.models import Sum, F, ExpressionWrapper, FloatField
    
    # Calculate date range for consumption analysis
    fifteen_days_ago = today - timedelta(days=15)
    
    # Get all active materials
    materials = Material.objects.filter(is_active=True)
    
    # Initialize results list
    projections = []
    
    for material in materials:
        # Get all concrete deliveries in the past 15 days
        recent_deliveries = ConcreteDelivery.objects.filter(
            delivery_date__gte=fifteen_days_ago,
            delivery_date__lte=today,
            inventory_deducted=True
        )
        
        if not recent_deliveries.exists():
            # No recent deliveries, can't calculate consumption
            projections.append({
                'material': material,
                'current_stock': material.current_stock,
                'unit': material.unit,
                'avg_daily_consumption': 0,
                'days_remaining': float('inf'),  # Infinite days if no consumption
                'status': 'OK'
            })
            continue
        
        # Initialize total consumption
        total_consumption = 0
        
        # Calculate total material consumption for each delivery
        for delivery in recent_deliveries:
            # Get mix ratios for this delivery's grade
            mix_ratios = MixRatio.objects.filter(
                grade=delivery.grade,
                material=material
            )
            
            if mix_ratios.exists():
                # Calculate material usage for this delivery
                for ratio in mix_ratios:
                    total_consumption += ratio.qty_per_m3 * delivery.quantity
        
        # Calculate average daily consumption
        avg_daily_consumption = total_consumption / 15 if total_consumption > 0 else 0
        
        # Calculate days remaining based on current stock
        if avg_daily_consumption > 0:
            days_remaining = material.current_stock / avg_daily_consumption
        else:
            days_remaining = float('inf')  # Infinite days if no consumption
        
        # Determine status based on days remaining
        if days_remaining < 3:
            status = 'Critical'
        elif days_remaining < 7:
            status = 'Low'
        else:
            status = 'OK'
        
        # Add to projections list
        projections.append({
            'material': material,
            'current_stock': material.current_stock,
            'unit': material.unit,
            'avg_daily_consumption': round(avg_daily_consumption, 2),
            'days_remaining': round(days_remaining, 1) if days_remaining != float('inf') else 'N/A',
            'status': status
        })
    
    # Sort by days remaining (ascending)
    projections.sort(key=lambda x: float('inf') if x['days_remaining'] == float('inf') else x['days_remaining'])
    
    return projections


@login_required
def due_report(request):
    """
    Comprehensive due report view showing customer, supplier and salary dues
    """
    report_type = request.GET.get('type', 'customer')
    due_before = request.GET.get('due_before')
    name_filter = request.GET.get('name', '')
    min_amount = request.GET.get('min_amount', '')
    
    # Convert min_amount to decimal or set to 0
    try:
        min_amount_value = float(min_amount) if min_amount else 0
    except ValueError:
        min_amount_value = 0
    
    # Get today's date for overdue highlighting
    today = timezone.now().date()
    
    # Parse due_before date if provided
    if due_before:
        try:
            due_before_date = datetime.strptime(due_before, '%Y-%m-%d').date()
        except ValueError:
            due_before_date = None
    else:
        due_before_date = None
    
    # Initialize context with filters
    context = {
        'report_type': report_type,
        'due_before': due_before,
        'name_filter': name_filter,
        'min_amount': min_amount,
        'today': today,
    }
    
    # Get customer dues
    if report_type == 'customer':
        customer_dues = []
        
        # Get deliveries with pending balance
        deliveries = Delivery.objects.filter(total_amount__gt=0).exclude(total_amount=0)
        
        # Apply name filter if provided
        if name_filter:
            deliveries = deliveries.filter(customer__name__icontains=name_filter)
        
        # Calculate pending amount and filter by minimum amount
        for delivery in deliveries:
            pending_amount = delivery.total_amount - delivery.received_amount
            
            # Skip if fully paid
            if pending_amount <= 0:
                continue
                
            # Skip if amount is less than minimum
            if pending_amount < min_amount_value:
                continue
            
            # Get the due date from credit terms if available
            credit_days = getattr(delivery, 'credit_days', 30)  # Default to 30 days
            due_date = delivery.date + timedelta(days=credit_days)
            
            # Apply due before filter if provided
            if due_before_date and due_date > due_before_date:
                continue
            
            customer_dues.append({
                'id': delivery.id,
                'customer': delivery.customer.name,
                'invoice_number': delivery.invoice_number,
                'date': delivery.date,
                'due_date': due_date,
                'total_amount': delivery.total_amount,
                'paid_amount': delivery.received_amount,
                'pending_amount': pending_amount,
                'is_overdue': due_date < today,
                'detail_url': reverse('customers:delivery_detail', args=[delivery.id]),
            })
        
        # Sort by due date (ascending)
        customer_dues.sort(key=lambda x: x['due_date'])
        
        context['dues'] = customer_dues
        context['total_pending'] = sum(due['pending_amount'] for due in customer_dues)
        context['total_overdue'] = sum(due['pending_amount'] for due in customer_dues if due['is_overdue'])
    
    # Get supplier dues
    elif report_type == 'supplier':
        supplier_dues = []
        
        # Get purchases with pending balance
        purchases = Purchase.objects.all()
        
        # Apply name filter if provided
        if name_filter:
            purchases = purchases.filter(supplier__name__icontains=name_filter)
        
        # Calculate pending amount and filter by minimum amount
        for purchase in purchases:
            pending_amount = purchase.total_amount - purchase.paid_amount
            
            # Skip if fully paid
            if pending_amount <= 0:
                continue
                
            # Skip if amount is less than minimum
            if pending_amount < min_amount_value:
                continue
            
            # Get the due date from credit terms if available
            credit_days = getattr(purchase, 'credit_days', 15)  # Default to 15 days
            due_date = purchase.date + timedelta(days=credit_days)
            
            # Apply due before filter if provided
            if due_before_date and due_date > due_before_date:
                continue
            
            supplier_dues.append({
                'id': purchase.id,
                'supplier': purchase.supplier.name,
                'invoice_number': purchase.invoice_number,
                'date': purchase.date,
                'due_date': due_date,
                'total_amount': purchase.total_amount,
                'paid_amount': purchase.paid_amount,
                'pending_amount': pending_amount,
                'is_overdue': due_date < today,
                'detail_url': reverse('suppliers:purchase_detail', args=[purchase.id]),
            })
        
        # Sort by due date (ascending)
        supplier_dues.sort(key=lambda x: x['due_date'])
        
        context['dues'] = supplier_dues
        context['total_pending'] = sum(due['pending_amount'] for due in supplier_dues)
        context['total_overdue'] = sum(due['pending_amount'] for due in supplier_dues if due['is_overdue'])
    
    # Get salary dues
    elif report_type == 'salary':
        salary_dues = []
        
        # Find unpaid salaries or upcoming ones
        salaries = Salary.objects.filter(is_paid=False)
        
        # Apply name filter if provided
        if name_filter:
            salaries = salaries.filter(employee__name__icontains=name_filter)
        
        # Process each salary record
        for salary in salaries:
            # Skip if amount is less than minimum
            if salary.amount < min_amount_value:
                continue
            
            # Default due date to last day of the month
            month_parts = salary.month.split('/')
            if len(month_parts) == 2:
                month, year = int(month_parts[0]), int(month_parts[1])
                _, last_day = monthrange(year, month)
                due_date = date(year, month, last_day)
            else:
                # Fallback if month format not recognized
                due_date = today
            
            # Apply due before filter if provided
            if due_before_date and due_date > due_before_date:
                continue
            
            salary_dues.append({
                'id': salary.id,
                'employee': salary.employee.name,
                'month': salary.month,
                'due_date': due_date,
                'amount': salary.amount,
                'is_overdue': due_date < today,
                'detail_url': reverse('expenses:salary_detail', args=[salary.id]),
            })
        
        # Sort by due date (ascending)
        salary_dues.sort(key=lambda x: x['due_date'])
        
        context['dues'] = salary_dues
        context['total_pending'] = sum(due['amount'] for due in salary_dues)
        context['total_overdue'] = sum(due['amount'] for due in salary_dues if due['is_overdue'])
    
    return render(request, 'core/due_report.html', context)


@login_required
def export_dues(request, format='excel'):
    """
    Export dues to Excel or PDF
    """
    report_type = request.GET.get('type', 'customer')
    due_before = request.GET.get('due_before')
    name_filter = request.GET.get('name', '')
    min_amount = request.GET.get('min_amount', '')
    
    # Reuse the same logic from due_report to get the data
    # But bypass the template and return the appropriate file
    
    # Get today's date for overdue highlighting
    today = timezone.now().date()
    
    # Parse due_before date if provided
    if due_before:
        try:
            due_before_date = datetime.strptime(due_before, '%Y-%m-%d').date()
        except ValueError:
            due_before_date = None
    else:
        due_before_date = None
    
    # Convert min_amount to decimal or set to 0
    try:
        min_amount_value = float(min_amount) if min_amount else 0
    except ValueError:
        min_amount_value = 0
    
    # Prepare data based on report type
    if report_type == 'customer':
        data = []
        headers = ['Customer', 'Invoice #', 'Invoice Date', 'Due Date', 'Total Amount', 'Paid Amount', 'Pending Amount', 'Status']
        filename = 'Customer_Dues'
        
        # Get deliveries with pending balance
        deliveries = Delivery.objects.filter(total_amount__gt=0).exclude(total_amount=0)
        
        # Apply name filter if provided
        if name_filter:
            deliveries = deliveries.filter(customer__name__icontains=name_filter)
        
        # Calculate pending amount and filter by minimum amount
        for delivery in deliveries:
            pending_amount = delivery.total_amount - delivery.received_amount
            
            # Skip if fully paid
            if pending_amount <= 0:
                continue
                
            # Skip if amount is less than minimum
            if pending_amount < min_amount_value:
                continue
            
            # Get the due date from credit terms if available
            credit_days = getattr(delivery, 'credit_days', 30)  # Default to 30 days
            due_date = delivery.date + timedelta(days=credit_days)
            
            # Apply due before filter if provided
            if due_before_date and due_date > due_before_date:
                continue
            
            status = 'Overdue' if due_date < today else 'Due'
            
            data.append([
                delivery.customer.name,
                delivery.invoice_number,
                delivery.date.strftime('%d-%m-%Y'),
                due_date.strftime('%d-%m-%Y'),
                delivery.total_amount,
                delivery.received_amount,
                pending_amount,
                status
            ])
    
    elif report_type == 'supplier':
        data = []
        headers = ['Supplier', 'Invoice #', 'Invoice Date', 'Due Date', 'Total Amount', 'Paid Amount', 'Pending Amount', 'Status']
        filename = 'Supplier_Dues'
        
        # Get purchases with pending balance
        purchases = Purchase.objects.all()
        
        # Apply name filter if provided
        if name_filter:
            purchases = purchases.filter(supplier__name__icontains=name_filter)
        
        # Calculate pending amount and filter by minimum amount
        for purchase in purchases:
            pending_amount = purchase.total_amount - purchase.paid_amount
            
            # Skip if fully paid
            if pending_amount <= 0:
                continue
                
            # Skip if amount is less than minimum
            if pending_amount < min_amount_value:
                continue
            
            # Get the due date from credit terms if available
            credit_days = getattr(purchase, 'credit_days', 15)  # Default to 15 days
            due_date = purchase.date + timedelta(days=credit_days)
            
            # Apply due before filter if provided
            if due_before_date and due_date > due_before_date:
                continue
            
            status = 'Overdue' if due_date < today else 'Due'
            
            data.append([
                purchase.supplier.name,
                purchase.invoice_number,
                purchase.date.strftime('%d-%m-%Y'),
                due_date.strftime('%d-%m-%Y'),
                purchase.total_amount,
                purchase.paid_amount,
                pending_amount,
                status
            ])
    
    elif report_type == 'salary':
        data = []
        headers = ['Employee', 'Month', 'Due Date', 'Amount', 'Status']
        filename = 'Salary_Dues'
        
        # Find unpaid salaries or upcoming ones
        salaries = Salary.objects.filter(is_paid=False)
        
        # Apply name filter if provided
        if name_filter:
            salaries = salaries.filter(employee__name__icontains=name_filter)
        
        # Process each salary record
        for salary in salaries:
            # Skip if amount is less than minimum
            if salary.amount < min_amount_value:
                continue
            
            # Default due date to last day of the month
            month_parts = salary.month.split('/')
            if len(month_parts) == 2:
                month, year = int(month_parts[0]), int(month_parts[1])
                _, last_day = monthrange(year, month)
                due_date = date(year, month, last_day)
            else:
                # Fallback if month format not recognized
                due_date = today
            
            # Apply due before filter if provided
            if due_before_date and due_date > due_before_date:
                continue
            
            status = 'Overdue' if due_date < today else 'Due'
            
            data.append([
                salary.employee.name,
                salary.month,
                due_date.strftime('%d-%m-%Y'),
                salary.amount,
                status
            ])
    
    # Export to Excel
    if format == 'excel':
        return export_to_excel(data, headers, filename)
    # Export to PDF
    else:
        return export_to_pdf(data, headers, filename, report_type)


def export_to_excel(data, headers, filename):
    """
    Export data to Excel format
    """
    import xlwt
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Dues Report')
    
    # Sheet header, first row
    row_num = 0
    
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    
    # Write headers
    for col_num, header in enumerate(headers):
        ws.write(row_num, col_num, header, font_style)
    
    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()
    
    # Define overdue style with red background
    overdue_style = xlwt.XFStyle()
    pattern = xlwt.Pattern()
    pattern.pattern = xlwt.Pattern.SOLID_PATTERN
    pattern.pattern_fore_colour = xlwt.Style.colour_map['light_yellow']
    overdue_style.pattern = pattern
    
    # Add data
    for row in data:
        row_num += 1
        is_overdue = row[-1] == 'Overdue'
        style = overdue_style if is_overdue else font_style
        
        for col_num, cell_value in enumerate(row):
            ws.write(row_num, col_num, cell_value, style)
    
    wb.save(response)
    return response


def export_to_pdf(data, headers, filename, report_type):
    """
    Export data to PDF format
    """
    from django.http import HttpResponse
    from django.template.loader import get_template
    import pdfkit
    
    # Prepare template context
    context = {
        'headers': headers,
        'data': data,
        'report_type': report_type,
        'today': timezone.now().date().strftime('%d-%m-%Y'),
        'title': f'{report_type.title()} Dues Report'
    }
    
    # Render HTML from template
    template = get_template('core/pdf/due_report_pdf.html')
    html = template.render(context)
    
    # Generate PDF using pdfkit
    try:
        pdf = pdfkit.from_string(html, False)
        
        # Create HTTP response with PDF content
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        return response
    except Exception as e:
        # If pdfkit fails, fallback to Excel
        return export_to_excel(data, headers, filename) 


@login_required
def cash_bank_book(request):
    """
    Cash Book and Bank Book view for tracking daily cash and bank transactions
    """
    # Get filter parameters
    book_type = request.GET.get('type', 'cash')  # 'cash' or 'bank'
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    mode_filter = request.GET.get('mode')
    
    # Default to current month if no dates provided
    today = timezone.now().date()
    if not start_date:
        start_date = date(today.year, today.month, 1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = today.strftime('%Y-%m-%d')
    
    # Convert string dates to datetime objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Determine payment modes to include based on book type and filter
    payment_modes = []
    if book_type == 'cash':
        payment_modes = ['CASH']
        if mode_filter:
            payment_modes = [mode_filter] if mode_filter in payment_modes else payment_modes
        title = "Cash Book"
    else:  # bank
        payment_modes = ['CHEQUE', 'BANK']
        if mode_filter:
            payment_modes = [mode_filter] if mode_filter in payment_modes else payment_modes
        title = "Bank Book"
    
    # Get previous day's closing balance as opening balance for start date
    previous_day = start_date_obj - timedelta(days=1)
    opening_balance = get_closing_balance(previous_day, payment_modes)

    # Get all relevant transactions within date range
    all_transactions = get_transactions(start_date_obj, end_date_obj, payment_modes)
    
    # Group transactions by date
    day_wise_entries = group_by_date(all_transactions, opening_balance)
    
    # Calculate running balance
    running_balance = opening_balance
    for date_str, entries in day_wise_entries.items():
        entries['opening_balance'] = running_balance
        entries['closing_balance'] = running_balance + entries['total_receipts'] - entries['total_payments']
        running_balance = entries['closing_balance']
    
    # Calculate overall totals
    total_receipts = sum(entry['total_receipts'] for entry in day_wise_entries.values())
    total_payments = sum(entry['total_payments'] for entry in day_wise_entries.values())
    
    context = {
        'title': title,
        'book_type': book_type,
        'start_date': start_date,
        'end_date': end_date,
        'mode_filter': mode_filter,
        'day_wise_entries': day_wise_entries,
        'payment_modes': [('', 'All')] + [(mode, mode.title()) for mode in payment_modes],
        'opening_balance': opening_balance,
        'total_receipts': total_receipts,
        'total_payments': total_payments,
        'closing_balance': opening_balance + total_receipts - total_payments,
    }
    
    return render(request, 'core/cash_bank_book.html', context)


def get_transactions(start_date, end_date, payment_modes):
    """
    Get all transactions from different sources within date range for specified payment modes
    """
    transactions = []
    
    # Get customer payments (receipts)
    customer_payments = CustomerPayment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date,
        payment_mode__in=payment_modes
    ).select_related('customer', 'delivery')
    
    for payment in customer_payments:
        description = f"Payment from {payment.customer.name}"
        if payment.delivery:
            description += f" for Invoice #{payment.delivery.invoice_number}"
        if payment.reference_number:
            description += f" (Ref: {payment.reference_number})"
        
        transactions.append({
            'date': payment.payment_date,
            'description': description,
            'reference': payment.reference_number or f"Receipt #{payment.id}",
            'receipt_amount': payment.amount_paid,
            'payment_amount': 0,
            'payment_mode': payment.get_payment_mode_display(),
            'entity_type': 'customer',
            'entity_id': payment.customer.id,
            'entity_name': payment.customer.name,
            'transaction_type': 'receipt',
            'detail_url': reverse('customers:payment_detail', args=[payment.id]),
        })
    
    # Get supplier payments (payments)
    supplier_payments = SupplierPayment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date,
        payment_mode__in=payment_modes
    ).select_related('supplier', 'purchase')
    
    for payment in supplier_payments:
        description = f"Payment to {payment.supplier.name}"
        if payment.purchase:
            description += f" for Invoice #{payment.purchase.invoice_number}"
        if payment.reference_number:
            description += f" (Ref: {payment.reference_number})"
        
        transactions.append({
            'date': payment.payment_date,
            'description': description,
            'reference': payment.reference_number or f"Payment #{payment.id}",
            'receipt_amount': 0,
            'payment_amount': payment.amount_paid,
            'payment_mode': payment.get_payment_mode_display(),
            'entity_type': 'supplier',
            'entity_id': payment.supplier.id,
            'entity_name': payment.supplier.name,
            'transaction_type': 'payment',
            'detail_url': reverse('suppliers:payment_detail', args=[payment.id]),
        })
    
    # Get expenses (payments)
    payment_method_map = {
        'CASH': 'CASH',
        'CHEQUE': 'CHEQUE',
        'BANK': 'ONLINE',  # Map BANK to ONLINE for expense payment method
    }
    
    expense_payment_methods = [payment_method_map[mode] for mode in payment_modes if mode in payment_method_map]
    
    expenses = Expense.objects.filter(
        date__gte=start_date,
        date__lte=end_date,
        payment_method__in=expense_payment_methods
    ).select_related('category')
    
    for expense in expenses:
        description = f"Expense: {expense.description}"
        if expense.category:
            description = f"{expense.category.name}: {expense.description}"
        
        transactions.append({
            'date': expense.date,
            'description': description,
            'reference': f"Expense #{expense.id}",
            'receipt_amount': 0,
            'payment_amount': expense.amount,
            'payment_mode': expense.get_payment_method_display(),
            'entity_type': 'expense',
            'entity_id': expense.id,
            'entity_name': expense.category.name if expense.category else "General Expense",
            'transaction_type': 'payment',
            'detail_url': reverse('expenses:expense_detail', args=[expense.id]),
        })
    
    # Get salaries (payments) - Only for CASH and BANK modes typically
    salaries = Salary.objects.filter(
        paid_on__gte=start_date,
        paid_on__lte=end_date,
        is_paid=True
    ).select_related('employee')
    
    # Filter salaries based on payment mode (assuming default is CASH unless specified)
    if 'CASH' not in payment_modes and 'BANK' in payment_modes:
        # If only bank is selected, only include bank transfers
        salaries = salaries.filter(payment_method='BANK')
    elif 'CASH' in payment_modes and 'BANK' not in payment_modes:
        # If only cash is selected, only include cash payments
        salaries = salaries.filter(Q(payment_method='CASH') | Q(payment_method=''))
    
    for salary in salaries:
        payment_mode = getattr(salary, 'payment_method', 'CASH')
        if not payment_mode:
            payment_mode = 'CASH'  # Default to CASH if not specified
        
        description = f"Salary paid to {salary.employee.name} for {salary.month}"
        
        transactions.append({
            'date': salary.paid_on,
            'description': description,
            'reference': f"Salary #{salary.id}",
            'receipt_amount': 0,
            'payment_amount': salary.amount,
            'payment_mode': payment_mode,
            'entity_type': 'salary',
            'entity_id': salary.id,
            'entity_name': salary.employee.name,
            'transaction_type': 'payment',
            'detail_url': reverse('expenses:salary_detail', args=[salary.id]),
        })
    
    # Sort transactions by date
    transactions.sort(key=lambda x: x['date'])
    
    return transactions


def group_by_date(transactions, opening_balance):
    """
    Group transactions by date and calculate daily totals
    """
    day_wise = {}
    
    for transaction in transactions:
        date_str = transaction['date'].strftime('%Y-%m-%d')
        
        if date_str not in day_wise:
            day_wise[date_str] = {
                'date': transaction['date'],
                'transactions': [],
                'total_receipts': 0,
                'total_payments': 0,
                'net_flow': 0,
            }
        
        day_wise[date_str]['transactions'].append(transaction)
        day_wise[date_str]['total_receipts'] += transaction['receipt_amount']
        day_wise[date_str]['total_payments'] += transaction['payment_amount']
    
    # Calculate net flow for each day
    for date_str, data in day_wise.items():
        data['net_flow'] = data['total_receipts'] - data['total_payments']
    
    return day_wise


def get_closing_balance(end_date, payment_modes):
    """
    Calculate closing balance as of a specific date for specified payment modes
    """
    # Start with a default opening balance of 0
    balance = 0
    
    # Query all historical transactions up to the specified date
    transactions = get_transactions(date(2000, 1, 1), end_date, payment_modes)
    
    # Calculate net balance
    for transaction in transactions:
        balance += transaction['receipt_amount'] - transaction['payment_amount']
    
    return balance


@login_required
def export_cash_bank_book(request, format='excel'):
    """
    Export Cash/Bank Book to Excel or PDF
    """
    # Get filter parameters
    book_type = request.GET.get('type', 'cash')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    mode_filter = request.GET.get('mode')
    
    # Default to current month if no dates provided
    today = timezone.now().date()
    if not start_date:
        start_date = date(today.year, today.month, 1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = today.strftime('%Y-%m-%d')
    
    # Convert string dates to datetime objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Determine payment modes to include based on book type and filter
    payment_modes = []
    if book_type == 'cash':
        payment_modes = ['CASH']
        if mode_filter:
            payment_modes = [mode_filter] if mode_filter in payment_modes else payment_modes
        title = "Cash Book"
    else:  # bank
        payment_modes = ['CHEQUE', 'BANK']
        if mode_filter:
            payment_modes = [mode_filter] if mode_filter in payment_modes else payment_modes
        title = "Bank Book"
    
    # Get previous day's closing balance as opening balance for start date
    previous_day = start_date_obj - timedelta(days=1)
    opening_balance = get_closing_balance(previous_day, payment_modes)
    
    # Get all relevant transactions within date range
    all_transactions = get_transactions(start_date_obj, end_date_obj, payment_modes)
    
    # Group transactions by date
    day_wise_entries = group_by_date(all_transactions, opening_balance)
    
    # Calculate running balance
    running_balance = opening_balance
    for date_str, entries in day_wise_entries.items():
        entries['opening_balance'] = running_balance
        entries['closing_balance'] = running_balance + entries['total_receipts'] - entries['total_payments']
        running_balance = entries['closing_balance']
    
    # Prepare data for export
    if format == 'excel':
        return export_book_to_excel(day_wise_entries, title, opening_balance, start_date, end_date)
    else:
        return export_book_to_pdf(day_wise_entries, title, opening_balance, start_date, end_date)


def export_book_to_excel(day_wise_entries, title, opening_balance, start_date, end_date):
    """
    Export Cash/Bank Book to Excel
    """
    import xlwt
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{title.replace(" ", "_")}_{start_date}_to_{end_date}.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(title)
    
    # Styles
    title_style = xlwt.XFStyle()
    title_style.font.bold = True
    title_style.font.height = 280
    
    header_style = xlwt.XFStyle()
    header_style.font.bold = True
    
    date_style = xlwt.XFStyle()
    date_style.num_format_str = 'DD-MM-YYYY'
    
    currency_style = xlwt.XFStyle()
    currency_style.num_format_str = '#,##0.00'
    
    bold_currency_style = xlwt.XFStyle()
    bold_currency_style.num_format_str = '#,##0.00'
    bold_currency_style.font.bold = True
    
    # Title and date range
    ws.write(0, 0, title, title_style)
    ws.write(1, 0, f"Period: {start_date} to {end_date}")
    
    # Headers
    row_num = 3
    columns = ['Date', 'Description', 'Reference', 'Receipts', 'Payments', 'Balance']
    
    for col_num, column_title in enumerate(columns):
        ws.write(row_num, col_num, column_title, header_style)
    
    # Opening balance row
    row_num += 1
    bank_name = context.get('selected_bank_name', 'All Banks')
    worksheet.write(row_num, 0, context['start_date'], date_style)
    worksheet.write(row_num, 1, 'Opening Balance')
    worksheet.write(row_num, 2, '')
    worksheet.write(row_num, 3, bank_name)
    worksheet.write(row_num, 4, '')
    worksheet.write(row_num, 5, '')
    worksheet.write(row_num, 6, context['opening_balance'], bold_amount_style)
    
    # Data rows
    running_balance = context['opening_balance']
    row_num += 1
    
    for date_str, day_data in sorted(day_wise_entries.items()):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Add day header with totals
        row_num += 1
        ws.write(row_num, 0, date_obj, date_style)
        ws.write(row_num, 1, f"--- {date_obj.strftime('%d-%b-%Y')} ---", header_style)
        ws.write(row_num, 2, 'Daily Total')
        ws.write(row_num, 3, day_data['total_receipts'], currency_style)
        ws.write(row_num, 4, day_data['total_payments'], currency_style)
        
        running_balance += day_data['net_flow']
        ws.write(row_num, 5, running_balance, bold_currency_style)
        
        # Add individual transactions
        for transaction in day_data['transactions']:
            row_num += 1
            ws.write(row_num, 0, transaction['date'], date_style)
            ws.write(row_num, 1, transaction['description'])
            ws.write(row_num, 2, transaction['reference'])
            ws.write(row_num, 3, transaction['bank_account'])
            ws.write(row_num, 4, transaction['receipt_amount'], currency_style)
            ws.write(row_num, 5, transaction['payment_amount'], currency_style)
            ws.write(row_num, 6, '')
            row_num += 1
    
    # Write grand total row
    row_num += 1
    worksheet.write(row_num, 0, '')
    worksheet.write(row_num, 1, 'Grand Total')
    worksheet.write(row_num, 2, '')
    worksheet.write(row_num, 3, '')
    worksheet.write(row_num, 4, context['total_receipts'], bold_amount_style)
    worksheet.write(row_num, 5, context['total_payments'], bold_amount_style)
    worksheet.write(row_num, 6, context['closing_balance'], bold_amount_style)
    
    # Set column widths
    ws.col(0).width = 3500  # Date
    ws.col(1).width = 10000  # Description
    ws.col(2).width = 5000  # Reference
    ws.col(3).width = 4000  # Receipts
    ws.col(4).width = 4000  # Payments
    ws.col(5).width = 4000  # Balance
    
    wb.save(response)
    return response


def export_book_to_pdf(day_wise_entries, title, opening_balance, start_date, end_date):
    """
    Export Cash/Bank Book to PDF
    """
    from django.http import HttpResponse
    from django.template.loader import get_template
    import pdfkit
    
    # Prepare template context
    context = {
        'title': title,
        'start_date': start_date,
        'end_date': end_date,
        'opening_balance': opening_balance,
        'day_wise_entries': sorted(day_wise_entries.items()),
        'current_date': timezone.now(),  # Using full datetime object instead of formatted date string
    }
    
    # Render HTML from template
    template = get_template('core/pdf/cash_bank_book_pdf.html')
    html = template.render(context)
    
    # Generate PDF using pdfkit
    try:
        pdf = pdfkit.from_string(html, False)
        
        # Create HTTP response with PDF content
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{title.replace(" ", "_")}_{start_date}_to_{end_date}.pdf"'
        return response
    except Exception as e:
        # Fallback to Excel if PDF generation fails
        return export_book_to_excel(day_wise_entries, title, opening_balance, start_date, end_date) 


class CashBookView(LoginRequiredMixin, TemplateView):
    template_name = 'core/cash_book.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range from request parameters or use default (current month)
        today = timezone.now().date()
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            # Default to first day of current month
            start_date = today.replace(day=1)
            
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            # Default to today
            end_date = today
            
        # Query all cash transactions
        customer_payments = CustomerPayment.objects.filter(
            payment_mode='cash',
            payment_date__range=[start_date, end_date]
        )
        
        supplier_payments = SupplierPayment.objects.filter(
            payment_mode='cash',
            payment_date__range=[start_date, end_date]
        )
        
        expenses = Expense.objects.filter(
            payment_mode='cash',
            date__range=[start_date, end_date]
        )
        
        salaries = Salary.objects.filter(
            payment_mode='cash',
            paid_on__range=[start_date, end_date]
        )
        
        # Calculate opening balance (all cash transactions before start_date)
        receipts_before = CustomerPayment.objects.filter(
            payment_mode='cash',
            payment_date__lt=start_date
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        
        payments_before = (
            SupplierPayment.objects.filter(payment_mode='cash', payment_date__lt=start_date).aggregate(total=Sum('amount_paid'))['total'] or 0 +
            Expense.objects.filter(payment_mode='cash', date__lt=start_date).aggregate(total=Sum('amount'))['total'] or 0 +
            Salary.objects.filter(payment_mode='cash', paid_on__lt=start_date).aggregate(total=Sum('amount'))['total'] or 0
        )
        
        opening_balance = receipts_before - payments_before
        
        # Calculate totals for the period
        total_receipts = customer_payments.aggregate(total=Sum('amount_paid'))['total'] or 0
        total_payments = (
            supplier_payments.aggregate(total=Sum('amount_paid'))['total'] or 0 +
            expenses.aggregate(total=Sum('amount'))['total'] or 0 +
            salaries.aggregate(total=Sum('amount'))['total'] or 0
        )
        
        closing_balance = opening_balance + total_receipts - total_payments
        
        # Organize transactions by date
        day_wise_entries = {}
        running_balance = opening_balance
        
        # Create a date range from start_date to end_date
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            day_wise_entries[date_str] = {
                'date': current_date,
                'transactions': [],
                'total_receipts': 0,
                'total_payments': 0,
            }
            
            # Get transactions for this day
            day_customer_payments = customer_payments.filter(payment_date=current_date)
            day_supplier_payments = supplier_payments.filter(payment_date=current_date)
            day_expenses = expenses.filter(date=current_date)
            day_salaries = salaries.filter(paid_on=current_date)
            
            # Add customer payments (receipts)
            for payment in day_customer_payments:
                day_wise_entries[date_str]['transactions'].append({
                    'date': payment.payment_date,
                    'description': f'Customer Payment - {payment.customer.name}',
                    'reference': f'Delivery #{payment.delivery.invoice_number if payment.delivery else "N/A"}',
                    'receipt_amount': payment.amount_paid,
                    'payment_amount': 0
                })
                day_wise_entries[date_str]['total_receipts'] += payment.amount_paid
                running_balance += payment.amount_paid
            
            # Add supplier payments
            for payment in day_supplier_payments:
                day_wise_entries[date_str]['transactions'].append({
                    'date': payment.payment_date,
                    'description': f'Supplier Payment - {payment.supplier.name}',
                    'reference': f'Purchase #{payment.purchase.invoice_number if payment.purchase else "N/A"}',
                    'receipt_amount': 0,
                    'payment_amount': payment.amount_paid
                })
                day_wise_entries[date_str]['total_payments'] += payment.amount_paid
                running_balance -= payment.amount_paid
            
            # Add expenses
            for expense in day_expenses:
                day_wise_entries[date_str]['transactions'].append({
                    'date': expense.date,
                    'description': f'Expense - {expense.category.name}',
                    'reference': f'{expense.description[:30]}...' if len(expense.description) > 30 else expense.description,
                    'receipt_amount': 0,
                    'payment_amount': expense.amount
                })
                day_wise_entries[date_str]['total_payments'] += expense.amount
                running_balance -= expense.amount
            
            # Add salaries
            for salary in day_salaries:
                day_wise_entries[date_str]['transactions'].append({
                    'date': salary.paid_on,
                    'description': f'Salary - {salary.employee.name}',
                    'reference': f'{salary.month}',
                    'receipt_amount': 0,
                    'payment_amount': salary.amount
                })
                day_wise_entries[date_str]['total_payments'] += salary.amount
                running_balance -= salary.amount
            
            # Update closing balance for the day
            day_wise_entries[date_str]['closing_balance'] = running_balance
            
            # Remove days with no transactions
            if not day_wise_entries[date_str]['transactions']:
                del day_wise_entries[date_str]
            
            current_date += timedelta(days=1)
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'opening_balance': opening_balance,
            'total_receipts': total_receipts,
            'total_payments': total_payments,
            'closing_balance': closing_balance,
            'day_wise_entries': day_wise_entries,
        })
        
        return context


class BankBookView(LoginRequiredMixin, TemplateView):
    template_name = 'core/bank_book.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range from request parameters or use default (current month)
        today = timezone.now().date()
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        bank_account_id = self.request.GET.get('bank_account')
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            # Default to first day of current month
            start_date = today.replace(day=1)
            
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            # Default to today
            end_date = today
        
        # Get all bank accounts
        bank_accounts = BankAccount.objects.filter(is_active=True)
        selected_bank_name = None
        
        # Bank account filter
        bank_filter = Q(payment_mode__in=['cheque', 'bank_transfer', 'upi', 'online'])
        if bank_account_id:
            bank_filter &= Q(bank_account_id=bank_account_id)
            selected_bank = BankAccount.objects.filter(id=bank_account_id).first()
            if selected_bank:
                selected_bank_name = selected_bank.name
            
        # Query all bank transactions
        customer_payments = CustomerPayment.objects.filter(
            bank_filter,
            payment_date__range=[start_date, end_date]
        )
        
        supplier_payments = SupplierPayment.objects.filter(
            bank_filter,
            payment_date__range=[start_date, end_date]
        )
        
        expenses = Expense.objects.filter(
            bank_filter,
            date__range=[start_date, end_date]
        )
        
        salaries = Salary.objects.filter(
            bank_filter,
            paid_on__range=[start_date, end_date]
        )
        
        # Calculate opening balance (all bank transactions before start_date)
        receipts_before = CustomerPayment.objects.filter(
            bank_filter,
            payment_date__lt=start_date
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        
        payments_before = (
            SupplierPayment.objects.filter(bank_filter, payment_date__lt=start_date).aggregate(total=Sum('amount_paid'))['total'] or 0 +
            Expense.objects.filter(bank_filter, date__lt=start_date).aggregate(total=Sum('amount'))['total'] or 0 +
            Salary.objects.filter(bank_filter, paid_on__lt=start_date).aggregate(total=Sum('amount'))['total'] or 0
        )
        
        opening_balance = receipts_before - payments_before
        
        # Calculate totals for the period
        total_receipts = customer_payments.aggregate(total=Sum('amount_paid'))['total'] or 0
        total_payments = (
            supplier_payments.aggregate(total=Sum('amount_paid'))['total'] or 0 +
            expenses.aggregate(total=Sum('amount'))['total'] or 0 +
            salaries.aggregate(total=Sum('amount'))['total'] or 0
        )
        
        closing_balance = opening_balance + total_receipts - total_payments
        
        # Organize transactions by date
        day_wise_entries = {}
        running_balance = opening_balance
        
        # Create a date range from start_date to end_date
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            day_wise_entries[date_str] = {
                'date': current_date,
                'transactions': [],
                'total_receipts': 0,
                'total_payments': 0,
            }
            
            # Get transactions for this day
            day_customer_payments = customer_payments.filter(payment_date=current_date)
            day_supplier_payments = supplier_payments.filter(payment_date=current_date)
            day_expenses = expenses.filter(date=current_date)
            day_salaries = salaries.filter(paid_on=current_date)
            
            # Add customer payments (receipts)
            for payment in day_customer_payments:
                bank_name = payment.bank_account.name if payment.bank_account else payment.payment_mode
                day_wise_entries[date_str]['transactions'].append({
                    'date': payment.payment_date,
                    'description': f'Customer Payment - {payment.customer.name}',
                    'reference': f'Delivery #{payment.delivery.invoice_number if payment.delivery else "N/A"}',
                    'bank_account': bank_name,
                    'receipt_amount': payment.amount_paid,
                    'payment_amount': 0
                })
                day_wise_entries[date_str]['total_receipts'] += payment.amount_paid
                running_balance += payment.amount_paid
            
            # Add supplier payments
            for payment in day_supplier_payments:
                bank_name = payment.bank_account.name if payment.bank_account else payment.payment_mode
                day_wise_entries[date_str]['transactions'].append({
                    'date': payment.payment_date,
                    'description': f'Supplier Payment - {payment.supplier.name}',
                    'reference': f'Purchase #{payment.purchase.invoice_number if payment.purchase else "N/A"}',
                    'bank_account': bank_name,
                    'receipt_amount': 0,
                    'payment_amount': payment.amount_paid
                })
                day_wise_entries[date_str]['total_payments'] += payment.amount_paid
                running_balance -= payment.amount_paid
            
            # Add expenses
            for expense in day_expenses:
                bank_name = expense.bank_account.name if expense.bank_account else expense.payment_mode
                day_wise_entries[date_str]['transactions'].append({
                    'date': expense.date,
                    'description': f'Expense - {expense.category.name}',
                    'reference': f'{expense.description[:30]}...' if len(expense.description) > 30 else expense.description,
                    'bank_account': bank_name,
                    'receipt_amount': 0,
                    'payment_amount': expense.amount
                })
                day_wise_entries[date_str]['total_payments'] += expense.amount
                running_balance -= expense.amount
            
            # Add salaries
            for salary in day_salaries:
                bank_name = salary.bank_account.name if salary.bank_account else salary.payment_mode
                day_wise_entries[date_str]['transactions'].append({
                    'date': salary.paid_on,
                    'description': f'Salary - {salary.employee.name}',
                    'reference': f'{salary.month}',
                    'bank_account': bank_name,
                    'receipt_amount': 0,
                    'payment_amount': salary.amount
                })
                day_wise_entries[date_str]['total_payments'] += salary.amount
                running_balance -= salary.amount
            
            # Update closing balance for the day
            day_wise_entries[date_str]['closing_balance'] = running_balance
            
            # Remove days with no transactions
            if not day_wise_entries[date_str]['transactions']:
                del day_wise_entries[date_str]
            
            current_date += timedelta(days=1)
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'opening_balance': opening_balance,
            'total_receipts': total_receipts,
            'total_payments': total_payments,
            'closing_balance': closing_balance,
            'day_wise_entries': day_wise_entries,
            'bank_accounts': bank_accounts,
            'selected_bank': bank_account_id,
            'selected_bank_name': selected_bank_name,
        })
        
        return context


class ExportCashBookView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        format_type = kwargs.get('format', 'excel')
        cash_book_view = CashBookView()
        cash_book_view.request = request
        context = cash_book_view.get_context_data()
        
        if format_type == 'excel':
            return self.export_excel(context)
        elif format_type == 'pdf':
            return self.export_pdf(context)
        else:
            return HttpResponse("Unsupported format", status=400)
    
    def export_excel(self, context):
        # Create a workbook and add a worksheet
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Cash Book')
        
        # Styles
        header_style = xlwt.easyxf('font: bold on; align: horiz center; pattern: pattern solid, fore_colour gray25;')
        date_style = xlwt.easyxf('font: bold off; align: horiz left;', num_format_str='DD-MMM-YYYY')
        amount_style = xlwt.easyxf('font: bold off; align: horiz right;', num_format_str='#,##0.00')
        bold_amount_style = xlwt.easyxf('font: bold on; align: horiz right;', num_format_str='#,##0.00')
        
        # Write header row
        headers = ['Date', 'Description', 'Reference', 'Receipts (₹)', 'Payments (₹)', 'Balance (₹)']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_style)
            worksheet.col(col_num).width = 256 * 20  # 20 characters wide
        
        # Write opening balance row
        row_num = 1
        bank_name = context.get('selected_bank_name', 'All Banks')
        worksheet.write(row_num, 0, context['start_date'], date_style)
        worksheet.write(row_num, 1, 'Opening Balance')
        worksheet.write(row_num, 2, '')
        worksheet.write(row_num, 3, bank_name)
        worksheet.write(row_num, 4, '')
        worksheet.write(row_num, 5, '')
        worksheet.write(row_num, 6, context['opening_balance'], bold_amount_style)
        
        # Write transactions
        running_balance = context['opening_balance']
        row_num += 1
        
        for date_str, day_data in context['day_wise_entries'].items():
            # Day header
            worksheet.write(row_num, 0, day_data['date'], date_style)
            worksheet.write(row_num, 1, f"--- {day_data['date'].strftime('%d %B %Y')} ---")
            worksheet.write(row_num, 2, 'Daily Total')
            worksheet.write(row_num, 3, '')
            worksheet.write(row_num, 4, day_data['total_receipts'], currency_style)
            worksheet.write(row_num, 5, day_data['total_payments'], currency_style)
            
            running_balance += day_data['net_flow']
            ws.write(row_num, 6, running_balance, bold_amount_style)
            
            # Transactions for the day
            for txn in day_data['transactions']:
                worksheet.write(row_num, 0, txn['date'], date_style)
                worksheet.write(row_num, 1, txn['description'])
                worksheet.write(row_num, 2, txn['reference'])
                worksheet.write(row_num, 3, txn['bank_account'])
                worksheet.write(row_num, 4, txn['receipt_amount'], currency_style)
                worksheet.write(row_num, 5, txn['payment_amount'], currency_style)
                worksheet.write(row_num, 6, '')
                row_num += 1
        
        # Write grand total row
        row_num += 1
        worksheet.write(row_num, 1, 'Grand Total', header_style)
        worksheet.write(row_num, 3, '')
        worksheet.write(row_num, 4, context['total_receipts'], bold_amount_style)
        worksheet.write(row_num, 5, context['total_payments'], bold_amount_style)
        worksheet.write(row_num, 6, context['closing_balance'], bold_amount_style)
        
        # Set column widths
        ws.col(0).width = 3500  # Date
        ws.col(1).width = 10000  # Description
        ws.col(2).width = 5000  # Reference
        ws.col(3).width = 4000  # Receipts
        ws.col(4).width = 4000  # Payments
        ws.col(5).width = 4000  # Balance
        
        wb.save(response)
        return response
    
    def export_pdf(self, context):
        # Render the template to HTML
        html_string = render(self.request, 'core/cash_book_pdf.html', context).content.decode('utf-8')
        
        # Convert HTML to PDF
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None
        }
        
        try:
            pdf = pdfkit.from_string(html_string, False, options=options)
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Cash_Book_{context["start_date"]}_{context["end_date"]}.pdf"'
            return response
        except Exception as e:
            # Fallback to Excel if PDF generation fails
            return self.export_excel(context)


class ExportBankBookView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        format_type = kwargs.get('format', 'excel')
        bank_book_view = BankBookView()
        bank_book_view.request = request
        context = bank_book_view.get_context_data()
        
        if format_type == 'excel':
            return self.export_excel(context)
        elif format_type == 'pdf':
            return self.export_pdf(context)
        else:
            return HttpResponse("Unsupported format", status=400)
    
    def export_excel(self, context):
        # Create a workbook and add a worksheet
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Bank Book')
        
        # Styles
        header_style = xlwt.easyxf('font: bold on; align: horiz center; pattern: pattern solid, fore_colour gray25;')
        date_style = xlwt.easyxf('font: bold off; align: horiz left;', num_format_str='DD-MMM-YYYY')
        amount_style = xlwt.easyxf('font: bold off; align: horiz right;', num_format_str='#,##0.00')
        bold_amount_style = xlwt.easyxf('font: bold on; align: horiz right;', num_format_str='#,##0.00')
        
        # Write header row
        headers = ['Date', 'Description', 'Reference', 'Bank Account', 'Deposits (₹)', 'Withdrawals (₹)', 'Balance (₹)']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_style)
            worksheet.col(col_num).width = 256 * 20  # 20 characters wide
        
        # Write opening balance row
        row_num = 1
        bank_name = context.get('selected_bank_name', 'All Banks')
        worksheet.write(row_num, 0, context['start_date'], date_style)
        worksheet.write(row_num, 1, 'Opening Balance')
        worksheet.write(row_num, 2, '')
        worksheet.write(row_num, 3, bank_name)
        worksheet.write(row_num, 4, '')
        worksheet.write(row_num, 5, '')
        worksheet.write(row_num, 6, context['opening_balance'], bold_amount_style)
        
        # Write transactions
        running_balance = context['opening_balance']
        row_num += 1
        
        for date_str, day_data in context['day_wise_entries'].items():
            # Day header
            worksheet.write(row_num, 0, day_data['date'], date_style)
            worksheet.write(row_num, 1, f"--- {day_data['date'].strftime('%d %B %Y')} ---")
            worksheet.write(row_num, 2, 'Daily Total')
            worksheet.write(row_num, 3, '')
            worksheet.write(row_num, 4, day_data['total_receipts'], bold_amount_style)
            worksheet.write(row_num, 5, day_data['total_payments'], bold_amount_style)
            
            running_balance += day_data['net_flow']
            ws.write(row_num, 6, running_balance, bold_amount_style)
            
            # Transactions for the day
            for txn in day_data['transactions']:
                worksheet.write(row_num, 0, txn['date'], date_style)
                worksheet.write(row_num, 1, txn['description'])
                worksheet.write(row_num, 2, txn['reference'])
                worksheet.write(row_num, 3, txn['bank_account'])
                worksheet.write(row_num, 4, txn['receipt_amount'], currency_style)
                worksheet.write(row_num, 5, txn['payment_amount'], currency_style)
                worksheet.write(row_num, 6, '')
                row_num += 1
        
        # Write grand total row
        row_num += 1
        worksheet.write(row_num, 1, 'Grand Total', header_style)
        worksheet.write(row_num, 4, context['total_receipts'], bold_amount_style)
        worksheet.write(row_num, 5, context['total_payments'], bold_amount_style)
        worksheet.write(row_num, 6, context['closing_balance'], bold_amount_style)
        
        # Set column widths
        ws.col(0).width = 3500  # Date
        ws.col(1).width = 10000  # Description
        ws.col(2).width = 5000  # Reference
        ws.col(3).width = 4000  # Receipts
        ws.col(4).width = 4000  # Payments
        ws.col(5).width = 4000  # Balance
        
        wb.save(response)
        return response
    
    def export_pdf(self, context):
        # Render the template to HTML
        html_string = render(self.request, 'core/bank_book_pdf.html', context).content.decode('utf-8')
        
        # Convert HTML to PDF
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None
        }
        
        try:
            pdf = pdfkit.from_string(html_string, False, options=options)
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Bank_Book_{context["start_date"]}_{context["end_date"]}.pdf"'
            return response
        except Exception as e:
            # Fallback to Excel if PDF generation fails
            return self.export_excel(context) 


def permission_denied_view(request, message=None):
    """
    View to display a permission denied page with custom message.
    """
    context = {
        'message': message
    }
    return render(request, 'core/permission_denied.html', context)


def is_admin(user):
    """Check if user is an admin."""
    return user.is_superuser or user.groups.filter(name='Admin').exists()

@user_passes_test(is_admin)
def run_setup_roles(request):
    """Run the setup_roles management command to reset permissions."""
    try:
        call_command('setup_roles')
        return JsonResponse({'success': True, 'message': 'Role permissions reset successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def bill_report(request):
    """
    Bill report view for tracking supplier bills/purchases
    """
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    supplier_id = request.GET.get('supplier')
    status = request.GET.get('status')
    
    # Default to current month if no dates provided
    today = timezone.now().date()
    if not start_date:
        start_date = date(today.year, today.month, 1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = today.strftime('%Y-%m-%d')
    
    # Convert string dates to datetime objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get suppliers for the filter dropdown
    suppliers = Supplier.objects.all().order_by('name')
    
    # Build the queryset for bills
    bills = Purchase.objects.filter(
        date__gte=start_date_obj,
        date__lte=end_date_obj
    ).order_by('-date')
    
    # Apply supplier filter if provided
    if supplier_id:
        bills = bills.filter(supplier_id=supplier_id)
    
    # Apply status filter if provided
    if status:
        if status == 'paid':
            bills = bills.filter(paid_amount__gte=F('total_amount'))
        elif status == 'unpaid':
            bills = bills.filter(paid_amount__lt=F('total_amount'))
    
    # Calculate totals
    total_bill_amount = bills.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid_amount = bills.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
    total_balance = total_bill_amount - total_paid_amount
    
    # Calculate status counts
    paid_count = bills.filter(paid_amount__gte=F('total_amount')).count()
    unpaid_count = bills.filter(paid_amount__lt=F('total_amount')).count()
    
    # Add balance and is_paid to each bill for the template
    for bill in bills:
        bill.balance = bill.total_amount - bill.paid_amount
        bill.is_paid = bill.paid_amount >= bill.total_amount
    
    context = {
        'title': 'Bill Report',
        'start_date': start_date,
        'end_date': end_date,
        'suppliers': suppliers,
        'selected_supplier': supplier_id,
        'status': status,
        'bills': bills,
        'total_bill_amount': total_bill_amount,
        'total_paid_amount': total_paid_amount,
        'total_balance': total_balance,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'bill_count': bills.count(),
        'query_params': request.GET.urlencode()
    }
    
    return render(request, 'core/bill_report.html', context)

@login_required
def export_bill_report(request, format='excel'):
    """
    Export Bill Report to Excel or PDF
    """
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    supplier_id = request.GET.get('supplier')
    status = request.GET.get('status')
    
    # Default to current month if no dates provided
    today = timezone.now().date()
    if not start_date:
        start_date = date(today.year, today.month, 1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = today.strftime('%Y-%m-%d')
    
    # Convert string dates to datetime objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Build the queryset for bills
    bills = Purchase.objects.filter(
        date__gte=start_date_obj,
        date__lte=end_date_obj
    ).order_by('-date')
    
    # Apply supplier filter if provided
    if supplier_id:
        bills = bills.filter(supplier_id=supplier_id)
    
    # Apply status filter if provided
    if status:
        if status == 'paid':
            bills = bills.filter(paid_amount__gte=F('total_amount'))
        elif status == 'unpaid':
            bills = bills.filter(paid_amount__lt=F('total_amount'))
    
    # Calculate totals
    total_bill_amount = bills.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid_amount = bills.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
    total_balance = total_bill_amount - total_paid_amount
    
    # Prepare data for export
    data = []
    headers = ['Date', 'Invoice #', 'Supplier', 'Notes', 'Total Amount', 'Paid Amount', 'Balance', 'Status']
    filename = 'Bill_Report'
    
    for bill in bills:
        is_paid = bill.paid_amount >= bill.total_amount
        status_text = 'Paid' if is_paid else 'Unpaid'
        balance = bill.total_amount - bill.paid_amount
        
        data.append([
            bill.date.strftime('%d-%m-%Y'),
            bill.invoice_number,
            bill.supplier.name,
            bill.notes or '-',
            bill.total_amount,
            bill.paid_amount,
            balance,
            status_text
        ])
    
    if format == 'excel':
        return export_bill_to_excel(data, headers, filename, start_date, end_date, total_bill_amount, total_paid_amount, total_balance)
    else:
        return export_bill_to_pdf(data, headers, filename, start_date, end_date, total_bill_amount, total_paid_amount, total_balance)

def export_bill_to_excel(data, headers, filename, start_date, end_date, total_bill_amount, total_paid_amount, total_balance):
    """
    Export Bill Report to Excel
    """
    import xlwt
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}_{start_date}_to_{end_date}.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Bill Report')
    
    # Styles
    title_style = xlwt.XFStyle()
    title_style.font.bold = True
    title_style.font.height = 280
    
    header_style = xlwt.XFStyle()
    header_style.font.bold = True
    
    date_style = xlwt.XFStyle()
    date_style.num_format_str = 'DD-MM-YYYY'
    
    currency_style = xlwt.XFStyle()
    currency_style.num_format_str = '#,##0.00'
    
    bold_currency_style = xlwt.XFStyle()
    bold_currency_style.num_format_str = '#,##0.00'
    bold_currency_style.font.bold = True
    
    # Title and date range
    ws.write(0, 0, 'Bill Report', title_style)
    ws.write(1, 0, f"Period: {start_date} to {end_date}")
    
    # Headers
    row_num = 3
    for col_num, column_title in enumerate(headers):
        ws.write(row_num, col_num, column_title, header_style)
    
    # Data rows
    for row in data:
        row_num += 1
        for col_num, cell_value in enumerate(row):
            if col_num == 0:  # Date column
                ws.write(row_num, col_num, cell_value, date_style)
            elif col_num in [4, 5, 6]:  # Amount columns
                ws.write(row_num, col_num, float(cell_value), currency_style)
            else:
                ws.write(row_num, col_num, cell_value)
    
    # Total row
    row_num += 2
    ws.write(row_num, 0, 'Grand Total', header_style)
    ws.write(row_num, 4, float(total_bill_amount), bold_currency_style)
    ws.write(row_num, 5, float(total_paid_amount), bold_currency_style)
    ws.write(row_num, 6, float(total_balance), bold_currency_style)
    
    # Set column widths
    ws.col(0).width = 3500  # Date
    ws.col(1).width = 4000  # Bill #
    ws.col(2).width = 8000  # Supplier
    ws.col(3).width = 10000  # Description
    ws.col(4).width = 4000  # Bill Amount
    ws.col(5).width = 4000  # Paid Amount
    ws.col(6).width = 4000  # Balance
    ws.col(7).width = 3000  # Status
    
    wb.save(response)
    return response

def export_bill_to_pdf(data, headers, filename, start_date, end_date, total_bill_amount, total_paid_amount, total_balance):
    """
    Export Bill Report to PDF
    """
    from django.http import HttpResponse
    from django.template.loader import get_template
    import pdfkit
    
    # Prepare template context
    context = {
        'title': 'Bill Report',
        'start_date': start_date,
        'end_date': end_date,
        'headers': headers,
        'data': data,
        'total_bill_amount': total_bill_amount,
        'total_paid_amount': total_paid_amount,
        'total_balance': total_balance,
        'current_date': timezone.now(),  # Using full datetime object
    }
    
    # Render HTML from template
    template = get_template('core/pdf/bill_report_pdf.html')
    html = template.render(context)
    
    # Generate PDF using pdfkit
    try:
        pdf = pdfkit.from_string(html, False)
        
        # Create HTTP response with PDF content
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}_{start_date}_to_{end_date}.pdf"'
        return response
    except Exception as e:
        # Fallback to Excel if PDF generation fails
        return export_bill_to_excel(data, headers, filename, start_date, end_date, total_bill_amount, total_paid_amount, total_balance)