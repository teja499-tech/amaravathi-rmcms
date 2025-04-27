from django.contrib import admin
from .models import Employee, SalaryRecord


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'phone', 'salary_amount', 'join_date', 'is_active')
    list_filter = ('is_active', 'role', 'join_date')
    search_fields = ('name', 'phone')
    date_hierarchy = 'join_date'
    ordering = ('name',)
    

@admin.register(SalaryRecord)
class SalaryRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'month', 'amount', 'is_paid', 'payment_date', 'due_date', 'is_overdue')
    list_filter = ('is_paid', 'month', 'employee')
    search_fields = ('employee__name', 'remarks')
    date_hierarchy = 'month'
    raw_id_fields = ('employee',)
    readonly_fields = ('is_overdue',)
    
    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue?'
