from django import forms
from django.forms import widgets
from .models import Expense, Vehicle, ExpenseCategory
# from taggit.forms import TagField
from django.utils import timezone


class ExpenseFilterForm(forms.Form):
    """Form for filtering expenses"""
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    expense_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Expense.EXPENSE_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.filter(is_active=True),
        required=False,
        empty_label="All Vehicles",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date()
    )
    
    min_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min ₹'}),
    )
    
    max_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max ₹'}),
    )
    
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tags (comma separated)', 
            'data-role': 'tagsinput'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search descriptions, reference numbers, etc.'
        })
    )


class VehicleForm(forms.ModelForm):
    """Form for adding and editing vehicles"""
    class Meta:
        model = Vehicle
        fields = [
            'name', 'vehicle_type', 'registration_number',
            'make', 'model', 'year', 'purchase_date',
            'insurance_expiry', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'make': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'insurance_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ExpenseForm(forms.ModelForm):
    """Form for adding and editing expenses with enhanced tagging and relationship features"""
    
    bill_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text="Upload expense bill (PDF or image)"
    )
    
    class Meta:
        model = Expense
        fields = [
            'category', 'expense_type', 'amount', 'date', 'payment_method',
            'description', 'vehicle', 'material', 'associated_delivery',
            'receipt', 'reference_number'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'id_category'}),
            'expense_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_expense_type'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'material': forms.Select(attrs={'class': 'form-select'}),
            'associated_delivery': forms.Select(attrs={'class': 'form-select'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the initial date to today if creating a new expense
        if not kwargs.get('instance'):
            self.fields['date'].initial = timezone.now().date()
        
        # Filter vehicle queryset to only show active vehicles
        self.fields['vehicle'].queryset = Vehicle.objects.filter(is_active=True)
        
        # Filter category queryset to only show active categories
        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True)
        
        # Add Bootstrap classes to all fields by default
        for field_name, field in self.fields.items():
            if not hasattr(field.widget, 'attrs') or 'class' not in field.widget.attrs:
                if hasattr(field.widget, 'attrs'):
                    field.widget.attrs['class'] = 'form-control'
        
        # Make the following fields not required
        for field_name in ['vehicle', 'material', 'associated_delivery', 'receipt', 'reference_number']:
            self.fields[field_name].required = False
            
        # Add support for dynamically showing/hiding fields based on expense_type
        self.fields['vehicle'].widget.attrs.update({'data-expense-type': 'vehicle,fuel'})
        self.fields['material'].widget.attrs.update({'data-expense-type': 'materials'})
        self.fields['associated_delivery'].widget.attrs.update({'data-expense-type': 'vehicle,materials'})
        
        # Show bill file field with link to existing file if editing and file exists
        if kwargs.get('instance') and kwargs['instance'].bill_url:
            self.fields['bill_file'].help_text = f'<a href="{kwargs["instance"].bill_url}" target="_blank">View current bill</a> (upload a new file to replace it)'
            self.fields['bill_file'].widget.attrs.update({'class': 'form-control mt-2'}) 