from django.core.management.base import BaseCommand
from employees.models import SalaryRecord
from django.db.models import Q


class Command(BaseCommand):
    help = 'Creates expense entries for all existing salary records that are paid but do not have associated expenses'
    
    def handle(self, *args, **options):
        # Get all salary records that are paid but don't have an expense_id
        records = SalaryRecord.objects.filter(
            Q(is_paid=True) & 
            (Q(expense_id__isnull=True) | Q(expense_id=0))
        )
        
        total_records = records.count()
        self.stdout.write(f"Found {total_records} salary records without expense entries")
        
        created_count = 0
        errors = []
        
        for record in records:
            try:
                expense = record.create_or_update_expense()
                if expense:
                    created_count += 1
                    self.stdout.write(f"Created expense for {record}")
            except Exception as e:
                errors.append((record.id, str(e)))
                self.stdout.write(self.style.ERROR(f"Error creating expense for record {record.id}: {e}"))
                
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} expense entries out of {total_records} records"))
        
        if errors:
            self.stdout.write(self.style.WARNING(f"Encountered {len(errors)} errors:"))
            for record_id, error in errors:
                self.stdout.write(f"  - Record {record_id}: {error}") 