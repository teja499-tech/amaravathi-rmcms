from django import forms
from .models import CommitmentCategory, OperationalCommitment, CommitmentPayment

class CommitmentCategoryForm(forms.ModelForm):
    class Meta:
        model = CommitmentCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class OperationalCommitmentForm(forms.ModelForm):
    class Meta:
        model = OperationalCommitment
        fields = [
            'title', 'category', 'description', 'amount',
            'reference_number', 'start_date', 'end_date',
            'payment_frequency', 'payment_day', 'next_payment_date',
            'status', 'is_active',
            'payee_name', 'contact_person', 'contact_phone', 'contact_email',
            'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_frequency': forms.Select(attrs={'class': 'form-control'}),
            'payment_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'next_payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'payee_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CommitmentPaymentForm(forms.ModelForm):
    class Meta:
        model = CommitmentPayment
        fields = [
            'commitment', 'amount_paid', 'payment_date', 
            'payment_mode', 'reference_number', 'remarks',
            'receipt_number', 'receipt_file'
        ]
        widgets = {
            'commitment': forms.Select(attrs={'class': 'form-control'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_mode': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'receipt_number': forms.TextInput(attrs={'class': 'form-control'}),
            'receipt_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class CommitmentFilterForm(forms.Form):
    """
    Form for filtering operational commitments
    """
    category = forms.ModelChoiceField(
        queryset=CommitmentCategory.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_frequency = forms.ChoiceField(
        choices=(('', 'All Frequencies'),) + tuple(OperationalCommitment.FREQUENCY_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=(('', 'All Statuses'),) + tuple(OperationalCommitment.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    due_status = forms.ChoiceField(
        choices=(
            ('', 'All'),
            ('due_today', 'Due Today'),
            ('due_soon', 'Due Soon (7 Days)'),
            ('overdue', 'Overdue'),
        ),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by title, payee...'})
    ) 