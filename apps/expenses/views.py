from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Expense, ExpenseCategory, Salary, Vehicle
from .forms import ExpenseForm, VehicleForm, ExpenseFilterForm
from apps.users.utils import (
    AdminRequiredMixin, AccountantRequiredMixin, ViewerRequiredMixin,
    admin_required, accountant_required, viewer_required
)

# Expense Category Views
class ExpenseCategoryListView(ViewerRequiredMixin, ListView):
    model = ExpenseCategory
    template_name = 'expenses/category_list.html'
    context_object_name = 'categories'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add expense totals for each category
        categories_with_totals = []
        for category in context['categories']:
            total_expense = Expense.objects.filter(category=category).aggregate(Sum('amount'))['amount__sum'] or 0
            categories_with_totals.append({
                'category': category,
                'total_expense': total_expense,
                'count': Expense.objects.filter(category=category).count()
            })
        
        context['categories_with_totals'] = categories_with_totals
        return context


class ExpenseCategoryCreateView(LoginRequiredMixin, CreateView):
    model = ExpenseCategory
    template_name = 'expenses/category_form.html'
    fields = ['name', 'default_type', 'description', 'is_active']
    success_url = reverse_lazy('expenses:category_list')

    def dispatch(self, request, *args, **kwargs):
        # Allow superusers or users with Admin role (case insensitive)
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        if request.user.is_superuser or 'admin' in request.user.role.lower() or request.user.role in ['ADMIN', 'Admin', 'Administrator']:
            return super().dispatch(request, *args, **kwargs)
            
        messages.error(request, "You don't have permission to create expense categories.")
        return redirect('expenses:category_list')

    def form_valid(self, form):
        messages.success(self.request, "Expense category created successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        # Log form errors
        print(f"Form validation failed: {form.errors}")
        messages.error(self.request, f"Please correct the errors below: {form.errors}")
        return super().form_invalid(form)


class ExpenseCategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = ExpenseCategory
    template_name = 'expenses/category_form.html'
    fields = ['name', 'default_type', 'description', 'is_active']
    success_url = reverse_lazy('expenses:category_list')

    def dispatch(self, request, *args, **kwargs):
        # Allow superusers or users with Admin role (case insensitive)
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        if request.user.is_superuser or 'admin' in request.user.role.lower() or request.user.role in ['ADMIN', 'Admin', 'Administrator']:
            return super().dispatch(request, *args, **kwargs)
            
        messages.error(request, "You don't have permission to update expense categories.")
        return redirect('expenses:category_list')

    def form_valid(self, form):
        messages.success(self.request, "Expense category updated successfully.")
        return super().form_valid(form)


# Vehicle Views
class VehicleListView(ViewerRequiredMixin, ListView):
    model = Vehicle
    template_name = 'expenses/vehicle_list.html'
    context_object_name = 'vehicles'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        vehicle_type = self.request.GET.get('type')
        status = self.request.GET.get('status')
        
        if vehicle_type:
            queryset = queryset.filter(vehicle_type=vehicle_type)
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add vehicle type and status filters
        context['vehicle_types'] = dict(Vehicle.VEHICLE_TYPE_CHOICES)
        context['selected_type'] = self.request.GET.get('type', '')
        context['selected_status'] = self.request.GET.get('status', '')
        
        # Add expense summaries for each vehicle
        vehicles_with_expenses = []
        for vehicle in context['vehicles']:
            expenses = Expense.objects.filter(vehicle=vehicle)
            total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
            
            # Get expenses by type
            expenses_by_type = expenses.values('expense_type').annotate(
                total=Sum('amount'),
                count=Count('id')
            )
            
            # Get recent expenses
            recent_expenses = expenses.order_by('-date')[:3]
            
            # Calculate maintenance metrics if applicable
            fuel_expenses = expenses.filter(expense_type='fuel').aggregate(Sum('amount'))['amount__sum'] or 0
            maintenance_expenses = expenses.filter(expense_type='maintenance').aggregate(Sum('amount'))['amount__sum'] or 0
            
            vehicles_with_expenses.append({
                'vehicle': vehicle,
                'total_expenses': total_expenses,
                'fuel_expenses': fuel_expenses,
                'maintenance_expenses': maintenance_expenses,
                'expense_count': expenses.count(),
                'expenses_by_type': expenses_by_type,
                'recent_expenses': recent_expenses
            })
        
        context['vehicles_with_expenses'] = vehicles_with_expenses
        return context


class VehicleDetailView(ViewerRequiredMixin, DetailView):
    model = Vehicle
    template_name = 'expenses/vehicle_detail.html'
    context_object_name = 'vehicle'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicle = self.object
        
        # Get expenses for this vehicle
        expenses = vehicle.expenses.order_by('-date')
        context['expenses'] = expenses
        
        # Calculate total expenses
        context['total_expenses'] = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Get expense breakdown by type
        expense_by_type = expenses.values('expense_type').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        context['expense_by_type'] = expense_by_type
        
        # Get expense trends (monthly)
        today = timezone.now().date()
        six_months_ago = today - timedelta(days=180)
        
        # Use SQLite-compatible date formatting instead of to_char
        monthly_expenses = []
        monthly_data = expenses.filter(date__gte=six_months_ago)
        
        # Group by year and month manually
        if monthly_data.exists():
            from django.db.models.functions import TruncMonth
            monthly_expenses = monthly_data.annotate(
                month=TruncMonth('date')
            ).values('month').annotate(
                total=Sum('amount')
            ).order_by('month')
            
            # Format month as YYYY-MM
            for entry in monthly_expenses:
                if entry['month']:
                    entry['month'] = entry['month'].strftime('%Y-%m')
        
        context['monthly_expenses'] = monthly_expenses
        
        # Check if insurance is expiring soon
        if vehicle.insurance_expiry:
            days_to_expiry = (vehicle.insurance_expiry - today).days
            context['days_to_insurance_expiry'] = days_to_expiry
            context['insurance_expiring_soon'] = days_to_expiry <= 30
            
        return context


class VehicleCreateView(ViewerRequiredMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'expenses/vehicle_form.html'
    success_url = reverse_lazy('expenses:vehicle_list')

    def form_valid(self, form):
        if not self.request.user.is_superuser and self.request.user.role != 'ADMIN' and self.request.user.role != 'ACCOUNTANT':
            messages.error(self.request, "You don't have permission to create vehicles.")
            return redirect('expenses:vehicle_list')
        messages.success(self.request, "Vehicle added successfully.")
        return super().form_valid(form)


class VehicleUpdateView(ViewerRequiredMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'expenses/vehicle_form.html'
    
    def get_success_url(self):
        return reverse_lazy('expenses:vehicle_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        if not self.request.user.is_superuser and self.request.user.role != 'ADMIN' and self.request.user.role != 'ACCOUNTANT':
            messages.error(self.request, "You don't have permission to update vehicles.")
            return redirect('expenses:vehicle_list')
        messages.success(self.request, "Vehicle updated successfully.")
        return super().form_valid(form)


class VehicleDeleteView(AdminRequiredMixin, DeleteView):
    model = Vehicle
    template_name = 'expenses/vehicle_confirm_delete.html'
    success_url = reverse_lazy('expenses:vehicle_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Vehicle deleted successfully.")
        return super().delete(request, *args, **kwargs)


# Enhanced Expense Views
class ExpenseListView(ViewerRequiredMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-date')
        
        # Get filter form data
        form = ExpenseFilterForm(self.request.GET)
        if form.is_valid():
            # Filter by category
            category = form.cleaned_data.get('category')
            if category:
                queryset = queryset.filter(category=category)
                
            # Filter by expense type
            expense_type = form.cleaned_data.get('expense_type')
            if expense_type:
                queryset = queryset.filter(expense_type=expense_type)
                
            # Filter by vehicle
            vehicle = form.cleaned_data.get('vehicle')
            if vehicle:
                queryset = queryset.filter(vehicle=vehicle)
                
            # Filter by date range
            start_date = form.cleaned_data.get('start_date')
            if start_date:
                queryset = queryset.filter(date__gte=start_date)
                
            end_date = form.cleaned_data.get('end_date')
            if end_date:
                queryset = queryset.filter(date__lte=end_date)
                
            # Filter by amount range
            min_amount = form.cleaned_data.get('min_amount')
            if min_amount:
                queryset = queryset.filter(amount__gte=min_amount)
                
            max_amount = form.cleaned_data.get('max_amount')
            if max_amount:
                queryset = queryset.filter(amount__lte=max_amount)
                
            # Filter by tags (requires conversion from comma-separated string)
            tags = form.cleaned_data.get('tags')
            if tags:
                # Use simple description search instead of tags
                tag_list = [tag.strip() for tag in tags.split(',')]
                for tag in tag_list:
                    queryset = queryset.filter(description__icontains=tag)
                
            # Search in description or reference_number
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(description__icontains=search) | 
                    Q(reference_number__icontains=search)
                )
                
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter form to context
        context['filter_form'] = ExpenseFilterForm(self.request.GET)
        
        # Calculate total expenses for current filter
        queryset = self.get_queryset()
        context['total_amount'] = queryset.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Add daily summary
        if 'start_date' in self.request.GET and 'end_date' in self.request.GET:
            daily_summary = queryset.values('date').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-date')
            context['daily_summary'] = daily_summary
        
        # Add monthly summary
        # Use SQLite-compatible date formatting instead of to_char
        from django.db.models.functions import TruncMonth
        monthly_data = queryset.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('-month')
        
        # Format month as YYYY-MM
        monthly_summary = []
        for entry in monthly_data:
            if entry['month']:
                formatted_entry = {
                    'month': entry['month'].strftime('%Y-%m'),
                    'total': entry['total']
                }
                monthly_summary.append(formatted_entry)
                
        context['monthly_summary'] = monthly_summary
        
        return context


class ExpenseDetailView(ViewerRequiredMixin, DetailView):
    model = Expense
    template_name = 'expenses/expense_detail.html'
    context_object_name = 'expense'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expense = self.object
        
        # Get related expenses (same category, vehicle, etc.)
        related_params = {}
        if expense.vehicle:
            related_params['vehicle'] = expense.vehicle
        elif expense.category:
            related_params['category'] = expense.category
            
        # Get related expenses excluding this one
        if related_params:
            context['related_expenses'] = Expense.objects.filter(
                **related_params
            ).exclude(id=expense.id).order_by('-date')[:5]
            
        return context


class ExpenseCreateView(ViewerRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    
    def get_success_url(self):
        return reverse_lazy('expenses:expense_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        if not self.request.user.is_superuser and self.request.user.role != 'ADMIN' and self.request.user.role != 'ACCOUNTANT':
            messages.error(self.request, "You don't have permission to create expenses.")
            return redirect('expenses:expense_list')
            
        form.instance.created_by = self.request.user
        messages.success(self.request, "Expense added successfully.")
        response = super().form_valid(form)
        
        # Handle bill file upload to Supabase if provided
        bill_file = self.request.FILES.get('bill_file')
        if bill_file:
            result = self.object.upload_bill_to_supabase(bill_file)
            if not result or not result.get('success'):
                messages.warning(self.request, "Expense saved but bill file could not be uploaded.")
                
        return response
    
    def get_initial(self):
        """Pre-populate form based on query parameters"""
        initial = super().get_initial()
        
        # Get query parameters
        category_id = self.request.GET.get('category')
        expense_type = self.request.GET.get('type')
        vehicle_id = self.request.GET.get('vehicle')
        
        # Set initial values if provided
        if category_id:
            try:
                initial['category'] = ExpenseCategory.objects.get(id=category_id)
            except ExpenseCategory.DoesNotExist:
                pass
                
        if expense_type:
            initial['expense_type'] = expense_type
            
        if vehicle_id:
            try:
                initial['vehicle'] = Vehicle.objects.get(id=vehicle_id)
            except Vehicle.DoesNotExist:
                pass
                
        return initial


class ExpenseUpdateView(ViewerRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    
    def get_success_url(self):
        return reverse_lazy('expenses:expense_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        if not self.request.user.is_superuser and self.request.user.role != 'ADMIN' and self.request.user.role != 'ACCOUNTANT':
            messages.error(self.request, "You don't have permission to update expenses.")
            return redirect('expenses:expense_list')
            
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Expense updated successfully.")
        response = super().form_valid(form)
        
        # Handle bill file upload to Supabase if provided
        bill_file = self.request.FILES.get('bill_file')
        if bill_file:
            # Delete previous file if exists
            if self.object.bill_file_path:
                self.object.delete_bill_from_supabase()
                
            # Upload new file
            result = self.object.upload_bill_to_supabase(bill_file)
            if not result or not result.get('success'):
                messages.warning(self.request, "Expense saved but bill file could not be uploaded.")
                
        return response


class ExpenseDeleteView(AdminRequiredMixin, DeleteView):
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expenses:expense_list')
    
    def delete(self, request, *args, **kwargs):
        expense = self.get_object()
        
        # Delete the bill file from Supabase if it exists
        if expense.bill_file_path:
            expense.delete_bill_from_supabase()
            
        messages.success(request, "Expense deleted successfully.")
        return super().delete(request, *args, **kwargs)


# Salary Views
class SalaryListView(ViewerRequiredMixin, ListView):
    model = Salary
    template_name = 'expenses/salary_list.html'
    context_object_name = 'salaries'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-month')
        
        # Filter by employee if provided
        employee = self.request.GET.get('employee')
        if employee:
            queryset = queryset.filter(employee__icontains=employee)
            
        # Filter by month/year if provided
        month = self.request.GET.get('month')
        if month:
            queryset = queryset.filter(month__icontains=month)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate total amount of salaries in the filtered queryset
        total_amount = self.get_queryset().aggregate(Sum('amount'))['amount__sum'] or 0
        context['total_amount'] = total_amount
        
        return context


class SalaryDetailView(ViewerRequiredMixin, DetailView):
    model = Salary
    template_name = 'expenses/salary_detail.html'
    context_object_name = 'salary'


class SalaryCreateView(ViewerRequiredMixin, CreateView):
    model = Salary
    template_name = 'expenses/salary_form.html'
    fields = ['employee', 'amount', 'month', 'paid_on', 'notes']
    success_url = reverse_lazy('expenses:salary_list')

    def form_valid(self, form):
        if not self.request.user.is_superuser and self.request.user.role != 'ADMIN' and self.request.user.role != 'ACCOUNTANT':
            messages.error(self.request, "You don't have permission to create salary payments.")
            return redirect('expenses:salary_list')
        messages.success(self.request, "Salary payment created successfully.")
        return super().form_valid(form)


class SalaryUpdateView(ViewerRequiredMixin, UpdateView):
    model = Salary
    template_name = 'expenses/salary_form.html'
    fields = ['employee', 'amount', 'month', 'paid_on', 'notes']
    success_url = reverse_lazy('expenses:salary_list')

    def form_valid(self, form):
        if not self.request.user.is_superuser and self.request.user.role != 'ADMIN' and self.request.user.role != 'ACCOUNTANT':
            messages.error(self.request, "You don't have permission to update salary payments.")
            return redirect('expenses:salary_list')
        messages.success(self.request, "Salary payment updated successfully.")
        return super().form_valid(form)


class SalaryDeleteView(AdminRequiredMixin, DeleteView):
    model = Salary
    template_name = 'expenses/salary_confirm_delete.html'
    success_url = reverse_lazy('expenses:salary_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Salary payment deleted successfully.")
        return super().delete(request, *args, **kwargs)


@viewer_required
def expense_dashboard(request):
    """
    Dashboard view showing expense stats and summaries
    """
    # Get latest expenses
    latest_expenses = Expense.objects.order_by('-date')[:5]
    
    # Get expense totals by category
    categories = ExpenseCategory.objects.all()
    category_totals = []
    
    for category in categories:
        total = Expense.objects.filter(category=category).aggregate(Sum('amount'))['amount__sum'] or 0
        category_totals.append({
            'category': category,
            'total': total
        })
    
    # Sort by total amount descending
    category_totals.sort(key=lambda x: x['total'], reverse=True)
    
    # Get vehicle expenses
    vehicle_expenses = Vehicle.objects.filter(is_active=True).annotate(
        total_expense=Sum('expenses__amount'),
        expense_count=Count('expenses')
    ).filter(total_expense__gt=0).order_by('-total_expense')[:5]
    
    # Get total expenses by expense type
    expense_by_type = Expense.objects.values('expense_type').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Get today's and this month's expenses
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    today_expenses = Expense.objects.filter(date=today).aggregate(Sum('amount'))['amount__sum'] or 0
    month_expenses = Expense.objects.filter(date__gte=month_start, date__lte=today).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get total salaries for current month
    current_month = today.strftime('%Y-%m')
    current_month_salaries = Salary.objects.filter(
        month__startswith=current_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'latest_expenses': latest_expenses,
        'category_totals': category_totals,
        'vehicle_expenses': vehicle_expenses,
        'expense_by_type': expense_by_type,
        'today_expenses': today_expenses,
        'month_expenses': month_expenses,
        'current_month_salaries': current_month_salaries,
        'total_month_outflow': month_expenses + current_month_salaries
    }
    
    return render(request, 'expenses/dashboard.html', context)


@viewer_required
def expense_report(request):
    """
    Detailed expense report view with filtering and aggregation
    """
    # Default to last 30 days if no date range specified
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get filter parameters
    filter_category = request.GET.get('category')
    filter_start_date = request.GET.get('start_date')
    filter_end_date = request.GET.get('end_date')
    filter_expense_type = request.GET.get('expense_type')
    filter_vehicle = request.GET.get('vehicle')
    
    # Apply date filters if provided
    if filter_start_date:
        try:
            start_date = datetime.strptime(filter_start_date, '%Y-%m-%d').date()
        except ValueError:
            pass
            
    if filter_end_date:
        try:
            end_date = datetime.strptime(filter_end_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Build base queryset with date filter
    expenses = Expense.objects.filter(date__gte=start_date, date__lte=end_date)
    
    # Apply category filter if provided
    if filter_category and filter_category != 'all':
        expenses = expenses.filter(category_id=filter_category)
        
    # Apply expense type filter if provided
    if filter_expense_type and filter_expense_type != 'all':
        expenses = expenses.filter(expense_type=filter_expense_type)
        
    # Apply vehicle filter if provided
    if filter_vehicle and filter_vehicle != 'all':
        expenses = expenses.filter(vehicle_id=filter_vehicle)
    
    # Calculate total expenses
    total_amount = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get expense breakdown by category
    category_totals = []
    categories = ExpenseCategory.objects.all()
    
    for category in categories:
        cat_total = expenses.filter(category=category).aggregate(Sum('amount'))['amount__sum'] or 0
        if cat_total > 0:
            category_totals.append({
                'category': category,
                'total': cat_total
            })
    
    # Sort by amount
    category_totals.sort(key=lambda x: x['total'], reverse=True)
    
    # Get expense breakdown by type
    type_totals = expenses.values('expense_type').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Get expense breakdown by vehicle
    vehicle_totals = expenses.filter(vehicle__isnull=False).values(
        'vehicle__name', 'vehicle__id'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Get daily expense data for chart
    daily_expenses = expenses.values('date').annotate(
        total=Sum('amount')
    ).order_by('date')
    
    # Get salaries for the same period
    salaries = Salary.objects.filter(paid_on__gte=start_date, paid_on__lte=end_date)
    total_salaries = salaries.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Calculate total outflow
    total_outflow = total_amount + total_salaries
    
    context = {
        'expenses': expenses.order_by('-date')[:100],  # Limit to 100 for performance
        'total_amount': total_amount,
        'total_salaries': total_salaries,
        'total_outflow': total_outflow,
        'category_totals': category_totals,
        'type_totals': type_totals,
        'vehicle_totals': vehicle_totals,
        'daily_expenses': daily_expenses,
        'start_date': start_date,
        'end_date': end_date,
        'categories': categories,
        'expense_types': Expense.EXPENSE_TYPE_CHOICES,
        'vehicles': Vehicle.objects.filter(is_active=True),
        'filter_category': filter_category,
        'filter_expense_type': filter_expense_type,
        'filter_vehicle': filter_vehicle,
    }
    
    return render(request, 'expenses/expense_report.html', context)


def salary_detail_redirect(request, pk):
    """
    Redirect from expenses salary detail to employees salary record detail
    """
    # Try to find the corresponding salary record
    try:
        salary = Salary.objects.get(pk=pk)
        from django.urls import reverse
        return redirect(reverse('employees:salary_record_detail', kwargs={'pk': salary.id}))
    except Salary.DoesNotExist:
        messages.error(request, "The salary record you're looking for doesn't exist.")
        return redirect('employees:salary_record_list')

def salary_edit_redirect(request, pk):
    """
    Redirect from expenses salary edit to employees salary record edit
    """
    try:
        salary = Salary.objects.get(pk=pk)
        from django.urls import reverse
        return redirect(reverse('employees:salary_record_update', kwargs={'pk': salary.id}))
    except Salary.DoesNotExist:
        messages.error(request, "The salary record you're trying to edit doesn't exist.")
        return redirect('employees:salary_record_list')

def salary_delete_redirect(request, pk):
    """
    Redirect from expenses salary delete to employees salary record delete
    """
    try:
        salary = Salary.objects.get(pk=pk)
        from django.urls import reverse
        return redirect(reverse('employees:salary_record_delete', kwargs={'pk': salary.id}))
    except Salary.DoesNotExist:
        messages.error(request, "The salary record you're trying to delete doesn't exist.")
        return redirect('employees:salary_record_list') 