from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.core.models import BaseModel
from django.contrib.postgres.fields import ArrayField
from apps.materials.models import Material
from apps.customers.models import Delivery
from apps.core.utils.storage import upload_to_supabase, get_file_from_supabase, delete_file_from_supabase
# from taggit.managers import TaggableManager


class ExpenseCategory(BaseModel):
    """
    Model for expense categories.
    """
    TYPE_CHOICES = [
        ('vehicle', 'Vehicle'),
        ('fuel', 'Fuel'),
        ('office', 'Office'),
        ('materials', 'Materials'),
        ('maintenance', 'Maintenance'),
        ('utilities', 'Utilities'),
        ('rent', 'Rent'),
        ('salary', 'Salary'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    default_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Expense Categories'


class Vehicle(BaseModel):
    """
    Model for company vehicles.
    """
    VEHICLE_TYPE_CHOICES = [
        ('truck', 'Truck'),
        ('mixer', 'Concrete Mixer'),
        ('car', 'Car'),
        ('bike', 'Bike'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100, help_text="Name or identifier of the vehicle")
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES)
    registration_number = models.CharField(max_length=20, unique=True)
    make = models.CharField(max_length=50, blank=True, null=True, help_text="Manufacturer of the vehicle")
    model = models.CharField(max_length=50, blank=True, null=True, help_text="Model of the vehicle")
    year = models.PositiveIntegerField(blank=True, null=True, help_text="Manufacturing year")
    purchase_date = models.DateField(blank=True, null=True)
    insurance_expiry = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.registration_number})"
    
    class Meta:
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
        ordering = ['name']


class Expense(BaseModel):
    """
    Model for expenses with enhanced tracking for vehicles and materials.
    """
    EXPENSE_TYPE_CHOICES = [
        ('vehicle', 'Vehicle'),
        ('fuel', 'Fuel'),
        ('office', 'Office'),
        ('materials', 'Materials'),
        ('maintenance', 'Maintenance'),
        ('utilities', 'Utilities'),
        ('rent', 'Rent'),
        ('salary', 'Salary'),
        ('other', 'Other'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque'),
    ]
    
    # Basic expense information
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='expenses')
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    description = models.TextField(blank=True, null=True)
    
    # Optional relationships
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, related_name='expenses', 
                              blank=True, null=True, help_text="Related vehicle (if applicable)")
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, related_name='expenses',
                              blank=True, null=True, help_text="Related material (if applicable)")
    associated_delivery = models.ForeignKey(Delivery, on_delete=models.SET_NULL, related_name='expenses',
                                         blank=True, null=True, help_text="Associated delivery (if applicable)")
    
    # Receipt and reference information
    receipt = models.FileField(upload_to='expense_receipts', blank=True, null=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True, 
                                     help_text="Invoice or reference number")
    
    # Supabase file storage fields
    bill_url = models.URLField(blank=True, null=True, help_text="URL to the expense bill in Supabase Storage")
    bill_file_path = models.CharField(max_length=255, blank=True, null=True, 
                                    help_text="Path to the expense bill in Supabase Storage")
    
    # Tags for granular classification
    # tags = TaggableManager(blank=True, help_text="Tags to classify expenses (e.g., diesel, repairs, spares)")
    
    def __str__(self):
        base_str = f"{self.category.name} - ₹{self.amount} - {self.date}"
        if self.vehicle:
            return f"{base_str} - {self.vehicle.name}"
        return base_str
        
    def upload_bill_to_supabase(self, file):
        """
        Upload the expense bill to Supabase storage
        """
        if not file:
            return None
            
        # Determine the folder based on category or vehicle
        folder = "expense-bills"
        if self.vehicle:
            folder = f"expense-bills/vehicle/{self.vehicle.id}"
        elif self.expense_type:
            folder = f"expense-bills/{self.expense_type}"
        else:
            folder = f"expense-bills/category/{self.category.id}"
            
        # Upload file to Supabase
        result = upload_to_supabase(
            file=file,
            folder=folder
        )
        
        if result.get('success'):
            self.bill_url = result.get('public_url')
            self.bill_file_path = result.get('path')
            self.save(update_fields=['bill_url', 'bill_file_path'])
            return result
        return None
        
    def get_bill_url(self):
        """
        Get the expense bill URL from Supabase
        """
        if not self.bill_file_path:
            return None
            
        # Refresh the URL from Supabase (in case it changed)
        result = get_file_from_supabase(path=self.bill_file_path)
        if result.get('success'):
            self.bill_url = result.get('public_url')
            self.save(update_fields=['bill_url'])
        return self.bill_url
        
    def delete_bill_from_supabase(self):
        """
        Delete the expense bill from Supabase
        """
        if not self.bill_file_path:
            return None
            
        result = delete_file_from_supabase(path=self.bill_file_path)
        if result.get('success'):
            self.bill_url = None
            self.bill_file_path = None
            self.save(update_fields=['bill_url', 'bill_file_path'])
        return result
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'


class Salary(BaseModel):
    """
    Model for employee salaries.
    """
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='salaries')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.DateField()  # Use the first day of the month
    paid_on = models.DateField()
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.employee.username} - {self.amount} - {self.month.strftime('%B %Y')}"
    
    class Meta:
        verbose_name_plural = 'Salaries' 