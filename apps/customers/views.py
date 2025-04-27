from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, FormView, RedirectView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q, Prefetch, Sum, F, ExpressionWrapper, DecimalField
from .models import Customer, Delivery, ConcreteDelivery, MixRatio, CustomerPayment
from apps.materials.models import Material
from django import forms
from datetime import datetime, date, timezone
from collections import defaultdict
from django.http import HttpResponse, JsonResponse, Http404
import csv
from .forms import CustomerPaymentForm, DeliveryForm, UnifiedDeliveryForm
from apps.core.decorators import permission_required, check_role_based_permission
from django.utils.decorators import method_decorator
from django.utils import timezone

# Stub classes for views referenced in urls but not fully implemented yet
# These will be replaced with actual implementations later

@method_decorator(check_role_based_permission('customer', 'view'), name='dispatch')
class CustomerListView(ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Customer.objects.all()
        search_query = self.request.GET.get('search', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(gst_number__icontains=search_query)
            )
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

@method_decorator(check_role_based_permission('customer', 'add'), name='dispatch')
class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    template_name = 'customers/customer_form.html'
    fields = ['name', 'address', 'phone', 'email', 'gst_number', 'is_active']

@method_decorator(check_role_based_permission('customer', 'change'), name='dispatch')
class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    template_name = 'customers/customer_form.html'
    fields = ['name', 'address', 'phone', 'email', 'gst_number', 'is_active']

@method_decorator(check_role_based_permission('customer', 'view'), name='dispatch')
class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'customers/customer_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        
        # Add recent regular deliveries
        context['recent_deliveries'] = customer.deliveries.all().order_by('-date')[:5]
        
        return context

@method_decorator(check_role_based_permission('customer', 'delete'), name='dispatch')
class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customers/customer_confirm_delete.html'

class CustomerLedgerView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'customers/customer_ledger.html'

class CustomerLedgerExcelView(LoginRequiredMixin, View):
    def get(self, request, pk):
        # Stub implementation
        return HttpResponse("Excel export not implemented")

class CustomerPaymentListView(LoginRequiredMixin, ListView):
    model = CustomerPayment
    template_name = 'customers/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = CustomerPayment.objects.all()
        
        # Filter by customer if specified
        customer_id = self.request.GET.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # Filter by search term if specified
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(customer__name__icontains=search_query) |
                Q(delivery__invoice_number__icontains=search_query) |
                Q(reference_number__icontains=search_query) |
                Q(payment_mode__icontains=search_query)
            )
        
        return queryset.order_by('-payment_date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all().order_by('name')
        context['selected_customer'] = self.request.GET.get('customer', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['today'] = date.today()
        return context

class CustomerPaymentCreateView(LoginRequiredMixin, CreateView):
    model = CustomerPayment
    template_name = 'customers/payment_form.html'
    form_class = CustomerPaymentForm
    
    def get_success_url(self):
        return reverse_lazy('customers:payment_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Payment recorded successfully.")
        return super().form_valid(form)

class CustomerPaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomerPayment
    template_name = 'customers/payment_form.html'
    form_class = CustomerPaymentForm
    
    def get_success_url(self):
        return reverse_lazy('customers:payment_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Payment updated successfully.")
        return super().form_valid(form)

class CustomerPaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = CustomerPayment
    template_name = 'customers/payment_confirm_delete.html'
    success_url = reverse_lazy('customers:payment_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Payment deleted successfully.")
        return super().delete(request, *args, **kwargs)

class CustomerLedgerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'customers/customer_ledger_list.html'

class ConcreteDeliveryListView(LoginRequiredMixin, ListView):
    model = ConcreteDelivery
    template_name = 'customers/concrete_delivery_list.html'
    context_object_name = 'deliveries'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = ConcreteDelivery.objects.all()
        
        # Filter by customer if specified
        customer_id = self.request.GET.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
            
        # Filter by grade if specified
        grade = self.request.GET.get('grade')
        if grade:
            queryset = queryset.filter(grade=grade)
            
        # Filter by date range if specified
        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(delivery_date__gte=start_date)
            
        end_date = self.request.GET.get('end_date')
        if end_date:
            queryset = queryset.filter(delivery_date__lte=end_date)
            
        return queryset.order_by('-delivery_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all().order_by('name')
        context['selected_customer'] = self.request.GET.get('customer', '')
        context['selected_grade'] = self.request.GET.get('grade', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['grade_choices'] = ConcreteDelivery.GRADE_CHOICES
        return context

class ConcreteDeliveryCreateView(LoginRequiredMixin, CreateView):
    model = ConcreteDelivery
    template_name = 'customers/concrete_delivery_form.html'
    fields = ['customer', 'delivery_date', 'grade', 'quantity', 'site_location', 'total_amount', 'received_amount', 'due_date', 'remarks', 'inventory_deducted']
    success_url = reverse_lazy('customers:concrete_delivery_list')
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Set customer ID if provided in query parameters
        customer_id = self.request.GET.get('customer')
        if customer_id:
            try:
                initial['customer'] = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                pass
                
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add mix ratios information for concrete deliveries
        materials_by_grade = {}
        
        for grade_code, grade_name in ConcreteDelivery.GRADE_CHOICES:
            if not grade_code:  # Skip empty choice
                continue
                
            mix_ratios = MixRatio.objects.filter(grade=grade_code)
            materials = []
            
            for ratio in mix_ratios:
                material = ratio.material
                materials.append({
                    'name': material.name,
                    'qty_per_m3': ratio.qty_per_m3,
                    'unit': material.unit,
                    'current_stock': material.current_stock
                })
            
            if materials:
                materials_by_grade[grade_code] = materials
        
        context['materials_by_grade'] = materials_by_grade
        
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Concrete delivery created successfully.")
        return super().form_valid(form)

class ConcreteDeliveryDetailView(LoginRequiredMixin, DetailView):
    model = ConcreteDelivery
    template_name = 'customers/concrete_delivery_detail.html'
    context_object_name = 'delivery'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = self.object.concrete_payments.all().order_by('-payment_date')
        context['today'] = date.today()
        return context

class ConcreteDeliveryUpdateView(LoginRequiredMixin, FormView):
    """
    View for updating a concrete delivery using the unified form
    """
    template_name = 'customers/delivery_form.html'
    form_class = UnifiedDeliveryForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.object = self.get_object()
        kwargs['instance'] = self.object
        return kwargs
    
    def get_object(self):
        pk = self.kwargs.get('pk')
        try:
            return ConcreteDelivery.objects.get(pk=pk)
        except ConcreteDelivery.DoesNotExist:
            raise Http404("Concrete delivery not found")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['instance'] = self.object
        
        # Add mix ratios information for concrete deliveries
        materials_by_grade = {}
        
        for grade_code, grade_name in ConcreteDelivery.GRADE_CHOICES:
            if not grade_code:  # Skip empty choice
                continue
                
            mix_ratios = MixRatio.objects.filter(grade=grade_code)
            materials = []
            
            for ratio in mix_ratios:
                material = ratio.material
                materials.append({
                    'name': material.name,
                    'qty_per_m3': ratio.qty_per_m3,
                    'unit': material.unit,
                    'current_stock': material.current_stock
                })
            
            if materials:
                materials_by_grade[grade_code] = materials
        
        context['materials_by_grade'] = materials_by_grade
        
        return context
    
    def form_valid(self, form):
        delivery = form.save()
        messages.success(self.request, "Concrete delivery updated successfully.")
        return redirect('customers:concrete_delivery_detail', pk=delivery.pk)

class MixRatioListView(LoginRequiredMixin, ListView):
    model = MixRatio
    template_name = 'customers/mix_ratio_list.html'

class MixRatioCreateView(LoginRequiredMixin, CreateView):
    model = MixRatio
    template_name = 'customers/mix_ratio_form.html'
    fields = ['grade', 'material', 'qty_per_m3']

class MixRatioUpdateView(LoginRequiredMixin, UpdateView):
    model = MixRatio
    template_name = 'customers/mix_ratio_form.html'
    fields = ['grade', 'material', 'qty_per_m3']

class MixRatioDeleteView(LoginRequiredMixin, DeleteView):
    model = MixRatio
    template_name = 'customers/mix_ratio_confirm_delete.html'

@check_role_based_permission('delivery', 'view')
def delivery_report(request):
    """View for generating delivery reports based on filters"""
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    customer_id = request.GET.get('customer')
    
    # Initialize queryset for regular deliveries
    regular_deliveries = Delivery.objects.all().order_by('-date')
    
    # Initialize queryset for concrete deliveries
    concrete_deliveries = ConcreteDelivery.objects.all().order_by('-delivery_date')
    
    # Apply date filters if provided
    if start_date:
        regular_deliveries = regular_deliveries.filter(date__gte=start_date)
        concrete_deliveries = concrete_deliveries.filter(delivery_date__gte=start_date)
    
    if end_date:
        regular_deliveries = regular_deliveries.filter(date__lte=end_date)
        concrete_deliveries = concrete_deliveries.filter(delivery_date__lte=end_date)
    
    # Apply customer filter if provided
    if customer_id:
        regular_deliveries = regular_deliveries.filter(customer_id=customer_id)
        concrete_deliveries = concrete_deliveries.filter(customer_id=customer_id)
    
    # Combine regular and concrete deliveries into a unified list
    deliveries = []
    
    # Process regular deliveries
    for delivery in regular_deliveries:
        deliveries.append({
            'date': delivery.date,
            'invoice_number': delivery.invoice_number,
            'customer': delivery.customer.name,
            'total_amount': delivery.total_amount,
            'received_amount': delivery.received_amount,
            'balance': delivery.total_amount - delivery.received_amount,
            'type': 'Regular',
            'id': delivery.id,
            'detail_url': reverse('customers:delivery_detail', args=[delivery.id])
        })
    
    # Process concrete deliveries
    for delivery in concrete_deliveries:
        deliveries.append({
            'date': delivery.delivery_date,
            'invoice_number': delivery.invoice_number,
            'customer': delivery.customer.name,
            'total_amount': delivery.total_amount,
            'received_amount': delivery.received_amount,
            'balance': delivery.total_amount - delivery.received_amount,
            'type': f'Concrete ({delivery.grade})',
            'id': delivery.id,
            'detail_url': reverse('customers:concrete_delivery_detail', args=[delivery.id])
        })
    
    # Sort deliveries by date (most recent first)
    deliveries.sort(key=lambda x: x['date'], reverse=True)
    
    # Calculate totals
    total_amount = sum(delivery['total_amount'] for delivery in deliveries)
    total_received = sum(delivery['received_amount'] for delivery in deliveries)
    total_balance = sum(delivery['balance'] for delivery in deliveries)
    
    # Get all customers for the filter dropdown
    customers = Customer.objects.filter(is_active=True).order_by('name')
    
    context = {
        'deliveries': deliveries,
        'total_amount': total_amount,
        'total_received': total_received,
        'total_balance': total_balance,
        'customers': customers,
        'selected_customer': customer_id,
        'start_date': start_date,
        'end_date': end_date,
        'filter_active': bool(start_date or end_date or customer_id)
    }
    
    return render(request, 'customers/delivery_report.html', context)

# Implemented delivery views

class DeliveryListView(LoginRequiredMixin, ListView):
    """
    View for listing all types of deliveries
    """
    model = Delivery
    template_name = 'customers/delivery_list.html'
    context_object_name = 'deliveries'
    paginate_by = 10
    
    def get_queryset(self):
        # Get filter parameters
        customer_id = self.request.GET.get('customer_id')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        concrete_only = self.request.GET.get('concrete_only')
        regular_only = self.request.GET.get('regular_only')
        
        # Start with empty lists
        regular_deliveries = []
        concrete_deliveries = []
        
        # Get regular deliveries if not concrete-only
        if not concrete_only:
            query = Delivery.objects.all()
            if customer_id:
                query = query.filter(customer_id=customer_id)
            if date_from:
                query = query.filter(date__gte=date_from)
            if date_to:
                query = query.filter(date__lte=date_to)
                
            # Convert regular deliveries to dictionaries with common attributes
            for delivery in query:
                regular_deliveries.append({
                    'id': delivery.id,
                    'is_concrete': False,
                    'invoice_number': delivery.invoice_number,
                    'customer': delivery.customer,
                    'date': delivery.date,
                    'delivery_date': delivery.date,  # For consistent access
                    'total_amount': delivery.total_amount,
                    'amount_received': delivery.received_amount,
                    'received_amount': delivery.received_amount,  # For consistent access
                    'balance': delivery.total_amount - delivery.received_amount,
                    'concrete_grade': None,
                    'quantity': None
                })
        
        # Get concrete deliveries if not regular-only
        if not regular_only:
            query = ConcreteDelivery.objects.all()
            if customer_id:
                query = query.filter(customer_id=customer_id)
            if date_from:
                query = query.filter(delivery_date__gte=date_from)
            if date_to:
                query = query.filter(delivery_date__lte=date_to)
                
            # Convert concrete deliveries to dictionaries with common attributes
            for delivery in query:
                concrete_deliveries.append({
                    'id': delivery.id,
                    'is_concrete': True,
                    'invoice_number': delivery.invoice_number,
                    'customer': delivery.customer,
                    'date': delivery.delivery_date,  # For consistent access
                    'delivery_date': delivery.delivery_date,
                    'total_amount': delivery.total_amount,
                    'amount_received': delivery.received_amount,
                    'received_amount': delivery.received_amount,
                    'balance': delivery.total_amount - delivery.received_amount,
                    'concrete_grade': delivery.grade,
                    'quantity': delivery.quantity
                })
        
        # Combine both lists and sort by date (descending)
        combined_deliveries = regular_deliveries + concrete_deliveries
        combined_deliveries.sort(key=lambda x: x['date'], reverse=True)
        
        return combined_deliveries
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all()
        context['customer_id'] = self.request.GET.get('customer_id', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['concrete_only'] = self.request.GET.get('concrete_only') == '1'
        context['regular_only'] = self.request.GET.get('regular_only') == '1'
        return context

class DeliveryCreateView(LoginRequiredMixin, FormView):
    """
    Unified view for creating both regular and concrete deliveries
    """
    template_name = 'customers/delivery_form.html'
    form_class = UnifiedDeliveryForm
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Set customer ID if provided in query parameters
        customer_id = self.request.GET.get('customer')
        if customer_id:
            try:
                initial['customer'] = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                pass
                
        # Set delivery type if provided in query parameters
        delivery_type = self.request.GET.get('delivery_type')
        if delivery_type in ['regular', 'concrete']:
            initial['delivery_type'] = delivery_type
            
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add mix ratios information for concrete deliveries
        materials_by_grade = {}
        
        for grade_code, grade_name in ConcreteDelivery.GRADE_CHOICES:
            if not grade_code:  # Skip empty choice
                continue
                
            mix_ratios = MixRatio.objects.filter(grade=grade_code)
            materials = []
            
            for ratio in mix_ratios:
                material = ratio.material
                materials.append({
                    'name': material.name,
                    'qty_per_m3': ratio.qty_per_m3,
                    'unit': material.unit,
                    'current_stock': material.current_stock
                })
            
            if materials:
                materials_by_grade[grade_code] = materials
        
        context['materials_by_grade'] = materials_by_grade
        
        return context
    
    def form_valid(self, form):
        delivery = form.save()
        
        delivery_type = form.cleaned_data.get('delivery_type')
        
        if delivery_type == 'regular':
            messages.success(self.request, "Regular delivery created successfully.")
            return redirect('customers:delivery_detail', pk=delivery.pk)
        else:  # concrete delivery
            messages.success(self.request, "Concrete delivery created successfully.")
            return redirect('customers:concrete_delivery_detail', pk=delivery.pk)
        
    def form_invalid(self, form):
        # Print out the form errors for debugging
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"Error in {field}: {error}")
        return super().form_invalid(form)


class DeliveryUpdateView(LoginRequiredMixin, FormView):
    """
    View for updating either a regular or concrete delivery
    """
    template_name = 'customers/delivery_form.html'
    form_class = UnifiedDeliveryForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.object = self.get_object()
        kwargs['instance'] = self.object
        return kwargs
    
    def get_object(self):
        pk = self.kwargs.get('pk')
        try:
            return Delivery.objects.get(pk=pk)
        except Delivery.DoesNotExist:
            raise Http404("Delivery not found")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['instance'] = self.object
        
        # Add mix ratios information for concrete deliveries
        materials_by_grade = {}
        
        for grade_code, grade_name in ConcreteDelivery.GRADE_CHOICES:
            if not grade_code:  # Skip empty choice
                continue
                
            mix_ratios = MixRatio.objects.filter(grade=grade_code)
            materials = []
            
            for ratio in mix_ratios:
                material = ratio.material
                materials.append({
                    'name': material.name,
                    'qty_per_m3': ratio.qty_per_m3,
                    'unit': material.unit,
                    'current_stock': material.current_stock
                })
            
            if materials:
                materials_by_grade[grade_code] = materials
        
        context['materials_by_grade'] = materials_by_grade
        
        return context
    
    def form_valid(self, form):
        delivery = form.save()
        
        delivery_type = form.cleaned_data.get('delivery_type')
        
        if delivery_type == 'regular':
            messages.success(self.request, "Regular delivery updated successfully.")
            return redirect('customers:delivery_detail', pk=delivery.pk)
        else:  # concrete delivery
            messages.success(self.request, "Concrete delivery updated successfully.")
            return redirect('customers:concrete_delivery_detail', pk=delivery.pk)


class DeliveryDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying delivery details
    """
    model = Delivery
    template_name = 'customers/delivery_detail.html'
    context_object_name = 'delivery'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = self.object.payments.all().order_by('-payment_date')
        context['today'] = date.today()
        return context

class CustomerRiskAssessmentView(LoginRequiredMixin, ListView):
    """
    View for displaying and managing customer risk assessments
    """
    model = Customer
    template_name = 'customers/risk_assessment.html'
    context_object_name = 'customers'
    
    def get_queryset(self):
        queryset = Customer.objects.all()
        
        # Filter by risk level if specified
        risk_level = self.request.GET.get('risk_level')
        if risk_level:
            queryset = queryset.filter(risk_score=risk_level)
            
        # Filter by search term if specified
        search_term = self.request.GET.get('search')
        if search_term:
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(phone__icontains=search_term) |
                Q(email__icontains=search_term)
            )
        
        return queryset.order_by('-risk_score', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['risk_levels'] = Customer.RISK_CHOICES
        context['selected_risk'] = self.request.GET.get('risk_level', '')
        context['search_term'] = self.request.GET.get('search', '')
        
        # Count customers by risk level
        for risk_code, risk_name in Customer.RISK_CHOICES:
            context[f'{risk_code.lower()}_count'] = Customer.objects.filter(risk_score=risk_code).count()
            
        # Add today's date for display
        context['today'] = date.today()
        
        return context
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for recalculating risk scores
        """
        # Get action parameter
        action = request.POST.get('action')
        
        if action == 'recalculate_all':
            # Recalculate risk scores for all customers
            count = 0
            for customer in Customer.objects.all():
                customer.calculate_risk_score()
                count += 1
            messages.success(request, f"Risk scores recalculated for all {count} customers")
        
        elif action == 'recalculate_selected':
            # Recalculate for selected customers
            customer_ids = request.POST.getlist('selected_customers')
            if customer_ids:
                count = 0
                for customer_id in customer_ids:
                    try:
                        customer = Customer.objects.get(pk=customer_id)
                        result = customer.calculate_risk_score()
                        count += 1
                        
                        # If only one customer is being recalculated, show detailed message
                        if len(customer_ids) == 1:
                            risk_level = result['risk_level']
                            risk_points = result['points']
                            risk_color = {
                                'HIGH': 'danger',
                                'MEDIUM': 'warning',
                                'LOW': 'success'
                            }.get(risk_level, 'info')
                            
                            messages.success(
                                request, 
                                f"Risk score updated for {customer.name}: "
                                f"<span class='text-{risk_color}'>{risk_level}</span> "
                                f"({risk_points} points)",
                                extra_tags='safe'
                            )
                    except Customer.DoesNotExist:
                        continue
                
                if len(customer_ids) > 1:
                    messages.success(request, f"Risk scores recalculated for {count} customers")
            else:
                messages.warning(request, "No customers selected for risk recalculation")
        
        elif action == 'update_risk':
            # Update risk score manually for a customer
            customer_id = request.POST.get('customer_id')
            risk_score = request.POST.get('risk_score')
            risk_notes = request.POST.get('risk_notes')
            
            try:
                customer = Customer.objects.get(pk=customer_id)
                customer.risk_score = risk_score
                customer.risk_notes = risk_notes
                customer.risk_last_updated = timezone.now()
                customer.save(update_fields=['risk_score', 'risk_notes', 'risk_last_updated'])
                
                messages.success(request, f"Risk score updated for {customer.name}")
            except Customer.DoesNotExist:
                messages.error(request, "Customer not found")
        
        # Redirect back to the same page
        return redirect('customers:risk_assessment')

# Add API endpoint for customer deliveries
def customer_deliveries_api(request):
    """
    API endpoint to get deliveries for a specific customer with balance info
    Used by the payment form to filter deliveries by customer
    """
    customer_id = request.GET.get('customer')
    if not customer_id:
        return JsonResponse([], safe=False)
    
    # Get deliveries with outstanding balance for this customer
    deliveries = Delivery.objects.filter(
        customer_id=customer_id,
        total_amount__gt=F('received_amount')
    ).order_by('-date')
    
    # Format the data for JSON response
    data = []
    for delivery in deliveries:
        # Calculate balance manually
        balance = delivery.total_amount - delivery.received_amount
        data.append({
            'id': delivery.id,
            'invoice_number': delivery.invoice_number,
            'date': delivery.date.strftime('%Y-%m-%d'),
            'total_amount': float(delivery.total_amount),
            'received_amount': float(delivery.received_amount),
            'balance': float(balance),
            'balance_formatted': f"₹{balance:.2f} due"
        })
    
    return JsonResponse(data, safe=False)

# Add a new view for concrete deliveries API
def concrete_deliveries_api(request):
    """
    API endpoint to get concrete deliveries for a specific customer with balance info
    Used by the payment form to filter concrete deliveries by customer
    """
    customer_id = request.GET.get('customer')
    if not customer_id:
        return JsonResponse([], safe=False)
    
    # Get concrete deliveries with outstanding balance for this customer
    deliveries = ConcreteDelivery.objects.filter(
        customer_id=customer_id,
        total_amount__gt=F('received_amount')
    ).order_by('-delivery_date')
    
    # Format the data for JSON response
    data = []
    for delivery in deliveries:
        # Calculate balance
        balance = delivery.total_amount - delivery.received_amount
        data.append({
            'id': delivery.id,
            'invoice_number': delivery.invoice_number,
            'grade': delivery.grade,
            'delivery_date': delivery.delivery_date.strftime('%Y-%m-%d'),
            'quantity': float(delivery.quantity),
            'site_location': delivery.site_location,
            'total_amount': float(delivery.total_amount),
            'received_amount': float(delivery.received_amount),
            'balance': float(balance),
            'balance_formatted': f"₹{balance:.2f} due"
        })
    
    return JsonResponse(data, safe=False)

class ConcreteDeliveryCreateRedirectView(RedirectView):
    """
    Redirects to the concrete delivery create view
    """
    def get_redirect_url(self, *args, **kwargs):
        # Get any query parameters from the request
        customer_id = self.request.GET.get('customer')
        query_params = f'?customer={customer_id}' if customer_id else ''
        # Redirect directly to the concrete delivery creation view
        return reverse('customers:concrete_delivery_create') + query_params