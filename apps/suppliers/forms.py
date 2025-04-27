from django import forms
from django.db.models import F
from .models import SupplierPayment, Purchase, Supplier
from apps.materials.models import PurchaseOrder
from django.utils import timezone


class PurchaseForm(forms.ModelForm):
    """
    Form for recording purchases from suppliers
    """
    due_date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text="Optional: Leave blank if no credit terms"
    )
    
    class Meta:
        model = Purchase
        fields = ['supplier', 'invoice_number', 'date', 'total_amount', 'paid_amount', 
                  'due_date', 'notes', 'invoice_file']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default date to today
        self.fields['date'].initial = timezone.localdate()
        
        # Ensure date input has proper attributes
        self.fields['due_date'].widget.attrs.update({'type': 'date', 'class': 'form-control'})


class SupplierPaymentForm(forms.ModelForm):
    """
    Form for recording payments to suppliers
    """
    class Meta:
        model = SupplierPayment
        fields = ['supplier', 'purchase_order', 'amount_paid', 'payment_mode', 'payment_date', 'reference_number', 'remarks']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        # If we have a purchase ID, pre-select it and its supplier
        purchase_id = kwargs.pop('purchase_id', None)
        supplier_id = kwargs.pop('supplier_id', None)
        
        super().__init__(*args, **kwargs)
        
        # Set all form fields to use proper Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
        
        # Set default date to today
        self.fields['payment_date'].initial = timezone.localdate()
        
        # Update field for PurchaseOrder instead of Purchase
        self.fields['purchase_order'].queryset = PurchaseOrder.objects.filter(
            inventory_updated=True
        ).order_by('-purchase_date')
        
        # If we have a purchase, filter and pre-select
        if purchase_id:
            try:
                purchase_order = PurchaseOrder.objects.get(pk=purchase_id)
                self.fields['purchase_order'].initial = purchase_order
                self.fields['supplier'].initial = purchase_order.supplier
                
                # Show amount remaining as initial value
                # Since PurchaseOrder doesn't have paid_amount/balance, use the total as initial
                self.fields['amount_paid'].help_text = f"Order amount: ₹{purchase_order.total_amount}"
                self.fields['amount_paid'].initial = purchase_order.total_amount
                
                # Disable changing the purchase order and supplier
                self.fields['purchase_order'].widget.attrs['readonly'] = True
                self.fields['supplier'].widget.attrs['readonly'] = True
                
            except PurchaseOrder.DoesNotExist:
                pass
        
        # If we only have supplier ID, pre-select it and filter purchase orders
        elif supplier_id:
            try:
                supplier = Supplier.objects.get(pk=supplier_id)
                self.fields['supplier'].initial = supplier
                self.fields['purchase_order'].queryset = PurchaseOrder.objects.filter(
                    supplier=supplier,
                    inventory_updated=True
                ).order_by('-purchase_date')
            except Supplier.DoesNotExist:
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        purchase_order = cleaned_data.get('purchase_order')
        supplier = cleaned_data.get('supplier')
        amount_paid = cleaned_data.get('amount_paid')
        payment_mode = cleaned_data.get('payment_mode')
        due_date = cleaned_data.get('due_date')
        
        # Ensure supplier matches purchase order
        if purchase_order and supplier and purchase_order.supplier != supplier:
            self.add_error('supplier', 'Supplier must match the purchase order supplier')
        
        # Validate amount paid - optionally allow overpayment
        if amount_paid and amount_paid < 0:
            self.add_error('amount_paid', 'Payment amount cannot be negative')
        
        # Validate due_date is required for credit payments
        if payment_mode == 'CREDIT' and not due_date:
            self.add_error('due_date', 'Due date is required for credit payments')
        
        return cleaned_data 