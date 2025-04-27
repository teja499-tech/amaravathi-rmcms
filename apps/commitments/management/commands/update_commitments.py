import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.commitments.models import OperationalCommitment
from apps.accounts.models import LedgerEntry
from decimal import Decimal

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates operational commitments, handling recurring payments and updating ledger entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-ledger',
            action='store_true',
            help='Create ledger entries for due commitments',
        )
        
        parser.add_argument(
            '--auto-update',
            action='store_true',
            help='Automatically update past due commitments to the next payment date',
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        update_ledger = options.get('update_ledger', False)
        auto_update = options.get('auto_update', False)
        
        # Get all active commitments
        active_commitments = OperationalCommitment.objects.filter(
            status='active',
            is_active=True
        )
        
        self.stdout.write(self.style.SUCCESS(f"Found {active_commitments.count()} active commitments"))
        
        # Process commitments
        updated_count = 0
        ledger_entries_created = 0
        
        for commitment in active_commitments:
            # Check if overdue
            if commitment.is_overdue:
                self.stdout.write(f"Commitment {commitment.title} is overdue (Due: {commitment.next_payment_date})")
                
                if auto_update and not commitment.current_payment_is_paid:
                    # Auto update to next payment date
                    old_date = commitment.next_payment_date
                    commitment.update_next_payment_date()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(
                        f"Updated commitment {commitment.title} from {old_date} to {commitment.next_payment_date}"
                    ))
            
            # Check if due today
            elif commitment.next_payment_date == today and not commitment.current_payment_is_paid:
                self.stdout.write(f"Commitment {commitment.title} is due today")
                
                # Create ledger entry if requested
                if update_ledger:
                    ledger_entry = LedgerEntry.objects.create(
                        date=today,
                        description=f"Due payment for {commitment.title} ({commitment.get_commitment_type_display()})",
                        amount=commitment.amount,
                        transaction_type='operational',
                        reference_number=commitment.reference_number,
                        commitment=commitment
                    )
                    ledger_entries_created += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Created ledger entry for {commitment.title} (₹{commitment.amount})"
                    ))
            
            # Check if due soon (within next 7 days)
            elif commitment.is_due_soon and not commitment.current_payment_is_paid:
                days_until_due = (commitment.next_payment_date - today).days
                self.stdout.write(f"Commitment {commitment.title} is due in {days_until_due} days")
        
        # Print summary
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_count} overdue commitments"))
        self.stdout.write(self.style.SUCCESS(f"Created {ledger_entries_created} ledger entries")) 