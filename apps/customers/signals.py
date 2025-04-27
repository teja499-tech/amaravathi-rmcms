from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Delivery, CustomerPayment, ConcreteDelivery
from apps.accounts.services import create_ledger_entry
from django.utils import timezone
from apps.accounts.models import BankAccount

@receiver(post_save, sender=Delivery)
def create_delivery_ledger_entry(sender, instance, created, **kwargs):
    """Create a ledger entry when a delivery is created"""
    if created:
        create_ledger_entry(
            date=instance.date,
            description=f"Delivery {instance.invoice_number} to {instance.customer.name}",
            amount=instance.total_amount,
            transaction_type='sale',
            reference_number=instance.invoice_number,
            customer=instance.customer,
            delivery=instance,
            created_by=instance.created_by if hasattr(instance, 'created_by') else None
        )

@receiver(post_save, sender=ConcreteDelivery)
def create_concrete_delivery_ledger_entry(sender, instance, created, **kwargs):
    """Create a ledger entry when a concrete delivery is created"""
    if created:
        create_ledger_entry(
            date=instance.delivery_date,
            description=f"Concrete Delivery {instance.invoice_number} to {instance.customer.name} ({instance.grade})",
            amount=instance.total_amount,
            transaction_type='sale',
            reference_number=instance.invoice_number,
            customer=instance.customer,
            created_by=instance.created_by if hasattr(instance, 'created_by') else None
        )

@receiver(post_save, sender=CustomerPayment)
def create_payment_ledger_entry(sender, instance, created, **kwargs):
    """Create a ledger entry when a payment is received"""
    if created:
        # Bank account is not available on the CustomerPayment model
        bank_account = None
                
        create_ledger_entry(
            date=instance.payment_date,
            description=f"Payment received from {instance.customer.name} for {instance.delivery.invoice_number if instance.delivery else 'multiple invoices'}",
            amount=instance.amount_paid,
            transaction_type='income',
            reference_number=instance.reference_number,
            customer=instance.customer,
            payment_method=instance.payment_mode,
            bank_account=bank_account,
            created_by=instance.created_by if hasattr(instance, 'created_by') else None
        ) 