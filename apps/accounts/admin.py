from django.contrib import admin
from .models import LedgerEntry, BankAccount, Transaction


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'description', 'amount', 'transaction_type', 'reference_number')
    list_filter = ('transaction_type', 'date')
    search_fields = ('description', 'reference_number')
    date_hierarchy = 'date'


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'bank_name', 'account_number', 'current_balance', 'is_active')
    list_filter = ('is_active', 'bank_name')
    search_fields = ('name', 'account_number', 'bank_name')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'bank_account', 'transaction_type', 'amount', 'description')
    list_filter = ('transaction_type', 'date', 'bank_account')
    search_fields = ('description', 'reference_number')
    date_hierarchy = 'date' 