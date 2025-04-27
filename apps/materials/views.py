from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, F, Sum, Count, Avg, OuterRef, Subquery
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
import json

from .models import Material, PurchaseOrder, PurchaseItem, InventoryEntry
from apps.suppliers.models import Purchase, SupplierPayment, Supplier
from apps.customers.models import Delivery, CustomerPayment, ConcreteDelivery, MixRatio


# Material Views
class MaterialListView(LoginRequiredMixin, ListView):
    model = Material
    context_object_name = 'materials'
    template_name = 'materials/material_list.html'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Material.objects.all()
        search_query = self.request.GET.get('q')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(unit__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class InventoryView(LoginRequiredMixin, ListView):
    model = Material
    context_object_name = 'materials'
    template_name = 'materials/inventory.html'
    
    def get_queryset(self):
        queryset = Material.objects.all()
        
        # Filter by material name (search)
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Filter by stock status
        stock_status = self.request.GET.get('stock_status')
        if stock_status == 'low':
            queryset = queryset.filter(current_stock__lt=F('reorder_level'))
        elif stock_status == 'normal':
            queryset = queryset.filter(current_stock__gte=F('reorder_level'))
        
        # Filter by last updated
        last_updated = self.request.GET.get('last_updated')
        if last_updated == 'today':
            from datetime import datetime, timedelta
            today = datetime.now().date()
            queryset = queryset.filter(updated_at__date=today)
        elif last_updated == 'week':
            from datetime import datetime, timedelta
            week_ago = datetime.now().date() - timedelta(days=7)
            queryset = queryset.filter(updated_at__date__gte=week_ago)
        elif last_updated == 'month':
            from datetime import datetime, timedelta
            month_ago = datetime.now().date() - timedelta(days=30)
            queryset = queryset.filter(updated_at__date__gte=month_ago)
        
        # Get inventory entries for each material
        for material in queryset:
            material.recent_entries = material.inventory_entries.all()[:5]
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['stock_status'] = self.request.GET.get('stock_status', '')
        context['last_updated'] = self.request.GET.get('last_updated', '')
        
        # Count materials with low stock
        context['low_stock_count'] = Material.objects.filter(current_stock__lt=F('reorder_level')).count()
        
        # Get suppliers and customers for the inventory form
        try:
            # Import here to avoid circular imports
            from apps.suppliers.models import Supplier
            from apps.customers.models import Customer
            
            context['suppliers'] = Supplier.objects.filter(is_active=True).order_by('name')
            context['customers'] = Customer.objects.filter(is_active=True).order_by('name')
        except ImportError:
            # Handle import error gracefully
            context['suppliers'] = []
            context['customers'] = []
            
        return context


class MaterialCreateView(LoginRequiredMixin, CreateView):
    model = Material
    template_name = 'materials/material_form.html'
    fields = ['name', 'description', 'unit', 'current_stock', 'reorder_level', 'is_active']
    success_url = reverse_lazy('materials:material_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Material added successfully.")
        return super().form_valid(form)


class MaterialDetailView(LoginRequiredMixin, DetailView):
    model = Material
    template_name = 'materials/material_detail.html'
    context_object_name = 'material'


class MaterialUpdateView(LoginRequiredMixin, UpdateView):
    model = Material
    template_name = 'materials/material_form.html'
    fields = ['name', 'description', 'unit', 'current_stock', 'reorder_level', 'is_active']
    
    def get_success_url(self):
        return reverse_lazy('materials:material_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, "Material information updated.")
        return super().form_valid(form)


class MaterialDeleteView(LoginRequiredMixin, DeleteView):
    model = Material
    template_name = 'materials/material_confirm_delete.html'
    success_url = reverse_lazy('materials:material_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Material deleted successfully.")
        return super().delete(request, *args, **kwargs)


# PurchaseOrder Views
class PurchaseOrderListView(LoginRequiredMixin, ListView):
    model = PurchaseOrder
    context_object_name = 'purchase_orders'
    template_name = 'materials/purchase_order_list.html'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = PurchaseOrder.objects.all()
        search_query = self.request.GET.get('q')
        
        if search_query:
            queryset = queryset.filter(
                Q(supplier__name__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'materials/purchase_order_detail.html'
    context_object_name = 'purchase_order'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.localdate()
        return context


class PurchaseOrderCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseOrder
    template_name = 'materials/purchase_order_form.html'
    fields = ['supplier', 'purchase_date', 'due_date', 'gst_percent', 'transport_cost', 'notes']
    success_url = reverse_lazy('materials:purchase_order_list')
    
    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items'] = PurchaseItemFormSet(self.request.POST)
        else:
            data['items'] = PurchaseItemFormSet()
        
        # Add auto update inventory checkbox
        data['auto_update_inventory'] = True
        return data
    
    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        self.object = form.save()
        
        if items.is_valid():
            items.instance = self.object
            items.save()
            
            # Update total amount after saving all items
            self.object.total_amount = self.object.calculate_total()
            self.object.save(update_fields=['total_amount'])
            
            # Check if auto_update_inventory is selected (checkbox present in form data)
            auto_update = 'auto_update_inventory' in self.request.POST
            
            # Update inventory with the purchase items if auto-update is selected
            if auto_update:
                updated_materials = self.object.update_inventory()
                
                # Create success message with updated stock information
                if updated_materials:
                    stock_message = "Updated stock levels: "
                    stock_details = [f"{item['name']}: {item['new_stock']} {item['quantity'].__class__.__name__}" for item in updated_materials]
                    stock_message += ", ".join(stock_details)
                    
                    messages.success(self.request, f"Purchase order created successfully. {stock_message}")
                else:
                    messages.success(self.request, "Purchase order created successfully.")
            else:
                messages.success(self.request, "Purchase order created successfully. Inventory was not updated.")
            
            return HttpResponseRedirect(self.get_success_url())
        
        return self.render_to_response(self.get_context_data(form=form))


class PurchaseOrderUpdateView(LoginRequiredMixin, UpdateView):
    model = PurchaseOrder
    template_name = 'materials/purchase_order_form.html'
    fields = ['supplier', 'purchase_date', 'due_date', 'gst_percent', 'transport_cost', 'notes']
    
    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items'] = PurchaseItemFormSet(self.request.POST, instance=self.object)
        else:
            data['items'] = PurchaseItemFormSet(instance=self.object)
        
        # Add auto update inventory checkbox
        data['auto_update_inventory'] = not self.object.inventory_updated
        return data
    
    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        self.object = form.save()
        
        if items.is_valid():
            items.instance = self.object
            items.save()
            
            # Update total amount after saving all items
            self.object.total_amount = self.object.calculate_total()
            self.object.save(update_fields=['total_amount'])
            
            # Check if auto_update_inventory is selected (checkbox present in form data)
            auto_update = 'auto_update_inventory' in self.request.POST
            
            # Update inventory if not already updated and auto-update is checked
            if not self.object.inventory_updated and auto_update:
                updated_materials = self.object.update_inventory()
                
                # Create success message with updated stock information
                if updated_materials:
                    stock_message = "Updated stock levels: "
                    stock_details = [f"{item['name']}: {item['new_stock']} {item['quantity'].__class__.__name__}" for item in updated_materials]
                    stock_message += ", ".join(stock_details)
                    
                    messages.success(self.request, f"Purchase order updated successfully. {stock_message}")
                else:
                    messages.success(self.request, "Purchase order updated successfully.")
            else:
                if self.object.inventory_updated:
                    messages.success(self.request, "Purchase order updated successfully. Inventory was already updated previously.")
                else:
                    messages.success(self.request, "Purchase order updated successfully. Inventory was not updated.")
            
            return HttpResponseRedirect(self.get_success_url())
        
        return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        return reverse_lazy('materials:purchase_order_detail', kwargs={'pk': self.object.pk})


class PurchaseOrderDeleteView(LoginRequiredMixin, DeleteView):
    model = PurchaseOrder
    template_name = 'materials/purchase_order_confirm_delete.html'
    success_url = reverse_lazy('materials:purchase_order_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Purchase order deleted successfully.")
        return super().delete(request, *args, **kwargs)


# Create formset for PurchaseItems
PurchaseItemFormSet = inlineformset_factory(
    PurchaseOrder, 
    PurchaseItem,
    fields=('material', 'quantity', 'rate_per_unit', 'gst_applicable'),
    extra=1,
    can_delete=True
)

@login_required
def update_inventory(request):
    """
    Handle inventory updates (stock in/out)
    """
    if request.method == 'POST':
        material_id = request.POST.get('material_id')
        entry_type = request.POST.get('entry_type')
        quantity = request.POST.get('quantity')
        reference_type = request.POST.get('reference_type')
        notes = request.POST.get('notes')
        
        # Get reference IDs from form data
        supplier_id = request.POST.get('supplier_id')
        customer_id = request.POST.get('customer_id')
        purchase_id = request.POST.get('purchase_id')
        delivery_id_with_type = request.POST.get('delivery_id')
        
        # Parse delivery_id to separate type and ID
        delivery_type = None
        delivery_id = None
        if delivery_id_with_type and '_' in delivery_id_with_type:
            delivery_type, delivery_id = delivery_id_with_type.split('_', 1)
        
        try:
            material = Material.objects.get(pk=material_id)
            
            # Build reference note based on the reference type
            reference_note = notes or ""
            reference_id = None
            
            if reference_type == 'PURCHASE' and supplier_id:
                # Import here to avoid circular imports
                from apps.suppliers.models import Supplier
                try:
                    supplier = Supplier.objects.get(pk=supplier_id)
                    reference_note = f"Purchase from {supplier.name}" + (f": {notes}" if notes else "")
                    
                    # If purchase ID is provided, link to that purchase
                    if purchase_id:
                        reference_id = purchase_id
                        reference_note += f" - Purchase ID: {purchase_id}"
                except Supplier.DoesNotExist:
                    pass
                    
            elif reference_type == 'SALE' and customer_id:
                # Import here to avoid circular imports
                from apps.customers.models import Customer, Delivery, ConcreteDelivery
                try:
                    customer = Customer.objects.get(pk=customer_id)
                    reference_note = f"Sale to {customer.name}" + (f": {notes}" if notes else "")
                    
                    # If delivery ID is provided, link to that delivery with the correct type
                    if delivery_id:
                        reference_id = delivery_id
                        
                        if delivery_type == 'regular':
                            try:
                                delivery = Delivery.objects.get(pk=delivery_id)
                                reference_note += f" - Delivery: {delivery.invoice_number}"
                            except Delivery.DoesNotExist:
                                reference_note += f" - Delivery ID: {delivery_id} (not found)"
                        elif delivery_type == 'concrete':
                            try:
                                concrete_delivery = ConcreteDelivery.objects.get(pk=delivery_id)
                                reference_note += f" - Concrete Delivery: {concrete_delivery.invoice_number} ({concrete_delivery.grade})"
                            except ConcreteDelivery.DoesNotExist:
                                reference_note += f" - Concrete Delivery ID: {delivery_id} (not found)"
                except Customer.DoesNotExist:
                    pass
            
            # Create inventory entry
            entry = InventoryEntry.objects.create(
                material=material,
                quantity=quantity,
                entry_type=entry_type,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=reference_note
            )
            
            # Material.update_stock() is called in the InventoryEntry.save() method
            
            if entry_type == 'IN':
                messages.success(request, f"Added {quantity} {material.unit} of {material.name} to inventory.")
            else:
                messages.success(request, f"Removed {quantity} {material.unit} of {material.name} from inventory.")
                
        except Material.DoesNotExist:
            messages.error(request, "Material not found.")
        except Exception as e:
            messages.error(request, f"Error updating inventory: {str(e)}")
    
    return redirect('materials:inventory_list')


class SmartSummaryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'materials/smart_summary.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get needed imports
        from django.db.models import Q, Sum, Count, Case, When, DecimalField, Value, CharField
        from django.db.models.functions import Concat
        from apps.customers.models import Customer
        
        # Get today's date
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)
        ninety_days_ago = today - timedelta(days=90)
        seven_days_later = today + timedelta(days=7)
        
        # Calculate total unpaid payables (sum of all unpaid supplier dues)
        total_payables = Purchase.objects.filter(
            total_amount__gt=F('paid_amount')
        ).annotate(
            balance=F('total_amount') - F('paid_amount')
        ).aggregate(
            total=Sum('balance')
        )['total'] or 0
        
        # Calculate total receivables (sum of all unpaid customer dues)
        # Regular deliveries with unpaid balance
        regular_receivables = Delivery.objects.filter(
            total_amount__gt=F('received_amount')
        ).annotate(
            balance=F('total_amount') - F('received_amount')
        ).aggregate(
            total=Sum('balance')
        )['total'] or 0
        
        # Concrete deliveries with unpaid balance
        concrete_receivables = ConcreteDelivery.objects.filter(
            total_amount__gt=F('received_amount')
        ).annotate(
            balance=F('total_amount') - F('received_amount')
        ).aggregate(
            total=Sum('balance')
        )['total'] or 0
        
        # Total receivables
        total_receivables = regular_receivables + concrete_receivables
        
        # Calculate overdue receivables (deliveries with due date < today and unpaid balance)
        regular_overdue = Delivery.objects.filter(
            due_date__lt=today,
            total_amount__gt=F('received_amount')
        ).annotate(
            balance=F('total_amount') - F('received_amount')
        ).aggregate(
            total=Sum('balance')
        )['total'] or 0
        
        concrete_overdue = ConcreteDelivery.objects.filter(
            due_date__lt=today,
            total_amount__gt=F('received_amount')
        ).annotate(
            balance=F('total_amount') - F('received_amount')
        ).aggregate(
            total=Sum('balance')
        )['total'] or 0
        
        overdue_receivables = regular_overdue + concrete_overdue
        
        # Get upcoming supplier payments (due within 7 days)
        upcoming_payments = SupplierPayment.objects.filter(
            payment_mode='credit',
            due_date__gte=today,
            due_date__lte=seven_days_later
        )
        upcoming_payments_count = upcoming_payments.count()
        
        # Get materials with low inventory (stock below reorder level)
        low_inventory_materials = Material.objects.filter(
            current_stock__lte=F('reorder_level')
        ).order_by('current_stock')
        low_inventory_count = low_inventory_materials.count()
        
        # Get top 5 suppliers by volume in past 30 days
        top_suppliers = Supplier.objects.filter(
            purchases__date__gte=thirty_days_ago
        ).annotate(
            total_volume=Sum('purchases__total_amount'),
            order_count=Count('purchases'),
            avg_order=Avg('purchases__total_amount')
        ).filter(
            total_volume__gt=0
        ).order_by('-total_volume')[:5]
        
        # Get raw materials used by grade over past 30 days
        
        # First get all concrete deliveries in the past 30 days
        concrete_deliveries = ConcreteDelivery.objects.filter(
            delivery_date__gte=thirty_days_ago,
            delivery_date__lte=today,
            inventory_deducted=True
        ).values('grade').annotate(
            total_quantity=Sum('quantity')
        ).order_by('grade')
        
        # Prepare data for the materials used chart
        materials_used_data = {}
        grades = []
        materials = []
        
        # Get unique materials and grades used in mix ratios
        all_mix_ratios = MixRatio.objects.select_related('material').all()
        unique_materials = set(mr.material.name for mr in all_mix_ratios)
        unique_grades = set(mr.grade for mr in all_mix_ratios)
        
        # Initialize the materials_used_data dictionary
        for material_name in unique_materials:
            materials_used_data[material_name] = {grade: 0 for grade in unique_grades}
            materials.append(material_name)
        
        for grade in unique_grades:
            grades.append(grade)
        
        # Calculate material usage by grade
        for delivery in concrete_deliveries:
            grade = delivery['grade']
            quantity = delivery['total_quantity']
            
            # Get mix ratios for this grade
            mix_ratios = MixRatio.objects.filter(grade=grade).select_related('material')
            
            for mix_ratio in mix_ratios:
                material_name = mix_ratio.material.name
                used_quantity = mix_ratio.qty_per_m3 * quantity
                materials_used_data[material_name][grade] += float(used_quantity)
        
        # Calculate total order value including concrete deliveries
        top_customers = Customer.objects.filter(
            Q(deliveries__date__gte=ninety_days_ago) | 
            Q(concrete_deliveries__delivery_date__gte=ninety_days_ago)
        ).annotate(
            regular_order_value=Sum('deliveries__total_amount', filter=Q(deliveries__date__gte=ninety_days_ago), default=0),
            concrete_order_value=Sum('concrete_deliveries__total_amount', filter=Q(concrete_deliveries__delivery_date__gte=ninety_days_ago), default=0),
            total_orders=Case(
                When(regular_order_value__gt=0, concrete_order_value__gt=0, then=F('regular_order_value') + F('concrete_order_value')),
                When(regular_order_value__gt=0, then=F('regular_order_value')),
                When(concrete_order_value__gt=0, then=F('concrete_order_value')),
                default=0,
                output_field=DecimalField()
            ),
            order_count=Count('deliveries', filter=Q(deliveries__date__gte=ninety_days_ago)) + 
                        Count('concrete_deliveries', filter=Q(concrete_deliveries__delivery_date__gte=ninety_days_ago))
        ).filter(
            total_orders__gt=0
        ).order_by('-total_orders')[:5]
        
        # Calculate total sales in the last 30 days (include both regular and concrete deliveries)
        regular_sales = Delivery.objects.filter(
            date__gte=thirty_days_ago,
            date__lte=today
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # For concrete deliveries, use the actual total_amount from the records
        concrete_sales = ConcreteDelivery.objects.filter(
            delivery_date__gte=thirty_days_ago,
            delivery_date__lte=today
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Get concrete delivery quantity for informational purposes
        concrete_deliveries_count = ConcreteDelivery.objects.filter(
            delivery_date__gte=thirty_days_ago,
            delivery_date__lte=today
        ).aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0
        
        # Total sales = regular + concrete
        total_sales = regular_sales + concrete_sales
        
        # Serialize the data for JavaScript
        materials_used_data_json = json.dumps(materials_used_data)
        materials_json = json.dumps(list(materials))
        grades_json = json.dumps(list(grades))
        
        context.update({
            'total_payables': total_payables,
            'total_receivables': total_receivables,
            'overdue_receivables': overdue_receivables,
            'upcoming_payments_count': upcoming_payments_count,
            'low_inventory_count': low_inventory_count,
            'low_inventory_materials': low_inventory_materials,
            'top_suppliers': top_suppliers,
            'materials_used_data': materials_used_data_json,
            'materials': materials_json,
            'grades': grades_json,
            'top_customers': top_customers,
            'thirty_days_ago': thirty_days_ago,
            'ninety_days_ago': ninety_days_ago,
            'total_sales': total_sales,
            'regular_sales': regular_sales,
            'concrete_sales': concrete_sales,
            'concrete_deliveries_count': concrete_deliveries_count,
            'smart_summary_url': '/materials/dashboard/',
        })
        
        return context


# API Views
class PurchaseOrderDetailsAPIView(LoginRequiredMixin, View):
    """API endpoint to get purchase order details including payment information"""
    
    def get(self, request, pk):
        try:
            # Get the purchase order
            purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
            
            # Calculate total paid
            total_paid = sum(payment.amount_paid for payment in purchase_order.supplier_payments.all())
            
            # Format the response data
            data = {
                'id': purchase_order.id,
                'purchase_date': purchase_order.purchase_date.strftime('%Y-%m-%d'),
                'due_date': purchase_order.due_date.strftime('%Y-%m-%d') if purchase_order.due_date else None,
                'total_amount': float(purchase_order.total_amount),
                'amount_paid': float(total_paid),
                'balance': float(purchase_order.balance),
                'payment_status': purchase_order.payment_status,
                'supplier': {
                    'id': purchase_order.supplier.id,
                    'name': purchase_order.supplier.name
                }
            }
            
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
