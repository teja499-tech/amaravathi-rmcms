from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.customers.models import Delivery, CustomerPayment, ConcreteDelivery
from apps.expenses.models import Expense
from apps.suppliers.models import Purchase, SupplierPayment
from apps.accounts.services import create_ledger_entry
from apps.accounts.models import LedgerEntry

class Command(BaseCommand):
    help = 'Populates the ledger with existing transactions from various modules'

    def handle(self, *args, **options):
        # Clear existing ledger entries if needed
        self.stdout.write('Checking for existing ledger entries...')
        existing_count = LedgerEntry.objects.count()
        if existing_count > 0:
            proceed = input(f"Found {existing_count} existing ledger entries. Do you want to clear them? (y/n): ")
            if proceed.lower() == 'y':
                LedgerEntry.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('Cleared existing ledger entries.'))
            else:
                self.stdout.write('Keeping existing ledger entries.')

        # Import Customer Deliveries
        self.stdout.write('Importing regular deliveries...')
        deliveries = Delivery.objects.all()
        delivery_count = 0
        for delivery in deliveries:
            try:
                create_ledger_entry(
                    date=delivery.date,
                    description=f"Delivery {delivery.invoice_number} to {delivery.customer.name}",
                    amount=delivery.total_amount,
                    transaction_type='sale',
                    reference_number=delivery.invoice_number,
                    customer=delivery.customer,
                    delivery=delivery
                )
                delivery_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error importing delivery {delivery.id}: {str(e)}'))
        self.stdout.write(self.style.SUCCESS(f'Imported {delivery_count} regular deliveries.'))

        # Import Concrete Deliveries
        self.stdout.write('Importing concrete deliveries...')
        concrete_deliveries = ConcreteDelivery.objects.all()
        concrete_count = 0
        for delivery in concrete_deliveries:
            try:
                create_ledger_entry(
                    date=delivery.delivery_date,
                    description=f"Concrete Delivery {delivery.invoice_number} to {delivery.customer.name} ({delivery.grade})",
                    amount=delivery.total_amount,
                    transaction_type='sale',
                    reference_number=delivery.invoice_number,
                    customer=delivery.customer
                )
                concrete_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error importing concrete delivery {delivery.id}: {str(e)}'))
        self.stdout.write(self.style.SUCCESS(f'Imported {concrete_count} concrete deliveries.'))

        # Import Customer Payments
        self.stdout.write('Importing customer payments...')
        payments = CustomerPayment.objects.all()
        payment_count = 0
        for payment in payments:
            try:
                create_ledger_entry(
                    date=payment.payment_date,
                    description=f"Payment received from {payment.customer.name} for {payment.delivery.invoice_number if payment.delivery else 'multiple invoices'}",
                    amount=payment.amount_paid,
                    transaction_type='income',
                    reference_number=getattr(payment, 'receipt_number', f'RCPT-{payment.id}'),
                    customer=payment.customer
                )
                payment_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error importing customer payment {payment.id}: {str(e)}'))
        self.stdout.write(self.style.SUCCESS(f'Imported {payment_count} customer payments.'))

        # Import Expenses
        self.stdout.write('Importing expenses...')
        expenses = Expense.objects.all()
        expense_count = 0
        for expense in expenses:
            try:
                create_ledger_entry(
                    date=expense.date,
                    description=f"Expense: {expense.description}",
                    amount=expense.amount,
                    transaction_type='expense',
                    reference_number=getattr(expense, 'reference_number', f'EXP-{expense.id}'),
                    created_by=expense.created_by if hasattr(expense, 'created_by') else None
                )
                expense_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error importing expense {expense.id}: {str(e)}'))
        self.stdout.write(self.style.SUCCESS(f'Imported {expense_count} expenses.'))

        # Import Purchases
        self.stdout.write('Importing supplier purchases...')
        purchases = Purchase.objects.all()
        purchase_count = 0
        for purchase in purchases:
            try:
                create_ledger_entry(
                    date=purchase.date,
                    description=f"Purchase from {purchase.supplier.name} ({purchase.invoice_number})",
                    amount=purchase.total_amount,
                    transaction_type='purchase',
                    reference_number=purchase.invoice_number,
                    supplier=purchase.supplier,
                    purchase=purchase
                )
                purchase_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error importing purchase {purchase.id}: {str(e)}'))
        self.stdout.write(self.style.SUCCESS(f'Imported {purchase_count} supplier purchases.'))

        # Import Supplier Payments
        self.stdout.write('Importing supplier payments...')
        try:
            supplier_payments = SupplierPayment.objects.all()
            supplier_payment_count = 0
            for payment in supplier_payments:
                try:
                    create_ledger_entry(
                        date=payment.payment_date,
                        description=f"Payment to {payment.supplier.name} for " + 
                                   (f"{payment.purchase.invoice_number}" if hasattr(payment, 'purchase') and payment.purchase else "multiple invoices"),
                        amount=payment.amount_paid,
                        transaction_type='expense',
                        reference_number=getattr(payment, 'reference_number', f'SPMT-{payment.id}'),
                        supplier=payment.supplier
                    )
                    supplier_payment_count += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error importing supplier payment {payment.id}: {str(e)}'))
            self.stdout.write(self.style.SUCCESS(f'Imported {supplier_payment_count} supplier payments.'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error accessing supplier payments: {str(e)}'))

        # Final summary
        total_imported = delivery_count + concrete_count + payment_count + expense_count + purchase_count
        self.stdout.write(self.style.SUCCESS(f'=== COMPLETED: Imported {total_imported} total transactions into the ledger ===')) 