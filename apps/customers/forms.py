from django import forms
from .models import Customer, Delivery, CustomerPayment, ConcreteDelivery, MixRatio
from django.db.models import F
from apps.materials.models import Material

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['customer', 'invoice_number', 'date', 'total_amount', 'received_amount', 'due_date', 'notes']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control', 'id': 'id_customer'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_invoice_number'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_date'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_total_amount'}),
            'received_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_received_amount'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_due_date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'id': 'id_notes'}),
        }

class UnifiedDeliveryForm(forms.Form):
    # Delivery type choice field
    delivery_type = forms.ChoiceField(
        choices=[('regular', 'Regular Delivery'), ('concrete', 'Concrete Delivery')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='regular',
        required=True
    )
    
    # Common fields for both delivery types
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    
    total_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        required=True
    )
    
    received_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        initial=0,
        required=False
    )
    
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    
    # Fields specific to concrete delivery
    grade = forms.ChoiceField(
        choices=ConcreteDelivery.GRADE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    quantity = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        required=False,
        help_text="Quantity in cubic meters (m³)"
    )
    
    site_location = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    inventory_deducted = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Notes/remarks field (common but with different names in models)
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )
    
    delivery_note_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        
        # If we're editing an existing instance, initialize the form values
        if self.instance:
            if isinstance(self.instance, Delivery):
                self.fields['delivery_type'].initial = 'regular'
                self.fields['customer'].initial = self.instance.customer.id
                self.fields['date'].initial = self.instance.date
                self.fields['total_amount'].initial = self.instance.total_amount
                self.fields['received_amount'].initial = self.instance.received_amount
                self.fields['due_date'].initial = self.instance.due_date
                self.fields['notes'].initial = self.instance.notes
            
            elif isinstance(self.instance, ConcreteDelivery):
                self.fields['delivery_type'].initial = 'concrete'
                self.fields['customer'].initial = self.instance.customer.id
                self.fields['date'].initial = self.instance.delivery_date
                self.fields['total_amount'].initial = self.instance.total_amount
                self.fields['received_amount'].initial = self.instance.received_amount
                self.fields['due_date'].initial = self.instance.due_date
                self.fields['grade'].initial = self.instance.grade
                self.fields['quantity'].initial = self.instance.quantity
                self.fields['site_location'].initial = self.instance.site_location
                self.fields['notes'].initial = self.instance.remarks
                self.fields['inventory_deducted'].initial = self.instance.inventory_deducted
    
    def clean(self):
        cleaned_data = super().clean()
        delivery_type = cleaned_data.get('delivery_type')
        
        # Validate required fields based on delivery type
        if delivery_type == 'concrete':
            grade = cleaned_data.get('grade')
            quantity = cleaned_data.get('quantity')
            site_location = cleaned_data.get('site_location')
            
            if not grade:
                self.add_error('grade', 'Concrete grade is required for concrete deliveries')
            
            if not quantity:
                self.add_error('quantity', 'Quantity is required for concrete deliveries')
            
            if not site_location:
                self.add_error('site_location', 'Site location is required for concrete deliveries')
                
            # Check if this concrete grade is valid and has mix ratios
            if grade and quantity:
                mix_ratios = MixRatio.objects.filter(grade=grade)
                if mix_ratios.exists():
                    # Validate material availability
                    insufficient_materials = []
                    for ratio in mix_ratios:
                        material = ratio.material
                        required_qty = ratio.qty_per_m3 * float(quantity)
                        
                        if material.current_stock < required_qty:
                            insufficient_materials.append(
                                f"{material.name}: Need {required_qty:.2f} {material.unit}, " +
                                f"Have {material.current_stock:.2f} {material.unit}"
                            )
                    
                    if insufficient_materials and not cleaned_data.get('inventory_deducted'):
                        self.add_error(None, f"Insufficient materials for this delivery: {', '.join(insufficient_materials)}")
        
        return cleaned_data
    
    def generate_invoice_number(self, delivery_type):
        """
        Generate a unique invoice number based on delivery type and current date
        Format: RD/YY/MM/NNNN for regular deliveries, CD/YY/MM/NNNN for concrete
        """
        from datetime import datetime
        
        today = datetime.now()
        year_short = today.strftime("%y")
        month = today.strftime("%m")
        
        prefix = "RD" if delivery_type == 'regular' else "CD"
        
        # Find the highest invoice number with the same prefix for the current month
        if delivery_type == 'regular':
            latest_deliveries = Delivery.objects.filter(
                invoice_number__startswith=f"{prefix}/{year_short}/{month}/"
            ).order_by('-invoice_number')
        else:
            latest_deliveries = ConcreteDelivery.objects.filter(
                invoice_number__startswith=f"{prefix}/{year_short}/{month}/"
            ).order_by('-invoice_number')
        
        if latest_deliveries.exists():
            try:
                # Extract the sequence number from the latest invoice
                latest_invoice = latest_deliveries.first().invoice_number
                sequence_number = int(latest_invoice.split('/')[-1]) + 1
            except (ValueError, IndexError):
                # If parsing fails, start with 1
                sequence_number = 1
        else:
            # No invoices for this month yet
            sequence_number = 1
        
        # Format: RD/YY/MM/NNNN or CD/YY/MM/NNNN
        return f"{prefix}/{year_short}/{month}/{sequence_number:04d}"
    
    def save(self, commit=True):
        delivery_type = self.cleaned_data.get('delivery_type')
        
        if delivery_type == 'regular':
            if self.instance and isinstance(self.instance, Delivery):
                # Update existing regular delivery
                delivery = self.instance
            else:
                # Create new regular delivery
                delivery = Delivery()
                # Generate invoice number for new entries only
                delivery.invoice_number = self.generate_invoice_number('regular')
            
            delivery.customer = self.cleaned_data.get('customer')
            # Only set invoice_number for new deliveries, keep existing for updates
            if not self.instance:
                delivery.invoice_number = self.generate_invoice_number('regular')
            delivery.date = self.cleaned_data.get('date')
            delivery.total_amount = self.cleaned_data.get('total_amount')
            delivery.received_amount = self.cleaned_data.get('received_amount', 0)
            delivery.due_date = self.cleaned_data.get('due_date')
            delivery.notes = self.cleaned_data.get('notes')
            
            if commit:
                delivery.save()
            return delivery
        
        else:  # concrete delivery
            if self.instance and isinstance(self.instance, ConcreteDelivery):
                # Update existing concrete delivery
                delivery = self.instance
            else:
                # Create new concrete delivery
                delivery = ConcreteDelivery()
                # Generate invoice number for new entries only
                delivery.invoice_number = self.generate_invoice_number('concrete')
            
            delivery.customer = self.cleaned_data.get('customer')
            # Only set invoice_number for new deliveries, keep existing for updates
            if not self.instance:
                delivery.invoice_number = self.generate_invoice_number('concrete')
            delivery.delivery_date = self.cleaned_data.get('date')
            delivery.total_amount = self.cleaned_data.get('total_amount')
            delivery.received_amount = self.cleaned_data.get('received_amount', 0)
            delivery.due_date = self.cleaned_data.get('due_date')
            delivery.grade = self.cleaned_data.get('grade')
            delivery.quantity = self.cleaned_data.get('quantity')
            delivery.site_location = self.cleaned_data.get('site_location')
            delivery.remarks = self.cleaned_data.get('notes')
            delivery.inventory_deducted = self.cleaned_data.get('inventory_deducted', False)
            
            if commit:
                delivery.save()
                
                # Handle file upload if provided
                delivery_note_file = self.cleaned_data.get('delivery_note_file')
                if delivery_note_file:
                    delivery.upload_delivery_note(delivery_note_file)
                
                # Deduct inventory if not already done
                if not delivery.inventory_deducted:
                    try:
                        delivery.deduct_inventory()
                    except Exception as e:
                        pass  # Handle inventory deduction errors gracefully
            
            return delivery

class CustomerPaymentForm(forms.ModelForm):
    class Meta:
        model = CustomerPayment
        fields = ['customer', 'delivery', 'concrete_delivery', 'amount_paid', 'payment_mode', 'payment_date', 'reference_number', 'due_date', 'remarks']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add a field to choose delivery type
        self.fields['delivery_type'] = forms.ChoiceField(
            choices=[('', '---------'), ('regular', 'Regular Delivery'), ('concrete', 'Concrete Delivery')],
            required=False,
            widget=forms.Select(attrs={'id': 'id_delivery_type', 'class': 'form-select'})
        )
        
        # Limit delivery choices to those with outstanding balance
        self.fields['delivery'].queryset = Delivery.objects.filter(
            total_amount__gt=F('received_amount')
        )
        
        # Limit concrete delivery choices to those with outstanding balance
        self.fields['concrete_delivery'].queryset = ConcreteDelivery.objects.filter(
            total_amount__gt=F('received_amount')
        )
        
        # Set initial delivery type if payment is being edited
        if self.instance.pk:
            if self.instance.delivery:
                self.initial['delivery_type'] = 'regular'
            elif self.instance.concrete_delivery:
                self.initial['delivery_type'] = 'concrete'
        
        # When a customer is selected, filter deliveries for that customer
        if self.data.get('customer'):
            try:
                customer_id = int(self.data.get('customer'))
                self.fields['delivery'].queryset = self.fields['delivery'].queryset.filter(
                    customer_id=customer_id
                )
                self.fields['concrete_delivery'].queryset = self.fields['concrete_delivery'].queryset.filter(
                    customer_id=customer_id
                )
            except (ValueError, TypeError):
                pass
        # If we're editing an existing payment
        elif self.instance.pk and self.instance.customer:
            self.fields['delivery'].queryset = Delivery.objects.filter(
                customer=self.instance.customer,
                total_amount__gt=F('received_amount')
            )
            self.fields['concrete_delivery'].queryset = ConcreteDelivery.objects.filter(
                customer=self.instance.customer,
                total_amount__gt=F('received_amount')
            )
            
            # If this payment is already linked to a delivery, include it even if balance is 0
            if self.instance.delivery:
                self.fields['delivery'].queryset = self.fields['delivery'].queryset | Delivery.objects.filter(pk=self.instance.delivery.pk)
            if self.instance.concrete_delivery:
                self.fields['concrete_delivery'].queryset = self.fields['concrete_delivery'].queryset | ConcreteDelivery.objects.filter(pk=self.instance.concrete_delivery.pk)
    
    def clean(self):
        cleaned_data = super().clean()
        payment_mode = cleaned_data.get('payment_mode')
        due_date = cleaned_data.get('due_date')
        delivery = cleaned_data.get('delivery')
        concrete_delivery = cleaned_data.get('concrete_delivery')
        
        # Check that both delivery types are not selected
        if delivery and concrete_delivery:
            self.add_error(None, "Please select either a regular delivery or a concrete delivery, not both.")
        
        # Check that credit payments have a due date
        if payment_mode == 'credit' and not due_date:
            self.add_error('due_date', 'Due date is required for credit payments')
            
        # Ensure payment amount doesn't exceed delivery balance
        amount_paid = cleaned_data.get('amount_paid')
        
        if delivery and amount_paid:
            # If editing, exclude current payment from calculation
            if self.instance.pk and self.instance.delivery == delivery:
                existing_payment = self.instance.amount_paid
                max_amount = delivery.total_amount - delivery.received_amount + existing_payment
            else:
                # Calculate balance manually instead of using the property
                max_amount = delivery.total_amount - delivery.received_amount
                
            if amount_paid > max_amount:
                self.add_error('amount_paid', f'Payment amount cannot exceed the remaining balance of {max_amount}')
        
        if concrete_delivery and amount_paid:
            # If editing, exclude current payment from calculation
            if self.instance.pk and self.instance.concrete_delivery == concrete_delivery:
                existing_payment = self.instance.amount_paid
                max_amount = concrete_delivery.total_amount - concrete_delivery.received_amount + existing_payment
            else:
                # Calculate balance manually instead of using the property
                max_amount = concrete_delivery.total_amount - concrete_delivery.received_amount
                
            if amount_paid > max_amount:
                self.add_error('amount_paid', f'Payment amount cannot exceed the remaining balance of {max_amount}')
                
        return cleaned_data 