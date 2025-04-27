from django.db import models
from apps.core.models import BaseModel
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.materials.models import Material, InventoryEntry
from decimal import Decimal
from django.urls import reverse
from django.core.validators import MinValueValidator
# from apps.inventory.models import Inventory  # Comment out this line if the import is not needed
from django.utils import timezone


class Customer(BaseModel):
    """
    Model for customer information.
    """
    RISK_CHOICES = [
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
    ]
    
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gst_number = models.CharField(max_length=15, blank=True, null=True, help_text="GST Registration Number")
    is_active = models.BooleanField(default=True)
    risk_score = models.CharField(max_length=10, choices=RISK_CHOICES, default='LOW', 
                                help_text="Risk assessment based on payment history")
    risk_notes = models.TextField(blank=True, null=True, 
                                help_text="Notes about risk factors and payment behavior")
    risk_last_updated = models.DateTimeField(blank=True, null=True, 
                                          help_text="When risk score was last updated")
    
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('customers:customer_detail', kwargs={'pk': self.pk})
    
    def get_recent_deliveries(self):
        return self.delivery_set.all().order_by('-date')[:5]
    
    def get_recent_payments(self):
        return self.customerpayment_set.all().order_by('-date')[:5]
    
    def get_account_summary(self):
        total_delivery_amount = self.delivery_set.aggregate(total=models.Sum('total_amount'))['total'] or 0
        total_payment_amount = self.customerpayment_set.aggregate(total=models.Sum('amount_paid'))['total'] or 0
        return {
            'total_delivery_amount': total_delivery_amount,
            'total_payment_amount': total_payment_amount,
            'balance': total_delivery_amount - total_payment_amount
        }
    
    def calculate_risk_score(self):
        """
        Calculate customer risk score based on comprehensive payment behavior analysis:
        
        Risk factors:
        - Overdue payments (number and amount)
        - Payment delays (average and maximum)
        - Outstanding balance ratio 
        - Number of unpaid deliveries
        - Recent payment trends
        """
        from datetime import timedelta
        from django.db.models import Sum, F, ExpressionWrapper, FloatField, Count
        from django.utils import timezone
        
        today = timezone.now().date()
        three_months_ago = today - timedelta(days=90)
        
        # Initialize risk metrics
        risk_factors = []
        total_points = 0  # Higher points = higher risk
        
        # ================ PAYMENT HISTORY ANALYSIS ==================
        
        # Get all deliveries (both regular and concrete)
        regular_deliveries = self.deliveries.all()
        concrete_deliveries = self.concrete_deliveries.all()
        
        # Calculate total delivered amount and received amount
        total_delivered = 0
        total_received = 0
        
        rd_totals = regular_deliveries.aggregate(
            total=Sum('total_amount'),
            received=Sum('received_amount')
        )
        cd_totals = concrete_deliveries.aggregate(
            total=Sum('total_amount'),
            received=Sum('received_amount')
        )
        
        if rd_totals['total']:
            total_delivered += rd_totals['total']
            total_received += rd_totals['received']
            
        if cd_totals['total']:
            total_delivered += cd_totals['total']
            total_received += cd_totals['received']
        
        # Calculate outstanding balance and ratio
        outstanding_balance = total_delivered - total_received if total_delivered else 0
        if total_delivered and total_delivered > 0:
            outstanding_ratio = (outstanding_balance / total_delivered) * 100
        else:
            outstanding_ratio = 0
        
        # ================ OVERDUE PAYMENTS ANALYSIS ==================
        
        # Get overdue deliveries (due date in past but not fully paid)
        overdue_regular = regular_deliveries.filter(
            due_date__lt=today,
            total_amount__gt=F('received_amount')
        )
        
        overdue_concrete = concrete_deliveries.filter(
            due_date__lt=today,
            total_amount__gt=F('received_amount')
        )
        
        # Count overdue deliveries and calculate overdue amount
        overdue_count = overdue_regular.count() + overdue_concrete.count()
        
        overdue_amount = 0
        for delivery in overdue_regular:
            overdue_amount += delivery.total_amount - delivery.received_amount
            
        for delivery in overdue_concrete:
            overdue_amount += delivery.total_amount - delivery.received_amount
        
        # Calculate maximum overdue days
        max_overdue_days = 0
        
        for delivery in overdue_regular:
            if delivery.due_date:
                days_overdue = (today - delivery.due_date).days
                max_overdue_days = max(max_overdue_days, days_overdue)
                
        for delivery in overdue_concrete:
            if delivery.due_date:
                days_overdue = (today - delivery.due_date).days
                max_overdue_days = max(max_overdue_days, days_overdue)
        
        # ================ PAYMENT PATTERN ANALYSIS ==================
        
        # Get all payments from the last 3 months
        recent_payments = self.payments.filter(payment_date__gte=three_months_ago).order_by('payment_date')
        
        # Calculate average payment delay
        total_delay_days = 0
        delayed_payments_count = 0
        
        for payment in recent_payments:
            if payment.due_date and payment.payment_date > payment.due_date:
                delay_days = (payment.payment_date - payment.due_date).days
                total_delay_days += delay_days
                delayed_payments_count += 1
        
        avg_delay = total_delay_days / delayed_payments_count if delayed_payments_count > 0 else 0
        
        # ================ RISK SCORE CALCULATION ==================
        
        # 1. Analyze outstanding balance ratio
        if outstanding_ratio >= 75:
            total_points += 40
            risk_factors.append(f"High outstanding balance ratio ({outstanding_ratio:.1f}%)")
        elif outstanding_ratio >= 50:
            total_points += 25
            risk_factors.append(f"Elevated outstanding balance ratio ({outstanding_ratio:.1f}%)")
        elif outstanding_ratio >= 25:
            total_points += 10
            risk_factors.append(f"Moderate outstanding balance ratio ({outstanding_ratio:.1f}%)")
        
        # 2. Analyze overdue deliveries
        if overdue_count >= 5:
            total_points += 35
            risk_factors.append(f"{overdue_count} overdue deliveries")
        elif overdue_count >= 3:
            total_points += 20
            risk_factors.append(f"{overdue_count} overdue deliveries")
        elif overdue_count >= 1:
            total_points += 10
            risk_factors.append(f"{overdue_count} overdue deliveries")
        
        # 3. Analyze overdue amount
        if overdue_amount > 0:
            overdue_percentage = (overdue_amount / total_delivered) * 100 if total_delivered > 0 else 0
            if overdue_percentage >= 50:
                total_points += 40
                risk_factors.append(f"High overdue amount ({overdue_percentage:.1f}% of total)")
            elif overdue_percentage >= 25:
                total_points += 25
                risk_factors.append(f"Substantial overdue amount ({overdue_percentage:.1f}% of total)")
            elif overdue_percentage >= 10:
                total_points += 10
                risk_factors.append(f"Moderate overdue amount ({overdue_percentage:.1f}% of total)")
        
        # 4. Analyze maximum overdue days
        if max_overdue_days >= 90:
            total_points += 40
            risk_factors.append(f"Very long overdue period ({max_overdue_days} days)")
        elif max_overdue_days >= 60:
            total_points += 30
            risk_factors.append(f"Long overdue period ({max_overdue_days} days)")
        elif max_overdue_days >= 30:
            total_points += 15
            risk_factors.append(f"Moderate overdue period ({max_overdue_days} days)")
        elif max_overdue_days >= 15:
            total_points += 5
            risk_factors.append(f"Short overdue period ({max_overdue_days} days)")
        
        # 5. Analyze payment delays
        if avg_delay >= 30:
            total_points += 25
            risk_factors.append(f"Severe payment delays (avg. {avg_delay:.1f} days)")
        elif avg_delay >= 15:
            total_points += 15
            risk_factors.append(f"Significant payment delays (avg. {avg_delay:.1f} days)")
        elif avg_delay >= 7:
            total_points += 5
            risk_factors.append(f"Moderate payment delays (avg. {avg_delay:.1f} days)")
        
        # ================ DETERMINE RISK LEVEL ==================
        
        if total_points >= 70:
            risk_level = 'HIGH'
        elif total_points >= 30:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
            
        # Include summary of balance in risk notes
        if total_delivered > 0:
            summary = f"Outstanding: ₹{outstanding_balance:.2f} ({outstanding_ratio:.1f}% of ₹{total_delivered:.2f} total)"
            if not risk_factors:
                risk_factors.append("No significant risk factors identified")
            risk_factors.insert(0, summary)
        
        # Update the model
        self.risk_score = risk_level
        self.risk_notes = "\n".join(risk_factors)
        self.risk_last_updated = timezone.now()
        self.save(update_fields=['risk_score', 'risk_notes', 'risk_last_updated'])
        
        return {
            'risk_level': risk_level, 
            'points': total_points, 
            'factors': risk_factors
        }
    
    def get_payment_recommendations(self):
        """
        Get payment recommendations based on risk score
        """
        if self.risk_score == 'HIGH':
            return {
                'require_advance': True,
                'manual_followup': True,
                'credit_limit': "No credit - advance payment only",
                'message': "High risk customer - require advance payment and manual approval for orders"
            }
        elif self.risk_score == 'MEDIUM':
            return {
                'require_advance': False,
                'manual_followup': True,
                'credit_limit': "Restricted credit - 50% advance payment",
                'message': "Medium risk customer - consider partial advance payment and follow up"
            }
        else:
            return {
                'require_advance': False,
                'manual_followup': False,
                'credit_limit': "Standard credit terms",
                'message': "Low risk customer - standard terms apply"
            }
    
    class Meta:
        ordering = ['name']


class Delivery(BaseModel):
    """
    Model for deliveries to customers.
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='deliveries')
    invoice_number = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    received_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True, help_text="Payment due date for this delivery")
    
    def __str__(self):
        return f"Delivery {self.invoice_number} - {self.customer.name}"
    
    @property
    def balance(self):
        return self.total_amount - self.received_amount
    
    def update_received_amount(self):
        """
        Update the received_amount based on all related payments
        """
        total_paid = self.payments.aggregate(total=models.Sum('amount_paid'))['total'] or Decimal('0')
        self.received_amount = total_paid
        self.save(update_fields=['received_amount'])
        return self.received_amount

    def get_absolute_url(self):
        return reverse('customers:delivery_list')
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Deliveries"


class MixRatio(BaseModel):
    """
    Model for defining concrete mix ratios for different grades.
    """
    GRADE_CHOICES = [
        ('M5', 'M5'),
        ('M7.5', 'M7.5'),
        ('M10', 'M10'),
        ('M15', 'M15'),
        ('M20', 'M20'),
        ('M25', 'M25'),
        ('M30', 'M30'),
        ('M35', 'M35'),
        ('M40', 'M40'),
        ('M45', 'M45'),
        ('M50', 'M50'),
        ('M55', 'M55'),
        ('M60', 'M60'),
        ('M65', 'M65'),
        ('M70', 'M70'),
    ]
    
    grade = models.CharField(max_length=5, choices=GRADE_CHOICES)
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='mix_ratios')
    qty_per_m3 = models.DecimalField(
        max_digits=8, decimal_places=2, 
        help_text="Quantity of material needed per cubic meter of concrete"
    )
    
    class Meta:
        unique_together = ['grade', 'material']
        verbose_name = "Mix Ratio"
        verbose_name_plural = "Mix Ratios"
    
    def __str__(self):
        return f"{self.grade} - {self.material.name}: {self.qty_per_m3} {self.material.unit}/m³"


class ConcreteDelivery(BaseModel):
    """
    Model for tracking concrete deliveries with specific grades.
    """
    GRADE_CHOICES = [
        ('M5', 'M5'),
        ('M7.5', 'M7.5'),
        ('M10', 'M10'),
        ('M15', 'M15'),
        ('M20', 'M20'),
        ('M25', 'M25'),
        ('M30', 'M30'),
        ('M35', 'M35'),
        ('M40', 'M40'),
        ('M45', 'M45'),
        ('M50', 'M50'),
        ('M55', 'M55'),
        ('M60', 'M60'),
        ('M65', 'M65'),
        ('M70', 'M70'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='concrete_deliveries')
    invoice_number = models.CharField(max_length=50, unique=True, blank=True, help_text="Unique invoice number for this delivery")
    delivery_date = models.DateField()
    grade = models.CharField(max_length=5, choices=GRADE_CHOICES)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, help_text="Quantity in cubic meters (m³)")
    site_location = models.CharField(max_length=255)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], default=Decimal('0'))
    received_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    due_date = models.DateField(blank=True, null=True, help_text="Payment due date for this delivery")
    remarks = models.TextField(blank=True, null=True)
    stock_validated = models.BooleanField(default=False, help_text="Indicates if stock levels have been validated")
    inventory_deducted = models.BooleanField(default=False, help_text="Indicates if inventory has been deducted")
    delivery_note_url = models.CharField(max_length=500, blank=True, null=True, help_text="URL for the delivery note file in Supabase")
    delivery_note_file_path = models.CharField(max_length=255, blank=True, null=True, help_text="Path of the file in Supabase storage")
    
    def __str__(self):
        if self.invoice_number:
            return f"Invoice {self.invoice_number} - {self.grade} - {self.quantity}m³ to {self.customer.name}"
        return f"{self.grade} - {self.quantity}m³ to {self.customer.name} on {self.delivery_date}"
    
    def get_absolute_url(self):
        return reverse('customers:concrete_delivery_detail', kwargs={'pk': self.pk})
    
    @property
    def balance(self):
        return self.total_amount - self.received_amount
    
    def update_received_amount(self):
        """
        Update the received_amount based on all related payments
        """
        total_paid = self.concrete_payments.aggregate(total=models.Sum('amount_paid'))['total'] or Decimal('0')
        self.received_amount = total_paid
        self.save(update_fields=['received_amount'])
        return self.received_amount
    
    def check_material_availability(self):
        """
        Check if there is sufficient material for the concrete delivery
        """
        mix_ratios = MixRatio.objects.filter(grade=self.grade)
        
        if not mix_ratios.exists():
            # No mix ratio defined, but that's okay
            return True
        
        insufficient_materials = []
        
        for ratio in mix_ratios:
            required_qty = ratio.qty_per_m3 * self.quantity
            available_qty = ratio.material.current_stock
            
            if required_qty > available_qty:
                insufficient_materials.append({
                    'material': ratio.material.name,
                    'required': required_qty,
                    'available': available_qty,
                    'unit': ratio.material.unit
                })
        
        if insufficient_materials:
            error_message = "Insufficient materials in inventory:\n"
            for item in insufficient_materials:
                error_message += f"- {item['material']}: Need {item['required']} {item['unit']}, but only {item['available']} {item['unit']} available\n"
            raise ValidationError(error_message)
        
        return True
    
    def deduct_inventory(self):
        """
        Deduct materials from inventory based on concrete grade and quantity
        """
        if self.inventory_deducted:
            return False
        
        mix_ratios = MixRatio.objects.filter(grade=self.grade)
        
        if not mix_ratios.exists():
            # No mix ratio defined, so nothing to deduct
            self.inventory_deducted = True
            self.stock_validated = True
            self.save(update_fields=['inventory_deducted', 'stock_validated'])
            return True
        
        # Check material availability first
        self.check_material_availability()
        
        # Create inventory entries for each material
        for ratio in mix_ratios:
            used_qty = ratio.qty_per_m3 * self.quantity
            
            # Create inventory entry to deduct the material
            InventoryEntry.objects.create(
                material=ratio.material,
                quantity=used_qty,
                entry_type='OUT',
                reference_type='CONCRETE_DELIVERY',
                reference_id=self.id,
                notes=f"Used for {self.grade} concrete delivery to {self.customer.name} at {self.site_location}"
            )
        
        self.inventory_deducted = True
        self.stock_validated = True
        self.save(update_fields=['inventory_deducted', 'stock_validated'])
        
        return True
    
    def upload_delivery_note(self, file, file_name=None):
        """
        Upload delivery note file to Supabase storage
        """
        from django.conf import settings
        from supabase import create_client, Client
        import os
        import uuid
        
        if not file:
            return None
            
        # Initialize Supabase client
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_KEY
        supabase: Client = create_client(url, key)
        
        # Generate a unique file name
        if not file_name:
            file_extension = os.path.splitext(file.name)[1].lower()
            file_name = f"{uuid.uuid4()}{file_extension}"
            
        # Define the path in Supabase storage
        file_path = f"delivery-notes/{self.customer.id}/{file_name}"
        
        # Upload the file
        try:
            result = supabase.storage.from_("documents").upload(
                path=file_path,
                file=file.read(),
                file_options={"content-type": file.content_type}
            )
            
            # Get public URL
            public_url = supabase.storage.from_("documents").get_public_url(file_path)
            
            # Update model fields
            self.delivery_note_file_path = file_path
            self.delivery_note_url = public_url
            self.save(update_fields=['delivery_note_file_path', 'delivery_note_url'])
            
            return public_url
        except Exception as e:
            print(f"Error uploading file to Supabase: {e}")
            return None
            
    def get_delivery_note_url(self):
        """
        Get the delivery note URL
        """
        if self.delivery_note_url:
            return self.delivery_note_url
        return None
        
    def delete_delivery_note(self):
        """
        Delete the delivery note file from Supabase storage
        """
        if not self.delivery_note_file_path:
            return False
            
        from django.conf import settings
        from supabase import create_client, Client
        
        # Initialize Supabase client
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_KEY
        supabase: Client = create_client(url, key)
        
        try:
            # Delete the file
            supabase.storage.from_("documents").remove([self.delivery_note_file_path])
            
            # Clear the fields
            self.delivery_note_file_path = None
            self.delivery_note_url = None
            self.save(update_fields=['delivery_note_file_path', 'delivery_note_url'])
            
            return True
        except Exception as e:
            print(f"Error deleting file from Supabase: {e}")
            return False
        
    def clean(self):
        """
        Custom validation to check stock levels before saving
        """
        if not self.stock_validated:
            try:
                # Make stock validation optional by not raising errors if no mix ratio exists
                mix_ratios = MixRatio.objects.filter(grade=self.grade)
                if mix_ratios.exists():
                    # Check material availability only if mix ratios are defined
                    self.check_material_availability()
            except ValidationError as e:
                raise e
    
    def save(self, *args, **kwargs):
        # Generate a unique invoice number if not provided
        if not self.invoice_number:
            # Format: CD-YYYYMMDD-XXX (CD: Concrete Delivery, Date, Sequential Number)
            from django.db.models import Max
            import datetime
            
            date_str = self.delivery_date.strftime('%Y%m%d')
            
            # Get the last concrete delivery with this date prefix
            prefix = f"CD-{date_str}-"
            last_invoice = ConcreteDelivery.objects.filter(
                invoice_number__startswith=prefix
            ).aggregate(Max('invoice_number'))['invoice_number__max']
            
            if last_invoice:
                # Extract the sequence number and increment
                seq_num = int(last_invoice.split('-')[-1]) + 1
            else:
                # Start with 1
                seq_num = 1
                
            # Format with leading zeros (e.g., 001, 002, etc.)
            self.invoice_number = f"{prefix}{seq_num:03d}"
            
        if not self.pk:  # Only for new objects
            self.clean()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Concrete Delivery"
        verbose_name_plural = "Concrete Deliveries"
        ordering = ['-delivery_date']


class CustomerPayment(BaseModel):
    """
    Model for tracking customer payments for deliveries.
    """
    PAYMENT_MODE_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit', 'Credit'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='payments', blank=True, null=True)
    concrete_delivery = models.ForeignKey(ConcreteDelivery, on_delete=models.CASCADE, related_name='concrete_payments', blank=True, null=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES)
    payment_date = models.DateField(default=timezone.now)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True, help_text="Due date for credit payments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.delivery:
            delivery_info = f" for {self.delivery}"
        elif self.concrete_delivery:
            delivery_info = f" for Concrete {self.concrete_delivery}"
        else:
            delivery_info = ""
        return f"Payment of ₹{self.amount_paid} by {self.customer.name}{delivery_info}"
    
    def get_absolute_url(self):
        return reverse('customers:payment_list')
    
    def clean(self):
        # Ensure payment has either a regular delivery or concrete delivery, but not both
        if self.delivery and self.concrete_delivery:
            raise ValidationError("A payment can only be linked to either a regular delivery or a concrete delivery, not both.")
            
        # Ensure payment doesn't exceed remaining balance
        if self.amount_paid and self.delivery:
            # Calculate balance manually
            current_balance = self.delivery.total_amount - self.delivery.received_amount
            if self.pk:  # If editing, account for this payment's current amount
                current_payment = CustomerPayment.objects.get(pk=self.pk)
                current_balance += current_payment.amount_paid
                
            if self.amount_paid > current_balance:
                raise ValidationError({
                    'amount_paid': f"Payment amount ({self.amount_paid}) exceeds remaining balance ({current_balance})"
                })
                
        # Check balance for concrete delivery
        if self.amount_paid and self.concrete_delivery:
            current_balance = self.concrete_delivery.total_amount - self.concrete_delivery.received_amount
            if self.pk:  # If editing, account for this payment's current amount
                current_payment = CustomerPayment.objects.get(pk=self.pk)
                current_balance += current_payment.amount_paid
                
            if self.amount_paid > current_balance:
                raise ValidationError({
                    'amount_paid': f"Payment amount ({self.amount_paid}) exceeds remaining balance ({current_balance})"
                })
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        # Update delivery's received amount
        if self.delivery:
            self.delivery.update_received_amount()
        elif self.concrete_delivery:
            self.concrete_delivery.update_received_amount()
    
    def delete(self, *args, **kwargs):
        # When deleting a payment, reduce the delivery's received amount
        if self.delivery:
            self.delivery.received_amount -= self.amount_paid
            self.delivery.save()
        elif self.concrete_delivery:
            self.concrete_delivery.received_amount -= self.amount_paid
            self.concrete_delivery.save()
            
        super().delete(*args, **kwargs)
    
    class Meta:
        ordering = ['-payment_date', '-created_at']
        verbose_name = "Customer Payment"
        verbose_name_plural = "Customer Payments"


@receiver(post_save, sender=ConcreteDelivery)
def deduct_materials_on_delivery(sender, instance, created, **kwargs):
    """
    Signal handler to deduct materials from inventory when a concrete delivery is created
    """
    if created and not instance.inventory_deducted:
        try:
            instance.deduct_inventory()
        except ValidationError:
            # If inventory deduction fails, we'll leave it for manual resolution
            # The inventory_deducted flag will remain False
            pass 

# Signal to update customer risk score when a payment is made or updated
@receiver(post_save, sender=CustomerPayment)
def update_customer_risk_on_payment(sender, instance, created, **kwargs):
    """
    Automatically update customer risk score whenever a payment is made or updated
    """
    if instance.customer:
        # Schedule risk recalculation
        instance.customer.calculate_risk_score() 