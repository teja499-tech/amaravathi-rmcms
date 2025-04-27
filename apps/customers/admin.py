from django.contrib import admin
from .models import Customer, Delivery


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'is_active')
    search_fields = ('name', 'phone', 'email')
    list_filter = ('is_active',)


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'date', 'total_amount', 'received_amount', 'balance')
    search_fields = ('invoice_number', 'customer__name')
    list_filter = ('date',)
    date_hierarchy = 'date'
    readonly_fields = ('balance',) 