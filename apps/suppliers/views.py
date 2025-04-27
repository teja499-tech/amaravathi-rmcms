from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, RedirectView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q, F, Sum
from datetime import date
from django.views import View
import logging
from django.db import models

from .models import Supplier, Purchase, SupplierPayment
from apps.materials.models import PurchaseOrder
from apps.core.utils.storage import upload_to_supabase
from .forms import SupplierPaymentForm

logger = logging.getLogger(__name__)


class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    context_object_name = 'suppliers'
    template_name = 'suppliers/supplier_list.html'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Supplier.objects.all()
        search_query = self.request.GET.get('q')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(contact_person__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(gst_number__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    template_name = 'suppliers/supplier_form.html'
    fields = ['name', 'contact_person', 'phone', 'email', 'gst_number', 'address', 'is_active']
    success_url = reverse_lazy('suppliers:supplier_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Supplier added successfully.")
        return super().form_valid(form)


class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = 'suppliers/supplier_detail.html'
    context_object_name = 'supplier'


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    template_name = 'suppliers/supplier_form.html'
    fields = ['name', 'contact_person', 'phone', 'email', 'gst_number', 'address', 'is_active']
    
    def get_success_url(self):
        return reverse_lazy('suppliers:supplier_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, "Supplier information updated.")
        return super().form_valid(form)


class SupplierDeleteView(LoginRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'suppliers/supplier_confirm_delete.html'
    success_url = reverse_lazy('suppliers:supplier_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Supplier deleted successfully.")
        return super().delete(request, *args, **kwargs)


class PurchaseListView(LoginRequiredMixin, ListView):
    model = Purchase
    context_object_name = 'purchases'
    template_name = 'suppliers/purchase_list.html'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Purchase.objects.all()
        
        # Filter by search query
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search_query) |
                Q(supplier__name__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
        
        # Filter by supplier if specified
        supplier_id = self.request.GET.get('supplier')
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
            
        return queryset.order_by('-date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['suppliers'] = Supplier.objects.all().order_by('name')
        context['selected_supplier'] = self.request.GET.get('supplier', '')
        return context


class PurchaseCreateView(LoginRequiredMixin, CreateView):
    model = Purchase
    template_name = 'suppliers/purchase_form.html'
    fields = ['supplier', 'invoice_number', 'date', 'due_date', 'total_amount', 'paid_amount', 'notes', 'invoice_file']
    success_url = reverse_lazy('suppliers:purchase_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Handle file upload to Supabase if one was provided
        if self.request.FILES.get('invoice_file'):
            file = self.request.FILES['invoice_file']
            result = self.object.upload_invoice_file(file)
            
            if not result or not result.get('success'):
                messages.warning(self.request, "Purchase saved but file upload failed. Please try uploading the file again.")
        
        messages.success(self.request, "Purchase added successfully.")
        return response


class PurchaseDetailView(LoginRequiredMixin, DetailView):
    model = Purchase
    context_object_name = 'purchase'
    template_name = 'suppliers/purchase_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        purchase = self.get_object()
        context['payments'] = purchase.payments.all().order_by('-payment_date')
        context['today'] = date.today()
        return context


class PurchaseUpdateView(LoginRequiredMixin, UpdateView):
    model = Purchase
    template_name = 'suppliers/purchase_form.html'
    fields = ['supplier', 'invoice_number', 'date', 'due_date', 'total_amount', 'notes', 'invoice_file']
    
    def get_success_url(self):
        return reverse_lazy('suppliers:purchase_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Handle file upload to Supabase if one was provided
        if self.request.FILES.get('invoice_file'):
            # Delete previous file if exists
            if self.object.invoice_file_path:
                self.object.delete_invoice_file()
                
            # Upload new file
            file = self.request.FILES['invoice_file']
            result = self.object.upload_invoice_file(file)
            
            if not result or not result.get('success'):
                messages.warning(self.request, "Purchase updated but file upload failed. Please try uploading the file again.")
        
        messages.success(self.request, f"Purchase {self.object.invoice_number} updated successfully.")
        return response


class PurchaseDeleteView(LoginRequiredMixin, DeleteView):
    model = Purchase
    template_name = 'suppliers/purchase_confirm_delete.html'
    success_url = reverse_lazy('suppliers:purchase_list')
    
    def delete(self, request, *args, **kwargs):
        purchase = self.get_object()
        messages.success(request, f"Purchase {purchase.invoice_number} deleted successfully.")
        return super().delete(request, *args, **kwargs)


@login_required
@csrf_exempt
def test_file_upload(request):
    """
    A test view for uploading files to Supabase storage
    """
    if request.method == 'POST':
        if 'file' in request.FILES:
            file = request.FILES['file']
            
            try:
                # Upload the file to Supabase
                result = upload_to_supabase(file=file, folder='test_uploads')
                
                if result.get('success'):
                    return JsonResponse({
                        'success': True,
                        'message': 'File uploaded successfully',
                        'filename': result.get('filename'),
                        'path': result.get('path'),
                        'url': result.get('public_url')
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': f"Upload failed: {result.get('error')}"
                    }, status=400)
                    
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f"Upload failed: {str(e)}"
                }, status=500)
        else:
            return JsonResponse({
                'success': False, 
                'message': 'No file provided'
            }, status=400)
    
    # Render the upload form for GET requests
    return render(request, 'suppliers/test_upload.html')


# Payment Views
class SupplierPaymentListView(LoginRequiredMixin, ListView):
    model = SupplierPayment
    context_object_name = 'payments'
    template_name = 'suppliers/payment_list.html'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = SupplierPayment.objects.all()
        
        # Filter by supplier if specified
        supplier_id = self.request.GET.get('supplier')
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Filter by purchase order if specified
        purchase_id = self.request.GET.get('purchase')
        if purchase_id:
            queryset = queryset.filter(purchase_order_id=purchase_id)
            
        # Filter by payment mode if specified
        payment_mode = self.request.GET.get('mode')
        if payment_mode:
            queryset = queryset.filter(payment_mode=payment_mode)
            
        # Filter by date range if specified
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            queryset = queryset.filter(payment_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(payment_date__lte=end_date)
            
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['suppliers'] = Supplier.objects.all()
        context['payment_modes'] = dict(SupplierPayment.PAYMENT_MODES)
        
        # Add current filter values
        context['selected_supplier'] = self.request.GET.get('supplier', '')
        context['selected_purchase'] = self.request.GET.get('purchase', '')
        context['selected_mode'] = self.request.GET.get('mode', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        # Add today's date for overdue payment highlighting
        context['today'] = date.today()
        
        return context
        

class SupplierPaymentCreateView(LoginRequiredMixin, CreateView):
    model = SupplierPayment
    form_class = SupplierPaymentForm
    template_name = 'suppliers/payment_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass purchase_id if provided in URL
        purchase_id = self.kwargs.get('purchase_id')
        if purchase_id:
            kwargs['purchase_id'] = purchase_id
            
        # Pass supplier_id if provided in URL
        supplier_id = self.kwargs.get('supplier_id')
        if supplier_id:
            kwargs['supplier_id'] = supplier_id
            
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        purchase_id = self.kwargs.get('purchase_id')
        if purchase_id:
            try:
                # Try to find a PurchaseOrder first, then fallback to legacy Purchase model
                try:
                    context['purchase_order'] = PurchaseOrder.objects.get(pk=purchase_id)
                except PurchaseOrder.DoesNotExist:
                    # Try legacy Purchase model as fallback
                    context['purchase'] = Purchase.objects.get(pk=purchase_id)
            except Purchase.DoesNotExist:
                pass
                
        supplier_id = self.kwargs.get('supplier_id')
        if supplier_id:
            try:
                context['supplier'] = Supplier.objects.get(pk=supplier_id)
            except Supplier.DoesNotExist:
                pass
                
        return context
    
    def get_success_url(self):
        # If we came from a purchase, go back to it
        purchase_id = self.kwargs.get('purchase_id')
        if purchase_id:
            # Try to find a PurchaseOrder first, then fallback to legacy Purchase model
            try:
                purchase_order = PurchaseOrder.objects.get(pk=purchase_id)
                return reverse_lazy('materials:purchase_order_detail', kwargs={'pk': purchase_id})
            except PurchaseOrder.DoesNotExist:
                try:
                    Purchase.objects.get(pk=purchase_id)
                    return reverse_lazy('suppliers:purchase_detail', kwargs={'pk': purchase_id})
                except Purchase.DoesNotExist:
                    pass
            
        # If we came from a supplier, go back to it
        supplier_id = self.kwargs.get('supplier_id')
        if supplier_id:
            return reverse_lazy('suppliers:supplier_detail', kwargs={'pk': supplier_id})
            
        # Default: go to payment list
        return reverse_lazy('suppliers:payment_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Create success message
        messages.success(self.request, f"Payment of ₹{form.instance.amount_paid} to {form.instance.supplier.name} recorded successfully.")
        
        return response


class SupplierPaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = SupplierPayment
    form_class = SupplierPaymentForm
    template_name = 'suppliers/payment_form.html'
    
    def get_success_url(self):
        return reverse_lazy('suppliers:payment_list')
    
    def form_valid(self, form):
        # Store the original purchase order for comparison
        original_purchase = None
        if self.object.purchase_order:
            original_purchase = self.object.purchase_order
            
        response = super().form_valid(form)
        
        # If the purchase order changed, update both the old and new ones
        if original_purchase and original_purchase != self.object.purchase_order:
            original_purchase.update_paid_amount()
            
        # Add success message
        messages.success(self.request, "Payment updated successfully.")
        return response


class SupplierPaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = SupplierPayment
    template_name = 'suppliers/payment_confirm_delete.html'
    success_url = reverse_lazy('suppliers:payment_list')
    
    def delete(self, request, *args, **kwargs):
        payment = self.get_object()
        purchase = payment.purchase_order
        supplier = payment.supplier
        
        # Call the parent's delete method
        response = super().delete(request, *args, **kwargs)
        
        # Update the purchase paid amount if applicable
        if purchase:
            purchase.update_paid_amount()
            messages.success(
                request, 
                f"Payment of ₹{payment.amount_paid} deleted. "
                f"New balance for {purchase.invoice_number}: ₹{purchase.balance}"
            )
        else:
            messages.success(
                request,
                f"Payment of ₹{payment.amount_paid} to {supplier.name} deleted successfully."
            )
            
        return response


class SupplierLedgerView(LoginRequiredMixin, DetailView):
    """
    View for displaying a supplier's ledger (all payments and purchases)
    """
    model = Supplier
    template_name = 'suppliers/supplier_ledger.html'
    context_object_name = 'supplier'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supplier = self.get_object()
        
        # Set today's date for overdue checking
        context['today'] = date.today()
        
        # Get filter parameters
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        show_type = self.request.GET.get('show_type', 'all')
        
        # Get all purchases for this supplier with filters
        purchases = supplier.purchases.all()
        if date_from:
            purchases = purchases.filter(date__gte=date_from)
        if date_to:
            purchases = purchases.filter(date__lte=date_to)
        if show_type == 'unpaid':
            purchases = [p for p in purchases if p.payment_status != 'Paid']
        
        # Get all payments for this supplier with filters
        payments = supplier.payments.all()
        if date_from:
            payments = payments.filter(payment_date__gte=date_from)
        if date_to:
            payments = payments.filter(payment_date__lte=date_to)
        
        # Order by date
        purchases = purchases.order_by('-date')
        payments = payments.order_by('-payment_date')
        
        # Hide based on show_type
        if show_type == 'purchases':
            payments = payments.none()
        elif show_type == 'payments':
            purchases = purchases.none()
        
        context['purchases'] = purchases
        context['payments'] = payments
        
        # Calculate summary statistics
        total_purchased = sum(purchase.total_amount for purchase in purchases)
        total_paid = sum(payment.amount_paid for payment in payments)
        context['total_purchased'] = total_purchased
        context['total_paid'] = total_paid
        context['balance'] = total_purchased - total_paid
        
        return context 


class SupplierPaymentPriorityView(LoginRequiredMixin, ListView):
    """
    View for prioritizing supplier payments based on material criticality and stock levels
    """
    model = Purchase
    template_name = 'suppliers/payment_priority.html'
    context_object_name = 'due_purchases'
    
    def get_queryset(self):
        # Get purchases with balance > 0
        queryset = Purchase.objects.filter(total_amount__gt=models.F('paid_amount'))
        
        # Filter by supplier if specified
        supplier_id = self.request.GET.get('supplier')
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add suppliers for filtering
        context['suppliers'] = Supplier.objects.all()
        context['selected_supplier'] = self.request.GET.get('supplier', '')
        
        from apps.materials.models import Material, PurchaseItem, PurchaseOrder, InventoryEntry
        from django.db.models import Sum
        
        # Analyze each purchase and determine priority
        prioritized_purchases = []
        for purchase in context['due_purchases']:
            # Find materials purchased from this supplier
            purchase_orders = PurchaseOrder.objects.filter(supplier=purchase.supplier)
            
            # Get all materials from this supplier's purchase orders
            supplier_materials = {}
            critical_materials = []
            low_stock_materials = []
            
            for po in purchase_orders:
                items = PurchaseItem.objects.filter(purchase_order=po)
                for item in items:
                    material = item.material
                    
                    # Calculate stock status
                    stock_percent = 0
                    if material.reorder_level > 0:
                        stock_percent = (material.current_stock / material.reorder_level) * 100
                    
                    # Determine criticality
                    is_critical = False
                    is_low = False
                    
                    if stock_percent <= 25:  # Critical if less than 25% of reorder level
                        is_critical = True
                        critical_materials.append(material.name)
                    elif stock_percent <= 75:  # Low if less than 75% of reorder level
                        is_low = True
                        low_stock_materials.append(material.name)
                    
                    # Store in supplier materials dict
                    if material.id not in supplier_materials:
                        supplier_materials[material.id] = {
                            'name': material.name,
                            'current_stock': material.current_stock,
                            'reorder_level': material.reorder_level,
                            'stock_percent': stock_percent,
                            'is_critical': is_critical,
                            'is_low': is_low
                        }
            
            # Determine priority based on material criticality and stock levels
            priority = "Low"
            recommendation = "Delay Possible"
            
            if critical_materials:
                priority = "High"
                recommendation = "Urgent"
            elif low_stock_materials:
                priority = "Medium"
                recommendation = "Pay Soon"
            
            # Add to prioritized purchases
            prioritized_purchases.append({
                'purchase': purchase,
                'priority': priority,
                'recommendation': recommendation,
                'critical_materials': critical_materials,
                'low_stock_materials': low_stock_materials,
                'materials': supplier_materials
            })
        
        context['prioritized_purchases'] = prioritized_purchases
        context['today'] = date.today()
        
        return context 


# Add redirect view classes
class PurchaseRedirectView(RedirectView):
    """Redirect old purchase detail URLs to new purchase order detail URLs"""
    
    def get_redirect_url(self, *args, **kwargs):
        # Get the purchase ID from kwargs
        purchase_id = kwargs.get('pk')
        
        try:
            # Try to find the corresponding PurchaseOrder
            purchase_order = PurchaseOrder.objects.get(pk=purchase_id)
            return reverse('materials:purchase_order_detail', kwargs={'pk': purchase_order.pk})
        except PurchaseOrder.DoesNotExist:
            # Fallback to purchase list if purchase order doesn't exist
            messages.error(self.request, "The requested purchase order could not be found.")
            return reverse('materials:purchase_order_list')

class PurchaseUpdateRedirectView(RedirectView):
    """Redirect old purchase update URLs to new purchase order update URLs"""
    
    def get_redirect_url(self, *args, **kwargs):
        # Get the purchase ID from kwargs
        purchase_id = kwargs.get('pk')
        
        try:
            # Try to find the corresponding PurchaseOrder
            purchase_order = PurchaseOrder.objects.get(pk=purchase_id)
            return reverse('materials:purchase_order_update', kwargs={'pk': purchase_order.pk})
        except PurchaseOrder.DoesNotExist:
            # Fallback to purchase list if purchase order doesn't exist
            messages.error(self.request, "The requested purchase order could not be found.")
            return reverse('materials:purchase_order_list')

class PurchaseDeleteRedirectView(RedirectView):
    """Redirect old purchase delete URLs to new purchase order delete URLs"""
    
    def get_redirect_url(self, *args, **kwargs):
        # Get the purchase ID from kwargs
        purchase_id = kwargs.get('pk')
        
        try:
            # Try to find the corresponding PurchaseOrder
            purchase_order = PurchaseOrder.objects.get(pk=purchase_id)
            return reverse('materials:purchase_order_delete', kwargs={'pk': purchase_order.pk})
        except PurchaseOrder.DoesNotExist:
            # Fallback to purchase list if purchase order doesn't exist
            messages.error(self.request, "The requested purchase order could not be found.")
            return reverse('materials:purchase_order_list')

class SupplierPurchaseOrdersAPIView(View):
    """API View to get purchase orders for a specific supplier"""
    
    def get(self, request, supplier_id):
        try:
            # Validate supplier_id
            if not supplier_id:
                logger.warning("SupplierPurchaseOrdersAPIView: No supplier_id provided")
                return JsonResponse({'error': 'Supplier ID is required'}, status=400)
                
            # Check if supplier exists
            try:
                supplier = Supplier.objects.get(pk=supplier_id)
            except Supplier.DoesNotExist:
                logger.warning(f"SupplierPurchaseOrdersAPIView: Supplier with ID {supplier_id} not found")
                return JsonResponse({'error': f'Supplier with ID {supplier_id} not found'}, status=404)
                
            # Get purchase orders for the specified supplier
            purchase_orders = PurchaseOrder.objects.filter(
                supplier_id=supplier_id, 
                inventory_updated=True
            ).order_by('-purchase_date')
            
            logger.info(f"SupplierPurchaseOrdersAPIView: Found {purchase_orders.count()} purchase orders for supplier {supplier_id}")
            
            # Format data for the response
            purchase_orders_data = []
            for po in purchase_orders:
                try:
                    # Format the ID as PO-{id} for the invoice_number field
                    invoice_format = f'PO-{po.id}'
                    
                    po_data = {
                        'id': po.id,
                        'purchase_date': po.purchase_date.strftime('%Y-%m-%d'),
                        'total_amount': float(po.total_amount),
                        'invoice_number': invoice_format,
                        'inventory_updated': po.inventory_updated
                    }
                    purchase_orders_data.append(po_data)
                except Exception as e:
                    # Log the error but continue processing other POs
                    logger.error(f"Error processing purchase order {po.id}: {str(e)}")
            
            return JsonResponse({'purchase_orders': purchase_orders_data})
        except Exception as e:
            logger.error(f"Error in SupplierPurchaseOrdersAPIView: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400) 