from django.db import models
from apps.core.models import BaseModel
from apps.core.utils.storage import upload_to_supabase, get_file_from_supabase, delete_file_from_supabase
from django.urls import reverse


class Supplier(BaseModel):
    """
    Model for supplier information.
    """
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    gst_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="GSTIN")
    address = models.TextField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class Purchase(BaseModel):
    """
    Model for purchases from suppliers.
    DEPRECATED: Use PurchaseOrder from materials app instead
    This model is kept for historical data only. New purchases should be created as PurchaseOrder objects.
    """
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchases')
    invoice_number = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True, help_text="Leave blank if no credit terms")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    
    # Supabase file storage fields
    invoice_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    invoice_file_path = models.CharField(max_length=255, blank=True, null=True)
    invoice_file_url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return f"Purchase {self.invoice_number} - {self.supplier.name}"
    
    @property
    def balance(self):
        return self.total_amount - self.paid_amount
    
    @property
    def payment_status(self):
        """
        Return payment status based on paid amount vs total amount
        """
        if self.paid_amount >= self.total_amount:
            return "Paid"
        elif self.paid_amount > 0:
            return "Partial"
        return "Pending"
    
    def update_paid_amount(self):
        """
        Update the paid amount based on all payments
        """
        total_paid = sum(payment.amount_paid for payment in self.payments.all())
        self.paid_amount = total_paid
        self.save(update_fields=['paid_amount'])
        return self.paid_amount
    
    def upload_invoice_file(self, file, file_name=None):
        """
        Upload invoice file to Supabase storage
        """
        try:
            result = upload_to_supabase(file, 'invoices', file_name)
            
            if result and result.get('success'):
                self.invoice_file_url = result.get('public_url')
                self.invoice_file_path = result.get('file_path')
                self.save(update_fields=['invoice_file_url', 'invoice_file_path'])
                
            return result
        except Exception as e:
            print(f"Error uploading file: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_invoice_file_url(self):
        """
        Get the invoice file URL
        """
        if not self.invoice_file_url and self.invoice_file_path:
            # Try to generate URL from path
            try:
                self.invoice_file_url = get_file_from_supabase(self.invoice_file_path)
                self.save(update_fields=['invoice_file_url'])
            except Exception as e:
                print(f"Error getting file URL: {e}")
                return None
        
        return self.invoice_file_url
    
    def delete_invoice_file(self):
        """
        Delete the invoice file from Supabase storage
        """
        if not self.invoice_file_path:
            return False
            
        try:
            result = delete_file_from_supabase(self.invoice_file_path)
            
            if result and result.get('success'):
                self.invoice_file_url = None
                self.invoice_file_path = None
                self.save(update_fields=['invoice_file_url', 'invoice_file_path'])
                
            return result
        except Exception as e:
            print(f"Error deleting file: {e}")
            return {'success': False, 'error': str(e)}


class SupplierPayment(BaseModel):
    """
    Model for tracking payments made to suppliers for purchases
    """
    PAYMENT_MODES = [
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
        ('BANK', 'Bank Transfer'),
        ('CREDIT', 'Credit'),
        ('UPI', 'UPI'),
        ('OTHER', 'Other'),
    ]
    
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='payments')
    # Changed from Purchase to PurchaseOrder in materials app
    purchase_order = models.ForeignKey('materials.PurchaseOrder', on_delete=models.CASCADE, 
                                     related_name='supplier_payments', null=True, blank=True,
                                     verbose_name="Purchase Order")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODES, default='CASH')
    payment_date = models.DateField()
    due_date = models.DateField(null=True, blank=True, help_text="Required only for credit payments")
    reference_number = models.CharField(max_length=50, blank=True, null=True, 
                                      help_text="Cheque number, transaction ID, etc.")
    remarks = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Payment of ₹{self.amount_paid} to {self.supplier.name} on {self.payment_date}"
    
    def get_absolute_url(self):
        return reverse('suppliers:payment_list')
    
    class Meta:
        ordering = ['-payment_date', '-created_at'] 