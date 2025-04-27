# Operational Commitments Management

## Overview

The Operational Commitments module helps track recurring financial obligations such as EMIs, leases, insurance premiums, and maintenance contracts. It provides tools for managing payment schedules, recording payments, and generating insights on upcoming financial obligations.

## Features

- **Recurring Commitment Tracking**: Define commitments with various frequencies (monthly, quarterly, etc.)
- **Payment Management**: Record payments for commitments with details like payment mode and reference numbers
- **Document Storage**: Upload and manage contracts and payment receipts using Supabase storage
- **Automatic Due Date Management**: System automatically calculates next payment dates
- **Financial Integration**: Payments are automatically reflected in the unified ledger
- **Dashboard Alerts**: Due and upcoming payments appear in dashboard alerts

## Models

### CommitmentCategory

Categories for classifying different types of operational commitments.

- **name**: Name of the category
- **description**: Optional detailed description

### OperationalCommitment

Main model for tracking recurring financial commitments.

- **title**: Title/name of the commitment
- **commitment_type**: Type of commitment (EMI, Lease, Insurance, etc.)
- **category**: Associated category
- **description**: Detailed description
- **amount**: Payment amount
- **reference_number**: Contract/Policy number
- **start_date**: When the commitment begins
- **end_date**: Optional end date (for finite commitments)
- **payment_frequency**: How often payments are due (monthly, quarterly, etc.)
- **payment_day**: Day of the month when payment is due
- **next_payment_date**: Next upcoming payment date
- **current_payment_is_paid**: Whether the current due payment has been made
- **status**: Active, Completed, or Terminated
- **is_active**: Quick toggle for active/inactive status
- **payee_name**: Institution/company to pay
- **contact_person**: Optional contact person
- **contact_phone**: Optional contact phone
- **contact_email**: Optional contact email
- **contract_document_url**: Link to stored contract document
- **notes**: Additional notes/terms

### CommitmentPayment

Tracks individual payments for commitments.

- **commitment**: Associated commitment
- **amount_paid**: Payment amount
- **payment_date**: Date of payment
- **payment_mode**: Mode of payment (Cash, Cheque, etc.)
- **reference_number**: Transaction/Cheque number
- **remarks**: Optional notes about the payment
- **receipt_number**: Optional receipt identification
- **receipt_url**: Link to stored receipt

## Automation

The system includes automated management via a Django management command:

```bash
# Check for commitments due today and create ledger entries
python manage.py update_commitments --update-ledger

# Automatically update overdue commitments to their next payment date
python manage.py update_commitments --auto-update
```

Recommended setup is to run this command as a daily cron job to ensure timely updates and reminders.

## Example Usage

### Creating a New Commitment

```python
# EMI for a Mixer Truck
commitment = OperationalCommitment.objects.create(
    title="Mixer Truck EMI",
    commitment_type="emi",
    amount=40000.00,
    start_date=date(2023, 1, 5),  # First payment on Jan 5, 2023
    payment_frequency="monthly",
    payment_day=5,  # Due on 5th of each month
    next_payment_date=date(2023, 1, 5),
    payee_name="HDFC Bank",
    reference_number="LOAN12345678",
    description="EMI for Mixer Truck purchased on Dec 2022",
)
```

### Recording a Payment

```python
# Record a payment for the commitment
payment = CommitmentPayment.objects.create(
    commitment=commitment,
    amount_paid=40000.00,
    payment_date=date(2023, 1, 5),
    payment_mode="BANK",
    reference_number="TXN987654321",
    remarks="January 2023 EMI payment"
)
```

## Dashboard Integration

The system automatically integrates commitments with:

- **Smart Alerts** on the dashboard showing commitments due today
- **Cash flow forecasts** for financial planning
- **Unified ledger** capturing all commitment payments

## Document Management

Both contracts and payment receipts can be uploaded, stored, and retrieved using Supabase storage integration. Use the following methods:

```python
# Upload contract document
commitment.upload_contract_document(file_object)

# Upload payment receipt
payment.upload_receipt(file_object)

# Retrieve document URLs
contract_url = commitment.get_contract_document_url()
receipt_url = payment.get_receipt_url()
``` 