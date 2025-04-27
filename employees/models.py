from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from apps.core.models import BaseModel
from django.db.models.signals import post_save
from django.dispatch import receiver


class Employee(BaseModel):
    """
    Model for storing employee information.
    """
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('supervisor', 'Supervisor'),
        ('worker', 'Worker'),
        ('driver', 'Driver'),
        ('accountant', 'Accountant'),
        ('admin', 'Admin Staff'),
        ('other', 'Other'),
    ]
    
    PAYMENT_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('weekly', 'Weekly'),
    ]
    
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    salary_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    join_date = models.DateField()
    is_active = models.BooleanField(default=True)
    salary_due_day = models.PositiveIntegerField(
        default=5,
        help_text="Day of the month (1-31) when salary is due",
        validators=[
            MinValueValidator(1),
            MaxValueValidator(31)
        ]
    )
    payment_cycle = models.CharField(
        max_length=10,
        choices=PAYMENT_CYCLE_CHOICES,
        default='monthly',
        help_text="Frequency of salary payments"
    )
    
    def __str__(self):
        return f"{self.name} - {self.role}"
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'


class SalaryRecord(BaseModel):
    """
    Model for tracking monthly salary records and payment status.
    """
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE,
        related_name='salary_records'
    )
    month = models.DateField(help_text="First day of the month")
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    remarks = models.TextField(blank=True, null=True, help_text="Notes about bonus or deductions")
    
    # Track the associated expense for this salary record
    expense_id = models.IntegerField(null=True, blank=True, 
                                    help_text="ID of the expense entry created for this salary")
    
    def __str__(self):
        payment_status = "Paid" if self.is_paid else "Pending"
        return f"{self.employee.name} - {self.month.strftime('%B %Y')} - {payment_status}"
    
    @property
    def is_overdue(self):
        """Check if the salary payment is overdue"""
        from django.utils import timezone
        return not self.is_paid and self.due_date < timezone.now().date()
    
    def create_or_update_expense(self):
        """
        Create or update an expense entry for this salary record.
        Only creates an expense if the salary is marked as paid.
        """
        if not self.is_paid or not self.payment_date:
            return None
            
        from apps.expenses.models import Expense, ExpenseCategory
        
        # Try to get the Salary expense category
        try:
            category = ExpenseCategory.objects.get(default_type='salary')
        except ExpenseCategory.DoesNotExist:
            # If it doesn't exist, create it
            category = ExpenseCategory.objects.create(
                name='Employee Salaries',
                default_type='salary',
                description='Salary payments to employees',
                is_active=True
            )
        
        expense_data = {
            'category': category,
            'expense_type': 'salary',
            'amount': self.amount,
            'date': self.payment_date,
            'payment_method': 'bank_transfer',  # Default to bank transfer, can be customized
            'description': f"Salary payment for {self.employee.name} - {self.month.strftime('%B %Y')}",
            'reference_number': f"Salary-{self.id}"
        }
        
        # If there's already an expense linked to this salary, update it
        if self.expense_id:
            try:
                expense = Expense.objects.get(id=self.expense_id)
                for key, value in expense_data.items():
                    setattr(expense, key, value)
                expense.save()
                return expense
            except Expense.DoesNotExist:
                # If the expense was deleted, create a new one
                pass
                
        # Create a new expense
        expense = Expense.objects.create(**expense_data)
        self.expense_id = expense.id
        # Save without triggering the save method again to avoid recursion
        SalaryRecord.objects.filter(id=self.id).update(expense_id=expense.id)
        return expense
    
    def save(self, *args, **kwargs):
        """
        Override save to auto-calculate due_date based on employee's settings
        if a due_date isn't already provided
        """
        import calendar
        from datetime import datetime, timedelta
        
        if not self.due_date:
            # Get the first day of the month
            first_day = self.month
            
            if self.employee.payment_cycle == 'monthly':
                # Calculate due date based on salary_due_day
                due_day = min(self.employee.salary_due_day, calendar.monthrange(first_day.year, first_day.month)[1])
                self.due_date = first_day.replace(day=due_day)
            elif self.employee.payment_cycle == 'weekly':
                # For weekly payments, due date is 7 days from the start of period
                self.due_date = first_day + timedelta(days=7)
        
        # Check if this is a new record or if is_paid status changed to True
        create_expense = False
        if self.pk:
            old_record = SalaryRecord.objects.get(pk=self.pk)
            if not old_record.is_paid and self.is_paid:
                create_expense = True
        elif self.is_paid:
            create_expense = True
            
        super().save(*args, **kwargs)
        
        # Create expense entry if needed
        if create_expense:
            self.create_or_update_expense()
    
    class Meta:
        ordering = ['-month', 'employee']
        verbose_name = 'Salary Record'
        verbose_name_plural = 'Salary Records'
        unique_together = ['employee', 'month']  # One salary record per employee per month


@receiver(post_save, sender=SalaryRecord)
def create_expense_for_salary(sender, instance, created, **kwargs):
    """
    Signal handler to create/update expense when a salary record is saved.
    """
    # This is a backup to ensure expenses are created even if the save method doesn't handle it
    if instance.is_paid and not instance.expense_id:
        instance.create_or_update_expense()
