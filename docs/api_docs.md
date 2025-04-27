# Amaravathi RMC Management System - API Documentation

This document describes the REST API provided by the Amaravathi RMC Management System for integration with other systems.

## API Overview

The Amaravathi RMC Management System provides a RESTful API that allows external applications to interact with the system's data and functionality. The API follows REST principles and uses JSON as the primary data exchange format.

## Base URL

All API endpoints are relative to the base URL:

```
https://your-domain.com/api/v1/
```

Replace `your-domain.com` with your actual domain where the system is hosted.

## Authentication

### Token Authentication

The API uses token-based authentication. To access protected endpoints, you need to include an authentication token in the request headers.

#### Obtaining a Token

To obtain an authentication token, send a POST request to the `/api/token/` endpoint with your credentials:

```http
POST /api/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

Response:

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

#### Using the Token

Include the token in the `Authorization` header of your requests:

```http
GET /api/v1/customers/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

### Permissions

API access is governed by the same role-based permissions as the web interface:

- **Admin**: Full access to all API endpoints
- **Accountant**: Access to financial data endpoints
- **Viewer**: Read-only access to permitted endpoints

## Response Format

All API responses are in JSON format with a consistent structure:

### Successful Responses

```json
{
  "status": "success",
  "data": {
    // Response data here
  }
}
```

### Error Responses

```json
{
  "status": "error",
  "error": {
    "code": "error_code",
    "message": "Human readable error message",
    "details": {} // Optional additional details
  }
}
```

### Common HTTP Status Codes

- `200 OK`: Request succeeded
- `201 Created`: Resource created successfully
- `204 No Content`: Request succeeded, no content returned
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Authenticated but not authorized
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Pagination

List endpoints return paginated results. Pagination information is included in the response:

```json
{
  "status": "success",
  "data": {
    "results": [
      // Array of items
    ],
    "count": 100,
    "next": "https://your-domain.com/api/v1/customers/?page=2",
    "previous": null
  }
}
```

You can specify the page size and page number using query parameters:

```
/api/v1/customers/?page=2&page_size=20
```

## API Endpoints

### Customers

#### List Customers

```http
GET /api/v1/customers/
```

Query parameters:
- `search`: Search term for customer name, email, or phone
- `page`: Page number for pagination
- `page_size`: Number of results per page
- `sort_by`: Field to sort by (e.g., `name`, `-created_at` for descending)

Response:

```json
{
  "status": "success",
  "data": {
    "results": [
      {
        "id": 1,
        "name": "ABC Construction",
        "contact_person": "John Doe",
        "email": "john@abcconstruction.com",
        "phone": "1234567890",
        "address": "123 Main St, City",
        "gst_number": "GSTIN12345",
        "credit_limit": 50000,
        "current_balance": 25000,
        "created_at": "2023-01-15T10:30:00Z",
        "updated_at": "2023-01-20T14:20:00Z"
      },
      // More customers...
    ],
    "count": 50,
    "next": "https://your-domain.com/api/v1/customers/?page=2",
    "previous": null
  }
}
```

#### Get Customer Details

```http
GET /api/v1/customers/{id}/
```

Response:

```json
{
  "status": "success",
  "data": {
    "id": 1,
    "name": "ABC Construction",
    "contact_person": "John Doe",
    "email": "john@abcconstruction.com",
    "phone": "1234567890",
    "address": "123 Main St, City",
    "gst_number": "GSTIN12345",
    "credit_limit": 50000,
    "current_balance": 25000,
    "delivery_locations": [
      {
        "id": 1,
        "name": "Main Site",
        "address": "456 Construction Ave, City",
        "coordinates": "12.9716,77.5946"
      }
    ],
    "recent_deliveries": [
      {
        "id": 101,
        "date": "2023-01-10T09:00:00Z",
        "status": "Delivered"
      }
    ],
    "created_at": "2023-01-15T10:30:00Z",
    "updated_at": "2023-01-20T14:20:00Z"
  }
}
```

#### Create Customer

```http
POST /api/v1/customers/
Content-Type: application/json

{
  "name": "XYZ Builders",
  "contact_person": "Jane Smith",
  "email": "jane@xyzbuilders.com",
  "phone": "9876543210",
  "address": "789 Second St, City",
  "gst_number": "GSTIN67890",
  "credit_limit": 75000
}
```

Response:

```json
{
  "status": "success",
  "data": {
    "id": 2,
    "name": "XYZ Builders",
    "contact_person": "Jane Smith",
    "email": "jane@xyzbuilders.com",
    "phone": "9876543210",
    "address": "789 Second St, City",
    "gst_number": "GSTIN67890",
    "credit_limit": 75000,
    "current_balance": 0,
    "created_at": "2023-02-01T11:20:00Z",
    "updated_at": "2023-02-01T11:20:00Z"
  }
}
```

#### Update Customer

```http
PUT /api/v1/customers/{id}/
Content-Type: application/json

{
  "name": "XYZ Builders & Co",
  "contact_person": "Jane Smith",
  "email": "jane@xyzbuilders.com",
  "phone": "9876543210",
  "address": "789 Second St, City",
  "gst_number": "GSTIN67890",
  "credit_limit": 100000
}
```

Response:

```json
{
  "status": "success",
  "data": {
    "id": 2,
    "name": "XYZ Builders & Co",
    "contact_person": "Jane Smith",
    "email": "jane@xyzbuilders.com",
    "phone": "9876543210",
    "address": "789 Second St, City",
    "gst_number": "GSTIN67890",
    "credit_limit": 100000,
    "current_balance": 0,
    "created_at": "2023-02-01T11:20:00Z",
    "updated_at": "2023-02-05T09:15:00Z"
  }
}
```

#### Delete Customer

```http
DELETE /api/v1/customers/{id}/
```

Response:

```json
{
  "status": "success",
  "data": null
}
```

### Deliveries

#### List Deliveries

```http
GET /api/v1/deliveries/
```

Query parameters:
- `customer_id`: Filter by customer ID
- `status`: Filter by status (`scheduled`, `in_transit`, `delivered`, `cancelled`)
- `date_from`: Filter by date range start (YYYY-MM-DD)
- `date_to`: Filter by date range end (YYYY-MM-DD)
- `page`: Page number for pagination
- `page_size`: Number of results per page

Response:

```json
{
  "status": "success",
  "data": {
    "results": [
      {
        "id": 1,
        "customer": {
          "id": 1,
          "name": "ABC Construction"
        },
        "delivery_date": "2023-02-10T08:00:00Z",
        "location": "Main Site, 456 Construction Ave, City",
        "status": "delivered",
        "total_quantity": 20,
        "total_amount": 60000,
        "created_at": "2023-02-08T10:30:00Z",
        "updated_at": "2023-02-10T16:20:00Z"
      },
      // More deliveries...
    ],
    "count": 30,
    "next": "https://your-domain.com/api/v1/deliveries/?page=2",
    "previous": null
  }
}
```

#### Get Delivery Details

```http
GET /api/v1/deliveries/{id}/
```

Response:

```json
{
  "status": "success",
  "data": {
    "id": 1,
    "customer": {
      "id": 1,
      "name": "ABC Construction",
      "phone": "1234567890"
    },
    "delivery_date": "2023-02-10T08:00:00Z",
    "location": "Main Site, 456 Construction Ave, City",
    "status": "delivered",
    "items": [
      {
        "material": {
          "id": 1,
          "name": "M25 Concrete"
        },
        "quantity": 15,
        "unit_price": 3000,
        "amount": 45000
      },
      {
        "material": {
          "id": 2,
          "name": "M30 Concrete"
        },
        "quantity": 5,
        "unit_price": 3200,
        "amount": 16000
      }
    ],
    "notes": "Delivered on time",
    "total_quantity": 20,
    "total_amount": 61000,
    "driver": {
      "id": 3,
      "name": "Ravi Kumar",
      "phone": "5555555555"
    },
    "vehicle": {
      "id": 2,
      "registration": "KA-01-AB-1234",
      "type": "Mixer Truck"
    },
    "created_at": "2023-02-08T10:30:00Z",
    "updated_at": "2023-02-10T16:20:00Z"
  }
}
```

#### Create Delivery

```http
POST /api/v1/deliveries/
Content-Type: application/json

{
  "customer_id": 1,
  "delivery_date": "2023-03-15T09:00:00Z",
  "location": "Main Site, 456 Construction Ave, City",
  "items": [
    {
      "material_id": 1,
      "quantity": 10,
      "unit_price": 3000
    },
    {
      "material_id": 2,
      "quantity": 8,
      "unit_price": 3200
    }
  ],
  "driver_id": 3,
  "vehicle_id": 2,
  "notes": "Customer requested early morning delivery"
}
```

Response:

```json
{
  "status": "success",
  "data": {
    "id": 2,
    "customer": {
      "id": 1,
      "name": "ABC Construction"
    },
    "delivery_date": "2023-03-15T09:00:00Z",
    "location": "Main Site, 456 Construction Ave, City",
    "status": "scheduled",
    "total_quantity": 18,
    "total_amount": 55600,
    "created_at": "2023-03-10T11:20:00Z",
    "updated_at": "2023-03-10T11:20:00Z"
  }
}
```

#### Update Delivery Status

```http
PATCH /api/v1/deliveries/{id}/status/
Content-Type: application/json

{
  "status": "in_transit",
  "notes": "Left the plant at 8:30 AM"
}
```

Response:

```json
{
  "status": "success",
  "data": {
    "id": 2,
    "status": "in_transit",
    "notes": "Left the plant at 8:30 AM",
    "updated_at": "2023-03-15T08:30:00Z"
  }
}
```

### Suppliers

#### List Suppliers

```http
GET /api/v1/suppliers/
```

#### Get Supplier Details

```http
GET /api/v1/suppliers/{id}/
```

#### Create Supplier

```http
POST /api/v1/suppliers/
```

#### Update Supplier

```http
PUT /api/v1/suppliers/{id}/
```

#### Delete Supplier

```http
DELETE /api/v1/suppliers/{id}/
```

### Materials

#### List Materials

```http
GET /api/v1/materials/
```

#### Get Material Details

```http
GET /api/v1/materials/{id}/
```

#### Create Material

```http
POST /api/v1/materials/
```

#### Update Material

```http
PUT /api/v1/materials/{id}/
```

#### Delete Material

```http
DELETE /api/v1/materials/{id}/
```

### Expenses

#### List Expenses

```http
GET /api/v1/expenses/
```

#### Get Expense Details

```http
GET /api/v1/expenses/{id}/
```

#### Create Expense

```http
POST /api/v1/expenses/
```

#### Update Expense

```http
PUT /api/v1/expenses/{id}/
```

#### Delete Expense

```http
DELETE /api/v1/expenses/{id}/
```

### Financial Transactions

#### List Transactions

```http
GET /api/v1/transactions/
```

#### Get Transaction Details

```http
GET /api/v1/transactions/{id}/
```

#### Create Transaction

```http
POST /api/v1/transactions/
```

#### Update Transaction

```http
PUT /api/v1/transactions/{id}/
```

### Employees

#### List Employees

```http
GET /api/v1/employees/
```

#### Get Employee Details

```http
GET /api/v1/employees/{id}/
```

#### Create Employee

```http
POST /api/v1/employees/
```

#### Update Employee

```http
PUT /api/v1/employees/{id}/
```

#### Delete Employee

```http
DELETE /api/v1/employees/{id}/
```

### Reports

#### Available Reports

```http
GET /api/v1/reports/
```

Response:

```json
{
  "status": "success",
  "data": {
    "available_reports": [
      {
        "id": "sales_summary",
        "name": "Sales Summary",
        "description": "Summary of sales by customer and period"
      },
      {
        "id": "expense_summary",
        "name": "Expense Summary",
        "description": "Summary of expenses by category and period"
      },
      // More reports...
    ]
  }
}
```

#### Generate Report

```http
POST /api/v1/reports/generate/
Content-Type: application/json

{
  "report_id": "sales_summary",
  "parameters": {
    "date_from": "2023-01-01",
    "date_to": "2023-03-31",
    "customer_id": null,  // Optional, null for all customers
    "group_by": "month"
  },
  "format": "json"  // One of: json, csv, pdf
}
```

Response:

```json
{
  "status": "success",
  "data": {
    "report": {
      "id": "sales_summary",
      "name": "Sales Summary",
      "parameters": {
        "date_from": "2023-01-01",
        "date_to": "2023-03-31",
        "group_by": "month"
      },
      "results": [
        {
          "period": "2023-01",
          "total_sales": 250000,
          "total_deliveries": 15
        },
        {
          "period": "2023-02",
          "total_sales": 320000,
          "total_deliveries": 18
        },
        {
          "period": "2023-03",
          "total_sales": 280000,
          "total_deliveries": 16
        }
      ],
      "summary": {
        "total_sales": 850000,
        "total_deliveries": 49,
        "average_per_month": 283333.33
      }
    }
  }
}
```

## Webhooks

The system can send webhook notifications for certain events. Webhooks must be configured by an administrator.

### Available Events

- `customer.created`
- `customer.updated`
- `delivery.scheduled`
- `delivery.status_changed`
- `delivery.completed`
- `invoice.created`
- `payment.received`

### Webhook Payload Format

```json
{
  "event": "delivery.status_changed",
  "timestamp": "2023-03-15T08:30:00Z",
  "data": {
    "delivery_id": 2,
    "previous_status": "scheduled",
    "new_status": "in_transit",
    "customer_id": 1,
    "notes": "Left the plant at 8:30 AM"
  }
}
```

## Rate Limiting

The API implements rate limiting to protect against abuse. Rate limits are specified in the response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1677766800
```

If you exceed the rate limit, you'll receive a `429 Too Many Requests` response.

## Error Codes

Common error codes returned by the API:

- `authentication_failed`: Invalid or missing authentication credentials
- `permission_denied`: Authenticated but not authorized for this action
- `not_found`: Requested resource not found
- `validation_error`: Request data failed validation
- `resource_exists`: Attempted to create a resource that already exists
- `rate_limit_exceeded`: Too many requests in a given time period
- `server_error`: Internal server error

## API Versioning

The API uses URL versioning (e.g., `/api/v1/`). When breaking changes are introduced, a new version will be released while maintaining backward compatibility for a reasonable period.

## SDK and Code Examples

### Python Client

```python
import requests

class AmaravathiClient:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        }
    
    def get_customers(self, page=1, page_size=20):
        url = f"{self.base_url}/api/v1/customers/"
        params = {'page': page, 'page_size': page_size}
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    def create_delivery(self, delivery_data):
        url = f"{self.base_url}/api/v1/deliveries/"
        response = requests.post(url, headers=self.headers, json=delivery_data)
        return response.json()

# Usage example
client = AmaravathiClient('https://your-domain.com', 'your_token_here')
customers = client.get_customers()
print(customers)
```

### JavaScript Client

```javascript
class AmaravathiClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.headers = {
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json'
    };
  }
  
  async getCustomers(page = 1, pageSize = 20) {
    const url = `${this.baseUrl}/api/v1/customers/?page=${page}&page_size=${pageSize}`;
    const response = await fetch(url, { headers: this.headers });
    return response.json();
  }
  
  async createDelivery(deliveryData) {
    const url = `${this.baseUrl}/api/v1/deliveries/`;
    const response = await fetch(url, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(deliveryData)
    });
    return response.json();
  }
}

// Usage example
const client = new AmaravathiClient('https://your-domain.com', 'your_token_here');
client.getCustomers().then(data => console.log(data));
```

## Support and Feedback

For API support or feedback, please contact api-support@amaravathirmc.com or open an issue on our [GitHub repository](https://github.com/teja499-tech/amaravathi-rmcms/issues). 