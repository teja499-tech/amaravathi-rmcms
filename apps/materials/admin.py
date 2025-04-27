from django.contrib import admin
from django.utils.html import format_html
from .models import Material, PurchaseOrder, PurchaseItem, InventoryEntry


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'current_stock', 'reorder_level', 'is_active')
    search_fields = ('name', 'description')
    list_filter = ('is_active', 'unit')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'unit')
        }),
        ('Inventory', {
            'fields': ('current_stock', 'reorder_level', 'is_active')
        }),
    )
    readonly_fields = ('current_stock',)


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    fields = ('material', 'quantity', 'rate_per_unit', 'gst_applicable', 'line_total')
    readonly_fields = ('line_total',)
    
    def line_total(self, obj):
        if obj.id:
            return obj.calculate_total()
        return '-'
    line_total.short_description = 'Line Total'


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'supplier', 'purchase_date', 'total_amount', 'gst_percent', 'transport_cost', 'inventory_updated')
    search_fields = ('supplier__name', 'notes')
    list_filter = ('purchase_date', 'supplier', 'inventory_updated')
    date_hierarchy = 'purchase_date'
    inlines = [PurchaseItemInline]
    readonly_fields = ('total_amount', 'calculated_total', 'inventory_updated')
    fieldsets = (
        (None, {
            'fields': ('supplier', 'purchase_date', 'gst_percent', 'transport_cost', 'notes')
        }),
        ('Totals', {
            'fields': ('total_amount', 'calculated_total', 'inventory_updated')
        }),
    )
    actions = ['update_inventory']
    
    def calculated_total(self, obj):
        if obj.id:
            return obj.calculate_total()
        return '-'
    calculated_total.short_description = 'Calculated Total'
    
    def update_inventory(self, request, queryset):
        updated = 0
        for purchase_order in queryset:
            if not purchase_order.inventory_updated:
                purchase_order.update_inventory()
                updated += 1
        
        if updated:
            self.message_user(request, f"{updated} purchase orders were used to update inventory.")
        else:
            self.message_user(request, "No inventory was updated. Either the selected purchase orders were already processed or they have no items.")
    update_inventory.short_description = "Update inventory from selected purchase orders"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Refresh total amount after saving
        if change:
            obj.total_amount = obj.calculate_total()
            obj.save(update_fields=['total_amount'])
    
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        # Save other types of formsets
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()


@admin.register(InventoryEntry)
class InventoryEntryAdmin(admin.ModelAdmin):
    list_display = ('material', 'quantity', 'entry_type', 'date', 'reference_type', 'reference_id')
    search_fields = ('material__name', 'notes')
    list_filter = ('entry_type', 'reference_type', 'date', 'material')
    date_hierarchy = 'date'
    fieldsets = (
        (None, {
            'fields': ('material', 'quantity', 'entry_type')
        }),
        ('Reference', {
            'fields': ('reference_type', 'reference_id', 'notes')
        }),
    )
    readonly_fields = ('date',)
