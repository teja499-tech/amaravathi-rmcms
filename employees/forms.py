from django import forms
from django.utils import timezone
from datetime import timedelta, date, datetime
from .models import Employee, SalaryRecord


class MonthField(forms.DateField):
    """Custom form field for month selection (YYYY-MM)"""
    
    def to_python(self, value):
        """Convert the string input value to a date object"""
        if value in self.empty_values:
            return None
        
        try:
            # Handle string input from the month picker (YYYY-MM)
            if isinstance(value, str) and len(value.split('-')) == 2:
                year, month = value.split('-')
                return date(int(year), int(month), 1)
            # If it's already a date object
            elif hasattr(value, 'year') and hasattr(value, 'month'):
                return date(value.year, value.month, 1)
        except (ValueError, TypeError):
            pass
            
        raise forms.ValidationError("Enter a valid month (YYYY-MM)")


class EmployeeForm(forms.ModelForm):
    """Form for creating and updating employees."""
    
    class Meta:
        model = Employee
        fields = [
            'name', 'phone', 'role', 'salary_amount', 
            'salary_due_day', 'payment_cycle', 'join_date', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'salary_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'salary_due_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '31'}),
            'payment_cycle': forms.Select(attrs={'class': 'form-select'}),
            'join_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EmployeeFilterForm(forms.Form):
    """Form for filtering employees."""
    role = forms.ChoiceField(
        choices=[('', 'All Roles')] + list(Employee.ROLE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'All Status'),
            ('active', 'Active'),
            ('inactive', 'Inactive'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name or phone'})
    )


class SalaryRecordForm(forms.ModelForm):
    """Form for creating and updating salary records."""
    
    # Override the month field with our custom MonthField
    month = MonthField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'month',
            'placeholder': 'YYYY-MM'
        })
    )
    
    class Meta:
        model = SalaryRecord
        fields = ['employee', 'month', 'amount', 'is_paid', 'payment_date', 'due_date', 'remarks']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If it's a new form (not an update)
        if not kwargs.get('instance'):
            # Set default month to first day of current month
            today = timezone.now().date()
            first_day = today.replace(day=1)
            self.fields['month'].initial = first_day
            
            # The due_date field is no longer required as it will be auto-calculated
            # based on the employee's settings when the form is saved
            self.fields['due_date'].required = False
            
        # Make payment_date required if is_paid is checked
        if self.data.get('is_paid') in ['on', 'true', 'True', '1']:
            self.fields['payment_date'].required = True
        else:
            self.fields['payment_date'].required = False
            
        # Make employee field a queryset of only active employees by default
        self.fields['employee'].queryset = Employee.objects.filter(is_active=True)
        
        # Add help text for month field
        self.fields['month'].help_text = "Select the month and year (will be converted to first day of month)"

    def clean_month(self):
        """Ensure the month field is always set to the first day of the month."""
        month_date = self.cleaned_data.get('month')
        if month_date and isinstance(month_date, date):
            # Just in case, ensure it's the first day of the month
            return month_date.replace(day=1)
        return month_date

    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee')
        month = cleaned_data.get('month')
        
        # If both employee and month are provided but due_date is not
        if employee and month and not cleaned_data.get('due_date'):
            import calendar
            from datetime import timedelta
            
            # Calculate due_date based on employee settings
            if employee.payment_cycle == 'monthly':
                due_day = min(employee.salary_due_day, 
                             calendar.monthrange(month.year, month.month)[1])
                cleaned_data['due_date'] = month.replace(day=due_day)
            elif employee.payment_cycle == 'weekly':
                cleaned_data['due_date'] = month + timedelta(days=7)
        
        return cleaned_data


class SalaryRecordFilterForm(forms.Form):
    """Form for filtering salary records."""
    
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        required=False,
        empty_label="All Employees",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'All Status'),
            ('paid', 'Paid'),
            ('pending', 'Pending'),
            ('overdue', 'Overdue'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    from_month = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    to_month = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active employees by default in the filter
        self.fields['employee'].queryset = Employee.objects.filter(is_active=True)


class BulkSalaryPaymentForm(forms.Form):
    """Form for selecting a month to process bulk salary payments."""
    
    month = MonthField(
        label="Select Month",
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'month',
            'placeholder': 'YYYY-MM',
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default month to current month
        today = timezone.now().date()
        current_month = today.replace(day=1)
        self.fields['month'].initial = current_month


class SalaryPaymentUpdateForm(forms.Form):
    """Form for updating multiple salary payments at once."""
    
    payment_date = forms.DateField(
        label="Payment Date",
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date',
        }),
        initial=timezone.now().date()
    )
    
    remarks = forms.CharField(
        label="Remarks",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Optional remarks for these payments'
        })
    )
    
    selected_records = forms.MultipleChoiceField(
        label="",
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        })
    )
    
    def __init__(self, salary_records=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if salary_records:
            # Create choices for the salary records
            choices = [(record.id, f"{record.employee.name} - ₹{record.amount}") 
                      for record in salary_records]
            self.fields['selected_records'].choices = choices 