from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from apps.core.models import BaseModel
from apps.suppliers.models import Supplier


class Material(BaseModel):
    """
    Model for tracking materials inventory.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=20, help_text="Unit of measurement (e.g., kg, ton, cubic meter)")
    current_stock = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    reorder_level = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.unit})"
    
    def update_stock(self):
        """
        Update current stock based on inventory entries
        """
        # Calculate total entries by adding IN and subtracting OUT entries
        entries = self.inventory_entries.all()
        
        # Use Decimal for precise calculations
        in_stock = Decimal('0')
        out_stock = Decimal('0')
        
        # Sum all entries with proper decimal handling
        for entry in entries:
            quantity = Decimal(str(entry.quantity))  # Ensure proper Decimal conversion
            if entry.entry_type == 'IN':
                in_stock += quantity
            elif entry.entry_type == 'OUT':
                out_stock += quantity
        
        # Update current stock 
        self.current_stock = in_stock - out_stock
        
        # Save the model with only the current_stock field
        self.save(update_fields=['current_stock', 'updated_at'])
        
        return self.current_stock
    
    class Meta:
        ordering = ['name']


class PurchaseOrder(BaseModel):
    """
    Model for tracking material purchase orders from suppliers.
    """
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    purchase_date = models.DateField()
    due_date = models.DateField(null=True, blank=True, help_text="Due date for payment, leave blank if no credit terms")
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    gst_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    transport_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    notes = models.TextField(blank=True, null=True)
    inventory_updated = models.BooleanField(default=False, help_text="Flag to track if inventory was updated")
    
    def __str__(self):
        return f"PO-{self.id} - {self.supplier.name} - {self.purchase_date}"
    
    @property
    def balance(self):
        """
        Calculate the balance amount that is still due after any payments
        """
        total_paid = sum(payment.amount_paid for payment in self.supplier_payments.all())
        return self.total_amount - total_paid
        
    @property
    def payment_status(self):
        """
        Return payment status based on paid amount vs total amount
        """
        total_paid = sum(payment.amount_paid for payment in self.supplier_payments.all())
        if total_paid >= self.total_amount:
            return "Paid"
        elif total_paid > 0:
            return "Partial"
        return "Pending"
        
    def update_paid_amount(self):
        """
        Update the status based on all payments
        """
        # This method is called when payments are made
        # We don't store paid_amount directly, but calculate it from related payments
        return self.balance
    
    def calculate_total(self):
        """
        Calculate the total amount including GST and transport cost
        """
        item_total = sum(item.calculate_total() for item in self.items.all())
        gst_amount = item_total * (self.gst_percent / Decimal('100'))
        return item_total + gst_amount + self.transport_cost
    
    def update_inventory(self):
        """
        Update inventory based on purchase items
        """
        if not self.inventory_updated:
            updated_materials = []
            
            for item in self.items.all():
                # Create inventory entry for this purchase item
                entry = InventoryEntry.objects.create(
                    material=item.material,
                    quantity=item.quantity,
                    entry_type='IN',
                    reference_type='PURCHASE',
                    reference_id=self.id,
                    notes=f"Purchase from {self.supplier.name} - Invoice: {self.id}"
                )
                
                # Update material stock
                item.material.update_stock()
                updated_materials.append({
                    'name': item.material.name,
                    'quantity': item.quantity,
                    'new_stock': item.material.current_stock
                })
            
            # Mark inventory as updated
            self.inventory_updated = True
            self.save(update_fields=['inventory_updated'])
            
            return updated_materials
        
        return []
    
    def save(self, *args, **kwargs):
        # Auto-calculate total amount when saving
        if self.pk:  # Only calculate for existing objects
            self.total_amount = self.calculate_total()
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-purchase_date']


class PurchaseItem(BaseModel):
    """
    Model for tracking individual items in a purchase order.
    """
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='purchase_items')
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    rate_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    gst_applicable = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.material.name} - {self.quantity} {self.material.unit}"
    
    def calculate_total(self):
        """
        Calculate the total amount for this item
        """
        return self.quantity * self.rate_per_unit
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the purchase order total
        self.purchase_order.save()
    
    class Meta:
        ordering = ['material__name']


class InventoryEntry(BaseModel):
    """
    Model for tracking inventory movements (IN/OUT)
    """
    ENTRY_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]
    
    REFERENCE_TYPES = [
        ('PURCHASE', 'Purchase Order'),
        ('SALE', 'Sale Order'),
        ('ADJUSTMENT', 'Manual Adjustment'),
        ('RETURN', 'Return'),
        ('OTHER', 'Other'),
    ]
    
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='inventory_entries')
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    entry_type = models.CharField(max_length=3, choices=ENTRY_TYPES)
    date = models.DateTimeField(auto_now_add=True)
    reference_type = models.CharField(max_length=20, choices=REFERENCE_TYPES)
    reference_id = models.PositiveIntegerField(null=True, blank=True, help_text="ID of the related document")
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.entry_type} - {self.material.name} - {self.quantity} {self.material.unit}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update material stock
        self.material.update_stock()
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Inventory Entries'
