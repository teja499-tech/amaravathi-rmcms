from django.contrib import admin
from .models import CommitmentCategory, OperationalCommitment, CommitmentPayment

class CommitmentPaymentInline(admin.TabularInline):
    model = CommitmentPayment
    extra = 0
    fields = ('payment_date', 'amount_paid', 'payment_mode', 'reference_number', 'remarks')

@admin.register(CommitmentCategory)
class CommitmentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(OperationalCommitment)
class OperationalCommitmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'payee_name', 'amount', 'payment_frequency', 
                    'next_payment_date', 'status', 'is_active')
    list_filter = ('category', 'payment_frequency', 'status', 'is_active')
    search_fields = ('title', 'payee_name', 'description', 'reference_number')
    date_hierarchy = 'next_payment_date'
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CommitmentPaymentInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'category', 'description', 'amount', 'status', 'is_active')
        }),
        ('Contract Details', {
            'fields': ('reference_number', 'start_date', 'end_date')
        }),
        ('Payment Schedule', {
            'fields': ('payment_frequency', 'payment_day', 'next_payment_date')
        }),
        ('Contact Information', {
            'fields': ('payee_name', 'contact_person', 'contact_phone', 'contact_email')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )

@admin.register(CommitmentPayment)
class CommitmentPaymentAdmin(admin.ModelAdmin):
    list_display = ('commitment', 'amount_paid', 'payment_date', 'payment_mode', 'reference_number')
    list_filter = ('payment_mode', 'payment_date')
    search_fields = ('commitment__title', 'reference_number', 'receipt_number', 'remarks')
    date_hierarchy = 'payment_date'
    autocomplete_fields = ['commitment']
    readonly_fields = ('created_at', 'updated_at')
