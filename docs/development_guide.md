# Amaravathi RMC Management System - Developer Guide

This guide is intended for developers who want to understand, modify, or contribute to the Amaravathi RMC Management System codebase.

## Table of Contents
1. [Project Architecture](#project-architecture)
2. [Development Environment Setup](#development-environment-setup)
3. [Code Organization](#code-organization)
4. [Database Schema](#database-schema)
5. [Key Components](#key-components)
6. [Adding New Features](#adding-new-features)
7. [Testing](#testing)
8. [Coding Standards](#coding-standards)
9. [Contribution Guidelines](#contribution-guidelines)
10. [API Reference](#api-reference)

## Project Architecture

The Amaravathi RMC Management System is built using the Django web framework, following the Model-View-Template (MVT) architectural pattern:

- **Models**: Define the data structure and database schema
- **Views**: Handle business logic and HTTP requests
- **Templates**: Render the UI for the end user

### System Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Client Browser │────▶│  Django Server  │────▶│    Database     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │   ▲
                               │   │
                               ▼   │
                        ┌─────────────────┐
                        │                 │
                        │  Static Files   │
                        │  Media Storage  │
                        │                 │
                        └─────────────────┘
```

### Key Technologies

- **Backend**: Django 5.x, Python 3.9+
- **Frontend**: Bootstrap 5, JavaScript
- **Database**: PostgreSQL (production), SQLite (development)
- **File Storage**: Local file system or Supabase (configurable)
- **Deployment**: Render, or any WSGI-compatible server

## Development Environment Setup

### Prerequisites

Ensure you have the following installed:
- Python 3.9+
- Git
- pip
- virtualenv or venv

### Setup Process

1. Clone the repository:
   ```bash
   git clone https://github.com/teja499-tech/amaravathi-rmcms.git
   cd AmaravathiRMCMS
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. Set up environment variables by creating a `.env` file:
   ```
   DEBUG=True
   SECRET_KEY=development_secret_key
   ALLOWED_HOSTS=localhost,127.0.0.1
   DATABASE_URL=sqlite:///db.sqlite3
   ```

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Code Organization

The project follows standard Django project structure with some customizations:

```
AmaravathiRMCMS/
├── amaravathi_rmbmp/      # Main Django project folder
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py        # Project settings
│   ├── urls.py            # Main URL declarations
│   └── wsgi.py
├── apps/                  # Custom Django apps
│   ├── accounts/          # User authentication and management
│   ├── customers/         # Customer management
│   ├── deliveries/        # Delivery tracking
│   ├── expenses/          # Expense tracking
│   ├── finance/           # Financial management
│   ├── materials/         # Material inventory
│   ├── reports/           # Reporting functionality
│   └── suppliers/         # Supplier management
├── docs/                  # Documentation
├── media/                 # User-uploaded files
├── static/                # Static files (CSS, JS, images)
├── staticfiles/           # Collected static files for production
├── templates/             # HTML templates
├── deployment/            # Deployment configurations
├── manage.py              # Django management script
├── requirements.txt       # Production dependencies
└── requirements-dev.txt   # Development dependencies
```

## Database Schema

The system uses a relational database with the following key models:

### Core Models

- **User**: Extended Django User for authentication
- **Customer**: Stores customer information
- **Supplier**: Stores supplier information
- **Material**: Defines materials used in concrete mixes
- **Delivery**: Records concrete deliveries to customers
- **Purchase**: Tracks materials purchased from suppliers
- **Expense**: Records business expenses
- **Transaction**: Financial transactions
- **Employee**: Employee information
- **Salary**: Employee salary records
- **BankAccount**: Company bank account details

### Entity Relationship Diagram

For a visual representation of the database schema, run:

```bash
python manage.py graph_models -a -g -o docs/erd.png
```

Note: This requires `django-extensions` and `pygraphviz` to be installed.

## Key Components

### Authentication System

The authentication system extends Django's built-in authentication with role-based permissions:

- **Admin**: Full system access
- **Accountant**: Financial operations access
- **Viewer**: Read-only access to designated areas

Implementation is in the `apps/accounts` module.

### Financial Management

Financial components include:

- Transaction tracking
- Ledger management
- Bank account reconciliation
- Financial reporting
- Expense categorization

Implementation is in the `apps/finance` module.

### Customer and Delivery Management

Components for managing customers and deliveries:

- Customer profiles
- Delivery scheduling
- Delivery status tracking
- Material quantity calculations
- Pricing and invoicing

Implementation spans `apps/customers` and `apps/deliveries` modules.

## Adding New Features

### General Process

1. **Plan the feature**:
   - Identify requirements
   - Consider database impact
   - Plan UI changes

2. **Create or modify models**:
   - Add models in the appropriate app
   - Create migrations
   - Update related models if needed

3. **Implement views**:
   - Create view functions or classes
   - Add URL patterns
   - Implement business logic

4. **Create templates**:
   - Create HTML templates
   - Add CSS/JS as needed
   - Ensure mobile responsiveness

5. **Add tests**:
   - Write unit tests for models
   - Write tests for views
   - Test form validation

6. **Document your changes**:
   - Update docstrings
   - Update user documentation if needed
   - Add comments for complex logic

### Example: Adding a New Report Type

```python
# In apps/reports/models.py
class CustomReport(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    query = models.TextField()
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

# In apps/reports/views.py
class CustomReportView(LoginRequiredMixin, View):
    def get(self, request, report_id):
        report = get_object_or_404(CustomReport, id=report_id)
        # Execute report query
        # Process results
        return render(request, 'reports/custom_report.html', {'report': report, 'results': results})
```

## Testing

### Running Tests

The project uses Django's built-in testing framework:

```bash
# Run all tests
python manage.py test

# Run tests for a specific app
python manage.py test apps.customers

# Run a specific test case
python manage.py test apps.customers.tests.test_models.CustomerModelTest
```

### Writing Tests

Each app should have a `tests` directory with test modules:

```
apps/customers/tests/
├── __init__.py
├── test_forms.py
├── test_models.py
└── test_views.py
```

Example test case:

```python
from django.test import TestCase
from apps.customers.models import Customer

class CustomerModelTest(TestCase):
    def setUp(self):
        Customer.objects.create(
            name="Test Customer",
            phone="1234567890",
            email="test@example.com"
        )
        
    def test_customer_str(self):
        customer = Customer.objects.get(name="Test Customer")
        self.assertEqual(str(customer), "Test Customer")
        
    def test_customer_contact_info(self):
        customer = Customer.objects.get(name="Test Customer")
        self.assertEqual(customer.phone, "1234567890")
        self.assertEqual(customer.email, "test@example.com")
```

## Coding Standards

The project follows PEP 8 Python style guidelines with some customizations:

### Python Code Style

- Use 4 spaces for indentation (no tabs)
- Maximum line length of 100 characters
- Use docstrings for all classes and functions
- Use type hints for function parameters and return values

### Django Best Practices

- Use class-based views when appropriate
- Follow Django's model naming conventions
- Use Django's ORM rather than raw SQL when possible
- Keep views thin, put business logic in models or service classes
- Use forms for data validation

### JavaScript and CSS

- Follow the [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use ES6 syntax where browser support allows
- Prefix CSS classes with the module name to avoid conflicts

### Code Quality Tools

The project uses several tools to maintain code quality:

```bash
# Run flake8 for Python linting
flake8

# Run black for Python code formatting
black .

# Run eslint for JavaScript linting
eslint static/js/

# Run tests with coverage
coverage run --source='.' manage.py test
coverage report
```

## Contribution Guidelines

### Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature-name`)
3. Make your changes
4. Run tests to ensure they pass
5. Run linters to ensure code quality
6. Commit your changes (`git commit -m 'Add some feature'`)
7. Push to your branch (`git push origin feature-name`)
8. Create a Pull Request

### Commit Message Guidelines

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
feat: add customer search feature
fix: correct calculation in invoice total
docs: update installation instructions
style: format code according to guidelines
refactor: simplify delivery status tracking
test: add tests for expense categorization
chore: update dependencies
```

### Code Review Process

- All code must be reviewed by at least one other developer
- Automated tests must pass before merging
- Code quality checks must pass before merging
- Documentation must be updated for new features

## API Reference

The system provides a REST API for integration with other systems.

### Authentication

API endpoints use token-based authentication:

```bash
# Request a token
curl -X POST https://example.com/api/token/ -d "username=user&password=pass"

# Use the token
curl -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" https://example.com/api/customers/
```

### Available Endpoints

Base URL: `https://example.com/api/v1/`

#### Customers API

- `GET /customers/` - List all customers
- `POST /customers/` - Create a new customer
- `GET /customers/{id}/` - Retrieve a specific customer
- `PUT /customers/{id}/` - Update a customer
- `DELETE /customers/{id}/` - Delete a customer

#### Deliveries API

- `GET /deliveries/` - List all deliveries
- `POST /deliveries/` - Create a new delivery
- `GET /deliveries/{id}/` - Retrieve a specific delivery
- `PUT /deliveries/{id}/` - Update a delivery
- `PATCH /deliveries/{id}/status/` - Update delivery status

For complete API documentation, refer to the [API Documentation](api_docs.md).

## Troubleshooting for Developers

### Common Development Issues

#### Migration Issues
```bash
# Reset migrations for an app
python manage.py migrate app_name zero
# Remove migration files and recreate
rm apps/app_name/migrations/0*
python manage.py makemigrations app_name
python manage.py migrate app_name
```

#### Static Files Not Loading
```bash
# Collect static files
python manage.py collectstatic --noinput
# Check static files settings in settings.py
```

#### Database Connectivity Issues
```bash
# Check database connection
python manage.py dbshell
# Verify settings in .env file
```

### Development Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Bootstrap Documentation](https://getbootstrap.com/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Further Reading

- [Architecture Overview](architecture.md)
- [API Documentation](api_docs.md)
- [User Guide](user_guide.md) (for understanding user workflows)
- [Installation Guide](installation_guide.md) (for deployment details)

## Support and Resources

- GitHub Repository: [AmaravathiRMCMS](https://github.com/teja499-tech/amaravathi-rmcms)
- Issue Tracker: [GitHub Issues](https://github.com/teja499-tech/amaravathi-rmcms/issues)
- Documentation: See the `docs` directory for additional guides 