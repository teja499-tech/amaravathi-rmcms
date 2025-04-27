from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Supplier, Purchase, SupplierPayment


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'gst_number', 'is_active')
    search_fields = ('name', 'contact_person', 'phone', 'email', 'gst_number')
    list_filter = ('is_active',)
    fieldsets = (
        (None, {
            'fields': ('name', 'contact_person', 'phone', 'email', 'gst_number')
        }),
        ('Additional Information', {
            'fields': ('address', 'is_active')
        }),
    )


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'supplier', 'date', 'total_amount', 'paid_amount', 'balance', 'payment_status', 'invoice_file_link')
    search_fields = ('invoice_number', 'supplier__name')
    list_filter = ('date', 'supplier')
    date_hierarchy = 'date'
    readonly_fields = ('balance', 'payment_status', 'invoice_file_link', 'invoice_file_path', 'invoice_file_url')
    fieldsets = (
        (None, {
            'fields': ('supplier', 'invoice_number', 'date', 'total_amount', 'paid_amount', 'balance', 'payment_status', 'notes')
        }),
        ('Invoice File', {
            'fields': ('invoice_file', 'invoice_file_link', 'invoice_file_path', 'invoice_file_url')
        }),
    )
    
    def invoice_file_link(self, obj):
        """
        Display a link to the invoice file if it exists
        """
        if obj.invoice_file_url:
            return format_html(
                '<a href="{}" target="_blank">View Invoice</a>',
                obj.invoice_file_url
            )
        return '-'
    invoice_file_link.short_description = 'Invoice File'
    
    def save_model(self, request, obj, form, change):
        """
        Handle file upload when saving the model
        """
        super().save_model(request, obj, form, change)
        
        # Handle file upload if present in the form
        if 'invoice_file' in form.files:
            file = form.files['invoice_file']
            obj.upload_invoice_file(file)
            
    def delete_model(self, request, obj):
        """
        Delete file from Supabase when deleting the model
        """
        # Delete the file if it exists
        if obj.invoice_file_path:
            obj.delete_invoice_file()
        
        super().delete_model(request, obj)


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_date', 'supplier', 'purchase_order_link', 'amount_paid', 'payment_mode', 'reference_number')
    search_fields = ('supplier__name', 'reference_number', 'remarks')
    list_filter = ('payment_date', 'supplier', 'payment_mode')
    date_hierarchy = 'payment_date'
    autocomplete_fields = ['supplier', 'purchase_order']
    
    fieldsets = (
        (None, {
            'fields': ('supplier', 'purchase_order', 'amount_paid', 'payment_date')
        }),
        ('Payment Details', {
            'fields': ('payment_mode', 'reference_number', 'remarks', 'due_date')
        }),
    )
    
    def purchase_order_link(self, obj):
        if obj.purchase_order:
            url = reverse("admin:materials_purchaseorder_change", args=[obj.purchase_order.pk])
            return format_html('<a href="{}">{}</a>', url, obj.purchase_order)
        return "-"
    purchase_order_link.short_description = "Purchase Order" 