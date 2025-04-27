from django.contrib import admin
from .models import ExpenseCategory, Expense, Salary, Vehicle


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_type', 'is_active', 'description')
    list_filter = ('default_type', 'is_active')
    search_fields = ('name',)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('name', 'registration_number', 'vehicle_type', 'make', 'purchase_date', 'is_active')
    list_filter = ('vehicle_type', 'is_active')
    search_fields = ('name', 'registration_number', 'make')
    date_hierarchy = 'purchase_date'


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'expense_type', 'amount', 'date', 'payment_method', 'vehicle')
    list_filter = ('category', 'expense_type', 'date', 'payment_method', 'vehicle')
    search_fields = ('description', 'vehicle__name', 'reference_number')
    date_hierarchy = 'date'


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'amount', 'month', 'paid_on')
    list_filter = ('month', 'paid_on')
    search_fields = ('employee__username', 'employee__first_name', 'employee__last_name')
    date_hierarchy = 'month' 